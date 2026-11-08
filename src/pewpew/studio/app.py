"""The studio FastAPI app: HTTP API, websocket sessions, and the built SPA.

`create_app` takes its collaborators as arguments so tests can inject fakes.
The defaults are the real rig: `pewpew.rig.load_catalog` and `compile_rig`
for arrangements, `pewpew.rig.geometry` for the GLBs, and the example looks
of `examples/` (`PEWPEW_STUDIO_EXAMPLES` names another folder), which
`GET /api/looks` lists and every session starts in one of (`START`). The geometry module
is imported on first use. While it or manifold3d is missing, catalog entries
carry no assembly URL and the GLB route answers 503.

The websocket speaks the engine's wire (`pewpew.sinks.preview`): the
`hello` on connect, a `layout` after each bind, the per-frame states with
the binary frames, `ack` and `refused`. The `refused` message names the
refused control, as the preview does, and the studio adds three controls of
its own: `session` (the session is refused or ends: the server is full, the
visitor was evicted, or it sat paused too long), `message` (a message the
socket does not accept: binary, or over the size limit) and `bind` (the
arrangement did not compile, with `issues` then, or no look runs on it).

Routes are plain `def` where they block, which FastAPI runs in its threadpool.
Production runs `python -m pewpew studio`, which sets uvicorn's websocket
message cap and shutdown bound (docs/studio/contracts.md).
"""

from __future__ import annotations

import asyncio
import dataclasses
import importlib
import json
import logging
import os
import threading
import time
from collections.abc import Callable, Coroutine
from contextlib import asynccontextmanager, suppress
from pathlib import Path
from typing import Annotated, Any, Literal

from fastapi import Body, FastAPI, HTTPException, Request, Response, WebSocket
from fastapi.exception_handlers import http_exception_handler
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from fastapi.routing import APIRoute
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.requests import HTTPConnection

from pewpew.jsonfile import TooDeep, loads
from pewpew.rig import Catalog, CompiledRig, compile_rig, load_arrangement, load_catalog
from pewpew.sinks.preview import answer_request, refusal, unanswered
from pewpew.studio.limits import (
    Admission,
    BodyLimit,
    Limits,
    RateLimiter,
    address_key,
    client_ip,
    declared_fixtures,
)
from pewpew.studio.session import START, Session, SessionRegistry, example_looks, start_looks
from pewpew.studio.store import ID_PATTERN, Store, arrangement_id, canonical_json, store_from_env
from pewpew.studio.transport import Outbox

logger = logging.getLogger(__name__)

IMMUTABLE = "public, max-age=31536000, immutable"
IDLE_TIMEOUT_S = 600.0  # no inbound message for this long pauses a session
PAUSED_TIMEOUT_S = 1800.0  # paused for this long closes it
EVICTED = "closed after a long pause to make room for another visitor; reload to continue"
PAUSED = "the session is paused; send resume first"
_WEB_DIST = Path(__file__).resolve().parents[3] / "web" / "dist" / "studio"
_EXAMPLES = Path(__file__).resolve().parents[3] / "examples"

Builders = tuple[Callable[[str, Any], bytes], Callable[[str, Any], str]]


class SavedArrangement(BaseModel):
    id: str


class IssueModel(BaseModel):
    level: Literal["error", "violation", "warning"]
    code: str
    message: str
    ref: str | None = None


class IssueList(BaseModel):
    issues: list[IssueModel]


ISSUES_422: dict[int | str, dict[str, Any]] = {422: {"model": IssueList, "description": "Unprocessable Content"}}


class CompileFailure(Exception):
    """An arrangement that cannot be compiled, or that breaks a limit."""

    def __init__(self, issues: list[dict]) -> None:
        super().__init__(issues[0]["message"] if issues else "invalid arrangement")
        self.issues = issues


class Busy(Exception):
    """A compile refused by a rate or concurrency limit."""

    def __init__(self, status: int, reason: str, retry_after: float) -> None:
        super().__init__(reason)
        self.status = status
        self.retry_after = retry_after

    def http(self) -> HTTPException:
        return HTTPException(self.status, str(self), headers={"Retry-After": str(int(self.retry_after) + 1)})


def _issue(obj: Any) -> dict:
    if isinstance(obj, dict):
        return obj
    if hasattr(obj, "model_dump"):
        return obj.model_dump(mode="json")
    if dataclasses.is_dataclass(obj):
        return dataclasses.asdict(obj)  # type: ignore[arg-type]
    return {k: getattr(obj, k, None) for k in ("level", "code", "message", "ref")}


def _error(code: str, message: str) -> dict:
    return {"level": "error", "code": code, "message": message, "ref": None}


def _unreadable(exc: BaseException) -> str:
    if isinstance(exc, OverflowError):
        return "a number in the JSON is too large"
    return str(exc)[:300] or "invalid JSON"


class _BodyRequest(Request):
    """A request that parses its JSON body with `pewpew.jsonfile.loads`, so
    nesting past `MAX_DEPTH` is refused on every platform."""

    async def json(self) -> Any:
        if not hasattr(self, "_json"):
            self._json = loads(await self.body())
        return self._json


class _BodyRoute(APIRoute):
    """A route that gives its endpoint a `_BodyRequest`. FastAPI wraps an
    error of the body parser in a 400, which `http_error` answers."""

    def get_route_handler(self) -> Callable[[Request], Coroutine[Any, Any, Response]]:
        handler = super().get_route_handler()

        async def route_handler(request: Request) -> Response:
            return await handler(_BodyRequest(request.scope, request.receive))

        return route_handler


def _issues_response(issues: list[dict]) -> JSONResponse:
    return JSONResponse({"issues": issues}, status_code=422)


def _address(conn: HTTPConnection) -> str:
    return address_key(client_ip(conn.headers, conn.client.host if conn.client else None))


def _default_compile(arrangement: dict, catalog: Catalog) -> CompiledRig:
    return compile_rig(load_arrangement(arrangement), catalog)


def _geometry() -> Builders | None:
    """`pewpew.rig.geometry`'s builders, or None while that module is missing."""
    try:
        geometry = importlib.import_module("pewpew.rig.geometry")
    except ImportError as exc:
        logger.warning("assembly geometry is not available: %s", exc)
        return None
    return geometry.build_glb, geometry.assembly_digest


@dataclasses.dataclass(frozen=True)
class _CatalogView:
    """`GET /api/catalog` as sent, and every assembly's GLB by digest.

    Built once per catalog, and every GLB is built here, so the GLB route
    only looks one up. `geometry` is False when there are no builders.
    """

    body: bytes
    assemblies: dict[str, bytes]  # assembly digest -> GLB
    geometry: bool

    @classmethod
    def of(cls, catalog: Any, builders: Builders | None) -> _CatalogView:
        try:
            return cls._build(catalog, builders)
        except ImportError as exc:  # the geometry module imports without manifold3d; building needs it
            logger.warning("assembly geometry is not available: %s", exc)
            return cls._build(catalog, None)

    @classmethod
    def _build(cls, catalog: Any, builders: Builders | None) -> _CatalogView:
        body = dict(catalog.to_json())
        assemblies: dict[str, bytes] = {}
        for key in ("fixture_types", "attachment_types"):
            entries = []
            for entry in body.get(key, []):
                built = _assembly(entry["id"], catalog, builders) if builders else None
                digest = None
                if built is not None:
                    digest, assemblies[digest] = built
                url = None if digest is None else f"/api/assembly/{digest}.glb"
                entries.append({**entry, "digest": digest, "assembly_url": url})
            body[key] = entries
        return cls(json.dumps(body).encode(), assemblies, builders is not None)


def _assembly(type_id: str, catalog: Any, builders: Builders) -> tuple[str, bytes] | None:
    """The digest and GLB of one type, or None when its data cannot be meshed."""
    build_glb, assembly_digest = builders
    try:
        return assembly_digest(type_id, catalog), build_glb(type_id, catalog)
    except (KeyError, ValueError):  # geometry.GeometryError is a ValueError
        logger.warning("no assembly for %s", type_id, exc_info=True)
        return None


def create_app(
    *,
    catalog: Any = None,
    compile: Callable[[dict, Any], Any] | None = None,
    store: Store | None = None,
    build_glb: Callable[[str, Any], bytes] | None = None,
    assembly_digest: Callable[[str, Any], str] | None = None,
    web_dist: Path | None = None,
    examples: Path | None = None,
    limits: Limits | None = None,
    fps: float = 30.0,
    idle_timeout_s: float = IDLE_TIMEOUT_S,
    paused_timeout_s: float = PAUSED_TIMEOUT_S,
) -> FastAPI:
    limits = limits or Limits()
    admission = Admission(limits)
    save_limiter = RateLimiter(limits.saves_per_minute)
    compile_limiter = RateLimiter(limits.compiles_per_minute, limits.compile_burst)
    compile_slots = threading.BoundedSemaphore(limits.max_concurrent_compiles)
    registry = SessionRegistry()
    compile_fn = compile or _default_compile
    view: _CatalogView | None = None
    view_lock = threading.Lock()
    if examples is None:
        examples = Path(os.environ.get("PEWPEW_STUDIO_EXAMPLES", _EXAMPLES))
    looks = example_looks(examples)
    if START not in looks:
        raise RuntimeError(f"no example look {START!r}: every session starts in it")
    looks_body = json.dumps(looks).encode()
    starts = start_looks(looks)

    def catalog_of() -> Any:
        nonlocal catalog
        if catalog is None:
            catalog = load_catalog()
        return catalog

    def catalog_view() -> _CatalogView:
        nonlocal view
        with view_lock:
            if view is None:
                builders = (build_glb, assembly_digest) if build_glb and assembly_digest else _geometry()
                view = _CatalogView.of(catalog_of(), builders)
            return view

    def compile_checked(arrangement: Any, key: str) -> Any:
        """Compile `arrangement` for the address `key`, under the limits.

        Blocks; call it off the event loop. Raises CompileFailure or Busy.
        Only a dict reaches the compiler, so a client string is never read as
        a file path.
        """
        if not isinstance(arrangement, dict):
            raise CompileFailure([_error("invalid", "an arrangement is a JSON object")])
        if declared_fixtures(arrangement, limits.max_fixtures) > limits.max_fixtures:
            raise CompileFailure(
                [_error("too_many_fixtures", f"limit of {limits.max_fixtures} fixtures per arrangement")]
            )
        wait = compile_limiter.allow(key)
        if wait is not None:
            raise Busy(429, f"limit of {limits.compiles_per_minute} compiles per minute per address", wait)
        if not compile_slots.acquire(timeout=limits.compile_wait_s):
            raise Busy(503, "the server is busy compiling; try again shortly", 1.0)
        try:
            rig = compile_fn(arrangement, catalog_of())
        except (ValueError, OverflowError) as exc:  # RigError and ValidationError are ValueErrors
            issues = [_issue(i) for i in getattr(exc, "issues", ())]
            raise CompileFailure(issues or [_error("invalid", _unreadable(exc))]) from None
        finally:
            compile_slots.release()
        if rig.n > limits.max_pixels:
            raise CompileFailure([_error("too_many_pixels", f"limit of {limits.max_pixels} pixels per arrangement")])
        return rig

    def bind_args(arrangement: Any, key: str) -> dict[str, Any]:
        """Compile for a websocket bind and return `Session.bind`'s arguments.
        Blocks; call it off the event loop."""
        rig = compile_checked(arrangement, key)
        limiter = getattr(rig, "limiter", None)
        return {
            "mapping": rig.mapping,
            # A rig without a limiter streams uncapped, with no power readings.
            "limiter": None if limiter is None else limiter(),
        }

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        nonlocal store
        if store is None:
            store = store_from_env(dict(os.environ))
        await asyncio.to_thread(store.init)
        try:
            yield
        finally:
            # uvicorn has already closed the sockets; stop what is left.
            await asyncio.to_thread(registry.close_all)
            await asyncio.to_thread(store.close)

    app = FastAPI(
        title="pewpew studio",
        lifespan=lifespan,
        docs_url="/api/docs",
        openapi_url="/api/openapi.json",
        generate_unique_id_function=lambda route: route.name,
    )
    app.router.route_class = _BodyRoute
    app.add_middleware(BodyLimit, limit=limits.max_body_bytes)
    app.state.sessions = registry
    app.state.admission = admission

    @app.exception_handler(RequestValidationError)
    async def request_issues(_request: Request, exc: RequestValidationError) -> JSONResponse:
        return _issues_response(
            [
                {"level": "error", "code": e["type"], "message": e["msg"], "ref": ".".join(map(str, e["loc"])) or None}
                for e in exc.errors()
            ]
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_error(request: Request, exc: StarletteHTTPException) -> Response:
        # FastAPI answers 400 to a body its JSON parser gave up on, such as one nested too deeply.
        if exc.status_code == 400 and isinstance(exc.__cause__, ValueError):
            code = "too_deep" if isinstance(exc.__cause__, TooDeep) else "json_invalid"
            return _issues_response([_error(code, _unreadable(exc.__cause__))])
        return await http_exception_handler(request, exc)

    # -- HTTP ------------------------------------------------------------------

    @app.get("/health/live", include_in_schema=False)
    def health_live() -> dict[str, bool]:
        return {"ok": True}

    @app.get("/api/catalog", response_model=dict[str, Any])
    def get_catalog() -> Response:
        return Response(catalog_view().body, media_type="application/json")

    @app.post("/api/compile", response_model=dict[str, Any], responses=ISSUES_422)
    def compile_arrangement(request: Request, arrangement: Annotated[dict[str, Any], Body()]) -> Response:
        try:
            rig = compile_checked(arrangement, _address(request))
        except CompileFailure as exc:
            return _issues_response(exc.issues)
        except Busy as exc:
            raise exc.http() from None
        return JSONResponse(rig.to_json())  # serialized here, in the threadpool

    @app.get("/api/assembly/{digest}.glb", response_class=Response, responses=ISSUES_422)
    def get_assembly(digest: str) -> Response:
        current = catalog_view()
        if not current.geometry:
            raise HTTPException(503, "assembly geometry is not available on this server yet")
        glb = current.assemblies.get(digest)
        if glb is None:
            raise HTTPException(404, "no such assembly")
        return Response(glb, media_type="model/gltf-binary", headers={"Cache-Control": IMMUTABLE})

    @app.post("/api/arrangements", responses=ISSUES_422)
    def save_arrangement(request: Request, arrangement: Annotated[dict[str, Any], Body()]) -> SavedArrangement:
        key = _address(request)
        wait = save_limiter.allow(key)
        if wait is not None:
            raise HTTPException(
                429,
                f"limit of {limits.saves_per_minute} saves per minute per address",
                headers={"Retry-After": str(int(wait) + 1)},
            )
        try:
            compile_checked(arrangement, key)
            text = canonical_json(arrangement)
        except CompileFailure as exc:
            return _issues_response(exc.issues)  # type: ignore[return-value]
        except Busy as exc:
            raise exc.http() from None
        except ValueError:
            return _issues_response(  # type: ignore[return-value]
                [_error("invalid", "arrangement is not plain JSON (NaN or infinity)")]
            )
        id_ = arrangement_id(text)
        store.put(id_, text)  # type: ignore[union-attr]
        return SavedArrangement(id=id_)

    @app.get("/api/arrangements/{id}", responses=ISSUES_422)
    def get_arrangement(id: str) -> Response:
        text = store.get(id) if ID_PATTERN.match(id) else None  # type: ignore[union-attr]
        if text is None:
            raise HTTPException(404, "no such arrangement")
        return Response(text, media_type="application/json", headers={"Cache-Control": IMMUTABLE})

    @app.get("/api/looks", response_model=dict[str, dict[str, Any]])
    def list_looks() -> Response:
        return Response(looks_body, media_type="application/json")

    # -- websocket -------------------------------------------------------------

    @app.websocket("/ws/session")
    async def ws_session(ws: WebSocket) -> None:
        key = _address(ws)
        await ws.accept()
        ticket = admission.acquire(key, registry.evict_longest_paused)
        if isinstance(ticket, str):
            await ws.send_text(json.dumps(refusal("session", ticket)))
            await ws.close(code=1013)
            return
        session: Session | None = None
        pump: asyncio.Future | None = None
        try:
            outbox = Outbox(asyncio.get_running_loop())
            session = Session(outbox, starts, fps=fps, max_pixels=limits.max_pixels)
            registry.add(session, ticket, lambda: outbox.close_with(refusal("session", EVICTED)))
            outbox.control(session.hello())
            session.start()
            pump = asyncio.ensure_future(outbox.pump(ws))
            visitor = _Visitor(
                ws,
                session,
                outbox,
                pump,
                lambda arrangement: bind_args(arrangement, key),
                limits.max_body_bytes,
                idle_timeout_s,
                paused_timeout_s,
            )
            await visitor.serve()
        except Exception:
            logger.debug("session socket ended", exc_info=True)
        finally:
            if pump is not None:
                pump.cancel()
            if session is not None:
                session.close()
                registry.discard(session)
            admission.release(ticket)
            with suppress(Exception):  # already closed
                await ws.close()

    _mount_spa(app, web_dist if web_dist is not None else Path(os.environ.get("PEWPEW_STUDIO_WEB_DIST", _WEB_DIST)))
    return app


@dataclasses.dataclass
class _Visitor:
    """One websocket: reads the client's messages and hands them to its session."""

    ws: WebSocket
    session: Session
    outbox: Outbox
    pump: asyncio.Future
    bind_args: Callable[[Any], dict[str, Any]]  # blocks; runs in a worker thread
    max_bytes: int
    idle_timeout_s: float
    paused_timeout_s: float

    async def serve(self) -> None:
        """Return when the client leaves, the pump ends, or a limit closes the socket."""
        idle_paused = False
        recv: asyncio.Future | None = None
        try:
            while True:
                if recv is None:
                    recv = asyncio.ensure_future(self.ws.receive())
                since = self.session.paused_since
                timeout = self.idle_timeout_s if since is None else since + self.paused_timeout_s - time.monotonic()
                done, _ = await asyncio.wait(
                    {recv, self.pump}, timeout=max(0.0, timeout), return_when=asyncio.FIRST_COMPLETED
                )
                if self.pump in done:
                    return
                if recv not in done:
                    if since is not None:
                        minutes = f"{self.paused_timeout_s / 60:g}"
                        await self._end(
                            refusal("session", f"closed after {minutes} minutes paused; reload to continue")
                        )
                        return
                    self.session.pause()
                    idle_paused = True
                    continue
                event, recv = recv.result(), None
                if event["type"] == "websocket.disconnect":
                    return
                text = event.get("text")
                if text is None:
                    self.outbox.control(refusal("message", "binary messages are not accepted"))
                    continue
                if len(text) > self.max_bytes or len(text.encode()) > self.max_bytes:
                    await self._end(refusal("message", f"messages are limited to {self.max_bytes} bytes"))
                    await self.ws.close(code=1009)
                    return
                try:
                    msg = loads(text)
                except ValueError:  # not JSON, or nested too deep
                    continue
                if not isinstance(msg, dict):
                    continue
                kind = msg.get("type")
                if idle_paused and kind != "pause":
                    self.session.resume()
                idle_paused = False
                await self._dispatch(kind, msg)
        finally:
            if recv is not None:
                recv.cancel()

    async def _end(self, message: dict) -> None:
        """Send `message` after what is queued, then let the pump finish."""
        self.outbox.close_with(message)
        await asyncio.wait({self.pump}, timeout=5.0)

    async def _dispatch(self, kind: object, msg: dict) -> None:
        """`pause`, `resume` and `bind` are the session's own; any other
        message goes whole to the aura's control, which may block until
        the loop thread answers, so it runs on a worker thread; while the
        session is paused, it is refused at once. A message that gets no
        reply (`unanswered`) gets none either way."""
        session, outbox = self.session, self.outbox
        if kind == "pause":
            session.pause()
        elif kind == "resume":
            session.resume()
        elif kind == "bind":
            await self._bind(msg.get("arrangement"))
        elif unanswered(msg):
            return
        elif session.paused:
            name = msg.get("name") if kind == "set" else None
            outbox.control(refusal(kind if isinstance(kind, str) else None, PAUSED,
                                   name=name if isinstance(name, str) else None, id=msg.get("id")))
        else:
            await asyncio.to_thread(answer_request, session.control, msg, outbox.control)

    async def _bind(self, arrangement: object) -> None:
        """Compile `arrangement` off the event loop, then rebind the session to it."""
        outbox = self.outbox
        if not isinstance(arrangement, dict):
            outbox.control(refusal("bind", "bind needs an arrangement object"))
            return
        try:
            args = await asyncio.to_thread(self.bind_args, arrangement)
        except CompileFailure as exc:
            outbox.control(refusal("bind", str(exc)[:300], issues=exc.issues))
            return
        except Busy as exc:
            outbox.control(refusal("bind", str(exc)))
            return
        except Exception:
            logger.warning("a bind failed to compile", exc_info=True)
            outbox.control(refusal("bind", "the arrangement could not be compiled"))
            return
        self.session.bind(**args)


def _mount_spa(app: FastAPI, dist: Path) -> None:
    """Serve the built SPA, when `dist` holds one. `/` and `/a/{id}` get the
    index; other paths get only files that exist inside `dist`."""
    index = dist / "index.html"
    if not index.is_file():
        return
    root = dist.resolve()
    if (dist / "assets").is_dir():
        app.mount("/assets", StaticFiles(directory=str(dist / "assets")), name="assets")

    @app.get("/", include_in_schema=False)
    @app.get("/a/{id}", include_in_schema=False)
    def spa_index(id: str = "") -> FileResponse:
        return FileResponse(str(index))

    @app.get("/{path:path}", include_in_schema=False)
    def spa_file(path: str) -> FileResponse:
        candidate = (dist / path).resolve()
        if path.startswith(("api/", "ws/", "health/")) or not candidate.is_relative_to(root) or not candidate.is_file():
            raise HTTPException(404, "not found")
        return FileResponse(str(candidate))

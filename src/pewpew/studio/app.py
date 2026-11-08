"""The Gallery's FastAPI app: the Console page, the shares, and one live session per visitor.

`create_app` takes its collaborators as arguments so tests can inject fakes.
The defaults are the real rig: `pewpew.rig.load_catalog` and
`pewpew.rig.runtime.compile_doc` (under `Limits.max_pixels`), and the
example looks of `examples/` (`PEWPEW_STUDIO_EXAMPLES` names another
folder, `pewpew.aura.book.examples_book`), which an older bare-arrangement
share and the default share open with.

HTTP:

- `GET /` and `GET /a/{id}`: the Console page the engine serves
  (`pewpew.sinks.preview.page`), titled "pewpew Gallery", never cached;
  `/a/{id}` of no stored share is a 404. Its files (`web_files()`) are
  served immutable, the parts catalog at `/parts.json` and each assembly at
  `/assembly/{digest}.glb`, as the engine serves them, gzipped when the
  client accepts it. Any other path is a 404.
- `POST /api/shares`: a form (`application/x-www-form-urlencoded`) with one
  field, `envelope`, the share's JSON text, which the Console's Publish
  posts from a top-level form. It is checked (`pewpew.share.check`),
  compiled under the limits and stored under its content id, then answered
  `303 See Other` to `/a/{id}`. Every refusal is one short line of
  `text/plain`, which the browser shows in the tab the form opened: 413 too
  large, 415 not a form, 422 not a share, or one that does not check or
  compile, 429 over the rate limit, 503 too busy to compile.
- `GET /health/live`.

No response carries a CORS header, and there is no API schema or docs page.

The websocket `/ws?a={id}` speaks the engine's wire (`pewpew.sinks.preview`)
for one session on share `id` (no `a`: the default share, the packaged
`golden-rings` arrangement and the example looks). A share is compiled
once and kept by id in a bounded cache (`_Shares`), so the compile limits
apply only to a share no session has opened lately. A session sends the
`hello` on connect, the per-frame states with the binary frames, `ack`,
`exported` and `refused`. The `refused` message names the refused control,
as the preview does, and the Gallery adds two controls of its own:
`session` (the session is refused or ends: the server is full, the share is
unknown or does not compile, no look starts on it, the visitor was evicted,
or it sat paused too long) and `message` (a message the socket does not
accept: binary, or over the size limit).

Production runs `python -m pewpew studio`, which sets uvicorn's websocket
message cap and shutdown bound (docs/studio/contracts.md).
"""

from __future__ import annotations

import asyncio
import dataclasses
import functools
import json
import logging
import os
import re
import threading
import time
from collections import OrderedDict
from collections.abc import Callable, Mapping
from contextlib import asynccontextmanager, suppress
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs

from fastapi import FastAPI, Request, Response, WebSocket
from fastapi.responses import PlainTextResponse, RedirectResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.requests import ClientDisconnect, HTTPConnection

from pewpew import share
from pewpew.aura.book import LookBook, examples_book
from pewpew.jsonfile import loads
from pewpew.rig import EXAMPLES, load_catalog
from pewpew.rig.runtime import compile_doc, plan_view, rig_view
from pewpew.sinks.preview import (
    ASSEMBLY_PATH,
    IMMUTABLE,
    accepts_gzip,
    answer_request,
    assembly,
    file_type,
    page,
    parts,
    refusal,
    unanswered,
    web_file,
    web_files,
    zipped,
)
from pewpew.studio.limits import Admission, BodyLimit, Limits, RateLimiter, address_key, client_ip
from pewpew.studio.session import NoLook, Session, SessionRegistry, Shared
from pewpew.studio.store import ID_PATTERN, Store, store_from_env
from pewpew.studio.transport import Outbox

logger = logging.getLogger(__name__)

IDLE_TIMEOUT_S = 600.0  # no inbound message for this long pauses a session
PAUSED_TIMEOUT_S = 1800.0  # paused for this long closes it
CACHED_SHARES = 32  # compiled shares kept by id
EVICTED = "closed after a long pause to make room for another visitor; reload to continue"
PAUSED = "the session is paused; send resume first"
UNKNOWN = "no share has this link"
SHARES_URL = "/api/shares"
FORM = "application/x-www-form-urlencoded"
# Percent-encoding writes a byte as three, so the form may be three times the envelope it carries.
FORM_INFLATION = 3
TITLE = re.compile(rb"<title>.*?</title>", re.DOTALL)
_EXAMPLES = Path(__file__).resolve().parents[3] / "examples"


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

    def response(self) -> Response:
        return _text(self.status, str(self), {"Retry-After": str(int(self.retry_after) + 1)})


class Unknown(Exception):
    """No share is stored under the id."""


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


def _text(status: int, text: str, headers: Mapping[str, str] | None = None) -> PlainTextResponse:
    """A refusal as one short line of plain text."""
    return PlainTextResponse(text.rstrip("\n") + "\n", status, headers=dict(headers or {}))


def _served(request: Request, body: tuple[bytes, bytes], kind: str, cache: str) -> Response:
    """`body` (raw, gzipped) of Content-Type `kind` and Cache-Control `cache`,
    gzipped when the request accepts it."""
    raw, gz = body
    headers = {"Vary": "Accept-Encoding", "Cache-Control": cache}
    if accepts_gzip(", ".join(request.headers.getlist("accept-encoding"))):
        return Response(gz, media_type=kind, headers={**headers, "Content-Encoding": "gzip"})
    return Response(raw, media_type=kind, headers=headers)


def _address(conn: HTTPConnection) -> str:
    return address_key(client_ip(conn.headers, conn.client.host if conn.client else None))


class _Shares:
    """Compiled shares by id, the `size` used last; thread-safe."""

    def __init__(self, size: int) -> None:
        self._size = size
        self._lock = threading.Lock()
        self._shares: OrderedDict[str, Shared] = OrderedDict()

    def get(self, id: str) -> Shared | None:
        with self._lock:
            found = self._shares.get(id)
            if found is not None:
                self._shares.move_to_end(id)
            return found

    def put(self, id: str, shared: Shared) -> None:
        with self._lock:
            self._shares[id] = shared
            self._shares.move_to_end(id)
            while len(self._shares) > self._size:
                self._shares.popitem(last=False)


def create_app(
    *,
    catalog: Any = None,
    compile: Callable[[dict, Any], Any] | None = None,
    store: Store | None = None,
    examples: Path | None = None,
    default: dict | None = None,
    limits: Limits | None = None,
    fps: float = 30.0,
    idle_timeout_s: float = IDLE_TIMEOUT_S,
    paused_timeout_s: float = PAUSED_TIMEOUT_S,
    cached: int = CACHED_SHARES,
) -> FastAPI:
    """The Gallery app. `default` is the arrangement of the share `/` runs
    (default: the packaged `golden-rings`), with the example looks in
    `examples`. Raises RuntimeError when `examples` holds no looks."""
    limits = limits or Limits()
    admission = Admission(limits)
    save_limiter = RateLimiter(limits.saves_per_minute)
    compile_limiter = RateLimiter(limits.compiles_per_minute, limits.compile_burst)
    compile_slots = threading.BoundedSemaphore(limits.max_concurrent_compiles)
    registry = SessionRegistry()
    shares = _Shares(cached)
    compile_fn = compile or functools.partial(compile_doc, max_pixels=limits.max_pixels)
    if examples is None:
        examples = Path(os.environ.get("PEWPEW_STUDIO_EXAMPLES", _EXAMPLES))
    book = examples_book(examples)
    if not book.looks:
        raise RuntimeError(f"no example looks in {examples}: an older share and the default share open with them")
    if default is None:
        default = json.loads((EXAMPLES / "golden-rings.json").read_text("utf-8"))
    default_text = json.dumps(default)
    default_lock = threading.Lock()
    default_share: Shared | None = None  # compiled on first use, and kept
    titled, count = TITLE.subn(b"<title>pewpew Gallery</title>", page()[0], count=1)
    if not count:
        logger.warning("the packaged page has no <title>; the Gallery serves it as it is")
    gallery_page = zipped(titled)

    def db() -> Store:
        assert store is not None, "the store opens with the app's lifespan"
        return store

    def catalog_of() -> Any:
        nonlocal catalog
        if catalog is None:
            catalog = load_catalog()
        return catalog

    def compile_checked(arrangement: Any, key: str | None) -> Any:
        """Compile `arrangement` for the address `key` (None: the Gallery's
        own, with no rate limit), under the limits.

        Blocks; call it off the event loop. Raises CompileFailure or Busy.
        Only a dict reaches the compiler, so a client string is never read as
        a file path.
        """
        if not isinstance(arrangement, dict):
            raise CompileFailure([_error("invalid", "an arrangement is a JSON object")])
        wait = compile_limiter.allow(key) if key is not None else None
        if wait is not None:
            raise Busy(429, f"limit of {limits.compiles_per_minute} compiles per minute per address", wait)
        if not compile_slots.acquire(timeout=limits.compile_wait_s):
            raise Busy(503, "the server is busy compiling; try again shortly", 1.0)
        try:
            return compile_fn(arrangement, catalog_of())
        except (ValueError, OverflowError) as exc:  # RigError and ValidationError are ValueErrors
            issues = [_issue(i) for i in getattr(exc, "issues", ())]
            raise CompileFailure(issues or [_error("invalid", _unreadable(exc))]) from None
        except Exception:  # a compiler bug: logged here, and never named to the visitor
            logger.warning("an arrangement failed to compile", exc_info=True)
            raise CompileFailure([_error("internal", "the arrangement could not be compiled")]) from None
        finally:
            compile_slots.release()

    def shared_of(envelope: dict, looks: LookBook, key: str | None) -> Shared:
        """Compile the share `envelope` with its looks book. Blocks; raises as `compile_checked`."""
        rig = compile_checked(envelope["arrangement"], key)
        return Shared(rig.mapping, plan_view(rig, catalog_of()), rig_view(rig), rig.limiter, looks)

    def open_share(id: str | None, key: str) -> Shared:
        """The compiled share `id`, or the default share for None, compiled
        on a miss. Blocks. Raises Unknown, CompileFailure or Busy."""
        nonlocal default_share
        if id is None:
            with default_lock:  # the first visitors wait for one compile
                if default_share is None:
                    default_share = shared_of(*share.read(default_text, book), None)
                return default_share
        if not ID_PATTERN.match(id):
            raise Unknown(UNKNOWN)
        found = shares.get(id)
        if found is not None:
            return found
        text = db().get(id)
        if text is None:
            raise Unknown(UNKNOWN)
        found = shared_of(*share.read(text, book), key)
        shares.put(id, found)
        return found

    def save(doc: object, key: str) -> str:
        """Check, compile and store the share `doc`; its id. Blocks.
        Raises ShareError, CompileFailure or Busy."""
        envelope, looks = share.check(doc, max_bytes=limits.max_body_bytes, max_fixtures=limits.max_fixtures)
        text = share.canonical_json(envelope)
        id_ = share.content_id(text)
        if shares.get(id_) is None:
            shares.put(id_, shared_of(envelope, looks, key))
        db().put(id_, text)
        return id_

    def stored(id: str) -> bool:
        """Whether a share is stored under `id`. Blocks."""
        return ID_PATTERN.match(id) is not None and (shares.get(id) is not None or db().get(id) is not None)

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

    app = FastAPI(title="pewpew Gallery", lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)
    # Percent-encoding inflates the form; the envelope inside it is held to max_body_bytes.
    app.add_middleware(BodyLimit, limit=limits.max_body_bytes,
                       paths={SHARES_URL: FORM_INFLATION * limits.max_body_bytes})
    app.state.sessions = registry
    app.state.admission = admission
    app.state.shares = shares

    @app.exception_handler(StarletteHTTPException)
    async def http_error(_request: Request, exc: StarletteHTTPException) -> Response:
        return _text(exc.status_code, str(exc.detail), exc.headers)

    # -- HTTP ------------------------------------------------------------------

    @app.get("/health/live")
    def health_live() -> dict[str, bool]:
        return {"ok": True}

    @app.get("/parts.json")
    def get_parts(request: Request) -> Response:
        # no-cache: the catalog changes with the Gallery.
        return _served(request, parts(), "application/json", "no-cache")

    @app.get("/assembly/{digest}.glb")
    def get_assembly(request: Request, digest: str) -> Response:
        glb = assembly(digest) if ASSEMBLY_PATH.fullmatch(request.url.path) else None
        if glb is None:
            return _text(404, "no such assembly")
        return _served(request, glb, "model/gltf-binary", IMMUTABLE)

    @app.get("/")
    def get_page(request: Request) -> Response:
        # no-cache: a reload after a deploy gets the new page.
        return _served(request, gallery_page, "text/html; charset=utf-8", "no-cache")

    @app.get("/a/{id}")
    def get_shared_page(request: Request, id: str) -> Response:
        if not stored(id):
            return _text(404, UNKNOWN)
        return _served(request, gallery_page, "text/html; charset=utf-8", "no-cache")

    @app.post(SHARES_URL)
    async def post_share(request: Request) -> Response:
        kind = request.headers.get("content-type", "").partition(";")[0].strip().lower()
        if kind != FORM:
            return _text(415, f"a share is posted as a form ({FORM})")
        key = _address(request)
        wait = save_limiter.allow(key)
        if wait is not None:
            return _text(429, f"limit of {limits.saves_per_minute} shares per minute per address",
                         {"Retry-After": str(int(wait) + 1)})
        try:
            body = await request.body()
        except ClientDisconnect:  # BodyLimit has answered 413 to a body over the limit
            return _text(413, "the share is over the limit")
        try:
            fields = parse_qs(body.decode("ascii"), strict_parsing=True, max_num_fields=1, errors="strict")
        except ValueError:  # not ASCII, not a form, more than one field, or bad UTF-8 in it
            fields = {}
        values = fields.get("envelope", [])
        if len(values) != 1:
            return _text(422, "a share is a form of one field, envelope")
        text = values[0]
        if len(text.encode("utf-8")) > limits.max_body_bytes:
            return _text(413, f"a share is at most {limits.max_body_bytes} bytes")
        try:
            doc = loads(text)
        except (ValueError, OverflowError) as exc:  # not JSON, or nested too deep
            return _text(422, f"the envelope is not JSON: {_unreadable(exc)}")
        try:
            id_ = await asyncio.to_thread(save, doc, key)
        except share.ShareError as exc:
            return _text(422, "this share does not check: " + "; ".join(exc.problems)[:2000])
        except CompileFailure as exc:
            reasons = "; ".join(str(i.get("message")) for i in exc.issues)
            return _text(422, f"this layout does not compile: {reasons}"[:2000])
        except Busy as exc:
            return exc.response()
        # 303: the browser fetches the share's page with a GET (RFC 9110 §15.4.4).
        return RedirectResponse(f"/a/{id_}", status_code=303)

    @app.get("/{path:path}")
    def get_file(request: Request, path: str) -> Response:
        if path not in web_files():
            return _text(404, "not found")
        return _served(request, web_file(path), file_type(path), IMMUTABLE)

    # -- websocket -------------------------------------------------------------

    @app.websocket("/ws")
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
            try:
                shared = await asyncio.to_thread(open_share, ws.query_params.get("a"), key)
                outbox = Outbox(asyncio.get_running_loop())
                session = Session(outbox, shared, fps=fps, max_pixels=limits.max_pixels)
            except (Unknown, CompileFailure, Busy, NoLook) as exc:
                reason = str(exc) if not isinstance(exc, CompileFailure) else f"this layout does not compile: {exc}"
                await ws.send_text(json.dumps(refusal("session", reason)))
                await ws.close(code=1013 if isinstance(exc, Busy) else 1008)
                return
            registry.add(session, ticket, lambda: outbox.close_with(refusal("session", EVICTED)))
            outbox.control(session.hello())
            session.start()
            pump = asyncio.ensure_future(outbox.pump(ws))
            visitor = _Visitor(ws, session, outbox, pump, limits.max_body_bytes, idle_timeout_s, paused_timeout_s)
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

    return app


@dataclasses.dataclass
class _Visitor:
    """One websocket: reads the client's messages and hands them to its session."""

    ws: WebSocket
    session: Session
    outbox: Outbox
    pump: asyncio.Future
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
        """`pause` and `resume` are the session's own; any other message
        goes whole to the aura's control, which may block until the loop
        thread answers, so it runs on a worker thread; while the session is
        paused, it is refused at once. A message that gets no reply
        (`unanswered`) gets none either way."""
        session, outbox = self.session, self.outbox
        if kind == "pause":
            session.pause()
        elif kind == "resume":
            session.resume()
        elif unanswered(msg):
            return
        elif session.paused:
            name = msg.get("name") if kind == "set" else None
            outbox.control(refusal(kind if isinstance(kind, str) else None, PAUSED,
                                   name=name if isinstance(name, str) else None, id=msg.get("id")))
        else:
            await asyncio.to_thread(answer_request, session.control, msg, outbox.control)

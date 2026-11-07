"""The build hash of the page source in `web/`.

The Vite build stamps it into `<meta name="pewpew-build">` of the built page,
and `tests/test_page_build.py` checks the stamp, so a source change without a
rebuild fails the suite. Run as a script, it prints the hash.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

WEB = Path(__file__).resolve().parent.parent / "web"

# What the built page is made from: everything in web/src but dotfiles
# (editor swap files, .DS_Store), the page shell, the build config and the
# workspace lockfile at the repo root. Tests and installed packages are not.
FILES = ("index.html", "package.json", "../pnpm-lock.yaml", "tsconfig.json", "tsconfig.node.json", "vite.config.ts")


def web_hash() -> str:
    """Return the SHA-256 of the page source files, as 16 hex digits."""
    paths = [WEB / name for name in FILES]
    paths += (p for p in (WEB / "src").rglob("*") if p.is_file() and not p.name.startswith("."))
    digest = hashlib.sha256()
    for path in sorted(paths):
        data = path.read_bytes()
        digest.update(f"{path.resolve().relative_to(WEB.parent).as_posix()}\0{len(data)}\0".encode())
        digest.update(data)
    return digest.hexdigest()[:16]


if __name__ == "__main__":
    print(web_hash())

from __future__ import annotations

from pathlib import Path


LIBOMP_CANDIDATES = (
    Path("/opt/homebrew/opt/libomp/lib/libomp.dylib"),
    Path("/opt/homebrew/lib/libomp.dylib"),
    Path("/usr/local/opt/libomp/lib/libomp.dylib"),
    Path("/usr/local/lib/libomp.dylib"),
)


def has_libomp() -> bool:
    return any(candidate.exists() for candidate in LIBOMP_CANDIDATES)


def libomp_hint() -> str:
    if has_libomp():
        return "libomp detected."
    return (
        "libomp not found. On macOS install it with `brew install libomp`, "
        "or run the service via Docker where the dependency is isolated."
    )

from __future__ import annotations

from pathlib import Path
import os


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


def prepare_runtime_cache(base_dir: Path) -> None:
    """Set writable cache dirs for matplotlib/fontconfig-heavy ML imports."""
    mpl_dir = base_dir / ".mplconfig"
    xdg_dir = base_dir / ".xdg-cache"
    fontconfig_dir = xdg_dir / "fontconfig"
    mpl_dir.mkdir(parents=True, exist_ok=True)
    fontconfig_dir.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("MPLCONFIGDIR", str(mpl_dir))
    os.environ.setdefault("XDG_CACHE_HOME", str(xdg_dir))

"""Where simulation output (GIFs, JSON logs) is written.

Every simulation writes next to its own ``run.py``. In a source checkout
that is what you want: the GIFs live beside the code and the docs link them.
Installed from PyPI, though, "next to run.py" is ``site-packages`` -- often
read-only, and never somewhere a user would look for results.

So the directory a simulation asks for is resolved here:

1. ``FLYBOTS_OUTPUT_DIR`` set: ``$FLYBOTS_OUTPUT_DIR/<simulation>/``.
   ``flybots run --out-dir`` sets it.
2. The package is installed (the directory is under ``site-packages`` or
   ``dist-packages``): ``./flybots-output/<simulation>/``.
3. Otherwise, the directory as given.
"""

from __future__ import annotations

import os
from pathlib import Path

__all__ = ["OUTPUT_DIR_ENV", "resolve_output_dir"]

OUTPUT_DIR_ENV = "FLYBOTS_OUTPUT_DIR"
_INSTALLED_MARKERS = frozenset({"site-packages", "dist-packages"})


def resolve_output_dir(requested: str | Path) -> Path:
    """Return the directory to write into instead of *requested*."""
    requested = Path(requested)
    override = os.getenv(OUTPUT_DIR_ENV)
    if override:
        return Path(override).expanduser() / requested.name
    if _INSTALLED_MARKERS.intersection(requested.resolve().parts):
        return Path.cwd() / "flybots-output" / requested.name
    return requested

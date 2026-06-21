"""Console helpers for cross-platform script output."""
from __future__ import annotations

import sys


def configure_stdio_utf8() -> None:
    """Use UTF-8 for stdout/stderr on Windows (cp1252 cannot print emoji)."""
    if sys.platform != "win32":
        return

    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is None:
            continue
        try:
            reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, OSError, ValueError):
            pass

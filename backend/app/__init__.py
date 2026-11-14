# LogRaven — Application Package

import sys

# Windows Application Control blocks ujson native C-extension DLL; setting to None forces standard json fallback
if "ujson" not in sys.modules:
    try:
        import ujson  # noqa: F401
    except (ImportError, OSError):
        sys.modules["ujson"] = None

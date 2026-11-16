"""
Executable root launcher for PyInstaller.
Ensures UTF-8 encoding on Windows console to prevent charmap encoding errors.
"""

import sys

if sys.platform == "win32":
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from pdf_extractor.cli import main

if __name__ == "__main__":
    main()

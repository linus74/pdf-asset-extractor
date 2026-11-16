"""
Dedicated Desktop GUI launcher for PyInstaller (--windowed, zero console).
If one or more PDF paths (or a folder) are passed via drag & drop onto the .exe icon,
opens the GUI with those files pre-loaded (single preview or batch queue).
"""

import sys
from pathlib import Path
from pdf_extractor.gui import launch_gui

if __name__ == "__main__":
    initial_pdfs = [Path(arg) for arg in sys.argv[1:] if Path(arg).exists()] if len(sys.argv) > 1 else None
    launch_gui(initial_pdfs=initial_pdfs)

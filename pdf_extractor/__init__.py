"""
pdf_extractor package root
"""

from .core import extract_pdf_assets, extract_batch_pdfs, collect_pdf_paths, inspect_pdf_preflight

__version__ = "2.3.0"
__all__ = [
    "extract_pdf_assets",
    "extract_batch_pdfs",
    "collect_pdf_paths",
    "inspect_pdf_preflight",
]

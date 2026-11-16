"""
Page geometry & box dimension extractor: MediaBox, CropBox, BleedBox, TrimBox,
ArtBox, rotation, standard paper size identification, and per-page metrics.
"""

from typing import List, Dict, Any, Optional
import pymupdf
import pikepdf
from ..utils.paper_sizes import (
    identify_paper_size,
    points_to_mm,
    points_to_inches,
)


def _rect_to_dict(rect: Optional[pymupdf.Rect]) -> Optional[Dict[str, Any]]:
    if not rect:
        return None
    width_pt = round(rect.width, 2)
    height_pt = round(rect.height, 2)
    format_name, orientation = identify_paper_size(width_pt, height_pt)
    return {
        "x0": round(rect.x0, 2),
        "y0": round(rect.y0, 2),
        "x1": round(rect.x1, 2),
        "y1": round(rect.y1, 2),
        "width_pt": width_pt,
        "height_pt": height_pt,
        "width_mm": points_to_mm(width_pt),
        "height_mm": points_to_mm(height_pt),
        "width_in": points_to_inches(width_pt),
        "height_in": points_to_inches(height_pt),
        "matched_size": format_name,
        "orientation": orientation,
    }


def extract_pages_geometry(
    doc: pymupdf.Document,
    pike_doc: Optional[pikepdf.Pdf] = None
) -> List[Dict[str, Any]]:
    """
    Analyzes geometry, boxes, and content metrics for every page.
    """
    pages_data = []

    for idx, page in enumerate(doc):
        pno = idx + 1
        rotation = page.rotation

        # Page boxes in PyMuPDF
        media_box = page.mediabox
        crop_box = page.cropbox

        # Additional prepress boxes: BleedBox, TrimBox, ArtBox
        # In PyMuPDF, page.bleedbox, page.trimbox, page.artbox are available in modern versions,
        # or can be read via pikepdf
        bleed_box = None
        trim_box = None
        art_box = None

        if hasattr(page, "bleedbox"):
            bleed_box = page.bleedbox
        if hasattr(page, "trimbox"):
            trim_box = page.trimbox
        if hasattr(page, "artbox"):
            art_box = page.artbox

        # Fallback to pikepdf for prepress boxes if not found
        if pike_doc and idx < len(pike_doc.pages):
            try:
                p_obj = pike_doc.pages[idx]
                if bleed_box is None and "/BleedBox" in p_obj:
                    b = [float(x) for x in p_obj.BleedBox]
                    bleed_box = pymupdf.Rect(b[0], b[1], b[2], b[3])
                if trim_box is None and "/TrimBox" in p_obj:
                    t = [float(x) for x in p_obj.TrimBox]
                    trim_box = pymupdf.Rect(t[0], t[1], t[2], t[3])
                if art_box is None and "/ArtBox" in p_obj:
                    a = [float(x) for x in p_obj.ArtBox]
                    art_box = pymupdf.Rect(a[0], a[1], a[2], a[3])
            except Exception:
                pass

        # Page label (e.g. roman numerals, custom numbering)
        page_label = str(pno)
        try:
            label = page.get_label()
            if label:
                page_label = label
        except Exception:
            pass

        # Text metrics
        try:
            text = page.get_text()
            char_count = len(text)
            word_count = len(text.split())
            text_preview = text.strip()[:200]
        except Exception:
            char_count = 0
            word_count = 0
            text_preview = ""

        # Drawings / Vector paths
        try:
            drawings_count = len(page.get_drawings())
        except Exception:
            drawings_count = 0

        # Links and annotations
        try:
            links = page.get_links()
            links_count = len(links)
        except Exception:
            links_count = 0

        try:
            annots = list(page.annots())
            annots_count = len(annots)
        except Exception:
            annots_count = 0

        media_info = _rect_to_dict(media_box)
        crop_info = _rect_to_dict(crop_box)
        bleed_info = _rect_to_dict(bleed_box) if bleed_box else None
        trim_info = _rect_to_dict(trim_box) if trim_box else None
        art_info = _rect_to_dict(art_box) if art_box else None

        # Images & Fonts count on this page
        try:
            page_images_count = len(page.get_images())
        except Exception:
            page_images_count = 0

        try:
            page_fonts_count = len(page.get_fonts())
        except Exception:
            page_fonts_count = 0

        pages_data.append({
            "page_number": pno,
            "page_label": page_label,
            "rotation": rotation,
            "mediabox": media_info,
            "cropbox": crop_info,
            "bleedbox": bleed_info,
            "trimbox": trim_info,
            "artbox": art_info,
            "stats": {
                "images_count": page_images_count,
                "fonts_count": page_fonts_count,
                "vector_drawings_count": drawings_count,
                "character_count": char_count,
                "word_count": word_count,
                "links_count": links_count,
                "annotations_count": annots_count,
                "text_snippet": text_preview,
            }
        })

    return pages_data

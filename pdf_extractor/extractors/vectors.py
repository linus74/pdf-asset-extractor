"""
Vector graphics extractor: extracts vector drawings, paths, and illustrations,
saving them as Scalable Vector Graphics (.svg) and Adobe Illustrator (.ai) files.
"""

import re
from pathlib import Path
from typing import List, Dict, Any, Set
import pymupdf
from ..utils.helpers import format_bytes, compute_sha256


def _color_to_hex(color_tuple) -> str | None:
    if not color_tuple:
        return None
    try:
        if len(color_tuple) == 3:  # RGB
            r, g, b = [int(max(0, min(1, c)) * 255) for c in color_tuple]
            return f"#{r:02x}{g:02x}{b:02x}"
        elif len(color_tuple) == 4:  # CMYK approx to RGB
            c, m, y, k = color_tuple
            r = int(255 * (1 - c) * (1 - k))
            g = int(255 * (1 - m) * (1 - k))
            b = int(255 * (1 - y) * (1 - k))
            return f"#{max(0, min(255, r)):02x}{max(0, min(255, g)):02x}{max(0, min(255, b)):02x}"
        elif len(color_tuple) == 1:  # Gray
            val = int(max(0, min(1, color_tuple[0])) * 255)
            return f"#{val:02x}{val:02x}{val:02x}"
    except Exception:
        pass
    return None


def extract_vectors(
    doc: pymupdf.Document,
    output_dir: Path
) -> List[Dict[str, Any]]:
    """
    Extracts vector graphics from each page where drawings exist.
    Exports both clean .svg and Adobe Illustrator (.ai) compatible files.
    """
    vectors_dir = output_dir / "vectors"
    vectors_dir.mkdir(parents=True, exist_ok=True)

    extracted_vectors: List[Dict[str, Any]] = []

    for page_idx, page in enumerate(doc):
        pno = page_idx + 1

        try:
            drawings = page.get_drawings()
        except Exception:
            drawings = []

        if not drawings:
            continue

        # Count geometry elements
        total_paths = len(drawings)
        lines_count = 0
        curves_count = 0
        rects_count = 0
        colors_used: Set[str] = set()

        min_x, min_y, max_x, max_y = float("inf"), float("inf"), float("-inf"), float("-inf")

        for d in drawings:
            # Bounding box
            r = d.get("rect")
            if r:
                min_x = min(min_x, r.x0)
                min_y = min(min_y, r.y0)
                max_x = max(max_x, r.x1)
                max_y = max(max_y, r.y1)

            # Colors
            f_hex = _color_to_hex(d.get("fill"))
            if f_hex:
                colors_used.add(f_hex)
            s_hex = _color_to_hex(d.get("color"))
            if s_hex:
                colors_used.add(s_hex)

            # Path items
            for item in d.get("items", []):
                cmd = item[0]
                if cmd == "l":  # line
                    lines_count += 1
                elif cmd == "c":  # bezier curve
                    curves_count += 1
                elif cmd == "re":  # rectangle
                    rects_count += 1

        bbox = None
        if min_x != float("inf") and max_x != float("-inf"):
            bbox = [round(min_x, 2), round(min_y, 2), round(max_x, 2), round(max_y, 2)]

        # 1. Export SVG
        svg_filename = f"page_{pno:03d}_vectors.svg"
        svg_path = vectors_dir / svg_filename
        try:
            raw_svg = page.get_svg_image()
            # Strip any raster <image> elements so it's pure vector
            clean_svg = re.sub(r"<image[^>]*/>", "", raw_svg)
            clean_svg = re.sub(r"<image[^>]*>.*?</image>", "", clean_svg, flags=re.DOTALL)

            with open(svg_path, "w", encoding="utf-8") as f:
                f.write(clean_svg)
            svg_size = len(clean_svg.encode("utf-8"))
        except Exception:
            svg_path = None
            svg_size = 0

        # 2. Export Adobe Illustrator (.ai) / Vector PDF
        # Adobe Illustrator natively opens PDF files as fully editable vector art (.ai)
        ai_filename = f"page_{pno:03d}_vectors.ai"
        ai_path = vectors_dir / ai_filename
        ai_size = 0

        try:
            single_doc = pymupdf.open()
            single_doc.insert_pdf(doc, from_page=page_idx, to_page=page_idx)
            single_page = single_doc[0]

            # Remove raster images on this page to leave only pure vector art
            try:
                for img_info in single_page.get_images():
                    img_xref = img_info[0]
                    single_page.delete_image(img_xref)
            except Exception:
                pass

            single_doc.save(str(ai_path), deflate=True)
            ai_size = ai_path.stat().st_size
            single_doc.close()
        except Exception:
            ai_path = None

        extracted_vectors.append({
            "page": pno,
            "svg_file": f"vectors/{svg_filename}" if svg_path and svg_path.exists() else None,
            "ai_file": f"vectors/{ai_filename}" if ai_path and ai_path.exists() else None,
            "paths_count": total_paths,
            "lines_count": lines_count,
            "curves_count": curves_count,
            "rectangles_count": rects_count,
            "colors_used": sorted(list(colors_used))[:20],
            "bbox": bbox,
            "svg_size": format_bytes(svg_size) if svg_size else "0 B",
            "ai_size": format_bytes(ai_size) if ai_size else "0 B",
        })

    return extracted_vectors

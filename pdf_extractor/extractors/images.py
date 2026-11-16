"""
Image extractor: extracts embedded raster images, reconstructs alpha transparency
with /SMask, deduplicates shared images, calculates effective DPI, and exports metadata.
"""

from pathlib import Path
from typing import List, Dict, Any, Set, Tuple
import pymupdf
from ..utils.helpers import compute_sha256, format_bytes, sanitize_filename


def extract_images(
    doc: pymupdf.Document,
    output_dir: Path
) -> List[Dict[str, Any]]:
    """
    Extracts all images from doc, saving unique image files into `output_dir / "images"`.
    Returns list of metadata dicts for each unique image.
    """
    images_dir = output_dir / "images"
    images_dir.mkdir(parents=True, exist_ok=True)

    extracted_images: List[Dict[str, Any]] = []
    # Map hash -> index in extracted_images
    hash_to_index: Dict[str, int] = {}
    # Map xref -> hash
    xref_to_hash: Dict[int, str] = {}

    img_counter = 1

    for page_idx, page in enumerate(doc):
        pno = page_idx + 1
        page_images = page.get_images(full=True)

        for img_tuple in page_images:
            xref = img_tuple[0]
            smask = img_tuple[1]
            width = img_tuple[2]
            height = img_tuple[3]
            bpc = img_tuple[4]
            colorspace = img_tuple[5]
            img_name = img_tuple[7]

            # Calculate placement rects on this page and effective DPI
            placements = []
            try:
                rects = page.get_image_rects(xref)
                for r in rects:
                    r_w = round(r.width, 2)
                    r_h = round(r.height, 2)
                    dpi_x = round((width / r.width) * 72, 1) if r.width > 0 else 0
                    dpi_y = round((height / r.height) * 72, 1) if r.height > 0 else 0
                    placements.append({
                        "page": pno,
                        "rect": [round(r.x0, 2), round(r.y0, 2), round(r.x1, 2), round(r.y1, 2)],
                        "width_pt": r_w,
                        "height_pt": r_h,
                        "dpi_x": dpi_x,
                        "dpi_y": dpi_y,
                        "dpi_avg": round((dpi_x + dpi_y) / 2, 1) if dpi_x and dpi_y else max(dpi_x, dpi_y),
                    })
            except Exception:
                pass

            # If already processed this xref
            if xref in xref_to_hash:
                img_hash = xref_to_hash[xref]
                idx = hash_to_index[img_hash]
                existing = extracted_images[idx]
                if pno not in existing["pages"]:
                    existing["pages"].append(pno)
                if placements:
                    existing["placements"].extend(placements)
                continue

            # Extract the image data
            has_transparency = bool(smask > 0)
            image_bytes = b""
            ext = "png"

            # Case A: Image has Soft Mask (SMask) transparency
            if has_transparency:
                try:
                    base_pix = pymupdf.Pixmap(doc, xref)
                    # If base pixmap is CMYK or other space not RGB, convert to RGB first
                    if base_pix.n >= 5 or base_pix.colorspace != pymupdf.csRGB:
                        rgb_pix = pymupdf.Pixmap(pymupdf.csRGB, base_pix)
                        base_pix = rgb_pix

                    mask_pix = pymupdf.Pixmap(doc, smask)
                    # Combine base pixmap with alpha mask
                    combined_pix = pymupdf.Pixmap(base_pix, mask_pix)
                    image_bytes = combined_pix.tobytes("png")
                    ext = "png"
                except Exception:
                    # Fallback to standard extraction
                    raw_dict = doc.extract_image(xref)
                    image_bytes = raw_dict.get("image", b"")
                    ext = raw_dict.get("ext", "png")
            else:
                # Case B: Standard image without mask
                try:
                    raw_dict = doc.extract_image(xref)
                    image_bytes = raw_dict.get("image", b"")
                    ext = raw_dict.get("ext", "png")
                    width = raw_dict.get("width", width)
                    height = raw_dict.get("height", height)
                    colorspace = raw_dict.get("colorspace", colorspace)
                    bpc = raw_dict.get("bpc", bpc)
                except Exception:
                    pass

                # If raw extraction was empty or failed, fallback to Pixmap
                if not image_bytes:
                    try:
                        pix = pymupdf.Pixmap(doc, xref)
                        if pix.n >= 5:
                            pix = pymupdf.Pixmap(pymupdf.csRGB, pix)
                        image_bytes = pix.tobytes("png")
                        ext = "png"
                    except Exception:
                        pass

            if not image_bytes:
                continue

            # Check duplication by hash
            img_hash = compute_sha256(image_bytes)
            xref_to_hash[xref] = img_hash

            if img_hash in hash_to_index:
                idx = hash_to_index[img_hash]
                existing = extracted_images[idx]
                if pno not in existing["pages"]:
                    existing["pages"].append(pno)
                if placements:
                    existing["placements"].extend(placements)
                continue

            # Save unique image to disk
            clean_ext = ext.lower().replace("jpeg", "jpg")
            filename = f"image_{img_counter:03d}_xref{xref}.{clean_ext}"
            file_path = images_dir / filename

            try:
                with open(file_path, "wb") as f:
                    f.write(image_bytes)
            except Exception:
                continue

            file_size = len(image_bytes)
            aspect_ratio = round(width / height, 2) if height > 0 else 1.0

            # Determine dominant DPI across placements
            avg_dpi = None
            if placements:
                valid_dpis = [p["dpi_avg"] for p in placements if p.get("dpi_avg")]
                if valid_dpis:
                    avg_dpi = round(sum(valid_dpis) / len(valid_dpis), 1)

            img_record = {
                "id": img_counter,
                "filename": f"images/{filename}",
                "file_path": str(file_path),
                "xref": xref,
                "smask_xref": smask if smask > 0 else None,
                "format": clean_ext.upper(),
                "width": width,
                "height": height,
                "aspect_ratio": aspect_ratio,
                "colorspace": str(colorspace),
                "bpc": bpc,
                "has_transparency": has_transparency,
                "file_size_bytes": file_size,
                "file_size": format_bytes(file_size),
                "sha256": img_hash,
                "pages": [pno],
                "placements": placements,
                "effective_dpi": avg_dpi,
            }

            hash_to_index[img_hash] = len(extracted_images)
            extracted_images.append(img_record)
            img_counter += 1

    return extracted_images

"""
Attachment extractor: extracts embedded files, portfolios, and annotation attachments.
"""

from pathlib import Path
from typing import List, Dict, Any, Set
import pymupdf
from ..utils.helpers import sanitize_filename, format_bytes, parse_pdf_date, compute_sha256


def extract_attachments(
    doc: pymupdf.Document,
    output_dir: Path
) -> List[Dict[str, Any]]:
    """
    Extracts all embedded files and attachments into `output_dir / "attachments"`.
    """
    attach_dir = output_dir / "attachments"
    attach_dir.mkdir(parents=True, exist_ok=True)

    extracted_attachments: List[Dict[str, Any]] = []
    seen_hashes: Set[str] = set()

    # 1. Document EmbeddedFiles catalog
    emb_count = doc.embfile_count()
    for i in range(emb_count):
        try:
            info = doc.embfile_info(i)
            raw_data = doc.embfile_get(i)
        except Exception:
            continue

        if not raw_data:
            continue

        sha = compute_sha256(raw_data)
        if sha in seen_hashes:
            continue
        seen_hashes.add(sha)

        original_name = info.get("filename") or info.get("ufilename") or f"attachment_{i+1}.bin"
        safe_name = sanitize_filename(original_name, fallback=f"attachment_{i+1}.bin")
        out_path = attach_dir / safe_name

        # If name conflict on disk
        counter = 1
        stem = Path(safe_name).stem
        suffix = Path(safe_name).suffix
        while out_path.exists():
            out_path = attach_dir / f"{stem}_{counter}{suffix}"
            counter += 1

        try:
            with open(out_path, "wb") as f:
                f.write(raw_data)
        except Exception:
            continue

        file_size = len(raw_data)
        extracted_attachments.append({
            "id": len(extracted_attachments) + 1,
            "filename": f"attachments/{out_path.name}",
            "original_name": original_name,
            "description": info.get("description") or "",
            "creation_date": parse_pdf_date(info.get("creationDate")),
            "modification_date": parse_pdf_date(info.get("modDate")),
            "file_size": format_bytes(file_size),
            "file_size_bytes": file_size,
            "sha256": sha,
            "source": "Catalog /EmbeddedFiles",
        })

    # 2. Check FileAttachment annotations on pages
    for page_idx, page in enumerate(doc):
        pno = page_idx + 1
        try:
            for annot in page.annots():
                if annot.type[0] == pymupdf.PDF_ANNOT_FILE_ATTACHMENT:
                    file_info = annot.file_info
                    if not file_info:
                        continue
                    file_data = annot.file_get()
                    if not file_data:
                        continue

                    sha = compute_sha256(file_data)
                    if sha in seen_hashes:
                        continue
                    seen_hashes.add(sha)

                    name = file_info.get("filename", f"page{pno}_annot_attachment.bin")
                    safe_name = sanitize_filename(name, fallback=f"page{pno}_annot.bin")
                    out_path = attach_dir / safe_name

                    counter = 1
                    stem = Path(safe_name).stem
                    suffix = Path(safe_name).suffix
                    while out_path.exists():
                        out_path = attach_dir / f"{stem}_{counter}{suffix}"
                        counter += 1

                    with open(out_path, "wb") as f:
                        f.write(file_data)

                    file_size = len(file_data)
                    extracted_attachments.append({
                        "id": len(extracted_attachments) + 1,
                        "filename": f"attachments/{out_path.name}",
                        "original_name": name,
                        "description": file_info.get("desc", f"Attached to page {pno}"),
                        "file_size": format_bytes(file_size),
                        "file_size_bytes": file_size,
                        "sha256": sha,
                        "source": f"Page {pno} Annotation",
                    })
        except Exception:
            pass

    return extracted_attachments

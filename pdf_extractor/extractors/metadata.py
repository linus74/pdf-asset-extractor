"""
Metadata extractor: document info, creator, producer, dates, PDF version,
XMP metadata packet, security/permissions, standards compliance (PDF/A, PDF/X).
"""

import os
import json
from pathlib import Path
from typing import Dict, Any, Optional
import pymupdf
import pikepdf
from ..utils.helpers import parse_pdf_date


def extract_metadata(
    doc: pymupdf.Document,
    pike_doc: Optional[pikepdf.Pdf],
    output_dir: Path
) -> Dict[str, Any]:
    """
    Extracts all metadata and generation details from the PDF.
    """
    metadata_dir = output_dir / "metadata"
    metadata_dir.mkdir(parents=True, exist_ok=True)

    # 1. Basic PyMuPDF metadata
    m = doc.metadata or {}

    info: Dict[str, Any] = {
        "title": m.get("title") or None,
        "author": m.get("author") or None,
        "subject": m.get("subject") or None,
        "keywords": m.get("keywords") or None,
        "creator": m.get("creator") or None,         # Authoring app (e.g. InDesign, Word)
        "producer": m.get("producer") or None,       # PDF engine (e.g. Distiller, Quartz)
        "creation_date_raw": m.get("creationDate") or None,
        "creation_date": parse_pdf_date(m.get("creationDate")),
        "modification_date_raw": m.get("modDate") or None,
        "modification_date": parse_pdf_date(m.get("modDate")),
        "trapped": m.get("trapped") or None,
        "pdf_format": m.get("format") or f"PDF {doc.version_count / 10:.1f}" if hasattr(doc, "version_count") else "PDF",
    }

    # 2. PDF Version from pikepdf or header
    pdf_version = "Unknown"
    if pike_doc:
        try:
            pdf_version = str(pike_doc.pdf_version)
        except Exception:
            pdf_version = str(doc.metadata.get("format", "Unknown"))
    info["pdf_version"] = pdf_version

    # 3. Pikepdf DocInfo enrichment (additional or custom tags)
    custom_docinfo = {}
    if pike_doc and hasattr(pike_doc, "docinfo"):
        try:
            for k, v in pike_doc.docinfo.items():
                clean_k = str(k).lstrip("/")
                val_str = str(v)
                if clean_k.lower() not in [x.lower() for x in info.keys()]:
                    custom_docinfo[clean_k] = val_str
        except Exception:
            pass
    info["custom_fields"] = custom_docinfo

    # 4. Security & Permissions
    is_encrypted = doc.is_encrypted
    permissions_dict: Dict[str, Any] = {
        "is_encrypted": is_encrypted,
        "needs_password": doc.needs_pass,
    }

    if is_encrypted:
        perm = doc.permissions
        permissions_dict.update({
            "can_print_low_res": bool(perm & pymupdf.PDF_PERM_PRINT),
            "can_modify_contents": bool(perm & pymupdf.PDF_PERM_MODIFY),
            "can_copy_text_and_graphics": bool(perm & pymupdf.PDF_PERM_COPY),
            "can_add_or_modify_annotations": bool(perm & pymupdf.PDF_PERM_ANNOTATE),
            "can_fill_forms": bool(perm & pymupdf.PDF_PERM_FORM),
            "can_extract_for_accessibility": bool(perm & pymupdf.PDF_PERM_ACCESSIBILITY),
            "can_assemble_document": bool(perm & pymupdf.PDF_PERM_ASSEMBLE),
            "can_print_high_res": bool(perm & pymupdf.PDF_PERM_PRINT_HQ),
        })
    info["security"] = permissions_dict

    # 5. Document Catalog properties
    catalog_info: Dict[str, Any] = {}
    if pike_doc and hasattr(pike_doc, "Root"):
        root = pike_doc.Root
        if "/PageMode" in root:
            catalog_info["page_mode"] = str(root.PageMode)
        if "/PageLayout" in root:
            catalog_info["page_layout"] = str(root.PageLayout)
        if "/Lang" in root:
            catalog_info["language"] = str(root.Lang)
        if "/MarkInfo" in root:
            try:
                catalog_info["is_tagged"] = bool(root.MarkInfo.get("/Marked", False))
            except Exception:
                catalog_info["is_tagged"] = False
        if "/ViewerPreferences" in root:
            try:
                vp = root.ViewerPreferences
                catalog_info["viewer_preferences"] = {
                    str(k).lstrip("/"): str(v) for k, v in vp.items()
                }
            except Exception:
                pass
    info["catalog"] = catalog_info

    # 6. Compliance / Standards Detection (PDF/A, PDF/X, PDF/UA)
    standards: Dict[str, Any] = {
        "pdf_a": None,
        "pdf_x": None,
        "pdf_ua": None,
    }

    # 7. XMP Metadata packet extraction
    xmp_raw = ""
    try:
        xmp_raw = doc.get_xml_metadata()
    except Exception:
        pass

    if not xmp_raw and pike_doc and hasattr(pike_doc, "Root") and "/Metadata" in pike_doc.Root:
        try:
            xmp_raw = pike_doc.Root.Metadata.read_bytes().decode("utf-8", errors="ignore")
        except Exception:
            pass

    info["has_xmp"] = bool(xmp_raw and len(xmp_raw.strip()) > 0)

    if info["has_xmp"]:
        xmp_file = metadata_dir / "xmp_metadata.xml"
        try:
            with open(xmp_file, "w", encoding="utf-8") as f:
                f.write(xmp_raw)
            info["xmp_file"] = "metadata/xmp_metadata.xml"
        except Exception:
            pass

        # Check standards in XMP
        xmp_lower = xmp_raw.lower()
        if "pdfaid:part" in xmp_lower:
            # Attempt to parse PDF/A part & conformance
            import re
            part = re.search(r"pdfaid:part[=>\"\s]+([0-9]+)", xmp_raw, re.IGNORECASE)
            conf = re.search(r"pdfaid:conformance[=>\"\s]+([A-Za-z0-9]+)", xmp_raw, re.IGNORECASE)
            p_val = part.group(1) if part else ""
            c_val = conf.group(1) if conf else ""
            standards["pdf_a"] = f"PDF/A-{p_val}{c_val}".strip("-")

        if "pdfx:gts_pdfxversion" in xmp_lower or "gts_pdfxversion" in xmp_lower:
            import re
            match = re.search(r"GTS_PDFXVersion[=>\"\s]+([^<>\"]+)", xmp_raw, re.IGNORECASE)
            standards["pdf_x"] = match.group(1).strip() if match else "PDF/X"
        elif "GTS_PDFXVersion" in custom_docinfo:
            standards["pdf_x"] = custom_docinfo["GTS_PDFXVersion"]

        if "pdfuaid:part" in xmp_lower:
            import re
            part = re.search(r"pdfuaid:part[=>\"\s]+([0-9]+)", xmp_raw, re.IGNORECASE)
            standards["pdf_ua"] = f"PDF/UA-{part.group(1)}" if part else "PDF/UA-1"

    info["standards"] = standards

    # Save info.json
    info_json_file = metadata_dir / "doc_info.json"
    with open(info_json_file, "w", encoding="utf-8") as f:
        json.dump(info, f, indent=2, ensure_ascii=False)

    return info

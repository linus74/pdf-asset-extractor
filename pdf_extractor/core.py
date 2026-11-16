"""
Core PDF extractor engine: coordinates document loading, pre-flight inspection,
execution of specialized extractors, aggregation of results, and generation of reports.
"""

import io
from pathlib import Path
from typing import Dict, Any, Optional, Callable, List, Sequence
import pymupdf
import pikepdf
from PIL import Image

from .extractors.metadata import extract_metadata
from .extractors.geometry import extract_pages_geometry
from .extractors.images import extract_images
from .extractors.fonts import extract_fonts
from .extractors.profiles import extract_color_profiles
from .extractors.attachments import extract_attachments
from .extractors.vectors import extract_vectors
from .reporters.json_reporter import generate_json_report
from .reporters.html_reporter import generate_html_report
from .utils.helpers import format_bytes, sanitize_filename
from .utils.paper_sizes import identify_paper_size, points_to_mm


def resolve_unique_output_dir(base_dir: Path, pdf_stem: str) -> Path:
    """
    Creates a unique parent folder inside `base_dir` named `<safe_stem>_estratto`
    (or `<safe_stem>_estratto_2`, `_3`, ... if it already exists) to prevent
    overwriting existing files in `base_dir`.
    """
    safe_stem = sanitize_filename(pdf_stem, max_length=80, fallback="pdf")
    folder_base = f"{safe_stem}_estratto"
    candidate = base_dir / folder_base
    counter = 2
    while candidate.exists():
        candidate = base_dir / f"{folder_base}_{counter}"
        counter += 1
    return candidate


def inspect_pdf_preflight(
    pdf_path: str | Path,
    password: Optional[str] = None,
    thumb_max_size: tuple[int, int] = (240, 310),
) -> Dict[str, Any]:
    """
    Fast pre-flight inspection for UI preview: reads page count, dimensions,
    creator/producer, encryption status, and renders page 1 thumbnail.
    """
    pdf_file = Path(pdf_path).resolve()
    if not pdf_file.exists():
        raise FileNotFoundError(f"File non trovato: {pdf_file}")

    file_size = pdf_file.stat().st_size
    info: Dict[str, Any] = {
        "file_name": pdf_file.name,
        "file_path": str(pdf_file),
        "file_size": format_bytes(file_size),
        "file_size_bytes": file_size,
        "is_encrypted": False,
        "needs_password": False,
        "unlocked": True,
        "total_pages": 0,
        "paper_format": "N/D",
        "dimensions_mm": "",
        "creator": None,
        "producer": None,
        "pdf_version": "PDF",
        "thumbnail": None,
    }

    doc = pymupdf.open(str(pdf_file))
    try:
        info["is_encrypted"] = bool(doc.is_encrypted)
        if doc.is_encrypted and doc.needs_pass:
            auth_ok = doc.authenticate(password or "")
            if not auth_ok:
                info["needs_password"] = True
                info["unlocked"] = False
                return info

        info["total_pages"] = len(doc)
        meta = doc.metadata or {}
        info["creator"] = meta.get("creator") or None
        info["producer"] = meta.get("producer") or None
        info["pdf_version"] = meta.get("format") or "PDF"

        if len(doc) > 0:
            page0 = doc[0]
            rect = page0.rect
            fmt, orient = identify_paper_size(rect.width, rect.height)
            info["paper_format"] = f"{fmt} ({orient})"
            info["dimensions_mm"] = f"{points_to_mm(rect.width)} × {points_to_mm(rect.height)} mm"

            # Render crisp thumbnail of page 1
            try:
                max_w, max_h = thumb_max_size
                zoom_x = max_w / max(rect.width, 1.0)
                zoom_y = max_h / max(rect.height, 1.0)
                zoom = min(zoom_x, zoom_y, 2.0)
                mat = pymupdf.Matrix(zoom, zoom)
                pix = page0.get_pixmap(matrix=mat, alpha=False)
                img = Image.open(io.BytesIO(pix.tobytes("png")))
                info["thumbnail"] = img
            except Exception:
                pass
    finally:
        doc.close()

    return info


def extract_pdf_assets(
    pdf_path: str | Path,
    output_dir: Optional[str | Path] = None,
    extract_imgs: bool = True,
    extract_fnts: bool = True,
    extract_profs: bool = True,
    extract_attaches: bool = True,
    extract_vecs: bool = True,
    generate_html: bool = True,
    password: Optional[str] = None,
    progress_callback: Optional[Callable[[str, float], None]] = None,
    create_subfolder: bool = True,
) -> Dict[str, Any]:
    """
    Main extraction pipeline.
    Extracts all images, fonts, color profiles, attachments, geometry, and metadata.
    When `create_subfolder=True` (default), creates a dedicated unique folder
    `<pdf_stem>_estratto` (or `_2`, `_3`, ...) inside `output_dir` (which defaults to `./output`).
    """
    def _report(msg: str, pct: float):
        if progress_callback:
            try:
                progress_callback(msg, pct)
            except Exception:
                pass

    pdf_file = Path(pdf_path).resolve()
    if not pdf_file.exists():
        raise FileNotFoundError(f"PDF file not found: {pdf_file}")

    base_dir = (Path.cwd() / "output") if output_dir is None else Path(output_dir).resolve()
    if create_subfolder:
        output_dir = resolve_unique_output_dir(base_dir, pdf_file.stem)
    else:
        output_dir = base_dir

    output_dir.mkdir(parents=True, exist_ok=True)

    _report("Apertura documento PDF...", 0.05)

    # 1. Open with PyMuPDF
    doc = pymupdf.open(str(pdf_file))
    if doc.is_encrypted and doc.needs_pass:
        auth = doc.authenticate(password or "")
        if not auth:
            doc.close()
            raise PermissionError("Il PDF è protetto da password. Inserisci una password valida per procedere.")

    # 2. Open with pikepdf for low-level inspection
    pike_doc = None
    try:
        if password:
            pike_doc = pikepdf.open(str(pdf_file), password=password)
        else:
            pike_doc = pikepdf.open(str(pdf_file))
    except Exception:
        pass

    try:
        # Extract metadata and document generation details
        _report("Estrazione metadati e informazioni software...", 0.12)
        metadata = extract_metadata(doc, pike_doc, output_dir)

        # Extract page geometry and prepress boxes
        _report("Analisi geometria pagine e formato...", 0.22)
        pages = extract_pages_geometry(doc, pike_doc)

        # Extract images
        images = []
        if extract_imgs:
            _report("Estrazione immagini e ricostruzione trasparenza...", 0.35)
            images = extract_images(doc, output_dir)

        # Extract vector graphics (.svg and .ai)
        vectors = []
        if extract_vecs:
            _report("Estrazione grafica vettoriale (.SVG / .AI)...", 0.55)
            vectors = extract_vectors(doc, output_dir)

        # Extract fonts
        fonts = []
        if extract_fnts:
            _report("Recupero e riparazione font incorporati...", 0.72)
            fonts = extract_fonts(doc, output_dir)

        # Extract color profiles & spot colors
        color_data = {"profiles": [], "spot_colors": []}
        if extract_profs and pike_doc:
            _report("Analisi profili colore ICC e inchiostri spot...", 0.85)
            color_data = extract_color_profiles(pike_doc, output_dir)

        # Extract attachments
        attachments = []
        if extract_attaches:
            _report("Estrazione file allegati...", 0.91)
            attachments = extract_attachments(doc, output_dir)

        # Compute summary
        total_pages = len(doc)
        total_images = len(images)
        total_fonts = len(fonts)
        embedded_fonts = sum(1 for f in fonts if f.get("is_embedded"))
        subset_fonts = sum(1 for f in fonts if f.get("is_subset"))
        total_profiles = len(color_data.get("profiles", []))
        total_spot = len(color_data.get("spot_colors", []))
        total_attachments = len(attachments)
        total_vector_pages = len(vectors)
        total_vector_paths = sum(v.get("paths_count", 0) for v in vectors)
        file_size = pdf_file.stat().st_size

        summary = {
            "file_name": pdf_file.name,
            "file_size": format_bytes(file_size),
            "file_size_bytes": file_size,
            "total_pages": total_pages,
            "total_images": total_images,
            "total_fonts": total_fonts,
            "embedded_fonts": embedded_fonts,
            "subset_fonts": subset_fonts,
            "color_profiles_count": total_profiles,
            "spot_colors_count": total_spot,
            "attachments_count": total_attachments,
            "vector_pages_count": total_vector_pages,
            "vector_paths_count": total_vector_paths,
        }

        result = {
            "source_pdf": str(pdf_file),
            "output_directory": str(output_dir),
            "summary": summary,
            "metadata": metadata,
            "pages": pages,
            "images": images,
            "fonts": fonts,
            "vectors": vectors,
            "color_management": color_data,
            "attachments": attachments,
        }

        # Generate JSON report
        _report("Salvataggio report JSON e dashboard HTML...", 0.96)
        json_path = generate_json_report(result, output_dir)
        result["json_report"] = str(json_path)

        # Generate HTML report
        if generate_html:
            html_path = generate_html_report(result, output_dir)
            result["html_report"] = str(html_path)

        _report("Estrazione completata!", 1.0)
        return result

    finally:
        doc.close()
        if pike_doc:
            pike_doc.close()


def collect_pdf_paths(inputs: Sequence[str | Path], recursive: bool = False) -> List[Path]:
    """
    Expands a mix of PDF file paths and directories into a deduplicated,
    order-preserving list of resolved `.pdf` file paths.
    """
    collected: List[Path] = []
    seen: set[Path] = set()

    for raw in inputs:
        p = Path(raw).resolve()
        if not p.exists():
            continue
        if p.is_file() and p.suffix.lower() == ".pdf":
            if p not in seen:
                seen.add(p)
                collected.append(p)
        elif p.is_dir():
            iterator = p.rglob("*") if recursive else p.iterdir()
            for child in sorted(iterator):
                if child.is_file() and child.suffix.lower() == ".pdf":
                    resolved = child.resolve()
                    if resolved not in seen:
                        seen.add(resolved)
                        collected.append(resolved)

    return collected


def extract_batch_pdfs(
    pdf_paths: Sequence[str | Path],
    output_dir: Optional[str | Path] = None,
    extract_imgs: bool = True,
    extract_fnts: bool = True,
    extract_profs: bool = True,
    extract_attaches: bool = True,
    extract_vecs: bool = True,
    generate_html: bool = True,
    password: Optional[str] = None,
    progress_callback: Optional[Callable[[str, float], None]] = None,
    item_callback: Optional[Callable[[int, int, Path, str, Any], None]] = None,
) -> Dict[str, Any]:
    """
    Processes multiple PDF files sequentially into isolated `<stem>_estratto`
    subfolders inside `output_dir` (default `./output`).
    Errors on individual PDFs are captured without halting the rest of the batch.
    """
    base_dir = (Path.cwd() / "output") if output_dir is None else Path(output_dir).resolve()
    base_dir.mkdir(parents=True, exist_ok=True)

    resolved_files = [Path(p).resolve() for p in pdf_paths]
    total = len(resolved_files)
    items_results: List[Dict[str, Any]] = []
    succeeded = 0
    failed = 0

    agg_pages = 0
    agg_images = 0
    agg_fonts = 0
    agg_embedded_fonts = 0
    agg_vectors = 0
    agg_profiles = 0
    agg_attachments = 0

    for idx, pdf_file in enumerate(resolved_files):
        if item_callback:
            try:
                item_callback(idx, total, pdf_file, "running", None)
            except Exception:
                pass

        def _per_file_progress(msg: str, sub_pct: float, _i=idx, _name=pdf_file.name):
            if progress_callback and total > 0:
                overall = (_i + sub_pct) / total
                try:
                    progress_callback(f"[{_i + 1}/{total}] {_name} — {msg}", overall)
                except Exception:
                    pass

        try:
            res = extract_pdf_assets(
                pdf_path=pdf_file,
                output_dir=base_dir,
                extract_imgs=extract_imgs,
                extract_fnts=extract_fnts,
                extract_profs=extract_profs,
                extract_attaches=extract_attaches,
                extract_vecs=extract_vecs,
                generate_html=generate_html,
                password=password,
                progress_callback=_per_file_progress,
                create_subfolder=True,
            )
            succeeded += 1
            s = res["summary"]
            agg_pages += s.get("total_pages", 0)
            agg_images += s.get("total_images", 0)
            agg_fonts += s.get("total_fonts", 0)
            agg_embedded_fonts += s.get("embedded_fonts", 0)
            agg_vectors += s.get("vector_pages_count", 0)
            agg_profiles += s.get("color_profiles_count", 0)
            agg_attachments += s.get("attachments_count", 0)

            items_results.append({
                "source_pdf": str(pdf_file),
                "file_name": pdf_file.name,
                "status": "success",
                "output_directory": res["output_directory"],
                "html_report": res.get("html_report"),
                "json_report": res.get("json_report"),
                "summary": s,
                "error": None,
            })
            if item_callback:
                try:
                    item_callback(idx, total, pdf_file, "success", res)
                except Exception:
                    pass

        except Exception as exc:
            failed += 1
            err_msg = str(exc)
            items_results.append({
                "source_pdf": str(pdf_file),
                "file_name": pdf_file.name,
                "status": "error",
                "output_directory": None,
                "html_report": None,
                "json_report": None,
                "summary": None,
                "error": err_msg,
            })
            if item_callback:
                try:
                    item_callback(idx, total, pdf_file, "error", err_msg)
                except Exception:
                    pass

    if progress_callback:
        try:
            progress_callback(f"Batch completato: {succeeded}/{total} PDF elaborati.", 1.0)
        except Exception:
            pass

    return {
        "mode": "batch",
        "output_directory": str(base_dir),
        "total_files": total,
        "succeeded": succeeded,
        "failed": failed,
        "items": items_results,
        "aggregate_summary": {
            "total_pages": agg_pages,
            "total_images": agg_images,
            "total_fonts": agg_fonts,
            "embedded_fonts": agg_embedded_fonts,
            "vector_pages_count": agg_vectors,
            "color_profiles_count": agg_profiles,
            "attachments_count": agg_attachments,
        },
    }

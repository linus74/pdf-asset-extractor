"""
Tests for PDF Asset & Metadata Extractor
"""

import io
import shutil
from pathlib import Path
import pytest
import pymupdf
import pikepdf
from PIL import Image, ImageDraw

from pdf_extractor.core import (
    extract_pdf_assets,
    extract_batch_pdfs,
    collect_pdf_paths,
    inspect_pdf_preflight,
)
from pdf_extractor.utils.paper_sizes import identify_paper_size, points_to_mm
from pdf_extractor.utils.helpers import parse_pdf_date, sanitize_filename, format_bytes


def create_comprehensive_test_pdf(filepath: Path) -> Path:
    """Creates a synthetic PDF containing images (RGB + transparent PNG), attachments, and metadata."""
    doc = pymupdf.open()

    # Page 1: A4 (595.28 x 841.89 pt)
    page1 = doc.new_page(width=595.28, height=841.89)

    # Insert text
    page1.insert_text((50, 72), "Sample Document with Embedded Assets", fontsize=16)
    page1.insert_text((50, 100), "This is a test paragraph for font and text metric extraction.", fontsize=12)

    # Create & insert image 1 (JPEG)
    img1 = Image.new("RGB", (300, 200), color=(60, 120, 240))
    d1 = ImageDraw.Draw(img1)
    d1.rectangle([30, 30, 270, 170], fill=(240, 180, 50))
    img1_io = io.BytesIO()
    img1.save(img1_io, format="JPEG")
    page1.insert_image(pymupdf.Rect(50, 150, 350, 350), stream=img1_io.getvalue())

    # Create & insert image 2 (RGBA transparent PNG)
    img2 = Image.new("RGBA", (180, 180), color=(0, 0, 0, 0))
    d2 = ImageDraw.Draw(img2)
    d2.ellipse([10, 10, 170, 170], fill=(220, 40, 100, 210))
    img2_io = io.BytesIO()
    img2.save(img2_io, format="PNG")
    page1.insert_image(pymupdf.Rect(50, 400, 230, 580), stream=img2_io.getvalue())

    # Page 2: US Letter (612 x 792 pt)
    page2 = doc.new_page(width=612.0, height=792.0)
    page2.insert_text((50, 72), "Page 2: Prepress & Attachments", fontsize=14)

    # Draw vector graphics on page 2
    shape = page2.new_shape()
    shape.draw_rect(pymupdf.Rect(50, 120, 250, 220))
    shape.draw_circle((350, 170), 50)
    shape.finish(color=(1, 0, 0), fill=(0, 0.6, 0.9), width=2)
    shape.commit()

    # Add embedded file attachment
    csv_bytes = b"id,name,value\n1,alpha,42\n2,beta,99\n3,gamma,150"
    doc.embfile_add(
        "dataset.csv",
        csv_bytes,
        filename="dataset.csv",
        ufilename="dataset.csv",
        desc="Tabular test dataset"
    )

    # Metadata
    doc.set_metadata({
        "title": "Comprehensive Test Document",
        "author": "Antigravity Test Suite",
        "subject": "Asset Extraction Verification",
        "keywords": "test, assets, extraction, font, images",
        "creator": "Adobe InDesign 2024 (Simulated)",
        "producer": "Adobe PDF Library 17.0 (Simulated)",
    })

    doc.save(str(filepath))
    doc.close()
    return filepath


def test_paper_sizes():
    name, orient = identify_paper_size(595.28, 841.89)
    assert name == "A4"
    assert orient == "Portrait"

    name, orient = identify_paper_size(841.89, 595.28)
    assert name == "A4"
    assert orient == "Landscape"

    name, orient = identify_paper_size(612.0, 792.0)
    assert name == "Letter"
    assert orient == "Portrait"


def test_helpers():
    assert sanitize_filename('test:file/name?.pdf') == "test_file_name_.pdf"
    assert format_bytes(500) == "500 B"
    assert format_bytes(2048) == "2.0 KB"
    assert format_bytes(1048576 * 2) == "2.00 MB"

    iso = parse_pdf_date("D:20240315143000+01'00'")
    assert iso is not None
    assert "2024-03-15" in iso


def test_full_extraction(tmp_path):
    pdf_path = tmp_path / "test_doc.pdf"
    create_comprehensive_test_pdf(pdf_path)

    base_dir = tmp_path / "extracted_assets"
    result = extract_pdf_assets(pdf_path, output_dir=base_dir)
    out_dir = Path(result["output_directory"])
    assert out_dir == base_dir / "test_doc_estratto"

    # Assert summary
    assert result["summary"]["total_pages"] == 2
    assert result["summary"]["total_images"] >= 2
    assert result["summary"]["attachments_count"] == 1

    # Assert metadata
    meta = result["metadata"]
    assert meta["title"] == "Comprehensive Test Document"
    assert meta["creator"] == "Adobe InDesign 2024 (Simulated)"
    assert meta["producer"] == "Adobe PDF Library 17.0 (Simulated)"

    # Assert page geometry
    pages = result["pages"]
    assert len(pages) == 2
    assert pages[0]["mediabox"]["matched_size"] == "A4"
    assert pages[1]["mediabox"]["matched_size"] == "Letter"

    # Assert images extracted and files exist on disk
    imgs = result["images"]
    assert len(imgs) >= 2
    for img in imgs:
        img_path = out_dir / Path(img["filename"])
        assert img_path.exists(), f"Image file {img_path} was not created"
        assert img["width"] > 0
        assert img["height"] > 0

    # Assert attachments extracted
    attaches = result["attachments"]
    assert len(attaches) == 1
    assert attaches[0]["original_name"] == "dataset.csv"
    att_path = out_dir / Path(attaches[0]["filename"])
    assert att_path.exists()
    assert att_path.read_bytes().startswith(b"id,name,value")

    # Assert vector graphics extracted (.svg and .ai)
    vectors = result["vectors"]
    assert len(vectors) >= 1
    v_item = [v for v in vectors if v["page"] == 2][0]
    assert v_item["paths_count"] >= 1
    svg_path = out_dir / Path(v_item["svg_file"])
    assert svg_path.exists(), "SVG vector file was not created"
    assert "<svg" in svg_path.read_text(encoding="utf-8")
    ai_path = out_dir / Path(v_item["ai_file"])
    assert ai_path.exists(), "Adobe Illustrator (.ai) vector file was not created"
    assert ai_path.stat().st_size > 0

    # Assert JSON & HTML reports generated
    assert (out_dir / "report.json").exists()
    assert (out_dir / "report.html").exists()
    assert (out_dir / "metadata" / "doc_info.json").exists()


def test_preflight_and_progress_callback(tmp_path):
    pdf_path = tmp_path / "preflight_doc.pdf"
    create_comprehensive_test_pdf(pdf_path)

    pre = inspect_pdf_preflight(pdf_path)
    assert pre["total_pages"] == 2
    assert "A4" in pre["paper_format"]
    assert pre["creator"] == "Adobe InDesign 2024 (Simulated)"
    assert pre["thumbnail"] is not None
    assert pre["unlocked"] is True

    events = []
    base_dir = tmp_path / "out_cb"
    res = extract_pdf_assets(
        pdf_path,
        output_dir=base_dir,
        generate_html=False,
        progress_callback=lambda msg, pct: events.append((msg, pct))
    )
    out_dir = Path(res["output_directory"])
    assert out_dir == base_dir / "preflight_doc_estratto"
    assert len(events) >= 5
    assert events[-1][1] == 1.0
    assert not (out_dir / "report.html").exists()
    assert (out_dir / "report.json").exists()


def test_unique_parent_folder_increment(tmp_path):
    pdf_path = tmp_path / "catalog.pdf"
    create_comprehensive_test_pdf(pdf_path)

    base_dir = tmp_path / "dest"
    r1 = extract_pdf_assets(pdf_path, output_dir=base_dir, generate_html=False)
    r2 = extract_pdf_assets(pdf_path, output_dir=base_dir, generate_html=False)
    r3 = extract_pdf_assets(pdf_path, output_dir=base_dir, generate_html=False)

    assert Path(r1["output_directory"]) == base_dir / "catalog_estratto"
    assert Path(r2["output_directory"]) == base_dir / "catalog_estratto_2"
    assert Path(r3["output_directory"]) == base_dir / "catalog_estratto_3"
    assert (Path(r1["output_directory"]) / "report.json").exists()
    assert (Path(r2["output_directory"]) / "report.json").exists()
    assert (Path(r3["output_directory"]) / "report.json").exists()


def test_batch_extraction(tmp_path):
    in_dir = tmp_path / "inputs"
    in_dir.mkdir()

    pdf_a = create_comprehensive_test_pdf(in_dir / "alpha.pdf")
    pdf_b = create_comprehensive_test_pdf(in_dir / "beta.pdf")
    # Non-PDF file in same folder should be ignored by collect_pdf_paths
    (in_dir / "notes.txt").write_text("ignore me", encoding="utf-8")
    # Corrupt PDF to test error isolation in batch
    bad_pdf = in_dir / "corrupt.pdf"
    bad_pdf.write_bytes(b"not a valid pdf content")

    collected = collect_pdf_paths([in_dir])
    assert len(collected) == 3

    out_base = tmp_path / "batch_out"
    statuses = []
    batch_res = extract_batch_pdfs(
        pdf_paths=collected,
        output_dir=out_base,
        generate_html=False,
        item_callback=lambda idx, tot, p, st, payload: statuses.append((p.name, st)),
    )

    assert batch_res["total_files"] == 3
    assert batch_res["succeeded"] == 2
    assert batch_res["failed"] == 1
    assert (out_base / "alpha_estratto" / "report.json").exists()
    assert (out_base / "beta_estratto" / "report.json").exists()
    assert ("corrupt.pdf", "error") in statuses
    assert ("alpha.pdf", "success") in statuses


def test_batch_html_report_and_non_overwrite(tmp_path):
    in_dir = tmp_path / "batch_in"
    in_dir.mkdir()
    p1 = create_comprehensive_test_pdf(in_dir / "one.pdf")
    p2 = create_comprehensive_test_pdf(in_dir / "two.pdf")

    out_base = tmp_path / "batch_html_out"
    b1 = extract_batch_pdfs([p1, p2], output_dir=out_base, generate_html=True)
    b2 = extract_batch_pdfs([p1, p2], output_dir=out_base, generate_html=True)

    r1 = Path(b1["html_report"])
    r2 = Path(b2["html_report"])
    assert r1.exists() and r1.name == "batch_report.html"
    assert r2.exists() and r2.name == "batch_report_2.html"

    html_txt = r1.read_text(encoding="utf-8")
    assert "one_estratto/report.html" in html_txt
    assert "two_estratto/report.html" in html_txt
    assert "one.pdf" in html_txt
    assert "two.pdf" in html_txt

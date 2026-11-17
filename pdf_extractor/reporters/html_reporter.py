"""
HTML Reporter: generates an elegant, standalone, offline-capable dashboard (report.html).
Includes image gallery, font inspector, ICC profile viewer, page geometry explorer, and XMP viewer.
"""

import html
import json
from datetime import datetime
from urllib.parse import quote
from pathlib import Path
from typing import Dict, Any


def generate_html_report(data: Dict[str, Any], output_dir: Path) -> Path:
    """
    Renders standalone interactive HTML report to `output_dir / "report.html"`.
    """
    report_file = output_dir / "report.html"

    doc_info = data.get("metadata", {})
    images = data.get("images", [])
    fonts = data.get("fonts", [])
    profiles_data = data.get("color_management", {})
    profiles = profiles_data.get("profiles", [])
    spot_colors = profiles_data.get("spot_colors", [])
    pages = data.get("pages", [])
    attachments = data.get("attachments", [])
    summary = data.get("summary", {})

    title = html.escape(doc_info.get("title") or Path(data.get("source_pdf", "Document")).name)
    creator = html.escape(doc_info.get("creator") or "Non specificato")
    producer = html.escape(doc_info.get("producer") or "Non specificato")
    pdf_version = html.escape(doc_info.get("pdf_version") or doc_info.get("pdf_format") or "PDF")
    created = html.escape(doc_info.get("creation_date") or doc_info.get("creation_date_raw") or "N/D")
    modified = html.escape(doc_info.get("modification_date") or doc_info.get("modification_date_raw") or "N/D")

    standards = doc_info.get("standards", {})
    std_badges = []
    if standards.get("pdf_a"):
        std_badges.append(f'<span class="badge badge-accent">{html.escape(standards["pdf_a"])}</span>')
    if standards.get("pdf_x"):
        std_badges.append(f'<span class="badge badge-warning">{html.escape(standards["pdf_x"])}</span>')
    if standards.get("pdf_ua"):
        std_badges.append(f'<span class="badge badge-info">{html.escape(standards["pdf_ua"])}</span>')

    # Security badge
    sec = doc_info.get("security", {})
    sec_badge = (
        '<span class="badge badge-danger">Protetto da Password / Crittografato</span>'
        if sec.get("is_encrypted")
        else '<span class="badge badge-success">Nessuna Crittografia (Aperto)</span>'
    )

    # Images cards HTML
    images_cards_html = []
    for img in images:
        f_name = html.escape(img.get("filename", ""))
        fmt = html.escape(img.get("format", ""))
        w = img.get("width", 0)
        h = img.get("height", 0)
        cs = html.escape(str(img.get("colorspace", "")))
        sz = html.escape(img.get("file_size", ""))
        alpha = "Sì (SMask)" if img.get("has_transparency") else "No"
        dpi_val = img.get("effective_dpi")
        dpi_badge = f'<span class="tag tag-dpi">{dpi_val} DPI</span>' if dpi_val else '<span class="tag">DPI N/D</span>'
        pages_str = ", ".join(str(p) for p in img.get("pages", []))

        images_cards_html.append(f"""
        <div class="card img-card" onclick="openModal('{f_name}', '{w}x{h} px', '{fmt}', '{sz}', '{cs}')">
          <div class="img-preview-box">
            <img src="{f_name}" alt="{f_name}" loading="lazy" />
          </div>
          <div class="card-body">
            <div class="card-header-row">
              <span class="badge badge-dark">{fmt}</span>
              {dpi_badge}
            </div>
            <div class="card-title-text" title="{f_name}">{Path(f_name).name}</div>
            <div class="card-meta-grid">
              <div><strong>Dim.:</strong> {w} &times; {h} px</div>
              <div><strong>Peso:</strong> {sz}</div>
              <div><strong>Spazio:</strong> {cs}</div>
              <div><strong>Alpha:</strong> {alpha}</div>
            </div>
            <div class="card-footer-pages">Pagine: {pages_str}</div>
            <a href="{f_name}" download class="btn-download" onclick="event.stopPropagation()">Scarica Immagine</a>
          </div>
        </div>
        """)

    # Fonts rows HTML
    fonts_rows_html = []
    for f in fonts:
        base = html.escape(f.get("basefont", ""))
        clean = html.escape(f.get("clean_name", ""))
        sub = html.escape(f.get("subtype", ""))
        enc = html.escape(f.get("encoding", ""))
        is_sub = f.get("is_subset", False)
        sub_tag = html.escape(f.get("subset_tag") or "")
        is_emb = f.get("is_embedded", False)
        saved = f.get("saved_file")
        glyphs = f.get("glyph_count")
        glyphs_str = str(glyphs) if glyphs is not None else "N/D"
        sz_str = f.get("file_size") or "-"
        pages_str = ", ".join(str(p) for p in f.get("pages", []))

        inst_status = f.get("install_status", "unknown")
        chars_sample = html.escape(f.get("chars_sample") or "")
        chars_cnt = f.get("chars_count", 0)

        if inst_status == "full":
            status_badge = '<span class="badge badge-success" title="Installabile e utilizzabile al 100% per qualsiasi testo">🟢 Font Completo</span>'
        elif inst_status == "subset":
            status_badge = f'<span class="badge badge-warning" title="Installabile nel sistema operativo, ma contiene solo i glifi estratti dal PDF">🟡 Sottinsieme ({chars_cnt} caratteri)</span>'
        elif is_emb:
            status_badge = '<span class="badge badge-info">Incorporato</span>'
        else:
            status_badge = '<span class="badge badge-neutral">Di Sistema (Non estraibile)</span>'

        dl_link = f'<a href="{saved}" download class="btn-sm">Scarica ({Path(saved).suffix})</a>' if saved else '<span class="text-muted">-</span>'

        sample_box = f'<div class="chars-sample-box font-code" title="Campione caratteri disponibili: {chars_sample}">{chars_sample}</div>' if chars_sample else '<span class="text-muted font-code">-</span>'

        flags_obj = f.get("flags", {})
        flag_tags = []
        if flags_obj.get("italic"): flag_tags.append("Corsivo")
        if flags_obj.get("force_bold"): flag_tags.append("Grassetto")
        if flags_obj.get("fixed_pitch"): flag_tags.append("Monospazio")
        if flags_obj.get("serif"): flag_tags.append("Serif")
        flags_str = ", ".join(flag_tags) if flag_tags else "Normale"

        fonts_rows_html.append(f"""
        <tr>
          <td>
            <strong>{clean}</strong>
            <div class="text-muted font-code">{base}</div>
          </td>
          <td><span class="tag">{sub}</span></td>
          <td>{status_badge}</td>
          <td>{sample_box}</td>
          <td>{glyphs_str}</td>
          <td>{sz_str}</td>
          <td><small>{flags_str}</small></td>
          <td><small>{pages_str}</small></td>
          <td>{dl_link}</td>
        </tr>
        """)

    # Profiles HTML
    profiles_rows_html = []
    for p in profiles:
        p_name = html.escape(p.get("description", ""))
        p_cs = html.escape(p.get("color_space", ""))
        p_dev = html.escape(p.get("device_class", ""))
        p_ver = html.escape(p.get("version", ""))
        p_sz = html.escape(p.get("file_size", ""))
        p_file = html.escape(p.get("filename", ""))
        profiles_rows_html.append(f"""
        <tr>
          <td><strong>{p_name}</strong></td>
          <td><span class="badge badge-info">{p_cs}</span></td>
          <td>{p_dev}</td>
          <td>{p_ver}</td>
          <td>{p_sz}</td>
          <td><a href="{p_file}" download class="btn-sm">Scarica .ICC</a></td>
        </tr>
        """)

    # Spot colors tags
    spot_tags_html = []
    for sc in spot_colors:
        spot_tags_html.append(f'<div class="spot-color-pill"><span class="spot-indicator"></span> {html.escape(sc)}</div>')
    if not spot_tags_html:
        spot_tags_html.append('<div class="text-muted">Nessun colore speciale / spot rilevato nel documento.</div>')

    # Pages rows HTML
    pages_rows_html = []
    for pg in pages:
        p_num = pg.get("page_number")
        p_lbl = html.escape(pg.get("page_label", str(p_num)))
        rot = pg.get("rotation", 0)

        mb = pg.get("mediabox") or {}
        tb = pg.get("trimbox") or {}
        bb = pg.get("bleedbox") or {}

        mb_name = html.escape(mb.get("matched_size", "N/D"))
        mb_orient = html.escape(mb.get("orientation", ""))
        mb_mm = f"{mb.get('width_mm', 0)} &times; {mb.get('height_mm', 0)} mm"
        mb_pt = f"{mb.get('width_pt', 0)} &times; {mb.get('height_pt', 0)} pt"

        tb_mm = f"{tb.get('width_mm', '-')} &times; {tb.get('height_mm', '-')} mm" if tb else "-"
        bb_mm = f"{bb.get('width_mm', '-')} &times; {bb.get('height_mm', '-')} mm" if bb else "-"

        stats = pg.get("stats", {})
        imgs_cnt = stats.get("images_count", 0)
        fnts_cnt = stats.get("fonts_count", 0)
        draws_cnt = stats.get("vector_drawings_count", 0)
        words_cnt = stats.get("word_count", 0)

        pages_rows_html.append(f"""
        <tr>
          <td><strong>Pagina {p_num}</strong> ({p_lbl})</td>
          <td>
            <strong>{mb_name}</strong> ({mb_orient})
            <div class="text-muted">{mb_mm} &bull; {mb_pt}</div>
          </td>
          <td>{tb_mm}</td>
          <td>{bb_mm}</td>
          <td>{rot}&deg;</td>
          <td><span class="badge badge-dark">{imgs_cnt}</span></td>
          <td><span class="badge badge-dark">{fnts_cnt}</span></td>
          <td>{draws_cnt}</td>
          <td>{words_cnt}</td>
        </tr>
        """)

    # Attachments rows HTML
    attachments_rows_html = []
    for att in attachments:
        a_name = html.escape(att.get("original_name", ""))
        a_desc = html.escape(att.get("description", ""))
        a_sz = html.escape(att.get("file_size", ""))
        a_src = html.escape(att.get("source", ""))
        a_file = html.escape(att.get("filename", ""))
        attachments_rows_html.append(f"""
        <tr>
          <td><strong>{a_name}</strong></td>
          <td>{a_desc or '<span class=\"text-muted\">-</span>'}</td>
          <td>{a_sz}</td>
          <td>{a_src}</td>
          <td><a href="{a_file}" download class="btn-sm">Scarica File</a></td>
        </tr>
        """)

    # Vectors rows HTML
    vectors = data.get("vectors", [])
    vectors_rows_html = []
    for v in vectors:
        p_num = v.get("page")
        svg_f = html.escape(v.get("svg_file") or "")
        ai_f = html.escape(v.get("ai_file") or "")
        paths_c = v.get("paths_count", 0)
        lines_c = v.get("lines_count", 0)
        curves_c = v.get("curves_count", 0)
        rects_c = v.get("rectangles_count", 0)
        svg_sz = html.escape(v.get("svg_size", "-"))
        ai_sz = html.escape(v.get("ai_size", "-"))

        swatches = []
        for hex_col in v.get("colors_used", []):
            swatches.append(f'<span class="color-dot" style="background-color: {html.escape(hex_col)};" title="{html.escape(hex_col)}"></span>')
        swatches_html = "".join(swatches) if swatches else '<span class="text-muted">-</span>'

        dl_svg = f'<a href="{svg_f}" download class="btn-sm">Scarica .SVG ({svg_sz})</a>' if svg_f else "-"
        dl_ai = f'<a href="{ai_f}" download class="btn-sm" style="background: rgba(245, 158, 11, 0.2); color: #fcd34d; border: 1px solid rgba(245, 158, 11, 0.4);">Scarica .AI ({ai_sz})</a>' if ai_f else "-"

        vectors_rows_html.append(f"""
        <tr>
          <td><strong>Pagina {p_num}</strong></td>
          <td><span class="badge badge-accent">{paths_c} tracciati</span></td>
          <td><small>Curve B&eacute;zier: {curves_c} &bull; Linee: {lines_c} &bull; Rettangoli: {rects_c}</small></td>
          <td><div class="swatches-wrap">{swatches_html}</div></td>
          <td>
            <div style="display:flex; gap:8px;">
              {dl_svg}
              {dl_ai}
            </div>
          </td>
        </tr>
        """)

    # XMP metadata XML content
    xmp_path = output_dir / "metadata" / "xmp_metadata.xml"
    xmp_content = ""
    if xmp_path.exists():
        try:
            with open(xmp_path, "r", encoding="utf-8", errors="ignore") as f:
                xmp_content = html.escape(f.read())
        except Exception:
            xmp_content = "Impossibile leggere file XMP."

    html_template = f"""<!DOCTYPE html>
<html lang="it">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>PDF Asset & Metadata Report: {title}</title>
  <style>
    :root {{
      --bg: #0f172a;
      --card-bg: #1e293b;
      --card-border: #334155;
      --text-main: #f8fafc;
      --text-muted: #94a3b8;
      --primary: #38bdf8;
      --primary-hover: #0284c7;
      --accent: #a855f7;
      --success: #22c55e;
      --warning: #f59e0b;
      --danger: #ef4444;
      --radius: 12px;
      --shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.4);
    }}
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
      background: var(--bg);
      color: var(--text-main);
      padding: 30px 20px;
      line-height: 1.5;
    }}
    .container {{
      max-width: 1400px;
      margin: 0 auto;
    }}
    header {{
      background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
      border: 1px solid var(--card-border);
      border-radius: var(--radius);
      padding: 30px;
      margin-bottom: 25px;
      box-shadow: var(--shadow);
    }}
    .header-top {{
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      flex-wrap: wrap;
      gap: 15px;
      margin-bottom: 20px;
    }}
    h1 {{
      font-size: 26px;
      font-weight: 700;
      color: #fff;
      display: flex;
      align-items: center;
      gap: 12px;
    }}
    .header-badges {{
      display: flex;
      gap: 8px;
      flex-wrap: wrap;
    }}
    .badge {{
      display: inline-block;
      padding: 4px 10px;
      border-radius: 9999px;
      font-size: 12px;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.5px;
    }}
    .badge-accent {{ background: rgba(168, 85, 247, 0.2); color: #d8b4fe; border: 1px solid rgba(168, 85, 247, 0.4); }}
    .badge-warning {{ background: rgba(245, 158, 11, 0.2); color: #fcd34d; border: 1px solid rgba(245, 158, 11, 0.4); }}
    .badge-info {{ background: rgba(56, 189, 248, 0.2); color: #7dd3fc; border: 1px solid rgba(56, 189, 248, 0.4); }}
    .badge-success {{ background: rgba(34, 197, 94, 0.2); color: #86efac; border: 1px solid rgba(34, 197, 94, 0.4); }}
    .badge-danger {{ background: rgba(239, 68, 68, 0.2); color: #fca5a5; border: 1px solid rgba(239, 68, 68, 0.4); }}
    .badge-neutral {{ background: rgba(148, 163, 184, 0.2); color: #cbd5e1; border: 1px solid rgba(148, 163, 184, 0.4); }}
    .badge-dark {{ background: #334155; color: #f8fafc; }}

    .meta-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
      gap: 15px;
      font-size: 14px;
      background: rgba(15, 23, 42, 0.6);
      padding: 18px;
      border-radius: 8px;
      border: 1px solid rgba(255, 255, 255, 0.05);
    }}
    .meta-item strong {{ color: #cbd5e1; }}

    /* KPI STATS CARDS */
    .kpi-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
      gap: 15px;
      margin-bottom: 30px;
    }}
    .kpi-card {{
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      border-radius: var(--radius);
      padding: 20px;
      text-align: center;
      box-shadow: var(--shadow);
    }}
    .kpi-val {{
      font-size: 32px;
      font-weight: 800;
      color: var(--primary);
      margin-bottom: 5px;
    }}
    .kpi-label {{
      font-size: 13px;
      color: var(--text-muted);
      text-transform: uppercase;
      font-weight: 600;
    }}

    /* TABS */
    .tabs-nav {{
      display: flex;
      gap: 10px;
      border-bottom: 2px solid var(--card-border);
      margin-bottom: 25px;
      overflow-x: auto;
      padding-bottom: 2px;
    }}
    .tab-btn {{
      background: transparent;
      border: none;
      color: var(--text-muted);
      font-size: 15px;
      font-weight: 600;
      padding: 10px 18px;
      border-radius: 8px 8px 0 0;
      cursor: pointer;
      display: flex;
      align-items: center;
      gap: 8px;
      transition: all 0.2s ease;
      white-space: nowrap;
    }}
    .tab-btn:hover {{
      color: #fff;
      background: rgba(255, 255, 255, 0.05);
    }}
    .tab-btn.active {{
      color: var(--primary);
      border-bottom: 3px solid var(--primary);
      background: rgba(56, 189, 248, 0.08);
    }}

    .tab-pane {{
      display: none;
    }}
    .tab-pane.active {{
      display: block;
      animation: fadeIn 0.3s ease;
    }}
    @keyframes fadeIn {{
      from {{ opacity: 0; transform: translateY(6px); }}
      to {{ opacity: 1; transform: translateY(0); }}
    }}

    /* IMAGE GALLERY */
    .gallery-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
      gap: 20px;
    }}
    .img-card {{
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      border-radius: var(--radius);
      overflow: hidden;
      cursor: pointer;
      transition: transform 0.2s ease, border-color 0.2s ease;
      box-shadow: var(--shadow);
      display: flex;
      flex-direction: column;
    }}
    .img-card:hover {{
      transform: translateY(-4px);
      border-color: var(--primary);
    }}
    .img-preview-box {{
      height: 200px;
      background: #090d16 repeating-conic-gradient(#151d2e 0% 25%, #0e1422 0% 50%) 50% / 20px 20px;
      display: flex;
      align-items: center;
      justify-content: center;
      overflow: hidden;
      padding: 10px;
    }}
    .img-preview-box img {{
      max-width: 100%;
      max-height: 100%;
      object-fit: contain;
    }}
    .card-body {{
      padding: 16px;
      display: flex;
      flex-direction: column;
      flex-grow: 1;
    }}
    .card-header-row {{
      display: flex;
      justify-content: space-between;
      margin-bottom: 8px;
    }}
    .card-title-text {{
      font-weight: 600;
      font-size: 14px;
      margin-bottom: 10px;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }}
    .card-meta-grid {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 6px;
      font-size: 12px;
      color: var(--text-muted);
      margin-bottom: 12px;
    }}
    .card-footer-pages {{
      font-size: 12px;
      color: var(--text-muted);
      margin-bottom: 14px;
    }}
    .btn-download {{
      display: block;
      text-align: center;
      background: rgba(56, 189, 248, 0.15);
      color: var(--primary);
      text-decoration: none;
      padding: 8px;
      border-radius: 6px;
      font-size: 13px;
      font-weight: 600;
      transition: background 0.2s;
      margin-top: auto;
    }}
    .btn-download:hover {{
      background: var(--primary);
      color: #0f172a;
    }}

    /* TABLES */
    .table-container {{
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      border-radius: var(--radius);
      overflow-x: auto;
      box-shadow: var(--shadow);
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      font-size: 14px;
      text-align: left;
    }}
    th, td {{
      padding: 12px 16px;
      border-bottom: 1px solid var(--card-border);
    }}
    th {{
      background: rgba(15, 23, 42, 0.7);
      font-weight: 600;
      color: #cbd5e1;
    }}
    tr:last-child td {{
      border-bottom: none;
    }}
    tr:hover td {{
      background: rgba(255, 255, 255, 0.02);
    }}
    .btn-sm {{
      display: inline-block;
      padding: 4px 10px;
      background: rgba(56, 189, 248, 0.15);
      color: var(--primary);
      border-radius: 4px;
      text-decoration: none;
      font-size: 12px;
      font-weight: 600;
    }}
    .btn-sm:hover {{
      background: var(--primary);
      color: #0f172a;
    }}
    .tag {{
      display: inline-block;
      padding: 2px 8px;
      border-radius: 4px;
      background: #334155;
      font-size: 12px;
      color: #e2e8f0;
    }}
    .tag-dpi {{
      background: rgba(34, 197, 94, 0.2);
      color: #86efac;
      font-weight: 600;
    }}
    .font-code {{
      font-family: monospace;
      font-size: 12px;
    }}
    .chars-sample-box {{
      max-width: 170px;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
      color: #7dd3fc;
      background: rgba(56, 189, 248, 0.08);
      padding: 2px 6px;
      border-radius: 4px;
      border: 1px solid rgba(56, 189, 248, 0.2);
    }}

    /* SPOT COLORS */
    .spot-colors-container {{
      display: flex;
      flex-wrap: wrap;
      gap: 12px;
      margin-top: 15px;
    }}
    .spot-color-pill {{
      display: flex;
      align-items: center;
      gap: 8px;
      background: #1e293b;
      border: 1px solid var(--card-border);
      padding: 8px 16px;
      border-radius: 8px;
      font-weight: 600;
      font-size: 14px;
    }}
    .spot-indicator {{
      width: 12px;
      height: 12px;
      border-radius: 50%;
      background: linear-gradient(135deg, #f59e0b, #ec4899);
      box-shadow: 0 0 8px rgba(245, 158, 11, 0.6);
    }}

    /* COLOR SWATCHES */
    .swatches-wrap {{
      display: flex;
      gap: 5px;
      flex-wrap: wrap;
      align-items: center;
    }}
    .color-dot {{
      width: 14px;
      height: 14px;
      border-radius: 50%;
      border: 1px solid rgba(255, 255, 255, 0.3);
      display: inline-block;
    }}

    /* XML CODE PREVIEW */
    pre.code-block {{
      background: #090d16;
      border: 1px solid var(--card-border);
      border-radius: var(--radius);
      padding: 20px;
      overflow-x: auto;
      font-family: Consolas, Monaco, "Courier New", monospace;
      font-size: 13px;
      color: #93c5fd;
      line-height: 1.6;
      max-height: 600px;
    }}

    /* MODAL */
    .modal {{
      display: none;
      position: fixed;
      z-index: 1000;
      left: 0;
      top: 0;
      width: 100%;
      height: 100%;
      background: rgba(0, 0, 0, 0.85);
      align-items: center;
      justify-content: center;
      padding: 20px;
    }}
    .modal-content {{
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      border-radius: var(--radius);
      max-width: 900px;
      width: 100%;
      max-height: 90vh;
      display: flex;
      flex-direction: column;
      overflow: hidden;
      box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.7);
    }}
    .modal-header {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 15px 20px;
      border-bottom: 1px solid var(--card-border);
    }}
    .modal-close {{
      font-size: 24px;
      background: none;
      border: none;
      color: var(--text-muted);
      cursor: pointer;
    }}
    .modal-close:hover {{ color: #fff; }}
    .modal-img-wrap {{
      flex-grow: 1;
      background: #090d16 repeating-conic-gradient(#151d2e 0% 25%, #0e1422 0% 50%) 50% / 20px 20px;
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 20px;
      max-height: 65vh;
      overflow: auto;
    }}
    .modal-img-wrap img {{
      max-width: 100%;
      max-height: 60vh;
      object-fit: contain;
    }}
    .modal-footer {{
      padding: 15px 20px;
      border-top: 1px solid var(--card-border);
      display: flex;
      justify-content: space-between;
      align-items: center;
      font-size: 13px;
    }}
    .empty-state {{
      text-align: center;
      padding: 40px;
      color: var(--text-muted);
    }}
  </style>
</head>
<body>

  <div class="container">
    <header>
      <div class="header-top">
        <div>
          <h1>📄 {title}</h1>
          <p style="color: var(--text-muted); font-size: 14px; margin-top: 4px;">Report Completo di Estrazione Risorse e Metadati</p>
        </div>
        <div class="header-badges">
          <span class="badge badge-info">{pdf_version}</span>
          {' '.join(std_badges)}
          {sec_badge}
        </div>
      </div>

      <div class="meta-grid">
        <div class="meta-item"><strong>Software di Creazione:</strong> {creator}</div>
        <div class="meta-item"><strong>Motore di Generazione (Producer):</strong> {producer}</div>
        <div class="meta-item"><strong>Data di Creazione:</strong> {created}</div>
        <div class="meta-item"><strong>Ultima Modifica:</strong> {modified}</div>
        <div class="meta-item"><strong>Autore / Soggetto:</strong> {html.escape(doc_info.get("author") or "N/D")} / {html.escape(doc_info.get("subject") or "N/D")}</div>
        <div class="meta-item"><strong>Trapped:</strong> {html.escape(str(doc_info.get("trapped") or "Non definito"))}</div>
      </div>
    </header>

    <!-- KPI STATS CARDS -->
    <div class="kpi-grid">
      <div class="kpi-card">
        <div class="kpi-val">{summary.get("total_pages", len(pages))}</div>
        <div class="kpi-label">Pagine Totali</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-val">{summary.get("total_images", len(images))}</div>
        <div class="kpi-label">Immagini Estratte</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-val">{len(vectors)}</div>
        <div class="kpi-label">Vettoriali (.SVG / .AI)</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-val">{summary.get("total_fonts", len(fonts))}</div>
        <div class="kpi-label">Font Censiti ({summary.get("embedded_fonts", 0)} incorporati)</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-val">{len(profiles)}</div>
        <div class="kpi-label">Profili ICC</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-val">{len(spot_colors)}</div>
        <div class="kpi-label">Colori Speciali (Spot)</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-val">{len(attachments)}</div>
        <div class="kpi-label">File Allegati</div>
      </div>
    </div>

    <!-- TABS NAVIGATION -->
    <div class="tabs-nav">
      <button class="tab-btn active" onclick="showTab('images')">🖼️ Immagini ({len(images)})</button>
      <button class="tab-btn" onclick="showTab('vectors')">📐 Vettoriali ({len(vectors)})</button>
      <button class="tab-btn" onclick="showTab('fonts')">🔤 Font ({len(fonts)})</button>
      <button class="tab-btn" onclick="showTab('profiles')">🎨 Profili Colore & Inchiostri</button>
      <button class="tab-btn" onclick="showTab('pages')">📏 Dimensioni & Pre-stampa ({len(pages)})</button>
      <button class="tab-btn" onclick="showTab('attachments')">📎 Allegati ({len(attachments)})</button>
      <button class="tab-btn" onclick="showTab('xmp')">ℹ️ Metadati & XMP</button>
    </div>

    <!-- TAB: IMAGES -->
    <div id="tab-images" class="tab-pane active">
      {'<div class="gallery-grid">' + ''.join(images_cards_html) + '</div>' if images_cards_html else '<div class="empty-state">Nessuna immagine raster incorporata trovata in questo PDF.</div>'}
    </div>

    <!-- TAB: VECTORS -->
    <div id="tab-vectors" class="tab-pane">
      <h3 style="margin-bottom: 8px; font-size: 18px;">Grafica Vettoriale Estratta (.SVG e Adobe Illustrator .AI)</h3>
      <p style="color: var(--text-muted); font-size: 14px; margin-bottom: 20px;">
        I file <strong>.SVG</strong> sono universali (compatibili con Figma, Illustrator, Inkscape e Web). I file <strong>.AI</strong> contengono la grafica vettoriale pura senza elementi raster, apribili nativamente in Adobe Illustrator con tutti i tracciati modificabili.
      </p>
      {'<div class="table-container"><table><thead><tr><th>Pagina</th><th>Tracciati Totali</th><th>Dettaglio Geometria</th><th>Colori Rilevati</th><th>Download</th></tr></thead><tbody>' + ''.join(vectors_rows_html) + '</tbody></table></div>' if vectors_rows_html else '<div class="empty-state">Nessuna grafica vettoriale rilevata nel PDF.</div>'}
    </div>

    <!-- TAB: FONTS -->
    <div id="tab-fonts" class="tab-pane">
      <h3 style="margin-bottom: 6px; font-size: 18px;">Font & Tipografia Censiti</h3>
      <p style="color: var(--text-muted); font-size: 13px; margin-bottom: 18px;">
        I font con stato <strong>🟢 Font Completo</strong> contengono l'intero alfabeto e sono utilizzabili liberamente per comporre qualsiasi testo. I font con stato <strong>🟡 Sottinsieme</strong> contengono esclusivamente i caratteri digitati nel documento originario (tutti gli altri caratteri daranno un glifo vuoto); il nostro tool li convalida e ripara per renderli installabili nel sistema operativo.
      </p>
      {'<div class="table-container"><table><thead><tr><th>Nome Font</th><th>Tipo</th><th>Stato & Installabilità</th><th>Campione Caratteri</th><th>Glifi</th><th>Dimensione</th><th>Attributi</th><th>Pagine</th><th>Download</th></tr></thead><tbody>' + ''.join(fonts_rows_html) + '</tbody></table></div>' if fonts_rows_html else '<div class="empty-state">Nessun font rilevato nel PDF.</div>'}
    </div>

    <!-- TAB: PROFILES -->
    <div id="tab-profiles" class="tab-pane">
      <h3 style="margin-bottom: 12px; font-size: 18px;">Profili ICC Incorporati</h3>
      {'<div class="table-container"><table><thead><tr><th>Descrizione Profilo</th><th>Spazio Colore</th><th>Classe Dispositivo</th><th>Versione</th><th>Dimensione</th><th>Download</th></tr></thead><tbody>' + ''.join(profiles_rows_html) + '</tbody></table></div>' if profiles_rows_html else '<div class="empty-state" style="padding:20px 0;">Nessun profilo ICC incorporato esplicitamente trovato.</div>'}

      <h3 style="margin-top: 35px; margin-bottom: 10px; font-size: 18px;">Colori Speciali (Spot Colors / Separations)</h3>
      <div class="spot-colors-container">
        {''.join(spot_tags_html)}
      </div>
    </div>

    <!-- TAB: PAGES -->
    <div id="tab-pages" class="tab-pane">
      <div class="table-container">
        <table>
          <thead>
            <tr>
              <th>Pagina</th>
              <th>Formato & MediaBox</th>
              <th>TrimBox (Ritaglio)</th>
              <th>BleedBox (Abbondanza)</th>
              <th>Rotazione</th>
              <th>Immagini</th>
              <th>Font</th>
              <th>Tracciati Vettoriali</th>
              <th>Parole</th>
            </tr>
          </thead>
          <tbody>
            {''.join(pages_rows_html)}
          </tbody>
        </table>
      </div>
    </div>

    <!-- TAB: ATTACHMENTS -->
    <div id="tab-attachments" class="tab-pane">
      {'<div class="table-container"><table><thead><tr><th>Nome File</th><th>Descrizione</th><th>Dimensione</th><th>Origine</th><th>Download</th></tr></thead><tbody>' + ''.join(attachments_rows_html) + '</tbody></table></div>' if attachments_rows_html else '<div class="empty-state">Nessun file o allegato incorporato nel PDF.</div>'}
    </div>

    <!-- TAB: XMP METADATA -->
    <div id="tab-xmp" class="tab-pane">
      <h3 style="margin-bottom: 15px; font-size: 18px;">Pacchetto XML Metadati XMP (Adobe Extensible Metadata Platform)</h3>
      {f'<pre class="code-block"><code>{xmp_content}</code></pre>' if xmp_content else '<div class="empty-state">Nessun flusso XMP presente nel PDF.</div>'}
    </div>

    <!-- DISCLAIMER FOOTER -->
    <footer style="margin-top: 50px; padding: 25px 20px; border-top: 1px solid var(--card-border); color: var(--text-muted); font-size: 12px; line-height: 1.6; text-align: center;">
      <p style="font-weight: 600; color: #cbd5e1; margin-bottom: 5px;">⚖️ Note Legali & Utilizzo Responsabile</p>
      <p style="max-width: 850px; margin: 0 auto;">
        Questo strumento è concepito per analisi tecnica, verifica di pre-stampa, audit di accessibilità e recupero dei propri archivi documentali.
        Le immagini, i font, la grafica vettoriale e i marchi estratti possono essere protetti da diritto d'autore, copyright o accordi di licenza commerciale (EULA).
        L'utente è l'unico responsabile di verificare e rispettare le licenze e i diritti di utilizzo prima di riutilizzare o ridistribuire qualsiasi risorsa estratta.
      </p>
    </footer>

  </div>

  <!-- MODAL FOR IMAGES -->
  <div id="imageModal" class="modal" onclick="closeModal()">
    <div class="modal-content" onclick="event.stopPropagation()">
      <div class="modal-header">
        <h4 id="modalTitle">Anteprima Immagine</h4>
        <button class="modal-close" onclick="closeModal()">&times;</button>
      </div>
      <div class="modal-img-wrap">
        <img id="modalImg" src="" alt="Anteprima">
      </div>
      <div class="modal-footer">
        <div id="modalMeta"></div>
        <a id="modalDownload" href="#" download class="btn-sm">Scarica Risoluzione Piena</a>
      </div>
    </div>
  </div>

  <script>
    function showTab(tabName) {{
      document.querySelectorAll('.tab-pane').forEach(el => el.classList.remove('active'));
      document.querySelectorAll('.tab-btn').forEach(el => el.classList.remove('active'));
      const activePane = document.getElementById('tab-' + tabName);
      if (activePane) activePane.classList.add('active');
      event.currentTarget.classList.add('active');
    }}

    function openModal(src, dims, fmt, sz, cs) {{
      document.getElementById('modalImg').src = src;
      document.getElementById('modalTitle').textContent = src.split('/').pop();
      document.getElementById('modalMeta').innerHTML = '<strong>' + fmt + '</strong> &bull; ' + dims + ' &bull; ' + sz + ' &bull; Spazio: ' + cs;
      document.getElementById('modalDownload').href = src;
      document.getElementById('imageModal').style.display = 'flex';
    }}

    function closeModal() {{
      document.getElementById('imageModal').style.display = 'none';
    }}

    document.addEventListener('keydown', function(e) {{
      if (e.key === 'Escape') closeModal();
    }});
  </script>
</body>
</html>
"""

    with open(report_file, "w", encoding="utf-8") as f:
        f.write(html_template)

    return report_file


def generate_batch_html_report(batch_data: Dict[str, Any], output_dir: Path) -> Path:
    """
    Renders a unified, offline-capable Batch Index Dashboard (`batch_report.html`,
    or `batch_report_2.html`, ... if already present) in `output_dir`, linking cleanly
    to every processed document's subfolder and individual `report.html`.
    """
    report_file = output_dir / "batch_report.html"
    counter = 2
    while report_file.exists():
        report_file = output_dir / f"batch_report_{counter}.html"
        counter += 1

    total_files = batch_data.get("total_files", 0)
    succeeded = batch_data.get("succeeded", 0)
    failed = batch_data.get("failed", 0)
    agg = batch_data.get("aggregate_summary", {})
    items = batch_data.get("items", [])
    timestamp = datetime.now().strftime("%d/%m/%Y %H:%M")

    status_badge = (
        f'<span class="badge badge-success">{succeeded}/{total_files} Completati</span>'
        if failed == 0
        else f'<span class="badge badge-warning">{succeeded}/{total_files} OK · {failed} Errori</span>'
    )

    rows_html = []
    for idx, item in enumerate(items, start=1):
        fname = html.escape(item.get("file_name", ""))
        src_full = html.escape(item.get("source_pdf", ""))
        status = item.get("status", "error")

        if status == "success":
            s = item.get("summary") or {}
            out_path = Path(item["output_directory"])
            sub_name = out_path.name
            sub_href = quote(sub_name)
            has_individual_html = bool(item.get("html_report")) and Path(item["html_report"]).exists()

            report_link = (
                f'<a href="{sub_href}/report.html" class="btn-primary-sm">Apri Report PDF &rarr;</a>'
                if has_individual_html
                else '<span class="text-muted">HTML disattivato</span>'
            )
            folder_link = f'<a href="{sub_href}/" class="btn-sm">Cartella</a>'

            rows_html.append(f"""
            <tr class="batch-row" data-name="{fname.lower()}">
              <td><span class="text-muted">{idx}</span></td>
              <td>
                <strong title="{src_full}">{fname}</strong>
                <div class="text-muted font-code">&rarr; {html.escape(sub_name)}/</div>
              </td>
              <td><span class="badge badge-success">OK</span></td>
              <td>{s.get("total_pages", 0)}</td>
              <td>{s.get("total_images", 0)}</td>
              <td>{s.get("vector_pages_count", 0)}</td>
              <td>{s.get("embedded_fonts", 0)} / {s.get("total_fonts", 0)}</td>
              <td>{s.get("color_profiles_count", 0)} / {s.get("attachments_count", 0)}</td>
              <td>
                <div style="display:flex; gap:8px; align-items:center;">
                  {report_link}
                  {folder_link}
                </div>
              </td>
            </tr>
            """)
        else:
            err_msg = html.escape(item.get("error") or "Errore sconosciuto")
            rows_html.append(f"""
            <tr class="batch-row" data-name="{fname.lower()}">
              <td><span class="text-muted">{idx}</span></td>
              <td>
                <strong title="{src_full}">{fname}</strong>
                <div style="color:#fca5a5; font-size:12px;">{err_msg}</div>
              </td>
              <td><span class="badge badge-danger">Errore</span></td>
              <td>-</td>
              <td>-</td>
              <td>-</td>
              <td>-</td>
              <td>-</td>
              <td><span class="text-muted">-</span></td>
            </tr>
            """)

    batch_html = f"""<!DOCTYPE html>
<html lang="it">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Batch Extraction Summary — PDF Asset Extractor</title>
  <style>
    :root {{
      --bg: #0f172a;
      --card-bg: #1e293b;
      --card-border: #334155;
      --text-main: #f8fafc;
      --text-muted: #94a3b8;
      --primary: #38bdf8;
      --primary-hover: #0284c7;
      --radius: 12px;
      --shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.4);
    }}
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
      background: var(--bg);
      color: var(--text-main);
      padding: 30px 20px;
      line-height: 1.5;
    }}
    .container {{ max-width: 1360px; margin: 0 auto; }}
    header {{
      background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
      border: 1px solid var(--card-border);
      border-radius: var(--radius);
      padding: 26px 30px;
      margin-bottom: 24px;
      box-shadow: var(--shadow);
      display: flex;
      justify-content: space-between;
      align-items: center;
      flex-wrap: wrap;
      gap: 15px;
    }}
    h1 {{ font-size: 24px; font-weight: 700; color: #fff; }}
    .sub {{ color: var(--text-muted); font-size: 13px; margin-top: 4px; }}
    .badge {{
      display: inline-block; padding: 4px 10px; border-radius: 9999px;
      font-size: 12px; font-weight: 600; text-transform: uppercase;
    }}
    .badge-success {{ background: rgba(34, 197, 94, 0.2); color: #86efac; border: 1px solid rgba(34, 197, 94, 0.4); }}
    .badge-warning {{ background: rgba(245, 158, 11, 0.2); color: #fcd34d; border: 1px solid rgba(245, 158, 11, 0.4); }}
    .badge-danger {{ background: rgba(239, 68, 68, 0.2); color: #fca5a5; border: 1px solid rgba(239, 68, 68, 0.4); }}
    .kpi-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(170px, 1fr));
      gap: 14px;
      margin-bottom: 24px;
    }}
    .kpi-card {{
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      border-radius: var(--radius);
      padding: 18px;
      text-align: center;
      box-shadow: var(--shadow);
    }}
    .kpi-val {{ font-size: 28px; font-weight: 800; color: var(--primary); margin-bottom: 4px; }}
    .kpi-label {{ font-size: 12px; color: var(--text-muted); text-transform: uppercase; font-weight: 600; }}
    .toolbar {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 14px;
      gap: 12px;
      flex-wrap: wrap;
    }}
    .search-input {{
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      border-radius: 8px;
      color: var(--text-main);
      padding: 8px 14px;
      font-size: 14px;
      width: 300px;
      max-width: 100%;
      outline: none;
    }}
    .search-input:focus {{ border-color: var(--primary); }}
    .table-container {{
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      border-radius: var(--radius);
      overflow-x: auto;
      box-shadow: var(--shadow);
    }}
    table {{ width: 100%; border-collapse: collapse; font-size: 14px; text-align: left; }}
    th, td {{ padding: 12px 16px; border-bottom: 1px solid var(--card-border); }}
    th {{ background: rgba(15, 23, 42, 0.7); font-weight: 600; color: #cbd5e1; }}
    tr:last-child td {{ border-bottom: none; }}
    tr:hover td {{ background: rgba(255, 255, 255, 0.02); }}
    .btn-primary-sm {{
      display: inline-block; padding: 5px 12px;
      background: var(--primary); color: #0f172a;
      border-radius: 6px; text-decoration: none; font-size: 12px; font-weight: 700;
    }}
    .btn-primary-sm:hover {{ background: #7dd3fc; }}
    .btn-sm {{
      display: inline-block; padding: 5px 10px;
      background: rgba(56, 189, 248, 0.14); color: var(--primary);
      border-radius: 6px; text-decoration: none; font-size: 12px; font-weight: 600;
    }}
    .btn-sm:hover {{ background: var(--primary); color: #0f172a; }}
    .text-muted {{ color: var(--text-muted); }}
    .font-code {{ font-family: monospace; font-size: 12px; }}
  </style>
</head>
<body>
  <div class="container">
    <header>
      <div>
        <h1>📚 Riepilogo Elaborazione Batch</h1>
        <div class="sub">Cartella base: <span class="font-code">{html.escape(str(output_dir))}</span> &bull; {timestamp}</div>
      </div>
      <div>{status_badge}</div>
    </header>

    <div class="kpi-grid">
      <div class="kpi-card">
        <div class="kpi-val">{succeeded}/{total_files}</div>
        <div class="kpi-label">PDF Elaborati</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-val">{agg.get("total_pages", 0)}</div>
        <div class="kpi-label">Pagine Totali</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-val">{agg.get("total_images", 0)}</div>
        <div class="kpi-label">Immagini Estratte</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-val">{agg.get("vector_pages_count", 0)}</div>
        <div class="kpi-label">Pagine Vettoriali</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-val">{agg.get("embedded_fonts", 0)}/{agg.get("total_fonts", 0)}</div>
        <div class="kpi-label">Font Incorporati</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-val">{agg.get("color_profiles_count", 0)}</div>
        <div class="kpi-label">Profili ICC</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-val">{agg.get("attachments_count", 0)}</div>
        <div class="kpi-label">Allegati</div>
      </div>
    </div>

    <div class="toolbar">
      <h2 style="font-size: 17px; font-weight: 600;">Documenti elaborati</h2>
      <input type="text" id="filterInput" class="search-input" placeholder="Filtra documenti per nome..." oninput="filterRows()" />
    </div>

    <div class="table-container">
      <table>
        <thead>
          <tr>
            <th>#</th>
            <th>Documento PDF &amp; Sottocartella</th>
            <th>Stato</th>
            <th>Pagine</th>
            <th>Immagini</th>
            <th>Vettoriali</th>
            <th>Font (Incorp.)</th>
            <th>Profili / Allegati</th>
            <th>Azioni</th>
          </tr>
        </thead>
        <tbody>
          {"".join(rows_html)}
        </tbody>
      </table>
    </div>

    <footer style="margin-top: 40px; padding: 20px; border-top: 1px solid var(--card-border); color: var(--text-muted); font-size: 12px; text-align: center;">
      <p><strong>PDF Asset Extractor</strong> · by Linus74 &copy; 2026 &mdash; Uso responsabile: verifica i diritti d'autore e le licenze (EULA) delle risorse estratte.</p>
    </footer>
  </div>

  <script>
    function filterRows() {{
      const q = document.getElementById('filterInput').value.toLowerCase().trim();
      document.querySelectorAll('.batch-row').forEach(tr => {{
        const name = tr.getAttribute('data-name') || '';
        tr.style.display = name.includes(q) ? '' : 'none';
      }});
    }}
  </script>
</body>
</html>
"""

    with open(report_file, "w", encoding="utf-8") as f:
        f.write(batch_html)

    return report_file


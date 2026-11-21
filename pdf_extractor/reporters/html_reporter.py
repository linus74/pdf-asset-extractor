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
from ..utils.i18n import tr, format_preflight_check, format_preflight_badge_label


_PF_BADGE_MAP = {
    "pass": ("badge-success", "pf_badge_pass"),
    "warn": ("badge-warning", "pf_badge_warn"),
    "fail": ("badge-danger", "pf_badge_fail"),
    "skipped": ("badge-neutral", "pf_badge_skip"),
}


def _pf_badge_html(status: str, lang: str) -> str:
    cls, key = _PF_BADGE_MAP.get(status, ("badge-neutral", "pf_badge_skip"))
    return f'<span class="badge {cls}">{tr(lang, key)}</span>'


def generate_html_report(data: Dict[str, Any], output_dir: Path, lang: str = "en") -> Path:
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

    t = lambda k, **kw: tr(lang, k, **kw)

    title = html.escape(doc_info.get("title") or Path(data.get("source_pdf", "Document")).name)
    creator = html.escape(doc_info.get("creator") or t("html_not_specified"))
    producer = html.escape(doc_info.get("producer") or t("html_not_specified"))
    pdf_version = html.escape(doc_info.get("pdf_version") or doc_info.get("pdf_format") or "PDF")
    created = html.escape(doc_info.get("creation_date") or doc_info.get("creation_date_raw") or "N/A")
    modified = html.escape(doc_info.get("modification_date") or doc_info.get("modification_date_raw") or "N/A")

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
        f'<span class="badge badge-danger">{t("html_encrypted")}</span>'
        if sec.get("is_encrypted")
        else f'<span class="badge badge-success">{t("html_open")}</span>'
    )

    # Print Readiness Audit rows & header badge
    audit = data.get("preflight_audit") or {}
    pf_overall = audit.get("status", "pass")
    pf_counts = audit.get("counts") or {}
    pf_thresholds = audit.get("thresholds") or {"min_dpi": 300, "critical_dpi": 150}
    pf_header_cls = {"pass": "badge-success", "warn": "badge-warning", "fail": "badge-danger"}.get(pf_overall, "badge-neutral")
    pf_header_label = html.escape(format_preflight_badge_label(audit, lang)) if audit else t("pf_status_pass")
    pf_header_badge = (
        f'<button type="button" class="badge {pf_header_cls}" '
        f'style="cursor:pointer;" onclick="showTab(\'preflight\')">{pf_header_label}</button>'
    )

    preflight_rows_html = []
    for chk in audit.get("checks", []):
        cid = chk.get("id", "")
        c_title = html.escape(t(f"pf_check_{cid}"))
        c_badge = _pf_badge_html(chk.get("status", "pass"), lang)
        c_summary = html.escape(format_preflight_check(chk, pf_thresholds, lang))

        aff_parts = []
        for det in (chk.get("details") or [])[:5]:
            if "dpi" in det:
                aff_parts.append(f"{det.get('file', '')} ({det['dpi']} DPI)")
            elif "colorspace" in det:
                aff_parts.append(f"{det.get('file', '')} [{det['colorspace']}]")
            elif "name" in det:
                aff_parts.append(str(det["name"]))
        if chk.get("affected_pages"):
            pages_str_pf = ", ".join(str(p) for p in chk["affected_pages"][:12])
            if len(chk["affected_pages"]) > 12:
                pages_str_pf += "..."
            aff_parts.append(t("pf_pages_affected", pages=pages_str_pf))
        aff_html = "<br>".join(html.escape(part) for part in aff_parts) if aff_parts else '<span class="text-muted">-</span>'

        preflight_rows_html.append(f"""
        <tr>
          <td><strong>{c_title}</strong></td>
          <td>{c_badge}</td>
          <td>{c_summary}</td>
          <td><small>{aff_html}</small></td>
        </tr>
        """)

    # Images cards HTML
    images_cards_html = []
    for img in images:
        f_name = html.escape(img.get("filename", ""))
        fmt = html.escape(img.get("format", ""))
        w = img.get("width", 0)
        h = img.get("height", 0)
        cs = html.escape(str(img.get("colorspace", "")))
        sz = html.escape(img.get("file_size", ""))
        alpha = t("yes_smask") if img.get("has_transparency") else t("no")
        dpi_val = img.get("effective_dpi")
        dpi_badge = f'<span class="tag tag-dpi">{dpi_val} DPI</span>' if dpi_val else '<span class="tag">DPI N/A</span>'
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
              <div><strong>{t("img_dims")}</strong> {w} &times; {h} px</div>
              <div><strong>{t("img_weight")}</strong> {sz}</div>
              <div><strong>{t("img_space")}</strong> {cs}</div>
              <div><strong>{t("img_alpha")}</strong> {alpha}</div>
            </div>
            <div class="card-footer-pages">{t("img_pages")} {pages_str}</div>
            <a href="{f_name}" download class="btn-download" onclick="event.stopPropagation()">{t("btn_dl_img")}</a>
          </div>
        </div>
        """)

    # Fonts rows HTML
    fonts_rows_html = []
    for f in fonts:
        base = html.escape(f.get("basefont", ""))
        clean = html.escape(f.get("clean_name", ""))
        sub = html.escape(f.get("subtype", ""))
        is_emb = f.get("is_embedded", False)
        saved = f.get("saved_file")
        glyphs = f.get("glyph_count")
        glyphs_str = str(glyphs) if glyphs is not None else "N/A"
        sz_str = f.get("file_size") or "-"
        pages_str = ", ".join(str(p) for p in f.get("pages", []))

        inst_status = f.get("install_status", "unknown")
        chars_sample = html.escape(f.get("chars_sample") or "")
        chars_cnt = f.get("chars_count", 0)

        if inst_status == "full":
            status_badge = f'<span class="badge badge-success">🟢 {t("font_full")}</span>'
        elif inst_status == "subset":
            status_badge = f'<span class="badge badge-warning">🟡 {t("font_subset", n=chars_cnt)}</span>'
        elif is_emb:
            status_badge = f'<span class="badge badge-info">{t("font_embedded")}</span>'
        else:
            status_badge = f'<span class="badge badge-neutral">{t("font_system")}</span>'

        dl_link = f'<a href="{saved}" download class="btn-sm">{t("dl_font", ext=Path(saved).suffix)}</a>' if saved else '<span class="text-muted">-</span>'
        sample_box = f'<div class="chars-sample-box font-code" title="{chars_sample}">{chars_sample}</div>' if chars_sample else '<span class="text-muted font-code">-</span>'

        flags_obj = f.get("flags", {})
        flag_tags = []
        if flags_obj.get("italic"): flag_tags.append(t("font_italic"))
        if flags_obj.get("force_bold"): flag_tags.append(t("font_bold"))
        if flags_obj.get("fixed_pitch"): flag_tags.append(t("font_mono"))
        if flags_obj.get("serif"): flag_tags.append("Serif")
        flags_str = ", ".join(flag_tags) if flag_tags else t("font_normal")

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
          <td><a href="{p_file}" download class="btn-sm">{t("dl_icc")}</a></td>
        </tr>
        """)

    # Spot colors tags
    spot_tags_html = []
    for sc in spot_colors:
        spot_tags_html.append(f'<div class="spot-color-pill"><span class="spot-indicator"></span> {html.escape(sc)}</div>')
    if not spot_tags_html:
        spot_tags_html.append(f'<div class="text-muted">{t("empty_spots")}</div>')

    # Pages rows HTML
    pages_rows_html = []
    for pg in pages:
        p_num = pg.get("page_number")
        p_lbl = html.escape(pg.get("page_label", str(p_num)))
        rot = pg.get("rotation", 0)

        mb = pg.get("mediabox") or {}
        tb = pg.get("trimbox") or {}
        bb = pg.get("bleedbox") or {}

        mb_name = html.escape(mb.get("matched_size", "N/A"))
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
          <td><strong>{t("page_word")} {p_num}</strong> ({p_lbl})</td>
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
          <td><a href="{a_file}" download class="btn-sm">{t("dl_file")}</a></td>
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

        dl_svg = f'<a href="{svg_f}" download class="btn-sm">{t("dl_svg", sz=svg_sz)}</a>' if svg_f else "-"
        dl_ai = f'<a href="{ai_f}" download class="btn-sm" style="background: rgba(245, 158, 11, 0.2); color: #fcd34d; border: 1px solid rgba(245, 158, 11, 0.4);">{t("dl_ai", sz=ai_sz)}</a>' if ai_f else "-"

        vectors_rows_html.append(f"""
        <tr>
          <td><strong>{t("page_word")} {p_num}</strong></td>
          <td><span class="badge badge-accent">{t("paths_label", n=paths_c)}</span></td>
          <td><small>{t("vec_detail_fmt", c=curves_c, l=lines_c, r=rects_c)}</small></td>
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
            xmp_content = "XMP read error."

    html_template = f"""<!DOCTYPE html>
<html lang="{html.escape(lang)}">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{t("html_doc_title")}: {title}</title>
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
          <p style="color: var(--text-muted); font-size: 14px; margin-top: 4px;">{t("html_doc_sub")}</p>
        </div>
        <div class="header-badges">
          <span class="badge badge-info">{pdf_version}</span>
          {' '.join(std_badges)}
          {sec_badge}
          {pf_header_badge}
        </div>
      </div>

      <div class="meta-grid">
        <div class="meta-item"><strong>{t("html_creator")}</strong> {creator}</div>
        <div class="meta-item"><strong>{t("html_producer")}</strong> {producer}</div>
        <div class="meta-item"><strong>{t("html_created")}</strong> {created}</div>
        <div class="meta-item"><strong>{t("html_modified")}</strong> {modified}</div>
        <div class="meta-item"><strong>{t("html_author_subj")}</strong> {html.escape(doc_info.get("author") or "N/A")} / {html.escape(doc_info.get("subject") or "N/A")}</div>
        <div class="meta-item"><strong>{t("html_trapped")}</strong> {html.escape(str(doc_info.get("trapped") or t("html_not_defined")))}</div>
      </div>
    </header>

    <!-- KPI STATS CARDS -->
    <div class="kpi-grid">
      <div class="kpi-card">
        <div class="kpi-val">{summary.get("total_pages", len(pages))}</div>
        <div class="kpi-label">{t("kpi_pages")}</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-val">{summary.get("total_images", len(images))}</div>
        <div class="kpi-label">{t("kpi_images")}</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-val">{len(vectors)}</div>
        <div class="kpi-label">{t("kpi_vectors")}</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-val">{summary.get("total_fonts", len(fonts))}</div>
        <div class="kpi-label">{t("kpi_fonts", e=summary.get("embedded_fonts", 0))}</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-val">{len(profiles)}</div>
        <div class="kpi-label">{t("kpi_profiles")}</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-val">{len(spot_colors)}</div>
        <div class="kpi-label">{t("kpi_spots")}</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-val">{len(attachments)}</div>
        <div class="kpi-label">{t("kpi_attachments")}</div>
      </div>
    </div>

    <!-- TABS NAVIGATION -->
    <div class="tabs-nav">
      <button class="tab-btn active" data-tab="images" onclick="showTab('images')">🖼️ {t("tab_images")} ({len(images)})</button>
      <button class="tab-btn" data-tab="vectors" onclick="showTab('vectors')">📐 {t("tab_vectors")} ({len(vectors)})</button>
      <button class="tab-btn" data-tab="fonts" onclick="showTab('fonts')">🔤 {t("tab_fonts")} ({len(fonts)})</button>
      <button class="tab-btn" data-tab="profiles" onclick="showTab('profiles')">🎨 {t("tab_profiles")}</button>
      <button class="tab-btn" data-tab="pages" onclick="showTab('pages')">📏 {t("tab_pages")} ({len(pages)})</button>
      <button class="tab-btn" data-tab="preflight" onclick="showTab('preflight')">🩺 {t("tab_preflight")}</button>
      <button class="tab-btn" data-tab="attachments" onclick="showTab('attachments')">📎 {t("tab_attachments")} ({len(attachments)})</button>
      <button class="tab-btn" data-tab="xmp" onclick="showTab('xmp')">ℹ️ {t("tab_xmp")}</button>
    </div>

    <!-- TAB: IMAGES -->
    <div id="tab-images" class="tab-pane active">
      {'<div class="gallery-grid">' + ''.join(images_cards_html) + '</div>' if images_cards_html else f'<div class="empty-state">{t("empty_images")}</div>'}
    </div>

    <!-- TAB: VECTORS -->
    <div id="tab-vectors" class="tab-pane">
      <h3 style="margin-bottom: 8px; font-size: 18px;">{t("vec_heading")}</h3>
      <p style="color: var(--text-muted); font-size: 14px; margin-bottom: 20px;">{t("vec_desc")}</p>
      {'<div class="table-container"><table><thead><tr><th>' + t("th_page") + '</th><th>' + t("th_paths") + '</th><th>' + t("th_geom_detail") + '</th><th>' + t("th_colors") + '</th><th>' + t("th_download") + '</th></tr></thead><tbody>' + ''.join(vectors_rows_html) + '</tbody></table></div>' if vectors_rows_html else f'<div class="empty-state">{t("empty_vectors")}</div>'}
    </div>

    <!-- TAB: FONTS -->
    <div id="tab-fonts" class="tab-pane">
      <h3 style="margin-bottom: 6px; font-size: 18px;">{t("font_heading")}</h3>
      <p style="color: var(--text-muted); font-size: 13px; margin-bottom: 18px;">{t("font_desc")}</p>
      {'<div class="table-container"><table><thead><tr><th>' + t("th_font_name") + '</th><th>' + t("th_type") + '</th><th>' + t("th_install_status") + '</th><th>' + t("th_char_sample") + '</th><th>' + t("th_glyphs") + '</th><th>' + t("th_size") + '</th><th>' + t("th_attrs") + '</th><th>' + t("th_pages") + '</th><th>' + t("th_download") + '</th></tr></thead><tbody>' + ''.join(fonts_rows_html) + '</tbody></table></div>' if fonts_rows_html else f'<div class="empty-state">{t("empty_fonts")}</div>'}
    </div>

    <!-- TAB: PROFILES -->
    <div id="tab-profiles" class="tab-pane">
      <h3 style="margin-bottom: 12px; font-size: 18px;">{t("prof_heading")}</h3>
      {'<div class="table-container"><table><thead><tr><th>' + t("th_prof_desc") + '</th><th>' + t("th_cs") + '</th><th>' + t("th_dev_class") + '</th><th>' + t("th_ver") + '</th><th>' + t("th_size") + '</th><th>' + t("th_download") + '</th></tr></thead><tbody>' + ''.join(profiles_rows_html) + '</tbody></table></div>' if profiles_rows_html else f'<div class="empty-state" style="padding:20px 0;">{t("empty_profiles")}</div>'}

      <h3 style="margin-top: 35px; margin-bottom: 10px; font-size: 18px;">{t("spot_heading")}</h3>
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
              <th>{t("th_page")}</th>
              <th>{t("th_fmt_mb")}</th>
              <th>{t("th_trim")}</th>
              <th>{t("th_bleed")}</th>
              <th>{t("th_rot")}</th>
              <th>{t("th_imgs")}</th>
              <th>{t("th_fnts")}</th>
              <th>{t("th_vec_paths")}</th>
              <th>{t("th_words")}</th>
            </tr>
          </thead>
          <tbody>
            {''.join(pages_rows_html)}
          </tbody>
        </table>
      </div>
    </div>

    <!-- TAB: PRINT READINESS (PREFLIGHT) -->
    <div id="tab-preflight" class="tab-pane">
      <h3 style="margin-bottom: 6px; font-size: 18px;">{t("preflight_heading")}</h3>
      <p style="color: var(--text-muted); font-size: 13px; margin-bottom: 18px;">{t("preflight_desc")}</p>
      <div style="display:flex; gap:10px; flex-wrap:wrap; margin-bottom:18px;">
        <span class="badge badge-success">{t("pf_badge_pass")}: {pf_counts.get("pass", 0)}</span>
        <span class="badge badge-warning">{t("pf_badge_warn")}: {pf_counts.get("warn", 0)}</span>
        <span class="badge badge-danger">{t("pf_badge_fail")}: {pf_counts.get("fail", 0)}</span>
      </div>
      <div class="table-container">
        <table>
          <thead>
            <tr>
              <th>{t("pf_th_check")}</th>
              <th>{t("pf_th_status")}</th>
              <th>{t("pf_th_summary")}</th>
              <th>{t("pf_th_affected")}</th>
            </tr>
          </thead>
          <tbody>
            {"".join(preflight_rows_html)}
          </tbody>
        </table>
      </div>
    </div>

    <!-- TAB: ATTACHMENTS -->
    <div id="tab-attachments" class="tab-pane">
      {'<div class="table-container"><table><thead><tr><th>' + t("th_filename") + '</th><th>' + t("th_desc") + '</th><th>' + t("th_size") + '</th><th>' + t("th_source") + '</th><th>' + t("th_download") + '</th></tr></thead><tbody>' + ''.join(attachments_rows_html) + '</tbody></table></div>' if attachments_rows_html else f'<div class="empty-state">{t("empty_attachments")}</div>'}
    </div>

    <!-- TAB: XMP METADATA -->
    <div id="tab-xmp" class="tab-pane">
      <h3 style="margin-bottom: 15px; font-size: 18px;">{t("xmp_heading")}</h3>
      {f'<pre class="code-block"><code>{xmp_content}</code></pre>' if xmp_content else f'<div class="empty-state">{t("empty_xmp")}</div>'}
    </div>

    <!-- DISCLAIMER FOOTER -->
    <footer style="margin-top: 50px; padding: 25px 20px; border-top: 1px solid var(--card-border); color: var(--text-muted); font-size: 12px; line-height: 1.6; text-align: center;">
      <p style="font-weight: 600; color: #cbd5e1; margin-bottom: 5px;">⚖️ {t("legal_title")}</p>
      <p style="max-width: 850px; margin: 0 auto;">{t("legal_body")}</p>
    </footer>

  </div>

  <!-- MODAL FOR IMAGES -->
  <div id="imageModal" class="modal" onclick="closeModal()">
    <div class="modal-content" onclick="event.stopPropagation()">
      <div class="modal-header">
        <h4 id="modalTitle">{t("modal_preview")}</h4>
        <button class="modal-close" onclick="closeModal()">&times;</button>
      </div>
      <div class="modal-img-wrap">
        <img id="modalImg" src="" alt="{t("modal_preview")}">
      </div>
      <div class="modal-footer">
        <div id="modalMeta"></div>
        <a id="modalDownload" href="#" download class="btn-sm">{t("modal_dl")}</a>
      </div>
    </div>
  </div>

  <script>
    function showTab(tabName) {{
      document.querySelectorAll('.tab-pane').forEach(el => el.classList.remove('active'));
      document.querySelectorAll('.tab-btn').forEach(el => el.classList.remove('active'));
      const activePane = document.getElementById('tab-' + tabName);
      if (activePane) activePane.classList.add('active');
      const activeBtn = document.querySelector('.tab-btn[data-tab="' + tabName + '"]');
      if (activeBtn) activeBtn.classList.add('active');
    }}

    function openModal(src, dims, fmt, sz, cs) {{
      document.getElementById('modalImg').src = src;
      document.getElementById('modalTitle').textContent = src.split('/').pop();
      document.getElementById('modalMeta').innerHTML = '<strong>' + fmt + '</strong> &bull; ' + dims + ' &bull; ' + sz + ' &bull; ' + cs;
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


def generate_batch_html_report(batch_data: Dict[str, Any], output_dir: Path, lang: str = "en") -> Path:
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
        f'<span class="badge badge-success">{tr(lang, "batch_done_badge", s=succeeded, t=total_files)}</span>'
        if failed == 0
        else f'<span class="badge badge-warning">{tr(lang, "batch_partial_badge", s=succeeded, t=total_files, f=failed)}</span>'
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
                f'<a href="{sub_href}/report.html" class="btn-primary-sm">{tr(lang, "btn_open_pdf_report")} &rarr;</a>'
                if has_individual_html
                else f'<span class="text-muted">{tr(lang, "html_disabled_txt")}</span>'
            )
            folder_link = f'<a href="{sub_href}/" class="btn-sm">{tr(lang, "btn_folder")}</a>'

            rows_html.append(f"""
            <tr class="batch-row" data-name="{fname.lower()}">
              <td><span class="text-muted">{idx}</span></td>
              <td>
                <strong title="{src_full}">{fname}</strong>
                <div class="text-muted font-code">&rarr; {html.escape(sub_name)}/</div>
              </td>
              <td><span class="badge badge-success">{tr(lang, "status_ok")}</span></td>
              <td>{_pf_badge_html(item.get("preflight_status", s.get("preflight_status", "pass")), lang)}</td>
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
            err_msg = html.escape(item.get("error") or tr(lang, "status_error"))
            rows_html.append(f"""
            <tr class="batch-row" data-name="{fname.lower()}">
              <td><span class="text-muted">{idx}</span></td>
              <td>
                <strong title="{src_full}">{fname}</strong>
                <div style="color:#fca5a5; font-size:12px;">{err_msg}</div>
              </td>
              <td><span class="badge badge-danger">{tr(lang, "status_error")}</span></td>
              <td>-</td>
              <td>-</td>
              <td>-</td>
              <td>-</td>
              <td>-</td>
              <td>-</td>
              <td><span class="text-muted">-</span></td>
            </tr>
            """)

    batch_html = f"""<!DOCTYPE html>
<html lang="{html.escape(lang)}">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{tr(lang, "batch_html_title")}</title>
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
        <h1>&#x1F4DA; {tr(lang, "batch_html_heading")}</h1>
        <div class="sub">{tr(lang, "batch_html_base")} <span class="font-code">{html.escape(str(output_dir))}</span> &bull; {timestamp}</div>
      </div>
      <div>{status_badge}</div>
    </header>

    <div class="kpi-grid">
      <div class="kpi-card">
        <div class="kpi-val">{succeeded}/{total_files}</div>
        <div class="kpi-label">{tr(lang, "batch_kpi_pdfs")}</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-val">{agg.get("total_pages", 0)}</div>
        <div class="kpi-label">{tr(lang, "kpi_pages")}</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-val">{agg.get("total_images", 0)}</div>
        <div class="kpi-label">{tr(lang, "kpi_images")}</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-val">{agg.get("vector_pages_count", 0)}</div>
        <div class="kpi-label">{tr(lang, "batch_kpi_vec_pages")}</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-val">{agg.get("embedded_fonts", 0)}/{agg.get("total_fonts", 0)}</div>
        <div class="kpi-label">{tr(lang, "batch_kpi_emb_fonts")}</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-val">{agg.get("color_profiles_count", 0)}</div>
        <div class="kpi-label">{tr(lang, "kpi_profiles")}</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-val">{agg.get("attachments_count", 0)}</div>
        <div class="kpi-label">{tr(lang, "kpi_attachments")}</div>
      </div>
    </div>

    <div class="toolbar">
      <h2 style="font-size: 17px; font-weight: 600;">{tr(lang, "batch_docs_heading")}</h2>
      <input type="text" id="filterInput" class="search-input" placeholder="{html.escape(tr(lang, "batch_filter_ph"))}" oninput="filterRows()" />
    </div>

    <div class="table-container">
      <table>
        <thead>
          <tr>
            <th>#</th>
            <th>{tr(lang, "th_doc_sub")}</th>
            <th>{tr(lang, "th_status")}</th>
            <th>{tr(lang, "batch_th_preflight")}</th>
            <th>{tr(lang, "th_pages")}</th>
            <th>{tr(lang, "th_imgs")}</th>
            <th>{tr(lang, "tab_vectors")}</th>
            <th>{tr(lang, "th_fonts_emb")}</th>
            <th>{tr(lang, "th_prof_att")}</th>
            <th>{tr(lang, "th_actions")}</th>
          </tr>
        </thead>
        <tbody>
          {"".join(rows_html)}
        </tbody>
      </table>
    </div>

    <footer style="margin-top: 40px; padding: 20px; border-top: 1px solid var(--card-border); color: var(--text-muted); font-size: 12px; text-align: center;">
      <p><strong>PDF Asset Extractor</strong> &middot; by Linus74 &copy; 2026 &mdash; {tr(lang, "legal_body")}</p>
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


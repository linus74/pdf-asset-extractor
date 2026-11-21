"""
Font extractor: extracts embedded font files (TTF, OTF, CFF, WOFF, PFB), detects subsets,
repairs missing tables with fonttools to ensure OS installability, analyzes character coverage,
and inventories referenced system fonts.
"""

import io
import re
from pathlib import Path
from typing import List, Dict, Any, Optional, Set, Tuple
import pymupdf
from fontTools.ttLib import TTFont, newTable
from fontTools.ttLib.tables._n_a_m_e import NameRecord
from ..utils.helpers import sanitize_filename, format_bytes, compute_sha256


SUBSET_REGEX = re.compile(r"^([A-Z]{6})\+(.+)$")


def _parse_font_flags(flags: int) -> Dict[str, bool]:
    return {
        "fixed_pitch": bool(flags & (1 << 0)),
        "serif": bool(flags & (1 << 1)),
        "symbolic": bool(flags & (1 << 2)),
        "script": bool(flags & (1 << 3)),
        "nonsymbolic": bool(flags & (1 << 5)),
        "italic": bool(flags & (1 << 6)),
        "all_cap": bool(flags & (1 << 16)),
        "small_cap": bool(flags & (1 << 17)),
        "force_bold": bool(flags & (1 << 18)),
    }


def _repair_and_inspect_font(
    buffer: bytes,
    clean_family_name: str,
    basefont: str,
    declared_subset: bool
) -> Tuple[bytes, Dict[str, Any]]:
    """
    Validates and repairs font tables (e.g. missing name table) using fonttools.
    Analyzes glyph counts, character coverage, and real installation viability.
    """
    info: Dict[str, Any] = {
        "glyph_count": None,
        "font_tables": [],
        "install_status": "unknown",
        "status_label": "Formato non direttamente installabile",
        "chars_count": 0,
        "chars_sample": "",
        "repaired_tables": [],
        "is_installable": False,
    }

    try:
        tt = TTFont(io.BytesIO(buffer))
    except Exception:
        # Bare stream that cannot be parsed as an SFNT container
        info["install_status"] = "raw_stream"
        info["status_label"] = "Flusso dati non standard (non installabile direttamente)"
        return buffer, info

    tables = set(tt.keys())
    info["font_tables"] = sorted(list(tables))

    # Glyph count
    if "maxp" in tt and hasattr(tt["maxp"], "numGlyphs"):
        info["glyph_count"] = int(tt["maxp"].numGlyphs)
    elif "CFF " in tt:
        try:
            info["glyph_count"] = len(tt["CFF "].cff[0].CharStrings)
        except Exception:
            pass

    # Inspect cmap for Unicode character coverage
    chars_list = []
    cmap = None
    try:
        cmap = tt.getBestCmap()
        if cmap:
            info["chars_count"] = len(cmap)
            chars_list = [chr(c) for c in sorted(cmap.keys()) if 32 <= c <= 126 or 160 <= c <= 255]
            sample = "".join(chars_list[:40])
            if len(chars_list) > 40:
                sample += "..."
            info["chars_sample"] = sample
    except Exception:
        pass

    # Check / Repair Name table
    # Windows font viewer and DirectWrite installer FAIL if name table or records are missing
    repaired = False
    if "name" not in tt or not hasattr(tt["name"], "names") or len(tt["name"].names) == 0:
        tt["name"] = newTable("name")
        tt["name"].names = []
        info["repaired_tables"].append("name")
        repaired = True

    existing_name_ids = {r.nameID for r in tt["name"].names} if hasattr(tt["name"], "names") else set()

    subfamily = "Regular"
    if "bold" in basefont.lower() and "italic" in basefont.lower():
        subfamily = "Bold Italic"
    elif "bold" in basefont.lower():
        subfamily = "Bold"
    elif "italic" in basefont.lower() or "oblique" in basefont.lower():
        subfamily = "Italic"

    def _add_name_record(name_id: int, text_val: str):
        # Windows Unicode BMP (Platform 3, Enc 1, Lang 0x0409)
        rec_win = NameRecord()
        rec_win.nameID = name_id
        rec_win.platformID = 3
        rec_win.platEncID = 1
        rec_win.langID = 0x0409
        rec_win.string = text_val.encode("utf-16be")
        tt["name"].names.append(rec_win)

        # Macintosh Roman (Platform 1, Enc 0, Lang 0)
        rec_mac = NameRecord()
        rec_mac.nameID = name_id
        rec_mac.platformID = 1
        rec_mac.platEncID = 0
        rec_mac.langID = 0
        rec_mac.string = text_val.encode("latin1", errors="ignore")
        tt["name"].names.append(rec_mac)

    if 1 not in existing_name_ids:  # Family Name
        _add_name_record(1, clean_family_name)
        repaired = True
    if 2 not in existing_name_ids:  # Subfamily Name
        _add_name_record(2, subfamily)
        repaired = True
    if 4 not in existing_name_ids:  # Full Font Name
        _add_name_record(4, f"{clean_family_name} {subfamily}".strip())
        repaired = True
    if 6 not in existing_name_ids:  # PostScript Name
        _add_name_record(6, basefont.replace(" ", "_"))
        repaired = True

    # Re-save if repaired
    if repaired:
        try:
            out_buf = io.BytesIO()
            tt.save(out_buf)
            buffer = out_buf.getvalue()
        except Exception:
            pass

    # Determine real-world installability and classification
    has_outline_table = "glyf" in tables or "CFF " in tables or "CFF2" in tables
    has_basic_tables = {"head", "hhea", "maxp"}.issubset(tables)

    if has_outline_table and has_basic_tables:
        info["is_installable"] = True
        # Check if it has a full alphabet
        alphabet_complete = set("abcdefghijklmnopqrstuvwxyz").issubset(set(c.lower() for c in chars_list))
        if declared_subset or info["chars_count"] < 80 or not alphabet_complete:
            info["install_status"] = "subset"
            info["status_label"] = "Sottinsieme Parziale (Installabile, ma contiene solo i caratteri usati nel PDF)"
        else:
            info["install_status"] = "full"
            info["status_label"] = "Font Completo (Installabile e fruibile per qualsiasi testo)"
    else:
        info["is_installable"] = False
        info["install_status"] = "incomplete"
        info["status_label"] = "Tabelle minime mancanti (non installabile direttamente)"

    return buffer, info


def extract_fonts(
    doc: pymupdf.Document,
    output_dir: Optional[Path] = None
) -> List[Dict[str, Any]]:
    """
    Extracts all embedded fonts and inventories all fonts across document pages.
    Saves recovered font files to `output_dir / "fonts"` with repair validation.
    When `output_dir` is None, inspects embedding and subset metadata in memory without disk writes.
    """
    write_files = output_dir is not None
    fonts_dir = (output_dir / "fonts") if write_files else None
    if fonts_dir is not None:
        fonts_dir.mkdir(parents=True, exist_ok=True)

    # Key: font xref (or unique basefont name if xref <= 0)
    fonts_map: Dict[Any, Dict[str, Any]] = {}
    font_id_counter = 1

    for page_idx, page in enumerate(doc):
        pno = page_idx + 1
        page_fonts = page.get_fonts(full=True)

        for f_tuple in page_fonts:
            xref = f_tuple[0]
            ext = f_tuple[1]
            ftype = f_tuple[2]
            basefont = f_tuple[3]
            reference_name = f_tuple[4]
            encoding = f_tuple[5]

            # Detect font subset
            is_subset = False
            subset_tag = None
            clean_family_name = basefont

            subset_match = SUBSET_REGEX.match(basefont)
            if subset_match:
                is_subset = True
                subset_tag = subset_match.group(1)
                clean_family_name = subset_match.group(2)

            key = xref if xref > 0 else f"{basefont}_{encoding}"

            if key not in fonts_map:
                fonts_map[key] = {
                    "id": font_id_counter,
                    "xref": xref if xref > 0 else None,
                    "basefont": basefont,
                    "clean_name": clean_family_name,
                    "subtype": ftype,
                    "declared_ext": ext,
                    "encoding": encoding,
                    "is_subset": is_subset,
                    "subset_tag": subset_tag,
                    "is_embedded": False,
                    "is_installable": False,
                    "install_status": "not_embedded",
                    "status_label": "Non incorporato (Font di sistema)",
                    "saved_file": None,
                    "file_size": None,
                    "glyph_count": None,
                    "chars_count": 0,
                    "chars_sample": "",
                    "flags": {},
                    "pages": [pno],
                }
                font_id_counter += 1
            else:
                if pno not in fonts_map[key]["pages"]:
                    fonts_map[key]["pages"].append(pno)

    # Extract font binaries for each font entry with xref > 0
    font_index = 1
    for key, f_info in fonts_map.items():
        xref = f_info["xref"]
        if not xref or xref <= 0:
            continue

        try:
            name, ext, ftype, buffer = doc.extract_font(xref)
        except Exception:
            buffer = None
            ext = "n/a"

        if buffer and len(buffer) > 0:
            f_info["is_embedded"] = True
            file_size = len(buffer)
            f_info["file_size_bytes"] = file_size
            f_info["file_size"] = format_bytes(file_size)

            if write_files:
                # Repair and inspect with fonttools
                buffer, repair_info = _repair_and_inspect_font(
                    buffer=buffer,
                    clean_family_name=f_info["clean_name"],
                    basefont=f_info["basefont"],
                    declared_subset=f_info["is_subset"]
                )

                f_info.update(repair_info)

                file_size = len(buffer)
                f_info["file_size_bytes"] = file_size
                f_info["file_size"] = format_bytes(file_size)
                f_hash = compute_sha256(buffer)
                f_info["sha256"] = f_hash

                clean_ext = ext.lower().replace("n/a", "bin")
                if clean_ext not in ["ttf", "otf", "cff", "woff", "pfb", "pfa"]:
                    clean_ext = "otf" if "cff" in ftype.lower() or "type1" in ftype.lower() else "ttf"

                safe_name = sanitize_filename(f_info["basefont"])
                font_filename = f"{font_index:02d}_{safe_name}.{clean_ext}"
                font_path = fonts_dir / font_filename

                try:
                    with open(font_path, "wb") as f:
                        f.write(buffer)
                    f_info["saved_file"] = f"fonts/{font_filename}"
                except Exception:
                    pass

                font_index += 1
            else:
                f_info["install_status"] = "subset" if f_info["is_subset"] else "full"

        # Extract flags from FontDescriptor if available in PDF
        try:
            fd_xref = None
            font_keys = doc.xref_get_keys(xref)
            if "FontDescriptor" in font_keys:
                fd_str = doc.xref_get_key(xref, "FontDescriptor")[1]
                fd_match = re.search(r"(\d+)\s+0\s+R", fd_str)
                if fd_match:
                    fd_xref = int(fd_match.group(1))

            if fd_xref:
                fd_keys = doc.xref_get_keys(fd_xref)
                if "Flags" in fd_keys:
                    flags_val = int(doc.xref_get_key(fd_xref, "Flags")[1].strip())
                    f_info["flags"] = _parse_font_flags(flags_val)
                    f_info["flags_raw"] = flags_val
        except Exception:
            pass

    return list(fonts_map.values())

"""
Internationalization (i18n) module supporting English ('en') and Italian ('it').
Auto-detects OS system language on first run and persists user preferences.
"""

import json
import locale
import sys
from pathlib import Path
from typing import Dict, Any

SUPPORTED_LANGS = ("en", "it")
PREFS_FILE = Path.home() / ".pdf_asset_extractor_prefs.json"


def detect_os_language() -> str:
    """Detects whether the OS UI language is Italian; defaults to English globally."""
    if sys.platform == "win32":
        try:
            import ctypes
            lang_id = ctypes.windll.kernel32.GetUserDefaultUILanguage()
            # Primary language ID 0x10 = Italian
            if (lang_id & 0x3FF) == 0x10:
                return "it"
            return "en"
        except Exception:
            pass

    try:
        loc = locale.getlocale()[0] or ""
        if loc.lower().startswith("it"):
            return "it"
    except Exception:
        pass
    return "en"


def load_preferences() -> Dict[str, Any]:
    """Loads persisted UI preferences (language, theme) safely."""
    try:
        if PREFS_FILE.exists():
            data = json.loads(PREFS_FILE.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return data
    except Exception:
        pass
    return {}


def save_preferences(updates: Dict[str, Any]) -> None:
    """Saves UI preferences safely without failing in read-only environments."""
    try:
        prefs = load_preferences()
        prefs.update(updates)
        PREFS_FILE.write_text(json.dumps(prefs, indent=2), encoding="utf-8")
    except Exception:
        pass


def get_default_language() -> str:
    """Returns saved user language preference, or falls back to OS language."""
    prefs = load_preferences()
    lang = prefs.get("lang")
    if lang in SUPPORTED_LANGS:
        return lang
    return detect_os_language()


TRANSLATIONS: Dict[str, Dict[str, str]] = {
    "en": {
        # Output subfolder suffix
        "folder_suffix": "_extracted",
        # GUI Header & Theme
        "theme_light": "Light Mode",
        "theme_dark": "Dark Mode",
        "footer_disclaimer": "Responsible use: verify copyrights and font EULAs before reusing extracted assets.",
        # Dropzone
        "drop_title": "Drop one or more PDFs (or a folder)",
        "drop_sub": "Single file or local Batch processing",
        "btn_choose_pdfs": "Choose PDFs...",
        "btn_choose_folder": "Folder...",
        # Single Preview
        "pdf_locked": "PDF is password protected",
        "pwd_placeholder": "Enter password...",
        "btn_unlock": "Unlock PDF",
        "preview_unavailable": "Preview unavailable",
        "page_singular": "1 page",
        "page_plural": "{n} pages",
        "encrypted_file": "Encrypted file",
        "enter_pwd_hint": "Enter password to preview and extract.",
        "status_wait_pwd": "Waiting for PDF password...",
        "unknown_gen": "Unknown generator",
        "app_prefix": "App: {app}",
        "btn_add_more_batch": "Add more (Batch)",
        "btn_change": "Change",
        # Batch Queue
        "batch_queue_title": "Batch Queue • {n} PDFs",
        "btn_add": "Add",
        "btn_clear": "Clear",
        "batch_footer_tip": "Drop more PDFs or folders here to append to the queue.",
        "status_queued": "Queued",
        "status_running": "Running",
        "status_ok": "OK",
        "status_error": "Error",
        "btn_open": "Open",
        # Right Panel Controls
        "lbl_profile": "Extraction profile",
        "preset_full": "Full",
        "preset_graphics": "Graphics",
        "preset_fonts": "Fonts",
        "preset_audit": "Audit Only",
        "sw_images": "HD Images (Alpha PNG)",
        "sw_vectors": "Vectors (.SVG / .AI)",
        "sw_fonts": "Fonts & Subsets",
        "sw_profiles": "ICC Profiles & Spot Inks",
        "sw_attachments": "Embedded Attachments",
        "sw_gen_html": "Generate HTML Report",
        "chk_auto_open_html": "Automatically open HTML Report in browser when done",
        "dest_placeholder": "Base folder (default: ./output)",
        "hint_empty": "A subfolder <name>_extracted (numbered if existing) will be created.",
        "hint_single": "Folder to be created: {name}",
        "hint_batch": "{n} separate subfolders (<name>_extracted) will be created in target folder.",
        # CTA & Status
        "btn_extract": "Extract Assets",
        "btn_extract_batch": "Start Batch ({n} PDFs)",
        "btn_processing": "Processing...",
        "status_idle": "Drop or select one or more PDFs to begin.",
        "status_ready": "Ready to extract.",
        "status_batch_ready": "Queue ready: {n} documents to process.",
        "status_saved_in": "Saved to: {name}",
        "status_batch_done": "Batch complete: {s}/{t} PDFs saved in {dir}/",
        "status_batch_partial": "Batch finished: {s} succeeded, {f} failed.",
        # Results Card
        "res_done": "Extraction complete",
        "res_batch_done": "Batch complete ({s}/{t} PDFs)",
        "res_batch_partial": "Batch complete ({s}/{t} OK, {f} errors)",
        "chip_images": "{n} Images",
        "chip_vectors": "{n} Vectors",
        "chip_fonts": "{e}/{t} Fonts",
        "chip_profiles": "{n} Profiles",
        "chip_attachments": "{n} Files",
        "btn_open_out": "Open Output Folder",
        "btn_open_batch": "Open Batch Folder",
        "btn_open_html": "Open HTML Report",
        "btn_open_batch_html": "Open Batch HTML Report",
        # Dialogs
        "dlg_no_pdf_found_title": "No PDF found",
        "dlg_no_pdf_found_msg": "Drop one or more .pdf files or a folder containing PDFs.",
        "dlg_empty_dir_title": "Empty folder",
        "dlg_empty_dir_msg": "No .pdf files found in the selected folder.",
        "dlg_read_err_title": "PDF read error",
        "dlg_read_err_msg": "Could not read file:\n{err}",
        "dlg_wrong_pwd_title": "Incorrect password",
        "dlg_wrong_pwd_msg": "The password entered is not correct.",
        "dlg_no_pdf_title": "No PDF selected",
        "dlg_no_pdf_msg": "Drop or select at least one PDF file before starting.",
        "dlg_err_title": "Extraction Error",
        "dlg_err_msg": "An error occurred:\n\n{err}",
        "dlg_browse_pdfs": "Select one or more PDF files",
        "dlg_browse_folder": "Select folder containing PDFs",
        "dlg_browse_dest": "Select base destination folder",
        "dlg_all_files": "All files",
        "dlg_pdf_files": "PDF Documents (*.pdf)",
        # Core Progress
        "prog_open": "Opening PDF document...",
        "prog_meta": "Extracting metadata & software info...",
        "prog_geom": "Analyzing page geometry & boxes...",
        "prog_imgs": "Extracting images & alpha masks...",
        "prog_vecs": "Extracting vector graphics (.SVG / .AI)...",
        "prog_fonts": "Recovering & repairing embedded fonts...",
        "prog_profs": "Scanning ICC color profiles & spot inks...",
        "prog_attach": "Extracting embedded attachments...",
        "prog_reports": "Saving JSON & HTML reports...",
        "prog_done": "Complete!",
        "prog_batch_done": "Batch complete: {s}/{t} PDFs processed.",
        "err_pwd_required": "This PDF is password protected. Enter a valid password to proceed.",
        # HTML Report (Single)
        "html_doc_title": "PDF Asset & Metadata Report",
        "html_doc_sub": "Complete Asset Extraction & Forensics Report",
        "html_encrypted": "Password Protected / Encrypted",
        "html_open": "Unencrypted (Open)",
        "html_not_specified": "Not specified",
        "html_not_defined": "Undefined",
        "html_creator": "Authoring Software (Creator):",
        "html_producer": "PDF Engine (Producer):",
        "html_created": "Created Date:",
        "html_modified": "Modified Date:",
        "html_author_subj": "Author / Subject:",
        "html_trapped": "Trapped:",
        "kpi_pages": "Total Pages",
        "kpi_images": "Extracted Images",
        "kpi_vectors": "Vector Pages (.SVG / .AI)",
        "kpi_fonts": "Fonts ({e} embedded)",
        "kpi_profiles": "ICC Profiles",
        "kpi_spots": "Spot Colors",
        "kpi_attachments": "Attachments",
        "tab_images": "Images",
        "tab_vectors": "Vectors",
        "tab_fonts": "Fonts",
        "tab_profiles": "Color Profiles & Inks",
        "tab_pages": "Dimensions & Pre-Press",
        "tab_attachments": "Attachments",
        "tab_xmp": "Metadata & XMP",
        "img_dims": "Size:",
        "img_weight": "File:",
        "img_space": "Space:",
        "img_alpha": "Alpha:",
        "img_pages": "Pages:",
        "yes_smask": "Yes (SMask)",
        "no": "No",
        "btn_dl_img": "Download Image",
        "empty_images": "No embedded raster images found in this PDF.",
        "vec_heading": "Extracted Vector Graphics (.SVG and Adobe Illustrator .AI)",
        "vec_desc": "<strong>.SVG</strong> files are universal (Figma, Illustrator, Inkscape, Web). <strong>.AI</strong> files contain pure vector artwork with raster images stripped, natively editable in Adobe Illustrator.",
        "empty_vectors": "No vector graphics detected in this PDF.",
        "th_page": "Page",
        "th_paths": "Total Paths",
        "th_geom_detail": "Geometry Details",
        "th_colors": "Detected Colors",
        "th_download": "Download",
        "paths_label": "{n} paths",
        "vec_detail_fmt": "Bézier Curves: {c} &bull; Lines: {l} &bull; Rectangles: {r}",
        "dl_svg": "Download .SVG ({sz})",
        "dl_ai": "Download .AI ({sz})",
        "font_heading": "Fonts & Typography Inventory",
        "font_desc": "<strong>Full Fonts</strong> contain the entire character set and work for typing any text. <strong>Partial Subsets</strong> only contain characters used in this PDF (missing characters appear as empty boxes); missing SFNT tables are automatically repaired for OS installability.",
        "empty_fonts": "No fonts detected in this PDF.",
        "th_font_name": "Font Name",
        "th_type": "Type",
        "th_install_status": "Status & Installability",
        "th_char_sample": "Character Sample",
        "th_glyphs": "Glyphs",
        "th_size": "Size",
        "th_attrs": "Attributes",
        "th_pages": "Pages",
        "font_full": "Full Font",
        "font_subset": "Subset ({n} chars)",
        "font_embedded": "Embedded",
        "font_system": "System (Not extractable)",
        "font_italic": "Italic",
        "font_bold": "Bold",
        "font_mono": "Monospace",
        "font_normal": "Regular",
        "dl_font": "Download ({ext})",
        "prof_heading": "Embedded ICC Profiles",
        "empty_profiles": "No explicitly embedded ICC profiles found.",
        "spot_heading": "Spot Colors / Separations",
        "empty_spots": "No custom spot inks detected in this document.",
        "th_prof_desc": "Profile Description",
        "th_cs": "Color Space",
        "th_dev_class": "Device Class",
        "th_ver": "Version",
        "dl_icc": "Download .ICC",
        "th_fmt_mb": "Format & MediaBox",
        "th_trim": "TrimBox",
        "th_bleed": "BleedBox",
        "th_rot": "Rotation",
        "th_imgs": "Images",
        "th_fnts": "Fonts",
        "th_vec_paths": "Vector Paths",
        "th_words": "Words",
        "page_word": "Page",
        "th_filename": "File Name",
        "th_desc": "Description",
        "th_source": "Source",
        "dl_file": "Download File",
        "empty_attachments": "No embedded file attachments in this PDF.",
        "xmp_heading": "XMP Metadata Packet (Adobe Extensible Metadata Platform)",
        "empty_xmp": "No XMP metadata stream present in this PDF.",
        "modal_preview": "Image Preview",
        "modal_dl": "Download Full Resolution",
        "legal_title": "Legal Notice & Responsible Use",
        "legal_body": "This tool is designed for technical inspection, pre-press verification, accessibility auditing, and recovering your own archives. Extracted images, fonts, vector artwork, and trademarks may be protected by copyright or commercial license agreements (EULA). You are solely responsible for verifying rights and licenses before reusing or redistributing any extracted assets.",
        # Batch HTML Report
        "batch_html_title": "Batch Extraction Summary — PDF Asset Extractor",
        "batch_html_heading": "Batch Extraction Summary",
        "batch_html_base": "Base folder:",
        "batch_done_badge": "{s}/{t} Completed",
        "batch_partial_badge": "{s}/{t} OK · {f} Errors",
        "batch_kpi_pdfs": "Processed PDFs",
        "batch_kpi_vec_pages": "Vector Pages",
        "batch_kpi_emb_fonts": "Embedded Fonts",
        "batch_docs_heading": "Processed Documents",
        "batch_filter_ph": "Filter documents by name...",
        "th_doc_sub": "PDF Document & Subfolder",
        "th_status": "Status",
        "th_prof_att": "Profiles / Files",
        "th_actions": "Actions",
        "btn_open_pdf_report": "Open PDF Report →",
        "html_disabled_txt": "HTML disabled",
        "btn_folder": "Folder",
        # Print Readiness Audit (Preflight)
        "tab_preflight": "Print Check",
        "preflight_heading": "Pre-Press & Print Readiness Audit",
        "preflight_desc": "Automated technical verification of image DPI, color spaces, print bleed margins, and font embedding.",
        "pf_status_pass": "Print Ready",
        "pf_status_warn": "Warnings ({n})",
        "pf_status_fail": "Issues ({n})",
        "pf_badge_pass": "PASS",
        "pf_badge_warn": "WARN",
        "pf_badge_fail": "FAIL",
        "pf_badge_skip": "SKIPPED",
        "pf_check_image_resolution": "Image Resolution (Effective DPI)",
        "pf_check_color_spaces": "Color Spaces & Separation",
        "pf_check_bleed_boxes": "Print Bleed & Trim Geometry",
        "pf_check_fonts_embedding": "Font Embedding",
        "pf_res_pass": "All {n} placed image(s) meet the >= {min_dpi} DPI print threshold.",
        "pf_res_none": "No raster images with placement DPI metrics to check.",
        "pf_res_skipped": "Image extraction disabled — DPI check skipped.",
        "pf_res_issues": "{crit} image(s) < {crit_dpi} DPI, {warn} image(s) between {crit_dpi}-{min_dpi} DPI.",
        "pf_cs_pass": "Consistent print color spaces detected (CMYK/Gray/Spot).",
        "pf_cs_none": "No RGB color separation warnings detected.",
        "pf_cs_skipped": "Image/profile extraction disabled — color check skipped.",
        "pf_cs_mixed": "Mixed color spaces detected: RGB ({rgb}) and CMYK ({cmyk}) images.",
        "pf_cs_rgb_only": "{rgb} RGB image(s) detected without CMYK assets — verify conversion for offset printing.",
        "pf_bleed_pass": "All {total} page(s) define a BleedBox extending beyond TrimBox.",
        "pf_bleed_partial": "{with_bleed}/{total} page(s) have print bleed beyond TrimBox; {missing} missing bleed.",
        "pf_bleed_missing": "No BleedBox margin beyond TrimBox detected across {total} page(s).",
        "pf_bleed_none": "No page geometry available.",
        "pf_fonts_pass": "All {total} font(s) are embedded ({subsets} subset(s)).",
        "pf_fonts_none": "No font references detected.",
        "pf_fonts_skipped": "Font extraction disabled — embedding check skipped.",
        "pf_fonts_fail": "{unemb} non-embedded system font(s) out of {total} — RIP may substitute typefaces.",
        "pf_pages_affected": "Pages: {pages}",
        "pf_th_check": "Check",
        "pf_th_status": "Status",
        "pf_th_summary": "Details",
        "pf_th_affected": "Affected Items / Pages",
        "pf_cli_title": "Print Readiness Audit",
        "batch_th_preflight": "Preflight",
    },
    "it": {
        # Output subfolder suffix
        "folder_suffix": "_estratto",
        # GUI Header & Theme
        "theme_light": "Tema Chiaro",
        "theme_dark": "Tema Scuro",
        "footer_disclaimer": "Uso responsabile: verifica i diritti d'autore e le licenze (EULA) di font, immagini e grafiche prima del riutilizzo.",
        # Dropzone
        "drop_title": "Trascina uno o più PDF (o una cartella)",
        "drop_sub": "Singolo file o elaborazione Batch locale",
        "btn_choose_pdfs": "Scegli file PDF...",
        "btn_choose_folder": "Cartella...",
        # Single Preview
        "pdf_locked": "PDF protetto da password",
        "pwd_placeholder": "Inserisci password...",
        "btn_unlock": "Sblocca PDF",
        "preview_unavailable": "Anteprima non disponibile",
        "page_singular": "1 pagina",
        "page_plural": "{n} pagine",
        "encrypted_file": "File crittografato",
        "enter_pwd_hint": "Inserisci la password per visualizzare e estrarre.",
        "status_wait_pwd": "In attesa della password del PDF...",
        "unknown_gen": "Generatore non dichiarato",
        "app_prefix": "App: {app}",
        "btn_add_more_batch": "Aggiungi altri (Batch)",
        "btn_change": "Cambia",
        # Batch Queue
        "batch_queue_title": "Coda Batch • {n} PDF",
        "btn_add": "Aggiungi",
        "btn_clear": "Svuota",
        "batch_footer_tip": "Trascina altri PDF o cartelle qui per aggiungerli alla coda.",
        "status_queued": "In coda",
        "status_running": "In corso",
        "status_ok": "OK",
        "status_error": "Errore",
        "btn_open": "Apri",
        # Right Panel Controls
        "lbl_profile": "Profilo di estrazione",
        "preset_full": "Completo",
        "preset_graphics": "Solo Grafica",
        "preset_fonts": "Solo Font",
        "preset_audit": "Solo Analisi",
        "sw_images": "Immagini HD (Alfa PNG)",
        "sw_vectors": "Vettoriali (.SVG / .AI)",
        "sw_fonts": "Font & Sottinsiemi",
        "sw_profiles": "Profili ICC & Tinte Spot",
        "sw_attachments": "Allegati Incorporati",
        "sw_gen_html": "Genera Report HTML",
        "chk_auto_open_html": "Apri automaticamente il Report HTML nel browser al termine",
        "dest_placeholder": "Cartella base (predefinito: ./output)",
        "hint_empty": "Verrà creata una sottocartella <nome>_estratto (numerata se già esistente).",
        "hint_single": "Verrà creata la cartella: {name}",
        "hint_batch": "Verranno create {n} sottocartelle separate (<nome>_estratto) nella directory scelta.",
        # CTA & Status
        "btn_extract": "Estrai Risorse",
        "btn_extract_batch": "Avvia Batch ({n} PDF)",
        "btn_processing": "Elaborazione in corso...",
        "status_idle": "Seleziona o trascina uno o più PDF per iniziare.",
        "status_ready": "Pronto per l'estrazione.",
        "status_batch_ready": "Coda pronta: {n} documenti da elaborare.",
        "status_saved_in": "Salvato in: {name}",
        "status_batch_done": "Batch completato: {s}/{t} PDF salvati in {dir}/",
        "status_batch_partial": "Batch terminato: {s} riusciti, {f} con errori.",
        # Results Card
        "res_done": "Estrazione completata",
        "res_batch_done": "Batch completato ({s}/{t} PDF)",
        "res_batch_partial": "Batch completato ({s}/{t} OK, {f} errori)",
        "chip_images": "{n} Immagini",
        "chip_vectors": "{n} Vettoriali",
        "chip_fonts": "{e}/{t} Font",
        "chip_profiles": "{n} Profili",
        "chip_attachments": "{n} Allegati",
        "btn_open_out": "Apri Cartella Output",
        "btn_open_batch": "Apri Cartella Batch",
        "btn_open_html": "Apri Report HTML",
        "btn_open_batch_html": "Apri Report Batch HTML",
        # Dialogs
        "dlg_no_pdf_found_title": "Nessun PDF trovato",
        "dlg_no_pdf_found_msg": "Trascina uno o più file .pdf oppure una cartella contenente PDF.",
        "dlg_empty_dir_title": "Cartella vuota",
        "dlg_empty_dir_msg": "Nessun file .pdf trovato nella cartella selezionata.",
        "dlg_read_err_title": "Errore lettura PDF",
        "dlg_read_err_msg": "Impossibile leggere il file:\n{err}",
        "dlg_wrong_pwd_title": "Password errata",
        "dlg_wrong_pwd_msg": "La password inserita non è corretta.",
        "dlg_no_pdf_title": "Nessun PDF",
        "dlg_no_pdf_msg": "Trascina o seleziona almeno un file PDF prima di avviare.",
        "dlg_err_title": "Errore Estrazione",
        "dlg_err_msg": "Si è verificato un errore:\n\n{err}",
        "dlg_browse_pdfs": "Seleziona uno o più file PDF",
        "dlg_browse_folder": "Seleziona cartella contenente PDF",
        "dlg_browse_dest": "Seleziona cartella base di destinazione",
        "dlg_all_files": "Tutti i file",
        "dlg_pdf_files": "Documenti PDF (*.pdf)",
        # Core Progress
        "prog_open": "Apertura documento PDF...",
        "prog_meta": "Estrazione metadati e informazioni software...",
        "prog_geom": "Analisi geometria pagine e formato...",
        "prog_imgs": "Estrazione immagini e ricostruzione trasparenza...",
        "prog_vecs": "Estrazione grafica vettoriale (.SVG / .AI)...",
        "prog_fonts": "Recupero e riparazione font incorporati...",
        "prog_profs": "Analisi profili colore ICC e inchiostri spot...",
        "prog_attach": "Estrazione file allegati...",
        "prog_reports": "Salvataggio report JSON e dashboard HTML...",
        "prog_done": "Estrazione completata!",
        "prog_batch_done": "Batch completato: {s}/{t} PDF elaborati.",
        "err_pwd_required": "Il PDF è protetto da password. Inserisci una password valida per procedere.",
        # HTML Report (Single)
        "html_doc_title": "Report Asset & Metadati PDF",
        "html_doc_sub": "Report Completo di Estrazione Risorse e Metadati",
        "html_encrypted": "Protetto da Password / Crittografato",
        "html_open": "Nessuna Crittografia (Aperto)",
        "html_not_specified": "Non specificato",
        "html_not_defined": "Non definito",
        "html_creator": "Software di Creazione:",
        "html_producer": "Motore di Generazione (Producer):",
        "html_created": "Data di Creazione:",
        "html_modified": "Ultima Modifica:",
        "html_author_subj": "Autore / Soggetto:",
        "html_trapped": "Trapped:",
        "kpi_pages": "Pagine Totali",
        "kpi_images": "Immagini Estratte",
        "kpi_vectors": "Vettoriali (.SVG / .AI)",
        "kpi_fonts": "Font Censiti ({e} incorporati)",
        "kpi_profiles": "Profili ICC",
        "kpi_spots": "Colori Speciali (Spot)",
        "kpi_attachments": "File Allegati",
        "tab_images": "Immagini",
        "tab_vectors": "Vettoriali",
        "tab_fonts": "Font",
        "tab_profiles": "Profili Colore & Inchiostri",
        "tab_pages": "Dimensioni & Pre-stampa",
        "tab_attachments": "Allegati",
        "tab_xmp": "Metadati & XMP",
        "img_dims": "Dim.:",
        "img_weight": "Peso:",
        "img_space": "Spazio:",
        "img_alpha": "Alpha:",
        "img_pages": "Pagine:",
        "yes_smask": "Sì (SMask)",
        "no": "No",
        "btn_dl_img": "Scarica Immagine",
        "empty_images": "Nessuna immagine raster incorporata trovata in questo PDF.",
        "vec_heading": "Grafica Vettoriale Estratta (.SVG e Adobe Illustrator .AI)",
        "vec_desc": "I file <strong>.SVG</strong> sono universali (compatibili con Figma, Illustrator, Inkscape e Web). I file <strong>.AI</strong> contengono la grafica vettoriale pura senza elementi raster, apribili nativamente in Adobe Illustrator con tutti i tracciati modificabili.",
        "empty_vectors": "Nessuna grafica vettoriale rilevata nel PDF.",
        "th_page": "Pagina",
        "th_paths": "Tracciati Totali",
        "th_geom_detail": "Dettaglio Geometria",
        "th_colors": "Colori Rilevati",
        "th_download": "Download",
        "paths_label": "{n} tracciati",
        "vec_detail_fmt": "Curve B&eacute;zier: {c} &bull; Linee: {l} &bull; Rettangoli: {r}",
        "dl_svg": "Scarica .SVG ({sz})",
        "dl_ai": "Scarica .AI ({sz})",
        "font_heading": "Font & Tipografia Censiti",
        "font_desc": "I font con stato <strong>Font Completo</strong> contengono l'intero alfabeto e sono utilizzabili liberamente per comporre qualsiasi testo. I font con stato <strong>Sottinsieme</strong> contengono esclusivamente i caratteri digitati nel documento originario; le tabelle SFNT mancanti vengono riparate automaticamente per renderli installabili.",
        "empty_fonts": "Nessun font rilevato nel PDF.",
        "th_font_name": "Nome Font",
        "th_type": "Tipo",
        "th_install_status": "Stato & Installabilità",
        "th_char_sample": "Campione Caratteri",
        "th_glyphs": "Glifi",
        "th_size": "Dimensione",
        "th_attrs": "Attributi",
        "th_pages": "Pagine",
        "font_full": "Font Completo",
        "font_subset": "Sottinsieme ({n} caratteri)",
        "font_embedded": "Incorporato",
        "font_system": "Di Sistema (Non estraibile)",
        "font_italic": "Corsivo",
        "font_bold": "Grassetto",
        "font_mono": "Monospazio",
        "font_normal": "Normale",
        "dl_font": "Scarica ({ext})",
        "prof_heading": "Profili ICC Incorporati",
        "empty_profiles": "Nessun profilo ICC incorporato esplicitamente trovato.",
        "spot_heading": "Colori Speciali (Spot Colors / Separations)",
        "empty_spots": "Nessun colore speciale / spot rilevato nel documento.",
        "th_prof_desc": "Descrizione Profilo",
        "th_cs": "Spazio Colore",
        "th_dev_class": "Classe Dispositivo",
        "th_ver": "Versione",
        "dl_icc": "Scarica .ICC",
        "th_fmt_mb": "Formato & MediaBox",
        "th_trim": "TrimBox (Ritaglio)",
        "th_bleed": "BleedBox (Abbondanza)",
        "th_rot": "Rotazione",
        "th_imgs": "Immagini",
        "th_fnts": "Font",
        "th_vec_paths": "Tracciati Vettoriali",
        "th_words": "Parole",
        "page_word": "Pagina",
        "th_filename": "Nome File",
        "th_desc": "Descrizione",
        "th_source": "Origine",
        "dl_file": "Scarica File",
        "empty_attachments": "Nessun file o allegato incorporato nel PDF.",
        "xmp_heading": "Pacchetto XML Metadati XMP (Adobe Extensible Metadata Platform)",
        "empty_xmp": "Nessun flusso XMP presente nel PDF.",
        "modal_preview": "Anteprima Immagine",
        "modal_dl": "Scarica Risoluzione Piena",
        "legal_title": "Note Legali & Utilizzo Responsabile",
        "legal_body": "Questo strumento è concepito per analisi tecnica, verifica di pre-stampa, audit di accessibilità e recupero dei propri archivi documentali. Le immagini, i font, la grafica vettoriale e i marchi estratti possono essere protetti da diritto d'autore, copyright o accordi di licenza commerciale (EULA). L'utente è l'unico responsabile di verificare e rispettare le licenze e i diritti di utilizzo prima di riutilizzare o ridistribuire qualsiasi risorsa estratta.",
        # Batch HTML Report
        "batch_html_title": "Riepilogo Elaborazione Batch — PDF Asset Extractor",
        "batch_html_heading": "Riepilogo Elaborazione Batch",
        "batch_html_base": "Cartella base:",
        "batch_done_badge": "{s}/{t} Completati",
        "batch_partial_badge": "{s}/{t} OK · {f} Errori",
        "batch_kpi_pdfs": "PDF Elaborati",
        "batch_kpi_vec_pages": "Pagine Vettoriali",
        "batch_kpi_emb_fonts": "Font Incorporati",
        "batch_docs_heading": "Documenti elaborati",
        "batch_filter_ph": "Filtra documenti per nome...",
        "th_doc_sub": "Documento PDF & Sottocartella",
        "th_status": "Stato",
        "th_prof_att": "Profili / Allegati",
        "th_actions": "Azioni",
        "btn_open_pdf_report": "Apri Report PDF →",
        "html_disabled_txt": "HTML disattivato",
        "btn_folder": "Cartella",
        # Print Readiness Audit (Preflight)
        "tab_preflight": "Preflight Stampa",
        "preflight_heading": "Audit Pre-Stampa & Qualità",
        "preflight_desc": "Verifica tecnica automatica di DPI immagini, spazi colore, abbondanza di stampa e incorporamento font.",
        "pf_status_pass": "Pronto Stampa",
        "pf_status_warn": "Avvisi ({n})",
        "pf_status_fail": "Critico ({n})",
        "pf_badge_pass": "OK",
        "pf_badge_warn": "AVVISO",
        "pf_badge_fail": "CRITICO",
        "pf_badge_skip": "SALTATO",
        "pf_check_image_resolution": "Risoluzione Immagini (DPI effettivi)",
        "pf_check_color_spaces": "Spazi Colore & Separazione",
        "pf_check_bleed_boxes": "Abbondanza (BleedBox) & Rifilo",
        "pf_check_fonts_embedding": "Incorporamento Font",
        "pf_res_pass": "Tutte le {n} immagini posizionate rispettano la soglia >= {min_dpi} DPI.",
        "pf_res_none": "Nessuna immagine raster con metriche DPI posizionate da verificare.",
        "pf_res_skipped": "Estrazione immagini disattivata — controllo DPI saltato.",
        "pf_res_issues": "{crit} immagini < {crit_dpi} DPI, {warn} immagini tra {crit_dpi} e {min_dpi} DPI.",
        "pf_cs_pass": "Spazi colore coerenti per stampa rilevati (CMYK/Gray/Spot).",
        "pf_cs_none": "Nessun avviso di conversione RGB rilevato.",
        "pf_cs_skipped": "Estrazione immagini/profili disattivata — controllo colori saltato.",
        "pf_cs_mixed": "Spazi colore misti rilevati: immagini RGB ({rgb}) e CMYK ({cmyk}).",
        "pf_cs_rgb_only": "{rgb} immagini in RGB senza asset CMYK — verificare conversione per stampa offset.",
        "pf_bleed_pass": "Tutte le {total} pagine definiscono una BleedBox oltre il TrimBox.",
        "pf_bleed_partial": "{with_bleed}/{total} pagine hanno abbondanza oltre il TrimBox; {missing} ne sono prive.",
        "pf_bleed_missing": "Nessuna abbondanza (BleedBox > TrimBox) rilevata su {total} pagine.",
        "pf_bleed_none": "Nessuna geometria pagina disponibile.",
        "pf_fonts_pass": "Tutti i {total} font sono incorporati ({subsets} subset).",
        "pf_fonts_none": "Nessun font rilevato.",
        "pf_fonts_skipped": "Estrazione font disattivata — controllo incorporamento saltato.",
        "pf_fonts_fail": "{unemb} font di sistema NON incorporati su {total} — rischio sostituzione in tipografia.",
        "pf_pages_affected": "Pagine: {pages}",
        "pf_th_check": "Controllo",
        "pf_th_status": "Esito",
        "pf_th_summary": "Dettaglio",
        "pf_th_affected": "Elementi / Pagine interessate",
        "pf_cli_title": "Audit Pre-Stampa",
        "batch_th_preflight": "Preflight",
    },
}


def tr(lang: str, key: str, **kwargs) -> str:
    """Translates key for given language ('en' or 'it'), formatting optional arguments."""
    code = lang if lang in TRANSLATIONS else "en"
    template = TRANSLATIONS[code].get(key) or TRANSLATIONS["en"].get(key) or key
    if kwargs:
        try:
            return template.format(**kwargs)
        except Exception:
            return template
    return template


def format_preflight_check(check: Dict[str, Any], thresholds: Dict[str, Any], lang: str = "en") -> str:
    """Formats a localized human-readable summary line for a single preflight check."""
    cid = check.get("id", "")
    reason = check.get("reason", "none")
    m = check.get("metrics") or {}
    min_dpi = thresholds.get("min_dpi", 300)
    crit_dpi = thresholds.get("critical_dpi", 150)

    if cid == "image_resolution":
        if reason == "skipped":
            return tr(lang, "pf_res_skipped")
        if reason == "issues":
            return tr(lang, "pf_res_issues", crit=m.get("critical", 0), warn=m.get("warning", 0), crit_dpi=crit_dpi, min_dpi=min_dpi)
        if reason == "pass":
            return tr(lang, "pf_res_pass", n=m.get("checked", 0), min_dpi=min_dpi)
        return tr(lang, "pf_res_none")

    if cid == "color_spaces":
        if reason == "skipped":
            return tr(lang, "pf_cs_skipped")
        if reason == "mixed":
            return tr(lang, "pf_cs_mixed", rgb=m.get("rgb", 0), cmyk=m.get("cmyk", 0))
        if reason == "rgb_only":
            return tr(lang, "pf_cs_rgb_only", rgb=m.get("rgb", 0))
        if reason == "pass":
            return tr(lang, "pf_cs_pass")
        return tr(lang, "pf_cs_none")

    if cid == "bleed_boxes":
        if reason == "pass":
            return tr(lang, "pf_bleed_pass", total=m.get("total", 0))
        if reason == "partial":
            return tr(lang, "pf_bleed_partial", with_bleed=m.get("with_bleed", 0), total=m.get("total", 0), missing=m.get("missing", 0))
        if reason == "missing":
            return tr(lang, "pf_bleed_missing", total=m.get("total", 0))
        return tr(lang, "pf_bleed_none")

    if cid == "fonts_embedding":
        if reason == "skipped":
            return tr(lang, "pf_fonts_skipped")
        if reason == "unembedded":
            return tr(lang, "pf_fonts_fail", unemb=m.get("unembedded", 0), total=m.get("total", 0))
        if reason == "pass":
            return tr(lang, "pf_fonts_pass", total=m.get("total", 0), subsets=m.get("subsets", 0))
        return tr(lang, "pf_fonts_none")

    return ""


def format_preflight_badge_label(audit: Dict[str, Any], lang: str = "en") -> str:
    """Formats localized overall preflight status label for GUI/HTML/CLI badges."""
    status = audit.get("status", "pass")
    counts = audit.get("counts") or {}
    if status == "fail":
        return tr(lang, "pf_status_fail", n=counts.get("fail", 1))
    if status == "warn":
        return tr(lang, "pf_status_warn", n=counts.get("warn", 1))
    return tr(lang, "pf_status_pass")

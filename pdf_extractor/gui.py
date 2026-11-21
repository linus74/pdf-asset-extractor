"""
Modern Studio-Grade Desktop GUI (v2.3) for PDF Deep Asset & Metadata Extractor.
Features horizontal Split-View layout, Single-PDF Pre-Flight thumbnail preview,
seamless multi-PDF / folder Batch Queue, 1-click presets, crisp adaptive icons,
Light/Dark theme toggle, deterministic progress, and clickable folder result badges.
"""

import os
import sys
import threading
import webbrowser
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox

import customtkinter as ctk

try:
    from tkinterdnd2 import TkinterDnD, DND_FILES
    HAS_DND = True
except Exception:
    HAS_DND = False

from .core import (
    extract_pdf_assets,
    extract_batch_pdfs,
    inspect_pdf_preflight,
    resolve_unique_output_dir,
    collect_pdf_paths,
)
from .utils.helpers import format_bytes
from .utils.icons import get_ctk_icon
from .utils.i18n import (
    tr,
    get_default_language,
    load_preferences,
    save_preferences,
    format_preflight_badge_label,
)

PRESET_KEYS = ("preset_full", "preset_graphics", "preset_fonts", "preset_audit")


# Calibrated theme palette (Linear / Figma / Affinity inspired)
PALETTE = {
    "bg": ("#F8FAFC", "#0B0F17"),
    "surface": ("#FFFFFF", "#131A26"),
    "surface_alt": ("#F1F5F9", "#182130"),
    "border": ("#CBD5E1", "#2D3A4F"),
    "border_active": ("#0284C7", "#38BDF8"),
    "text": ("#0F172A", "#F8FAFC"),
    "text_muted": ("#64748B", "#94A3B8"),
    "accent": ("#0284C7", "#0EA5E9"),
    "accent_hover": ("#0369A1", "#0284C7"),
    "success_bg": ("#ECFDF5", "#0B2922"),
    "success_border": ("#10B981", "#10B981"),
    "success_text": ("#065F46", "#A7F3D0"),
    "warn_bg": ("#FFFBEB", "#2B210B"),
    "warn_border": ("#F59E0B", "#F59E0B"),
    "badge_bg": ("#E2E8F0", "#1E293B"),
}


def _resolve_asset_path(rel_path: str) -> Path | None:
    """Resolves bundled resource paths both in dev mode and PyInstaller _MEIPASS."""
    candidates = [
        Path(__file__).resolve().parent.parent / rel_path,
        Path.cwd() / rel_path,
    ]
    if hasattr(sys, "_MEIPASS"):
        candidates.insert(0, Path(sys._MEIPASS) / rel_path)
    for c in candidates:
        if c.exists():
            return c
    return None


if HAS_DND:
    class BaseWindow(ctk.CTk, TkinterDnD.DnDWrapper):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.TkdndVersion = TkinterDnD._require(self)
else:
    class BaseWindow(ctk.CTk):
        pass


class PDFExtractorApp(BaseWindow):
    def __init__(self, initial_pdfs: list[Path] | None = None):
        super().__init__()

        prefs = load_preferences()
        saved_theme = prefs.get("theme", "Dark")
        self.current_theme = saved_theme if saved_theme in ("Dark", "Light") else "Dark"
        self.lang = get_default_language()
        self._current_preset_key = "preset_full"

        ctk.set_appearance_mode(self.current_theme)
        ctk.set_default_color_theme("blue")

        self.title("PDF Asset Extractor")
        self.geometry("960x630")
        self.minsize(900, 580)
        self.configure(fg_color=PALETTE["bg"])

        ico_path = _resolve_asset_path("assets/app_icon.ico")
        if ico_path and sys.platform == "win32":
            try:
                self.iconbitmap(str(ico_path))
            except Exception:
                pass

        # State
        self.queued_pdfs: list[Path] = []
        self.batch_row_widgets: dict[Path, dict] = {}
        self.pdf_password: str | None = None
        self.last_result: dict | None = None
        self.is_extracting = False
        self.thumb_ctk_img = None

        # Preload crisp adaptive icons
        self.icons = {
            "logo": get_ctk_icon("logo", size=24),
            "upload": get_ctk_icon("upload", size=34, light_color="#0284C7", dark_color="#38BDF8"),
            "files": get_ctk_icon("files", size=16, light_color="#0284C7", dark_color="#38BDF8"),
            "plus": get_ctk_icon("plus", size=14),
            "image": get_ctk_icon("image", size=16),
            "vector": get_ctk_icon("vector", size=16),
            "font": get_ctk_icon("font", size=16),
            "palette": get_ctk_icon("palette", size=16),
            "attachment": get_ctk_icon("attachment", size=16),
            "folder": get_ctk_icon("folder", size=16),
            "globe": get_ctk_icon("globe", size=16),
            "sun": get_ctk_icon("sun", size=16, light_color="#334155", dark_color="#FCD34D"),
            "moon": get_ctk_icon("moon", size=16, light_color="#334155", dark_color="#CBD5E1"),
            "lock": get_ctk_icon("lock", size=28, light_color="#D97706", dark_color="#FBBF24"),
        }

        self._build_ui()

        if initial_pdfs:
            expanded = collect_pdf_paths(initial_pdfs)
            if expanded:
                self.after(100, lambda: self._add_pdfs(expanded, replace=True))

    def _build_ui(self):
        # ---------------------------------------------------------
        # 1. SLIM TOP HEADER BAR (with version & Linus74 · 2026)
        # ---------------------------------------------------------
        self.topbar = ctk.CTkFrame(self, height=54, corner_radius=0, fg_color=PALETTE["surface"], border_width=0)
        self.topbar.pack(fill="x", side="top")

        self.brand_frame = ctk.CTkFrame(self.topbar, fg_color="transparent")
        self.brand_frame.pack(side="left", padx=20, pady=10)

        self.logo_lbl = ctk.CTkLabel(self.brand_frame, text="", image=self.icons["logo"])
        self.logo_lbl.pack(side="left", padx=(0, 10))

        self.title_lbl = ctk.CTkLabel(
            self.brand_frame,
            text="PDF Asset Extractor",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=PALETTE["text"]
        )
        self.title_lbl.pack(side="left")

        self.ver_badge = ctk.CTkLabel(
            self.brand_frame,
            text="v2.3",
            font=ctk.CTkFont(size=10, weight="bold"),
            fg_color=PALETTE["badge_bg"],
            text_color=PALETTE["text_muted"],
            corner_radius=6,
            padx=7,
            pady=1
        )
        self.ver_badge.pack(side="left", padx=(8, 0))

        self.author_lbl = ctk.CTkLabel(
            self.brand_frame,
            text="·  Linus74 © 2026",
            font=ctk.CTkFont(size=11),
            text_color=PALETTE["text_muted"]
        )
        self.author_lbl.pack(side="left", padx=(8, 0), pady=(1, 0))

        # Theme toggle button + Language switcher on top right
        theme_text_key = "theme_light" if self.current_theme == "Dark" else "theme_dark"
        theme_icon = self.icons["sun"] if self.current_theme == "Dark" else self.icons["moon"]
        self.theme_btn = ctk.CTkButton(
            self.topbar,
            text=tr(self.lang, theme_text_key),
            image=theme_icon,
            compound="left",
            width=112,
            height=30,
            corner_radius=8,
            fg_color=PALETTE["surface_alt"],
            hover_color=PALETTE["badge_bg"],
            text_color=PALETTE["text"],
            font=ctk.CTkFont(size=12),
            command=self._toggle_theme
        )
        self.theme_btn.pack(side="right", padx=(8, 20), pady=10)

        self.lang_seg = ctk.CTkSegmentedButton(
            self.topbar,
            values=["EN", "IT"],
            width=82,
            height=30,
            corner_radius=8,
            font=ctk.CTkFont(size=11, weight="bold"),
            command=self._set_language
        )
        self.lang_seg.set(self.lang.upper())
        self.lang_seg.pack(side="right", pady=10)

        self.top_sep = ctk.CTkFrame(self, height=1, fg_color=PALETTE["border"])
        self.top_sep.pack(fill="x")

        # ---------------------------------------------------------
        # 2. MAIN SPLIT-VIEW BODY (Left 43% / Right 57%)
        # ---------------------------------------------------------
        self.main_body = ctk.CTkFrame(self, fg_color="transparent")
        self.main_body.pack(fill="both", expand=True, padx=20, pady=(16, 8))
        self.main_body.grid_columnconfigure(0, weight=43, uniform="cols")
        self.main_body.grid_columnconfigure(1, weight=57, uniform="cols")
        self.main_body.grid_rowconfigure(0, weight=1)

        # === LEFT PANEL: DROPZONE / SINGLE PREVIEW / BATCH QUEUE ===
        self.left_card = ctk.CTkFrame(
            self.main_body,
            corner_radius=12,
            fg_color=PALETTE["surface"],
            border_width=1,
            border_color=PALETTE["border"]
        )
        self.left_card.grid(row=0, column=0, sticky="nsew", padx=(0, 12))

        self._build_dropzone_view()
        self._build_preview_view()
        self._build_batch_view()
        self._show_left_mode("dropzone")

        if HAS_DND:
            try:
                self.left_card.drop_target_register(DND_FILES)
                self.left_card.dnd_bind("<<Drop>>", self._on_drop_files)
                self.left_card.dnd_bind("<<DragEnter>>", self._on_drag_enter)
                self.left_card.dnd_bind("<<DragLeave>>", self._on_drag_leave)
            except Exception:
                pass

        # === RIGHT PANEL: PRESETS, SWITCHES, OUTPUT, CTA, RESULTS ===
        self.right_card = ctk.CTkFrame(
            self.main_body,
            corner_radius=12,
            fg_color=PALETTE["surface"],
            border_width=1,
            border_color=PALETTE["border"]
        )
        self.right_card.grid(row=0, column=1, sticky="nsew")
        self._build_right_panel()

        # ---------------------------------------------------------
        # 3. SLIM DISCLAIMER FOOTER
        # ---------------------------------------------------------
        self.footer = ctk.CTkLabel(
            self,
            text=tr(self.lang, "footer_disclaimer"),
            font=ctk.CTkFont(size=11),
            text_color=PALETTE["text_muted"]
        )
        self.footer.pack(side="bottom", pady=(0, 10))

    # ---------------------------------------------------------
    # LEFT PANEL VIEWS (Dropzone, Single Preview, Batch Queue)
    # ---------------------------------------------------------
    def _build_dropzone_view(self):
        self.dropzone_view = ctk.CTkFrame(self.left_card, fg_color="transparent")

        self.drop_inner_box = ctk.CTkFrame(
            self.dropzone_view,
            corner_radius=10,
            fg_color=PALETTE["surface_alt"],
            border_width=1,
            border_color=PALETTE["border"]
        )
        self.drop_inner_box.pack(fill="both", expand=True, padx=16, pady=16)

        inner = ctk.CTkFrame(self.drop_inner_box, fg_color="transparent")
        inner.place(relx=0.5, rely=0.5, anchor="center")

        ctk.CTkLabel(inner, text="", image=self.icons["upload"]).pack(pady=(0, 12))

        self.drop_title_lbl = ctk.CTkLabel(
            inner,
            text=tr(self.lang, "drop_title"),
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=PALETTE["text"]
        )
        self.drop_title_lbl.pack(pady=(0, 4))

        self.drop_sub_lbl = ctk.CTkLabel(
            inner,
            text=tr(self.lang, "drop_sub"),
            font=ctk.CTkFont(size=12),
            text_color=PALETTE["text_muted"]
        )
        self.drop_sub_lbl.pack(pady=(0, 16))

        btn_row = ctk.CTkFrame(inner, fg_color="transparent")
        btn_row.pack()

        self.drop_browse_btn = ctk.CTkButton(
            btn_row,
            text=tr(self.lang, "btn_choose_pdfs"),
            height=36,
            corner_radius=8,
            fg_color=PALETTE["accent"],
            hover_color=PALETTE["accent_hover"],
            font=ctk.CTkFont(size=13, weight="bold"),
            command=lambda: self._browse_pdfs(replace=True)
        )
        self.drop_browse_btn.pack(side="left", padx=(0, 8))

        self.drop_folder_btn = ctk.CTkButton(
            btn_row,
            text=tr(self.lang, "btn_choose_folder"),
            image=self.icons["folder"],
            compound="left",
            height=36,
            width=110,
            corner_radius=8,
            fg_color=PALETTE["surface_alt"],
            hover_color=PALETTE["badge_bg"],
            text_color=PALETTE["text"],
            border_width=1,
            border_color=PALETTE["border"],
            font=ctk.CTkFont(size=12, weight="bold"),
            command=lambda: self._browse_folder_pdfs(replace=True)
        )
        self.drop_folder_btn.pack(side="left")

    def _build_preview_view(self):
        self.preview_view = ctk.CTkFrame(self.left_card, fg_color="transparent")

        self.thumb_container = ctk.CTkFrame(
            self.preview_view,
            corner_radius=8,
            fg_color=PALETTE["surface_alt"],
            border_width=1,
            border_color=PALETTE["border"]
        )
        self.thumb_container.pack(fill="both", expand=True, padx=16, pady=(16, 10))

        self.thumb_label = ctk.CTkLabel(self.thumb_container, text="")
        self.thumb_label.place(relx=0.5, rely=0.5, anchor="center")

        # Password inline frame
        self.lock_frame = ctk.CTkFrame(self.thumb_container, fg_color="transparent")
        ctk.CTkLabel(self.lock_frame, text="", image=self.icons["lock"]).pack(pady=(0, 6))
        self.lock_title_lbl = ctk.CTkLabel(
            self.lock_frame,
            text=tr(self.lang, "pdf_locked"),
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=PALETTE["text"]
        )
        self.lock_title_lbl.pack(pady=(0, 8))

        self.pwd_entry = ctk.CTkEntry(
            self.lock_frame,
            placeholder_text=tr(self.lang, "pwd_placeholder"),
            show="•",
            width=200
        )
        self.pwd_entry.pack(pady=(0, 8))
        self.pwd_entry.bind("<Return>", lambda e: self._unlock_pdf())

        self.unlock_btn = ctk.CTkButton(
            self.lock_frame,
            text=tr(self.lang, "btn_unlock"),
            width=120,
            height=30,
            command=self._unlock_pdf
        )
        self.unlock_btn.pack()

        # Pre-flight metadata info card
        self.meta_box = ctk.CTkFrame(self.preview_view, fg_color="transparent")
        self.meta_box.pack(fill="x", padx=16, pady=(0, 14))

        self.pdf_name_lbl = ctk.CTkLabel(
            self.meta_box,
            text="",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=PALETTE["text"],
            anchor="w"
        )
        self.pdf_name_lbl.pack(fill="x")

        self.pdf_chips_lbl = ctk.CTkLabel(
            self.meta_box,
            text="",
            font=ctk.CTkFont(size=11),
            text_color=PALETTE["accent"],
            anchor="w"
        )
        self.pdf_chips_lbl.pack(fill="x", pady=(2, 2))

        self.pdf_gen_lbl = ctk.CTkLabel(
            self.meta_box,
            text="",
            font=ctk.CTkFont(size=11),
            text_color=PALETTE["text_muted"],
            anchor="w"
        )
        self.pdf_gen_lbl.pack(fill="x", pady=(0, 10))

        # Action row: Add more (promote to Batch) | Replace
        pv_btns = ctk.CTkFrame(self.meta_box, fg_color="transparent")
        pv_btns.pack(fill="x")

        self.add_more_btn = ctk.CTkButton(
            pv_btns,
            text=tr(self.lang, "btn_add_more_batch"),
            image=self.icons["plus"],
            compound="left",
            height=30,
            corner_radius=8,
            fg_color=PALETTE["surface_alt"],
            hover_color=PALETTE["badge_bg"],
            text_color=PALETTE["text"],
            border_width=1,
            border_color=PALETTE["border"],
            font=ctk.CTkFont(size=12),
            command=lambda: self._browse_pdfs(replace=False)
        )
        self.add_more_btn.pack(side="left", fill="x", expand=True, padx=(0, 6))

        self.change_btn = ctk.CTkButton(
            pv_btns,
            text=tr(self.lang, "btn_change"),
            width=82,
            height=30,
            corner_radius=8,
            fg_color=PALETTE["surface_alt"],
            hover_color=PALETTE["badge_bg"],
            text_color=PALETTE["text"],
            font=ctk.CTkFont(size=12),
            command=lambda: self._browse_pdfs(replace=True)
        )
        self.change_btn.pack(side="right")

    def _build_batch_view(self):
        self.batch_view = ctk.CTkFrame(self.left_card, fg_color="transparent")

        # Top header of Batch Queue
        b_hdr = ctk.CTkFrame(self.batch_view, fg_color="transparent")
        b_hdr.pack(fill="x", padx=16, pady=(14, 8))

        title_wrap = ctk.CTkFrame(b_hdr, fg_color="transparent")
        title_wrap.pack(side="left")
        ctk.CTkLabel(title_wrap, text="", image=self.icons["files"]).pack(side="left", padx=(0, 8))
        self.batch_count_lbl = ctk.CTkLabel(
            title_wrap,
            text=tr(self.lang, "batch_queue_title", n=0),
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=PALETTE["text"]
        )
        self.batch_count_lbl.pack(side="left")

        btns_wrap = ctk.CTkFrame(b_hdr, fg_color="transparent")
        btns_wrap.pack(side="right")

        self.batch_add_btn = ctk.CTkButton(
            btns_wrap,
            text=tr(self.lang, "btn_add"),
            image=self.icons["plus"],
            compound="left",
            width=82,
            height=26,
            corner_radius=6,
            fg_color=PALETTE["surface_alt"],
            hover_color=PALETTE["badge_bg"],
            text_color=PALETTE["text"],
            border_width=1,
            border_color=PALETTE["border"],
            font=ctk.CTkFont(size=11, weight="bold"),
            command=lambda: self._browse_pdfs(replace=False)
        )
        self.batch_add_btn.pack(side="left", padx=(0, 6))

        self.batch_clear_btn = ctk.CTkButton(
            btns_wrap,
            text=tr(self.lang, "btn_clear"),
            width=60,
            height=26,
            corner_radius=6,
            fg_color="transparent",
            hover_color=PALETTE["badge_bg"],
            text_color=PALETTE["text_muted"],
            font=ctk.CTkFont(size=11),
            command=self._clear_queue
        )
        self.batch_clear_btn.pack(side="left")

        # Scrollable queue container
        self.batch_scroll = ctk.CTkScrollableFrame(
            self.batch_view,
            corner_radius=8,
            fg_color=PALETTE["surface_alt"],
            border_width=1,
            border_color=PALETTE["border"]
        )
        self.batch_scroll.pack(fill="both", expand=True, padx=16, pady=(0, 8))

        # Bottom tip
        self.batch_footer_lbl = ctk.CTkLabel(
            self.batch_view,
            text=tr(self.lang, "batch_footer_tip"),
            font=ctk.CTkFont(size=11),
            text_color=PALETTE["text_muted"]
        )
        self.batch_footer_lbl.pack(padx=16, pady=(0, 12))

    def _show_left_mode(self, mode: str):
        self.dropzone_view.pack_forget()
        self.preview_view.pack_forget()
        self.batch_view.pack_forget()
        if mode == "dropzone":
            self.dropzone_view.pack(fill="both", expand=True)
        elif mode == "preview":
            self.preview_view.pack(fill="both", expand=True)
        elif mode == "batch":
            self.batch_view.pack(fill="both", expand=True)

    # ---------------------------------------------------------
    # RIGHT PANEL CONTROLS & RESULTS
    # ---------------------------------------------------------
    def _build_right_panel(self):
        # 1. Presets Bar
        preset_hdr = ctk.CTkFrame(self.right_card, fg_color="transparent")
        preset_hdr.pack(fill="x", padx=18, pady=(16, 6))

        self.preset_title_lbl = ctk.CTkLabel(
            preset_hdr,
            text=tr(self.lang, "lbl_profile"),
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=PALETTE["text_muted"]
        )
        self.preset_title_lbl.pack(anchor="w", pady=(0, 6))

        preset_values = [tr(self.lang, k) for k in PRESET_KEYS]
        self.preset_seg = ctk.CTkSegmentedButton(
            preset_hdr,
            values=preset_values,
            command=self._apply_preset,
            font=ctk.CTkFont(size=12, weight="bold"),
            height=32
        )
        self.preset_seg.set(tr(self.lang, self._current_preset_key))
        self.preset_seg.pack(fill="x")

        # 2. Switches Grid (2 columns)
        switches_frame = ctk.CTkFrame(
            self.right_card,
            corner_radius=10,
            fg_color=PALETTE["surface_alt"],
            border_width=1,
            border_color=PALETTE["border"]
        )
        switches_frame.pack(fill="x", padx=18, pady=10)
        switches_frame.grid_columnconfigure(0, weight=1)
        switches_frame.grid_columnconfigure(1, weight=1)

        def _make_switch(parent, row, col, icon_key, text, default_on=True):
            cell = ctk.CTkFrame(parent, fg_color="transparent")
            cell.grid(row=row, column=col, padx=12, pady=7, sticky="ew")
            ctk.CTkLabel(cell, text="", image=self.icons[icon_key]).pack(side="left", padx=(0, 8))
            sw = ctk.CTkSwitch(
                cell,
                text=text,
                font=ctk.CTkFont(size=12),
                text_color=PALETTE["text"],
                switch_width=36,
                switch_height=18,
                command=self._on_manual_switch
            )
            if default_on:
                sw.select()
            sw.pack(side="left", fill="x")
            return sw

        self.sw_images = _make_switch(switches_frame, 0, 0, "image", tr(self.lang, "sw_images"), True)
        self.sw_vectors = _make_switch(switches_frame, 0, 1, "vector", tr(self.lang, "sw_vectors"), True)
        self.sw_fonts = _make_switch(switches_frame, 1, 0, "font", tr(self.lang, "sw_fonts"), True)
        self.sw_profiles = _make_switch(switches_frame, 1, 1, "palette", tr(self.lang, "sw_profiles"), True)
        self.sw_attachments = _make_switch(switches_frame, 2, 0, "attachment", tr(self.lang, "sw_attachments"), True)
        self.sw_gen_html = _make_switch(switches_frame, 2, 1, "globe", tr(self.lang, "sw_gen_html"), True)

        # Optional Auto-Open HTML toggle row (OFF by default)
        html_opt_row = ctk.CTkFrame(self.right_card, fg_color="transparent")
        html_opt_row.pack(fill="x", padx=20, pady=(0, 6))
        self.chk_auto_open_html = ctk.CTkCheckBox(
            html_opt_row,
            text=tr(self.lang, "chk_auto_open_html"),
            font=ctk.CTkFont(size=11),
            text_color=PALETTE["text_muted"],
            checkbox_width=16,
            checkbox_height=16
        )
        self.chk_auto_open_html.deselect()
        self.chk_auto_open_html.pack(anchor="w")

        # 3. Output Destination Row
        dest_row = ctk.CTkFrame(self.right_card, fg_color="transparent")
        dest_row.pack(fill="x", padx=18, pady=(4, 2))

        ctk.CTkLabel(dest_row, text="", image=self.icons["folder"]).pack(side="left", padx=(0, 8))
        self.dest_entry = ctk.CTkEntry(
            dest_row,
            placeholder_text=tr(self.lang, "dest_placeholder"),
            height=32,
            font=ctk.CTkFont(size=12),
            border_color=PALETTE["border"]
        )
        self.dest_entry.insert(0, str(Path.cwd() / "output"))
        self.dest_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))

        self.dest_btn = ctk.CTkButton(
            dest_row,
            text=tr(self.lang, "btn_change"),
            width=76,
            height=32,
            fg_color=PALETTE["surface_alt"],
            hover_color=PALETTE["badge_bg"],
            text_color=PALETTE["text"],
            font=ctk.CTkFont(size=12),
            command=self._browse_output_dir
        )
        self.dest_btn.pack(side="right")

        self.dest_hint_lbl = ctk.CTkLabel(
            self.right_card,
            text=tr(self.lang, "hint_empty"),
            font=ctk.CTkFont(size=10),
            text_color=PALETTE["text_muted"],
            anchor="w"
        )
        self.dest_hint_lbl.pack(fill="x", padx=44, pady=(0, 8))

        # 4. Action CTA + Progress
        self.cta_frame = ctk.CTkFrame(self.right_card, fg_color="transparent")
        self.cta_frame.pack(fill="x", padx=18, pady=(2, 8))

        self.extract_btn = ctk.CTkButton(
            self.cta_frame,
            text=tr(self.lang, "btn_extract"),
            height=42,
            corner_radius=8,
            fg_color=PALETTE["accent"],
            hover_color=PALETTE["accent_hover"],
            font=ctk.CTkFont(size=14, weight="bold"),
            command=self._start_extraction
        )
        self.extract_btn.pack(fill="x")

        self.progress_bar = ctk.CTkProgressBar(self.cta_frame, height=6, mode="determinate")
        self.progress_bar.set(0)

        self.status_lbl = ctk.CTkLabel(
            self.cta_frame,
            text=tr(self.lang, "status_idle"),
            font=ctk.CTkFont(size=11),
            text_color=PALETTE["text_muted"],
            anchor="w"
        )
        self.status_lbl.pack(fill="x", pady=(6, 0))

        # 5. Actionable Results Card (Shown in place after extraction)
        self.results_card = ctk.CTkFrame(
            self.right_card,
            corner_radius=10,
            fg_color=PALETTE["success_bg"],
            border_width=1,
            border_color=PALETTE["success_border"]
        )

        res_top = ctk.CTkFrame(self.results_card, fg_color="transparent")
        res_top.pack(fill="x", padx=14, pady=(10, 8))

        self.res_title_lbl = ctk.CTkLabel(
            res_top,
            text=tr(self.lang, "res_done"),
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=PALETTE["success_text"]
        )
        self.res_title_lbl.pack(side="left")

        self.res_preflight_lbl = ctk.CTkLabel(
            res_top,
            text="",
            font=ctk.CTkFont(size=11, weight="bold"),
            fg_color=PALETTE["surface"],
            text_color=PALETTE["text_muted"],
            corner_radius=6,
            padx=8,
            pady=2
        )
        self.res_preflight_lbl.pack(side="right")

        self.chips_row = ctk.CTkFrame(self.results_card, fg_color="transparent")
        self.chips_row.pack(fill="x", padx=14, pady=(0, 10))

        res_btns = ctk.CTkFrame(self.results_card, fg_color="transparent")
        res_btns.pack(fill="x", padx=14, pady=(0, 12))

        self.open_dir_btn = ctk.CTkButton(
            res_btns,
            text=tr(self.lang, "btn_open_out"),
            image=self.icons["folder"],
            compound="left",
            height=34,
            corner_radius=8,
            fg_color="#059669",
            hover_color="#047857",
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self._open_output_folder
        )
        self.open_dir_btn.pack(side="left", fill="x", expand=True, padx=(0, 8))

        self.open_html_btn = ctk.CTkButton(
            res_btns,
            text=tr(self.lang, "btn_open_html"),
            image=self.icons["globe"],
            compound="left",
            height=34,
            corner_radius=8,
            fg_color=PALETTE["surface"],
            hover_color=PALETTE["surface_alt"],
            text_color=PALETTE["text"],
            border_width=1,
            border_color=PALETTE["border"],
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self._open_html_report
        )
        self.open_html_btn.pack(side="left", fill="x", expand=True)

    # ---------------------------------------------------------
    # INTERACTIONS, QUEUE MANAGEMENT & LOGIC
    # ---------------------------------------------------------
    def _toggle_theme(self):
        if self.current_theme == "Dark":
            ctk.set_appearance_mode("Light")
            self.current_theme = "Light"
            self.theme_btn.configure(text=tr(self.lang, "theme_dark"), image=self.icons["moon"])
        else:
            ctk.set_appearance_mode("Dark")
            self.current_theme = "Dark"
            self.theme_btn.configure(text=tr(self.lang, "theme_light"), image=self.icons["sun"])
        save_preferences({"theme": self.current_theme})

    def _set_language(self, choice: str):
        new_lang = choice.strip().lower()
        if new_lang == self.lang:
            return
        self.lang = new_lang
        save_preferences({"lang": self.lang})
        self._apply_language_texts()

    def _apply_language_texts(self):
        L = self.lang
        theme_key = "theme_light" if self.current_theme == "Dark" else "theme_dark"
        self.theme_btn.configure(text=tr(L, theme_key))
        self.footer.configure(text=tr(L, "footer_disclaimer"))

        # Left dropzone / preview / batch controls
        self.drop_title_lbl.configure(text=tr(L, "drop_title"))
        self.drop_sub_lbl.configure(text=tr(L, "drop_sub"))
        self.drop_browse_btn.configure(text=tr(L, "btn_choose_pdfs"))
        self.drop_folder_btn.configure(text=tr(L, "btn_choose_folder"))

        self.lock_title_lbl.configure(text=tr(L, "pdf_locked"))
        self.pwd_entry.configure(placeholder_text=tr(L, "pwd_placeholder"))
        self.unlock_btn.configure(text=tr(L, "btn_unlock"))
        self.add_more_btn.configure(text=tr(L, "btn_add_more_batch"))
        self.change_btn.configure(text=tr(L, "btn_change"))

        self.batch_add_btn.configure(text=tr(L, "btn_add"))
        self.batch_clear_btn.configure(text=tr(L, "btn_clear"))
        self.batch_footer_lbl.configure(text=tr(L, "batch_footer_tip"))

        # Right panel controls
        self.preset_title_lbl.configure(text=tr(L, "lbl_profile"))
        self.preset_seg.configure(values=[tr(L, k) for k in PRESET_KEYS])
        self.preset_seg.set(tr(L, self._current_preset_key))

        self.sw_images.configure(text=tr(L, "sw_images"))
        self.sw_vectors.configure(text=tr(L, "sw_vectors"))
        self.sw_fonts.configure(text=tr(L, "sw_fonts"))
        self.sw_profiles.configure(text=tr(L, "sw_profiles"))
        self.sw_attachments.configure(text=tr(L, "sw_attachments"))
        self.sw_gen_html.configure(text=tr(L, "sw_gen_html"))
        self.chk_auto_open_html.configure(text=tr(L, "chk_auto_open_html"))

        self.dest_entry.configure(placeholder_text=tr(L, "dest_placeholder"))
        self.dest_btn.configure(text=tr(L, "btn_change"))

        if not self.is_extracting:
            self._sync_view_to_queue()
        else:
            self.extract_btn.configure(text=tr(L, "btn_processing"))
            self._refresh_dest_hint()

        if self.results_card.winfo_ismapped() and self.last_result:
            if self.last_result.get("mode") == "batch":
                self._populate_batch_results_card(self.last_result)
            else:
                self._populate_single_results_card(self.last_result)

    def _apply_preset(self, choice: str):
        selected_key = "preset_full"
        for k in PRESET_KEYS:
            if choice == tr("en", k) or choice == tr("it", k):
                selected_key = k
                break
        self._current_preset_key = selected_key

        switches = [self.sw_images, self.sw_vectors, self.sw_fonts, self.sw_profiles, self.sw_attachments]
        if selected_key == "preset_full":
            for s in switches:
                s.select()
            self.sw_gen_html.select()
        elif selected_key == "preset_graphics":
            self.sw_images.select()
            self.sw_vectors.select()
            self.sw_fonts.deselect()
            self.sw_profiles.select()
            self.sw_attachments.deselect()
        elif selected_key == "preset_fonts":
            self.sw_images.deselect()
            self.sw_vectors.deselect()
            self.sw_fonts.select()
            self.sw_profiles.deselect()
            self.sw_attachments.deselect()
        elif selected_key == "preset_audit":
            for s in switches:
                s.deselect()
            self.sw_gen_html.select()

    def _on_manual_switch(self):
        pass

    def _on_drag_enter(self, event):
        self.left_card.configure(border_color=PALETTE["border_active"], border_width=2)
        self.drop_inner_box.configure(border_color=PALETTE["border_active"], border_width=2)

    def _on_drag_leave(self, event):
        self.left_card.configure(border_color=PALETTE["border"], border_width=1)
        self.drop_inner_box.configure(border_color=PALETTE["border"], border_width=1)

    def _on_drop_files(self, event):
        self.left_card.configure(border_color=PALETTE["border"], border_width=1)
        self.drop_inner_box.configure(border_color=PALETTE["border"], border_width=1)
        if self.is_extracting:
            return
        try:
            raw_items = self.tk.splitlist(event.data)
        except Exception:
            raw_items = [event.data]

        paths = [Path(str(x).strip().strip('"')) for x in raw_items if str(x).strip()]
        found_pdfs = collect_pdf_paths(paths)
        if not found_pdfs:
            messagebox.showwarning(
                tr(self.lang, "dlg_no_pdf_found_title"),
                tr(self.lang, "dlg_no_pdf_found_msg"),
            )
            return

        # If currently empty, replace; if already holding files, append cleanly
        replace = len(self.queued_pdfs) == 0
        self._add_pdfs(found_pdfs, replace=replace)

    def _browse_pdfs(self, replace: bool = True):
        if self.is_extracting:
            return
        files = filedialog.askopenfilenames(
            title=tr(self.lang, "dlg_browse_pdfs"),
            filetypes=[
                (tr(self.lang, "dlg_pdf_files"), "*.pdf"),
                (tr(self.lang, "dlg_all_files"), "*.*"),
            ]
        )
        if files:
            pdfs = collect_pdf_paths([Path(f) for f in files])
            if pdfs:
                self._add_pdfs(pdfs, replace=replace)

    def _browse_folder_pdfs(self, replace: bool = True):
        if self.is_extracting:
            return
        d = filedialog.askdirectory(title=tr(self.lang, "dlg_browse_folder"))
        if d:
            pdfs = collect_pdf_paths([Path(d)])
            if not pdfs:
                messagebox.showinfo(
                    tr(self.lang, "dlg_empty_dir_title"),
                    tr(self.lang, "dlg_empty_dir_msg"),
                )
                return
            self._add_pdfs(pdfs, replace=replace)

    def _add_pdfs(self, new_pdfs: list[Path], replace: bool = False):
        self.results_card.pack_forget()
        if replace:
            self.queued_pdfs = []
            self.pdf_password = None

        existing = set(self.queued_pdfs)
        for p in new_pdfs:
            if p not in existing:
                self.queued_pdfs.append(p)
                existing.add(p)

        self._sync_view_to_queue()

    def _remove_from_queue(self, pdf_path: Path):
        if self.is_extracting:
            return
        target = pdf_path.resolve()
        if target in self.queued_pdfs:
            self.queued_pdfs.remove(target)
        elif pdf_path in self.queued_pdfs:
            self.queued_pdfs.remove(pdf_path)
        self._sync_view_to_queue()

    def _clear_queue(self):
        if self.is_extracting:
            return
        self.queued_pdfs = []
        self.pdf_password = None
        self.results_card.pack_forget()
        self._sync_view_to_queue()

    def _sync_view_to_queue(self):
        count = len(self.queued_pdfs)
        if count == 0:
            self._show_left_mode("dropzone")
            self.extract_btn.configure(text=tr(self.lang, "btn_extract"))
            self.status_lbl.configure(text=tr(self.lang, "status_idle"), text_color=PALETTE["text_muted"])
            self._refresh_dest_hint()
        elif count == 1:
            self._render_single_preview(self.queued_pdfs[0], password=self.pdf_password)
            self.extract_btn.configure(text=tr(self.lang, "btn_extract"))
            self._refresh_dest_hint()
        else:
            self._render_batch_queue()
            self._show_left_mode("batch")
            self.extract_btn.configure(text=tr(self.lang, "btn_extract_batch", n=count))
            self.status_lbl.configure(text=tr(self.lang, "status_batch_ready", n=count), text_color=PALETTE["text_muted"])
            self._refresh_dest_hint()

    def _render_single_preview(self, p: Path, password: str | None = None):
        try:
            pre = inspect_pdf_preflight(p, password=password, thumb_max_size=(260, 275))
        except Exception as e:
            messagebox.showerror(
                tr(self.lang, "dlg_read_err_title"),
                tr(self.lang, "dlg_read_err_msg", err=e),
            )
            self.queued_pdfs = []
            self._show_left_mode("dropzone")
            return

        self._show_left_mode("preview")
        display_name = p.name if len(p.name) <= 38 else p.name[:35] + "..."
        self.pdf_name_lbl.configure(text=display_name)

        if pre.get("needs_password") and not pre.get("unlocked"):
            self.thumb_label.place_forget()
            self.lock_frame.place(relx=0.5, rely=0.5, anchor="center")
            self.pdf_chips_lbl.configure(text=f"{pre['file_size']}  •  {tr(self.lang, 'encrypted_file')}")
            self.pdf_gen_lbl.configure(text=tr(self.lang, "enter_pwd_hint"))
            self.status_lbl.configure(text=tr(self.lang, "status_wait_pwd"), text_color="#F59E0B")
        else:
            self.lock_frame.place_forget()
            self.thumb_label.place(relx=0.5, rely=0.5, anchor="center")

            thumb = pre.get("thumbnail")
            if thumb is not None:
                self.thumb_ctk_img = ctk.CTkImage(light_image=thumb, dark_image=thumb, size=thumb.size)
                self.thumb_label.configure(image=self.thumb_ctk_img, text="")
            else:
                self.thumb_label.configure(image=None, text=tr(self.lang, "preview_unavailable"))

            pages_txt = (
                tr(self.lang, "page_singular")
                if pre["total_pages"] == 1
                else tr(self.lang, "page_plural", n=pre["total_pages"])
            )
            self.pdf_chips_lbl.configure(text=f"{pre['paper_format']}  •  {pages_txt}  •  {pre['file_size']}")

            gen_app = pre.get("creator") or pre.get("producer") or tr(self.lang, "unknown_gen")
            if len(gen_app) > 42:
                gen_app = gen_app[:39] + "..."
            self.pdf_gen_lbl.configure(text=tr(self.lang, "app_prefix", app=gen_app))
            self.status_lbl.configure(text=tr(self.lang, "status_ready"), text_color=PALETTE["text_muted"])

    def _render_batch_queue(self):
        for child in self.batch_scroll.winfo_children():
            child.destroy()
        self.batch_row_widgets.clear()

        self.batch_count_lbl.configure(text=tr(self.lang, "batch_queue_title", n=len(self.queued_pdfs)))

        for p in self.queued_pdfs:
            row = ctk.CTkFrame(
                self.batch_scroll,
                corner_radius=8,
                fg_color=PALETTE["surface"],
                border_width=1,
                border_color=PALETTE["border"]
            )
            row.pack(fill="x", pady=(0, 6))

            status_badge = ctk.CTkLabel(
                row,
                text=tr(self.lang, "status_queued"),
                width=66,
                corner_radius=5,
                fg_color=PALETTE["badge_bg"],
                text_color=PALETTE["text_muted"],
                font=ctk.CTkFont(size=10, weight="bold")
            )
            status_badge.pack(side="left", padx=(8, 8), pady=8)

            info_col = ctk.CTkFrame(row, fg_color="transparent")
            info_col.pack(side="left", fill="x", expand=True, pady=6)

            short_name = p.name if len(p.name) <= 30 else p.name[:27] + "..."
            ctk.CTkLabel(
                info_col,
                text=short_name,
                font=ctk.CTkFont(size=12, weight="bold"),
                text_color=PALETTE["text"],
                anchor="w"
            ).pack(fill="x")

            sz_str = format_bytes(p.stat().st_size) if p.exists() else "-"
            sub_lbl = ctk.CTkLabel(
                info_col,
                text=sz_str,
                font=ctk.CTkFont(size=10),
                text_color=PALETTE["text_muted"],
                anchor="w"
            )
            sub_lbl.pack(fill="x")

            action_btn = ctk.CTkButton(
                row,
                text="×",
                width=26,
                height=26,
                corner_radius=6,
                fg_color="transparent",
                hover_color=PALETTE["badge_bg"],
                text_color=PALETTE["text_muted"],
                font=ctk.CTkFont(size=14, weight="bold"),
                command=lambda target=p: self._remove_from_queue(target)
            )
            action_btn.pack(side="right", padx=8)

            self.batch_row_widgets[p] = {
                "row": row,
                "badge": status_badge,
                "sub_lbl": sub_lbl,
                "action_btn": action_btn,
            }

    def _refresh_dest_hint(self):
        base_str = self.dest_entry.get().strip()
        base_dir = Path(base_str) if base_str else (Path.cwd() / "output")
        count = len(self.queued_pdfs)
        if count == 0:
            self.dest_hint_lbl.configure(text=tr(self.lang, "hint_empty"))
        elif count == 1:
            next_folder = resolve_unique_output_dir(base_dir, self.queued_pdfs[0].stem, lang=self.lang)
            self.dest_hint_lbl.configure(text=tr(self.lang, "hint_single", name=next_folder.name))
        else:
            self.dest_hint_lbl.configure(text=tr(self.lang, "hint_batch", n=count))

    def _unlock_pdf(self):
        if len(self.queued_pdfs) != 1:
            return
        pwd = self.pwd_entry.get()
        self.pdf_password = pwd
        self._render_single_preview(self.queued_pdfs[0], password=pwd)
        if self.lock_frame.winfo_ismapped():
            messagebox.showwarning(
                tr(self.lang, "dlg_wrong_pwd_title"),
                tr(self.lang, "dlg_wrong_pwd_msg"),
            )

    def _browse_output_dir(self):
        d = filedialog.askdirectory(title=tr(self.lang, "dlg_browse_dest"))
        if d:
            self.dest_entry.delete(0, "end")
            self.dest_entry.insert(0, str(Path(d)))
            self._refresh_dest_hint()

    # ---------------------------------------------------------
    # EXTRACTION EXECUTION (Single & Batch)
    # ---------------------------------------------------------
    def _start_extraction(self):
        if not self.queued_pdfs:
            messagebox.showwarning(
                tr(self.lang, "dlg_no_pdf_title"),
                tr(self.lang, "dlg_no_pdf_msg"),
            )
            return
        if self.is_extracting:
            return

        self.is_extracting = True
        self.results_card.pack_forget()
        self.extract_btn.configure(state="disabled", text=tr(self.lang, "btn_processing"))
        self._set_batch_controls_enabled(False)
        self.progress_bar.pack(fill="x", pady=(8, 0))
        self.progress_bar.set(0.03)

        thread = threading.Thread(target=self._run_worker, daemon=True)
        thread.start()

    def _set_batch_controls_enabled(self, enabled: bool):
        state = "normal" if enabled else "disabled"
        try:
            self.batch_add_btn.configure(state=state)
            self.batch_clear_btn.configure(state=state)
            self.add_more_btn.configure(state=state)
            self.change_btn.configure(state=state)
        except Exception:
            pass

    def _run_worker(self):
        dest = self.dest_entry.get().strip()
        out_path = Path(dest) if dest else None
        files_snapshot = list(self.queued_pdfs)
        run_lang = self.lang

        def _on_progress(msg: str, pct: float):
            self.after(0, lambda m=msg, p=pct: self._update_progress(m, p))

        def _on_batch_item(idx: int, total: int, pdf_p: Path, status: str, payload):
            self.after(0, lambda: self._update_batch_item_ui(pdf_p, status, payload))

        try:
            if len(files_snapshot) == 1:
                res = extract_pdf_assets(
                    pdf_path=files_snapshot[0],
                    output_dir=out_path,
                    extract_imgs=bool(self.sw_images.get()),
                    extract_fnts=bool(self.sw_fonts.get()),
                    extract_profs=bool(self.sw_profiles.get()),
                    extract_attaches=bool(self.sw_attachments.get()),
                    extract_vecs=bool(self.sw_vectors.get()),
                    generate_html=bool(self.sw_gen_html.get()),
                    password=self.pdf_password,
                    progress_callback=_on_progress,
                    lang=run_lang,
                )
                self.last_result = res
                self.after(0, self._on_single_success, res)
            else:
                res = extract_batch_pdfs(
                    pdf_paths=files_snapshot,
                    output_dir=out_path,
                    extract_imgs=bool(self.sw_images.get()),
                    extract_fnts=bool(self.sw_fonts.get()),
                    extract_profs=bool(self.sw_profiles.get()),
                    extract_attaches=bool(self.sw_attachments.get()),
                    extract_vecs=bool(self.sw_vectors.get()),
                    generate_html=bool(self.sw_gen_html.get()),
                    password=self.pdf_password,
                    progress_callback=_on_progress,
                    item_callback=_on_batch_item,
                    lang=run_lang,
                )
                self.last_result = res
                self.after(0, self._on_batch_success, res)
        except Exception as e:
            self.after(0, self._on_error, str(e))

    def _update_progress(self, msg: str, pct: float):
        self.progress_bar.set(pct)
        self.status_lbl.configure(text=msg, text_color=PALETTE["text_muted"])

    def _update_batch_item_ui(self, pdf_path: Path, status: str, payload):
        w = self.batch_row_widgets.get(pdf_path)
        if not w:
            return
        badge = w["badge"]
        sub_lbl = w["sub_lbl"]
        btn = w["action_btn"]

        if status == "running":
            badge.configure(text=tr(self.lang, "status_running"), fg_color="#0284C7", text_color="#FFFFFF")
            btn.configure(state="disabled")
        elif status == "success":
            badge.configure(text=tr(self.lang, "status_ok"), fg_color="#059669", text_color="#FFFFFF")
            out_folder = Path(payload["output_directory"])
            sub_lbl.configure(text=f"→ {out_folder.name}")
            btn.configure(
                text=tr(self.lang, "btn_open"),
                width=46,
                state="normal",
                fg_color=PALETTE["surface_alt"],
                text_color=PALETTE["accent"],
                font=ctk.CTkFont(size=11, weight="bold"),
                command=lambda p=out_folder: self._open_path(p)
            )
        elif status == "error":
            badge.configure(text=tr(self.lang, "status_error"), fg_color="#DC2626", text_color="#FFFFFF")
            err_short = str(payload)[:36] + ("..." if len(str(payload)) > 36 else "")
            sub_lbl.configure(text=err_short, text_color="#EF4444")
            btn.configure(
                text="!",
                width=28,
                state="normal",
                text_color="#EF4444",
                command=lambda err=str(payload), name=pdf_path.name: messagebox.showerror(
                    f"{tr(self.lang, 'status_error')}: {name}", err
                )
            )

    def _populate_single_results_card(self, res: dict):
        out_dir = Path(res["output_directory"])
        self.status_lbl.configure(text=tr(self.lang, "status_saved_in", name=out_dir.name), text_color="#10B981")

        self.results_card.configure(fg_color=PALETTE["success_bg"], border_color=PALETTE["success_border"])
        self.res_title_lbl.configure(text=tr(self.lang, "res_done"), text_color=PALETTE["success_text"])

        audit = res.get("preflight_audit")
        if audit:
            pf_st = audit.get("status", "pass")
            pf_color = {"pass": "#10B981", "warn": "#F59E0B", "fail": "#EF4444"}.get(pf_st, PALETTE["text_muted"])
            self.res_preflight_lbl.configure(text=format_preflight_badge_label(audit, self.lang), text_color=pf_color)
        else:
            self.res_preflight_lbl.configure(text="")

        for widget in self.chips_row.winfo_children():
            widget.destroy()

        s = res["summary"]
        chips_spec = [
            (tr(self.lang, "chip_images", n=s["total_images"]), out_dir / "images"),
            (tr(self.lang, "chip_vectors", n=s.get("vector_pages_count", 0)), out_dir / "vectors"),
            (tr(self.lang, "chip_fonts", e=s["embedded_fonts"], t=s["total_fonts"]), out_dir / "fonts"),
            (tr(self.lang, "chip_profiles", n=s["color_profiles_count"]), out_dir / "profiles"),
            (tr(self.lang, "chip_attachments", n=s["attachments_count"]), out_dir / "attachments"),
        ]
        self._render_result_chips(chips_spec)

        self.open_dir_btn.configure(text=tr(self.lang, "btn_open_out"))
        self.open_html_btn.pack(side="left", fill="x", expand=True)
        self.open_html_btn.configure(
            text=tr(self.lang, "btn_open_html"),
            state="normal" if res.get("html_report") else "disabled",
        )

    def _on_single_success(self, res: dict):
        self.is_extracting = False
        self.progress_bar.pack_forget()
        self._set_batch_controls_enabled(True)
        self.extract_btn.configure(state="normal", text=tr(self.lang, "btn_extract"))
        self._refresh_dest_hint()

        self._populate_single_results_card(res)
        self.results_card.pack(fill="x", padx=18, pady=(4, 14))

        if self.chk_auto_open_html.get() and res.get("html_report"):
            self._open_html_report()

    def _populate_batch_results_card(self, res: dict):
        succ = res["succeeded"]
        tot = res["total_files"]
        failed = res["failed"]
        base_dir = Path(res["output_directory"])

        if failed == 0:
            self.status_lbl.configure(
                text=tr(self.lang, "status_batch_done", s=succ, t=tot, dir=base_dir.name),
                text_color="#10B981",
            )
            self.results_card.configure(fg_color=PALETTE["success_bg"], border_color=PALETTE["success_border"])
            self.res_title_lbl.configure(
                text=tr(self.lang, "res_batch_done", s=succ, t=tot),
                text_color=PALETTE["success_text"],
            )
        else:
            self.status_lbl.configure(
                text=tr(self.lang, "status_batch_partial", s=succ, f=failed),
                text_color="#F59E0B",
            )
            self.results_card.configure(fg_color=PALETTE["warn_bg"], border_color=PALETTE["warn_border"])
            self.res_title_lbl.configure(
                text=tr(self.lang, "res_batch_partial", s=succ, t=tot, f=failed),
                text_color="#F59E0B",
            )

        for widget in self.chips_row.winfo_children():
            widget.destroy()

        agg = res["aggregate_summary"]
        pf_pass = agg.get("preflight_pass", 0)
        pf_warn = agg.get("preflight_warn", 0)
        pf_fail = agg.get("preflight_fail", 0)
        pf_parts = []
        if pf_pass:
            pf_parts.append(f"{pf_pass} {tr(self.lang, 'pf_badge_pass')}")
        if pf_warn:
            pf_parts.append(f"{pf_warn} {tr(self.lang, 'pf_badge_warn')}")
        if pf_fail:
            pf_parts.append(f"{pf_fail} {tr(self.lang, 'pf_badge_fail')}")
        pf_batch_col = "#EF4444" if pf_fail else ("#F59E0B" if pf_warn else "#10B981")
        self.res_preflight_lbl.configure(text=f"Preflight: {' · '.join(pf_parts)}" if pf_parts else "", text_color=pf_batch_col)

        chips_spec = [
            (tr(self.lang, "chip_images", n=agg["total_images"]), base_dir),
            (tr(self.lang, "chip_vectors", n=agg["vector_pages_count"]), base_dir),
            (tr(self.lang, "chip_fonts", e=agg["embedded_fonts"], t=agg["total_fonts"]), base_dir),
            (tr(self.lang, "chip_profiles", n=agg["color_profiles_count"]), base_dir),
            (tr(self.lang, "chip_attachments", n=agg["attachments_count"]), base_dir),
        ]
        self._render_result_chips(chips_spec)

        # In batch mode, show both the parent folder button and the unified Batch HTML Index button
        self.open_dir_btn.configure(text=tr(self.lang, "btn_open_batch"))
        self.open_html_btn.pack(side="left", fill="x", expand=True)
        self.open_html_btn.configure(
            text=tr(self.lang, "btn_open_batch_html"),
            state="normal" if res.get("html_report") else "disabled",
        )

    def _on_batch_success(self, res: dict):
        self.is_extracting = False
        self.progress_bar.pack_forget()
        self._set_batch_controls_enabled(True)
        self.extract_btn.configure(state="normal", text=tr(self.lang, "btn_extract_batch", n=len(self.queued_pdfs)))

        self._populate_batch_results_card(res)
        self.results_card.pack(fill="x", padx=18, pady=(4, 14))

        if self.chk_auto_open_html.get() and res.get("html_report"):
            self._open_html_report()

    def _render_result_chips(self, chips_spec: list[tuple[str, Path]]):
        for label_txt, target_sub in chips_spec:
            btn = ctk.CTkButton(
                self.chips_row,
                text=label_txt,
                height=26,
                width=82,
                corner_radius=6,
                fg_color=PALETTE["surface"],
                hover_color=PALETTE["surface_alt"],
                text_color=PALETTE["text"],
                border_width=1,
                border_color=PALETTE["border"],
                font=ctk.CTkFont(size=11, weight="bold"),
                command=lambda p=target_sub: self._open_path(p)
            )
            btn.pack(side="left", padx=(0, 6))

    def _on_error(self, err_msg: str):
        self.is_extracting = False
        self.progress_bar.pack_forget()
        self._set_batch_controls_enabled(True)
        cnt = len(self.queued_pdfs)
        btn_txt = tr(self.lang, "btn_extract_batch", n=cnt) if cnt > 1 else tr(self.lang, "btn_extract")
        self.extract_btn.configure(state="normal", text=btn_txt)
        self.status_lbl.configure(text=f"{tr(self.lang, 'status_error')}: {err_msg}", text_color="#EF4444")
        messagebox.showerror(tr(self.lang, "dlg_err_title"), tr(self.lang, "dlg_err_msg", err=err_msg))

    def _open_path(self, target: Path):
        if target.exists():
            if sys.platform == "win32":
                os.startfile(target)
            else:
                webbrowser.open(target.as_uri())
        else:
            self._open_output_folder()

    def _open_output_folder(self):
        if self.last_result and self.last_result.get("output_directory"):
            self._open_path(Path(self.last_result["output_directory"]))

    def _open_html_report(self):
        if self.last_result and self.last_result.get("html_report"):
            html_p = Path(self.last_result["html_report"])
            if html_p.exists():
                webbrowser.open(html_p.as_uri())


def launch_gui(initial_pdfs: list[Path] | Path | None = None):
    """Starts the Desktop GUI application loop."""
    if isinstance(initial_pdfs, Path):
        pdfs = [initial_pdfs]
    else:
        pdfs = list(initial_pdfs) if initial_pdfs else None
    app = PDFExtractorApp(initial_pdfs=pdfs)
    app.mainloop()


if __name__ == "__main__":
    arg_pdfs = [Path(a) for a in sys.argv[1:]] if len(sys.argv) > 1 else None
    launch_gui(initial_pdfs=arg_pdfs)

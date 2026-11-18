# Changelog

All notable changes to **PDF Asset Extractor** will be documented in this file.

## [2.3.0] - 2026-11-18

### Added
- **Internationalization (i18n — English & Italian)**:
  - Automatic OS UI language detection on first launch (English globally by default, Italian on Italian Windows/OS locales) with persistent user preferences (`~/.pdf_asset_extractor_prefs.json` for language and theme).
  - **Live GUI Language Switcher (`EN` / `IT`)** in the header bar that switches every label, preset (`Full`/`Graphics`/`Fonts`/`Audit Only` <-> `Completo`/`Solo Grafica`/`Solo Font`/`Solo Analisi`), switch, progress message, dialog, and result chip instantly without restarting.
  - **Localized HTML Dashboards & Folders**: Both `report.html` and `batch_report.html` are now generated in the active language, and output subfolders adapt cleanly (`<name>_extracted` in English, `<name>_estratto` in Italian).
  - **CLI `--lang` Option**: Added `--lang [en|it]` flag alongside localized CLI help, progress spinners, and Rich summary tables.
- **Automated Tests**: Added `test_i18n_translations_and_locale_folders` verifying `EN`/`IT` key parity, localized subfolder suffixes, and localized HTML reports.

## [2.2.0] - 2026-11-17

### Added
- **Unified Batch HTML Index (`batch_report.html`)**: Running a multi-PDF batch with HTML reporting enabled now generates a self-contained `batch_report.html` summary dashboard in the base output directory.
  - Displays aggregate KPI cards across the entire batch (processed PDFs, total pages, images, vector pages, embedded fonts, ICC profiles, attachments).
  - Includes a live filename search/filter bar and per-document table with `OK` / `Error` status, direct relative links (`Apri Report PDF →`) to each individual `<name>_estratto/report.html`, and folder links.
  - Anti-overwrite incremental naming (`batch_report_2.html`, `batch_report_3.html`, ...) when running multiple batches into the same folder.
- **Batch HTML Auto-Open & GUI Button**:
  - Updated the *"Apri automaticamente il Report HTML nel browser al termine"* checkbox to work seamlessly for both single-PDF and Batch extractions.
  - Added the **`Apri Report Batch HTML`** button directly in the Batch completion panel.
- **CLI Batch `--open` Support**: Passing `--open` with multiple PDFs or a directory now prints the `batch_report.html` path and opens it automatically in the default browser.
- **Automated Tests**: Added `test_batch_html_report_and_non_overwrite` verifying batch index HTML generation, relative links, and incremental naming.

## [2.1.0] - 2026-11-17

### Added
- **Modern Split-View Desktop GUI (`PDF-Extractor.exe`)**: Zero-console `--windowed` Windows executable with custom icon, Dark & Light theme toggle, 1-click presets (`Completo`, `Solo Grafica`, `Solo Font`, `Solo Analisi`), and deterministic step-by-step progress.
- **Instant Pre-Flight Preview**: Drag & drop a PDF (or drop files directly onto the `.exe` icon) to view a rendered Page 1 thumbnail, detected paper format, page count, authoring software, and inline password prompt for encrypted PDFs.
- **Multi-PDF & Folder Batch Mode**: Adaptive Batch Queue with per-file status, error isolation, and dedicated `<name>_estratto` (or `_2`, `_3`) anti-overwrite subfolders.
- **Comprehensive PDF Extractors**:
  - **Images**: Native stream extraction, `/SMask` 32-bit RGBA transparency reconstruction, SHA-256 deduplication, and effective print DPI calculation.
  - **Vectors**: Clean raster-stripped `.svg` and pure-vector Adobe Illustrator `.ai` export per page with HEX color swatches.
  - **Fonts**: Embedded `.ttf`/`.otf`/`.cff`/`.woff` extraction, subset detection (`ABCDEF+...`), `fonttools` SFNT `name` table repair, glyph counts, and Unicode coverage sampling.
  - **Color & Pre-Press**: Embedded `.icc` profile extraction + header parsing, spot ink detection (`/Separation` / `/DeviceN`), and `MediaBox`/`CropBox`/`BleedBox`/`TrimBox`/`ArtBox` dimensions in pt, mm, and inches.
  - **Metadata & Attachments**: `Creator`/`Producer`, PDF/A, PDF/X, PDF/UA compliance detection, raw `xmp_metadata.xml`, security permissions, and `/EmbeddedFiles` + annotation attachments.
- **Open-Source Showcase & Samples**: Added copyright-free `samples/` PDFs (using Apache 2.0 Roboto fonts) and README screenshots.

"""
Command Line Interface (CLI) for pdf-images-extract using Click and Rich.
Supports single PDF extraction, multi-PDF / directory batch processing, and Desktop GUI mode.
"""

import sys
import webbrowser
from pathlib import Path
import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

from .core import (
    extract_pdf_assets,
    extract_batch_pdfs,
    inspect_pdf_print_readiness,
    inspect_batch_print_readiness,
    collect_pdf_paths,
)
from .utils.i18n import (
    get_default_language,
    SUPPORTED_LANGS,
    tr,
    format_preflight_check,
    format_preflight_badge_label,
)

if sys.platform == "win32":
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

console = Console(legacy_windows=False)


@click.command(context_settings=dict(help_option_names=["-h", "--help"]))
@click.argument("pdf_paths", nargs=-1, type=click.Path(exists=True, path_type=Path))
@click.option(
    "-o", "--output", "output_dir",
    type=click.Path(file_okay=False, path_type=Path),
    default=None,
    help="Base destination folder for '<pdf_name>_extracted' (or '_estratto' in IT) (default: ./output)"
)
@click.option("--gui", is_flag=True, help="Launch the Desktop GUI")
@click.option("--no-images", is_flag=True, help="Disable image extraction")
@click.option("--no-fonts", is_flag=True, help="Disable font extraction")
@click.option("--no-vectors", is_flag=True, help="Disable vector graphics extraction (.svg and .ai)")
@click.option("--no-profiles", is_flag=True, help="Disable ICC color profile extraction")
@click.option("--no-attachments", is_flag=True, help="Disable embedded attachment extraction")
@click.option("--no-html", is_flag=True, help="Do not generate interactive HTML report")
@click.option("--open", "open_report", is_flag=True, help="Automatically open the HTML report in browser when done")
@click.option("--preflight-only", is_flag=True, help="Run in-memory Print Readiness Audit without writing any output files")
@click.option("-p", "--password", default=None, help="Password for encrypted PDFs")
@click.option(
    "--lang",
    type=click.Choice(list(SUPPORTED_LANGS), case_sensitive=False),
    default=None,
    help="Output language for reports and folder names ('en' or 'it'). Auto-detected by default."
)
@click.option("-q", "--quiet", is_flag=True, help="Quiet mode (no console output except errors)")
def main(
    pdf_paths: tuple[Path, ...],
    output_dir: Path | None,
    gui: bool,
    no_images: bool,
    no_fonts: bool,
    no_vectors: bool,
    no_profiles: bool,
    no_attachments: bool,
    no_html: bool,
    open_report: bool,
    preflight_only: bool,
    password: str | None,
    lang: str | None,
    quiet: bool,
):
    """
    Extract images, vector graphics (.SVG/.AI), fonts (full & subsets),
    ICC color profiles, spot colors, page geometry, and metadata from one or more PDFs.

    Run without arguments (or with --gui) to launch the Desktop GUI.
    """
    if gui or not pdf_paths:
        from .gui import launch_gui
        launch_gui()
        return

    resolved_lang = lang.lower() if lang else get_default_language()
    is_it = resolved_lang == "it"

    resolved_pdfs = collect_pdf_paths(list(pdf_paths))
    if not resolved_pdfs:
        msg = "Nessun file .pdf trovato nei percorsi specificati." if is_it else "No .pdf files found in the specified paths."
        console.print(f"[bold red]{'Errore' if is_it else 'Error'}:[/bold red] {msg}")
        sys.exit(1)

    # Single PDF mode
    if len(resolved_pdfs) == 1:
        pdf_path = resolved_pdfs[0]
        if not quiet:
            proc_lbl = "File in elaborazione" if is_it else "Processing file"
            console.print(
                Panel.fit(
                    "[bold cyan]PDF Asset & Metadata Deep Extractor[/bold cyan] [dim]by Linus74 · 2026[/dim]\n"
                    f"[dim]{proc_lbl}: [white]{pdf_path.name}[/white][/dim]",
                    border_style="cyan"
                )
            )

        try:
            if preflight_only:
                result = inspect_pdf_print_readiness(
                    pdf_path=pdf_path,
                    password=password,
                    lang=resolved_lang,
                )
                if not quiet:
                    _print_preflight_audit_table(result.get("preflight_audit"), resolved_lang)
                if result.get("preflight_audit", {}).get("status") == "fail":
                    sys.exit(2)
                return

            if not quiet:
                with Progress(
                    SpinnerColumn(),
                    TextColumn("[progress.description]{task.description}"),
                    console=console,
                    transient=True
                ) as progress:
                    spin_lbl = "Estrazione in corso da PDF..." if is_it else "Extracting PDF assets..."
                    progress.add_task(f"[yellow]{spin_lbl}", total=None)
                    result = extract_pdf_assets(
                        pdf_path=pdf_path,
                        output_dir=output_dir,
                        extract_imgs=not no_images,
                        extract_fnts=not no_fonts,
                        extract_profs=not no_profiles,
                        extract_attaches=not no_attachments,
                        extract_vecs=not no_vectors,
                        generate_html=not no_html,
                        password=password,
                        lang=resolved_lang,
                    )
            else:
                result = extract_pdf_assets(
                    pdf_path=pdf_path,
                    output_dir=output_dir,
                    extract_imgs=not no_images,
                    extract_fnts=not no_fonts,
                    extract_profs=not no_profiles,
                    extract_attaches=not no_attachments,
                    extract_vecs=not no_vectors,
                    generate_html=not no_html,
                    password=password,
                    lang=resolved_lang,
                )
        except Exception as e:
            err_lbl = "Errore durante l'elaborazione del PDF" if is_it else "Error processing PDF"
            console.print(f"[bold red]{err_lbl}:[/bold red] {e}")
            sys.exit(1)

        if not quiet:
            _print_single_summary(result, lang=resolved_lang)

        if open_report and result.get("html_report"):
            webbrowser.open(Path(result["html_report"]).as_uri())
        return

    # Batch Multi-PDF mode
    if preflight_only:
        if not quiet:
            b_title = "Verifica Stampa Batch" if is_it else "Batch Print Check"
            console.print(
                Panel.fit(
                    f"[bold cyan]PDF Asset & Metadata Deep Extractor — {b_title}[/bold cyan] [dim]by Linus74 · 2026[/dim]\n"
                    f"[dim]{len(resolved_pdfs)} PDF[/dim]",
                    border_style="cyan"
                )
            )
        batch_pf = inspect_batch_print_readiness(
            pdf_paths=resolved_pdfs,
            password=password,
            lang=resolved_lang,
        )
        if not quiet:
            _print_batch_summary(batch_pf, lang=resolved_lang)
        if batch_pf["failed"] > 0 and batch_pf["succeeded"] == 0:
            sys.exit(1)
        return

    if not quiet:
        mode_lbl = "Modalità Batch" if is_it else "Batch Mode"
        queue_lbl = "File in coda" if is_it else "Queued files"
        console.print(
            Panel.fit(
                f"[bold cyan]PDF Asset & Metadata Deep Extractor — {mode_lbl}[/bold cyan] [dim]by Linus74 · 2026[/dim]\n"
                f"[dim]{queue_lbl}: [white]{len(resolved_pdfs)} PDF[/white][/dim]",
                border_style="cyan"
            )
        )

    if not quiet:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
            transient=True
        ) as progress:
            b_lbl = f"Elaborazione batch di {len(resolved_pdfs)} PDF..." if is_it else f"Batch processing {len(resolved_pdfs)} PDFs..."
            task = progress.add_task(f"[yellow]{b_lbl}", total=None)
            batch_res = extract_batch_pdfs(
                pdf_paths=resolved_pdfs,
                output_dir=output_dir,
                extract_imgs=not no_images,
                extract_fnts=not no_fonts,
                extract_profs=not no_profiles,
                extract_attaches=not no_attachments,
                extract_vecs=not no_vectors,
                generate_html=not no_html,
                password=password,
                progress_callback=lambda msg, pct: progress.update(task, description=f"[yellow]{msg}"),
                lang=resolved_lang,
            )
    else:
        batch_res = extract_batch_pdfs(
            pdf_paths=resolved_pdfs,
            output_dir=output_dir,
            extract_imgs=not no_images,
            extract_fnts=not no_fonts,
            extract_profs=not no_profiles,
            extract_attaches=not no_attachments,
            extract_vecs=not no_vectors,
            generate_html=not no_html,
            password=password,
            lang=resolved_lang,
        )

    if not quiet:
        _print_batch_summary(batch_res, lang=resolved_lang)

    if open_report and batch_res.get("html_report"):
        webbrowser.open(Path(batch_res["html_report"]).as_uri())

    if batch_res["failed"] > 0 and batch_res["succeeded"] == 0:
        sys.exit(1)


def _print_preflight_audit_table(audit: dict | None, lang: str = "en"):
    if not audit:
        return
    pf_tbl = Table(
        title=f"{tr(lang, 'pf_cli_title')} — {format_preflight_badge_label(audit, lang)}",
        show_header=True,
        header_style="bold cyan",
    )
    pf_tbl.add_column(tr(lang, "pf_th_check"), style="white", width=32)
    pf_tbl.add_column(tr(lang, "pf_th_status"), style="bold", width=10)
    pf_tbl.add_column(tr(lang, "pf_th_summary"), style="dim")
    thresholds = audit.get("thresholds") or {}
    for chk in audit.get("checks", []):
        st = chk.get("status", "pass")
        color_tag = {"pass": "green", "warn": "yellow", "fail": "red"}.get(st, "dim")
        badge_key = {"pass": "pf_badge_pass", "warn": "pf_badge_warn", "fail": "pf_badge_fail"}.get(st, "pf_badge_skip")
        pf_tbl.add_row(
            tr(lang, f"pf_check_{chk.get('id', '')}"),
            f"[{color_tag}]{tr(lang, badge_key)}[/{color_tag}]",
            format_preflight_check(chk, thresholds, lang),
        )
    console.print(pf_tbl)


def _print_single_summary(result: dict, lang: str = "en"):
    is_it = lang == "it"
    summary = result["summary"]
    meta = result["metadata"]
    color = result["color_management"]
    pages = result["pages"]

    tbl = Table(
        title="Riepilogo Estrazione Risorse" if is_it else "Asset Extraction Summary",
        show_header=True,
        header_style="bold magenta",
    )
    tbl.add_column("Proprietà" if is_it else "Property", style="dim", width=28)
    tbl.add_column("Valore Rilevato" if is_it else "Detected Value", style="white")

    tbl.add_row("Nome File" if is_it else "File Name", summary["file_name"])
    tbl.add_row("Dimensione File" if is_it else "File Size", summary["file_size"])
    tbl.add_row("Pagine Totali" if is_it else "Total Pages", str(summary["total_pages"]))

    formats_seen = set()
    for p in pages:
        mb = p.get("mediabox")
        if mb and mb.get("matched_size"):
            formats_seen.add(f"{mb['matched_size']} ({mb.get('orientation', '')})")
    nd = "N/D" if is_it else "N/A"
    unspec = "[dim]Non specificato[/dim]" if is_it else "[dim]Not specified[/dim]"
    tbl.add_row("Dimensioni Pagine" if is_it else "Page Dimensions", ", ".join(formats_seen) if formats_seen else nd)

    tbl.add_row("Versione PDF" if is_it else "PDF Version", meta.get("pdf_version", nd))
    tbl.add_row("Software Creazione (Creator)" if is_it else "Authoring Software (Creator)", meta.get("creator") or unspec)
    tbl.add_row("Motore Generazione (Producer)" if is_it else "PDF Engine (Producer)", meta.get("producer") or unspec)

    stds = meta.get("standards", {})
    std_list = [v for k, v in stds.items() if v]
    if std_list:
        tbl.add_row("Standard di Conformità" if is_it else "Compliance Standards", ", ".join(std_list))

    if is_it:
        tbl.add_row("Immagini Estratte", f"[bold green]{summary['total_images']}[/bold green] uniche")
        tbl.add_row("Grafica Vettoriale", f"[bold green]{summary.get('vector_pages_count', 0)}[/bold green] pagine ({summary.get('vector_paths_count', 0)} tracciati, .svg e .ai)")
        tbl.add_row("Font Recuperati", f"[bold green]{summary['total_fonts']}[/bold green] (Incorporati: {summary['embedded_fonts']}, Sottinsiemi: {summary['subset_fonts']})")
        tbl.add_row("Profili ICC", f"{summary['color_profiles_count']} estratti")
        if color.get("spot_colors"):
            tbl.add_row("Colori Speciali (Spot)", ", ".join(color["spot_colors"]))
        tbl.add_row("Allegati Incorporati", f"{summary['attachments_count']} file")
    else:
        tbl.add_row("Extracted Images", f"[bold green]{summary['total_images']}[/bold green] unique")
        tbl.add_row("Vector Graphics", f"[bold green]{summary.get('vector_pages_count', 0)}[/bold green] pages ({summary.get('vector_paths_count', 0)} paths, .svg and .ai)")
        tbl.add_row("Recovered Fonts", f"[bold green]{summary['total_fonts']}[/bold green] (Embedded: {summary['embedded_fonts']}, Subsets: {summary['subset_fonts']})")
        tbl.add_row("ICC Profiles", f"{summary['color_profiles_count']} extracted")
        if color.get("spot_colors"):
            tbl.add_row("Spot Colors", ", ".join(color["spot_colors"]))
        tbl.add_row("Embedded Attachments", f"{summary['attachments_count']} files")

    console.print(tbl)
    _print_preflight_audit_table(result.get("preflight_audit"), lang)

    if is_it:
        out_panel = (
            f"[bold green]✓ Estrazione completata con successo![/bold green]\n\n"
            f"📁 [bold]Cartella output:[/bold] [cyan]{result['output_directory']}[/cyan]\n"
            f"📊 [bold]Report JSON:[/bold] [cyan]{result.get('json_report')}[/cyan]\n"
        )
        if result.get("html_report"):
            out_panel += f"🌐 [bold]Report HTML Interattivo:[/bold] [cyan]{result.get('html_report')}[/cyan]\n"
        legal_note = "Nota: Assicurati di disporre dei diritti di utilizzo per le immagini, i font e le risorse estratte conformemente alle licenze e alle norme sul diritto d'autore."
    else:
        out_panel = (
            f"[bold green]✓ Extraction complete![/bold green]\n\n"
            f"📁 [bold]Output folder:[/bold] [cyan]{result['output_directory']}[/cyan]\n"
            f"📊 [bold]JSON Report:[/bold] [cyan]{result.get('json_report')}[/cyan]\n"
        )
        if result.get("html_report"):
            out_panel += f"🌐 [bold]Interactive HTML Report:[/bold] [cyan]{result.get('html_report')}[/cyan]\n"
        legal_note = "Note: Ensure you have the rights and licenses (EULA) before reusing extracted images, fonts, or assets."

    console.print(Panel(out_panel, border_style="green"))
    console.print(f"[dim]⚖️  [italic]{legal_note}[/italic][/dim]\n")


def _print_batch_summary(batch_res: dict, lang: str = "en"):
    is_it = lang == "it"
    tbl = Table(
        title="Riepilogo Batch Multi-PDF" if is_it else "Multi-PDF Batch Summary",
        show_header=True,
        header_style="bold magenta",
    )
    tbl.add_column("File PDF" if is_it else "PDF File", style="white")
    tbl.add_column("Stato" if is_it else "Status", style="bold")
    tbl.add_column(tr(lang, "batch_th_preflight"), style="bold")
    tbl.add_column("Img / Vet / Font" if is_it else "Img / Vec / Font", style="cyan")
    tbl.add_column("Sottocartella Creata" if is_it else "Created Subfolder", style="dim")

    for item in batch_res["items"]:
        if item["status"] == "success":
            s = item["summary"]
            pf_st = item.get("preflight_status", s.get("preflight_status", "pass"))
            pf_col = {"pass": "green", "warn": "yellow", "fail": "red"}.get(pf_st, "dim")
            pf_key = {"pass": "pf_badge_pass", "warn": "pf_badge_warn", "fail": "pf_badge_fail"}.get(pf_st, "pf_badge_skip")
            counts = f"{s['total_images']} / {s.get('vector_pages_count', 0)} / {s['embedded_fonts']}"
            folder_name = Path(item["output_directory"]).name if item.get("output_directory") else "-"
            tbl.add_row(item["file_name"], "[green]OK[/green]", f"[{pf_col}]{tr(lang, pf_key)}[/{pf_col}]", counts, folder_name)
        else:
            err_lbl = "Errore" if is_it else "Error"
            tbl.add_row(item["file_name"], f"[red]{err_lbl}[/red]", "-", "-", item.get("error") or "")

    console.print(tbl)
    if not batch_res.get("output_directory"):
        agg = batch_res["aggregate_summary"]
        console.print(
            f"[bold cyan]{tr(lang, 'pf_cli_title')}:[/bold cyan] "
            f"[green]{agg.get('preflight_pass', 0)} {tr(lang, 'pf_badge_pass')}[/green] · "
            f"[yellow]{agg.get('preflight_warn', 0)} {tr(lang, 'pf_badge_warn')}[/yellow] · "
            f"[red]{agg.get('preflight_fail', 0)} {tr(lang, 'pf_badge_fail')}[/red]\n"
        )
        return
    if is_it:
        batch_panel = (
            f"[bold green]✓ Batch completato: {batch_res['succeeded']}/{batch_res['total_files']} PDF elaborati.[/bold green]\n"
            f"📁 [bold]Cartella base output:[/bold] [cyan]{batch_res['output_directory']}[/cyan]"
        )
        if batch_res.get("html_report"):
            batch_panel += f"\n🌐 [bold]Report Batch HTML:[/bold] [cyan]{batch_res['html_report']}[/cyan]"
    else:
        batch_panel = (
            f"[bold green]✓ Batch complete: {batch_res['succeeded']}/{batch_res['total_files']} PDFs processed.[/bold green]\n"
            f"📁 [bold]Base output folder:[/bold] [cyan]{batch_res['output_directory']}[/cyan]"
        )
        if batch_res.get("html_report"):
            batch_panel += f"\n🌐 [bold]Batch HTML Report:[/bold] [cyan]{batch_res['html_report']}[/cyan]"
    console.print(Panel(batch_panel, border_style="green"))


if __name__ == "__main__":
    main()

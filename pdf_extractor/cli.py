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

from .core import extract_pdf_assets, extract_batch_pdfs, collect_pdf_paths

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
    help="Cartella base di destinazione in cui creare '<nome_pdf>_estratto' (predefinito: ./output)"
)
@click.option("--gui", is_flag=True, help="Avvia l'interfaccia grafica desktop")
@click.option("--no-images", is_flag=True, help="Disabilita estrazione delle immagini")
@click.option("--no-fonts", is_flag=True, help="Disabilita estrazione dei font")
@click.option("--no-vectors", is_flag=True, help="Disabilita estrazione grafica vettoriale (.svg e .ai)")
@click.option("--no-profiles", is_flag=True, help="Disabilita estrazione dei profili colore ICC")
@click.option("--no-attachments", is_flag=True, help="Disabilita estrazione degli allegati")
@click.option("--no-html", is_flag=True, help="Non generare il report interattivo HTML")
@click.option("--open", "open_report", is_flag=True, help="Apri automaticamente il report HTML nel browser al termine")
@click.option("-p", "--password", default=None, help="Password per PDF protetti o crittografati")
@click.option("-q", "--quiet", is_flag=True, help="Modalità silenziosa (nessun output console tranne errori)")
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
    password: str | None,
    quiet: bool,
):
    """
    Estrae immagini, grafica vettoriale (.SVG/.AI), font (completi e sottinsiemi),
    profili colore ICC, colori speciali, dimensioni di pagina e metadati da uno o più PDF.

    Se eseguito senza argomenti (o con --gui), avvia l'interfaccia Desktop.
    """
    if gui or not pdf_paths:
        from .gui import launch_gui
        launch_gui()
        return

    resolved_pdfs = collect_pdf_paths(list(pdf_paths))
    if not resolved_pdfs:
        console.print("[bold red]Errore:[/bold red] Nessun file .pdf trovato nei percorsi specificati.")
        sys.exit(1)

    # Single PDF mode
    if len(resolved_pdfs) == 1:
        pdf_path = resolved_pdfs[0]
        if not quiet:
            console.print(
                Panel.fit(
                    "[bold cyan]PDF Asset & Metadata Deep Extractor[/bold cyan] [dim]by Linus74 · 2026[/dim]\n"
                    f"[dim]File in elaborazione: [white]{pdf_path.name}[/white][/dim]",
                    border_style="cyan"
                )
            )

        try:
            if not quiet:
                with Progress(
                    SpinnerColumn(),
                    TextColumn("[progress.description]{task.description}"),
                    console=console,
                    transient=True
                ) as progress:
                    progress.add_task("[yellow]Estrazione in corso da PDF...", total=None)
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
                )
        except Exception as e:
            console.print(f"[bold red]Errore durante l'elaborazione del PDF:[/bold red] {e}")
            sys.exit(1)

        if not quiet:
            _print_single_summary(result)

        if open_report and result.get("html_report"):
            webbrowser.open(Path(result["html_report"]).as_uri())
        return

    # Batch Multi-PDF mode
    if not quiet:
        console.print(
            Panel.fit(
                "[bold cyan]PDF Asset & Metadata Deep Extractor — Modalità Batch[/bold cyan] [dim]by Linus74 · 2026[/dim]\n"
                f"[dim]File in coda: [white]{len(resolved_pdfs)} PDF[/white][/dim]",
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
            task = progress.add_task(f"[yellow]Elaborazione batch di {len(resolved_pdfs)} PDF...", total=None)
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
        )

    if not quiet:
        _print_batch_summary(batch_res)

    if batch_res["failed"] > 0 and batch_res["succeeded"] == 0:
        sys.exit(1)


def _print_single_summary(result: dict):
    summary = result["summary"]
    meta = result["metadata"]
    color = result["color_management"]
    pages = result["pages"]

    tbl = Table(title="Riepilogo Estrazione Risorse", show_header=True, header_style="bold magenta")
    tbl.add_column("Proprietà", style="dim", width=28)
    tbl.add_column("Valore Rilevato", style="white")

    tbl.add_row("Nome File", summary["file_name"])
    tbl.add_row("Dimensione File", summary["file_size"])
    tbl.add_row("Pagine Totali", str(summary["total_pages"]))

    formats_seen = set()
    for p in pages:
        mb = p.get("mediabox")
        if mb and mb.get("matched_size"):
            formats_seen.add(f"{mb['matched_size']} ({mb.get('orientation', '')})")
    tbl.add_row("Dimensioni Pagine", ", ".join(formats_seen) if formats_seen else "N/D")

    tbl.add_row("Versione PDF", meta.get("pdf_version", "N/D"))
    tbl.add_row("Software Creazione (Creator)", meta.get("creator") or "[dim]Non specificato[/dim]")
    tbl.add_row("Motore Generazione (Producer)", meta.get("producer") or "[dim]Non specificato[/dim]")

    stds = meta.get("standards", {})
    std_list = [v for k, v in stds.items() if v]
    if std_list:
        tbl.add_row("Standard di Conformità", ", ".join(std_list))

    tbl.add_row("Immagini Estratte", f"[bold green]{summary['total_images']}[/bold green] uniche")
    tbl.add_row("Grafica Vettoriale", f"[bold green]{summary.get('vector_pages_count', 0)}[/bold green] pagine ({summary.get('vector_paths_count', 0)} tracciati, .svg e .ai)")
    tbl.add_row("Font Recuperati", f"[bold green]{summary['total_fonts']}[/bold green] (Incorporati: {summary['embedded_fonts']}, Sottinsiemi: {summary['subset_fonts']})")
    tbl.add_row("Profili ICC", f"{summary['color_profiles_count']} estratti")
    if color.get("spot_colors"):
        tbl.add_row("Colori Speciali (Spot)", ", ".join(color["spot_colors"]))
    tbl.add_row("Allegati Incorporati", f"{summary['attachments_count']} file")

    console.print(tbl)

    out_panel = (
        f"[bold green]✓ Estrazione completata con successo![/bold green]\n\n"
        f"📁 [bold]Cartella output:[/bold] [cyan]{result['output_directory']}[/cyan]\n"
        f"📊 [bold]Report JSON:[/bold] [cyan]{result.get('json_report')}[/cyan]\n"
    )
    if result.get("html_report"):
        out_panel += f"🌐 [bold]Report HTML Interattivo:[/bold] [cyan]{result.get('html_report')}[/cyan]\n"

    console.print(Panel(out_panel, border_style="green"))
    console.print(
        "[dim]⚖️  [italic]Nota: Assicurati di disporre dei diritti di utilizzo per le immagini, i font e le risorse estratte "
        "conformemente alle licenze e alle norme sul diritto d'autore.[/italic][/dim]\n"
    )


def _print_batch_summary(batch_res: dict):
    tbl = Table(title="Riepilogo Batch Multi-PDF", show_header=True, header_style="bold magenta")
    tbl.add_column("File PDF", style="white")
    tbl.add_column("Stato", style="bold")
    tbl.add_column("Img / Vet / Font", style="cyan")
    tbl.add_column("Sottocartella Creata", style="dim")

    for item in batch_res["items"]:
        if item["status"] == "success":
            s = item["summary"]
            counts = f"{s['total_images']} / {s.get('vector_pages_count', 0)} / {s['embedded_fonts']}"
            folder_name = Path(item["output_directory"]).name
            tbl.add_row(item["file_name"], "[green]OK[/green]", counts, folder_name)
        else:
            tbl.add_row(item["file_name"], "[red]Errore[/red]", "-", item.get("error") or "")

    console.print(tbl)
    console.print(
        Panel(
            f"[bold green]✓ Batch completato: {batch_res['succeeded']}/{batch_res['total_files']} PDF elaborati.[/bold green]\n"
            f"📁 [bold]Cartella base output:[/bold] [cyan]{batch_res['output_directory']}[/cyan]",
            border_style="green"
        )
    )


if __name__ == "__main__":
    main()

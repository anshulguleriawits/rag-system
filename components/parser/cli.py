from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from components.parser.config import config
from components.parser.logging_setup import get_logger, setup_logging
from components.parser.pipeline import ParsingPipeline
from components.parser.routing.router import EXTENSION_STRATEGY

app = typer.Typer(
    name="parsecli",
    help="RAG Parser CLI — parse, inspect, and debug documents",
    no_args_is_help=True,
)
console = Console()
logger = get_logger(__name__)


def _setup(verbose: bool = False) -> ParsingPipeline:
    if verbose:
        config.log_level = "DEBUG"
    setup_logging()
    return ParsingPipeline()


def _output_docs(
    docs: list,
    fmt: str,
    output_path: Optional[Path] = None,
) -> None:
    if fmt == "json":
        data = [
            {"content": d.content, "meta": d.meta} for d in docs
        ]
        text = json.dumps(data, indent=2, default=str)
    elif fmt == "table":
        table = Table(title="Parsed Documents")
        table.add_column("Document ID")
        table.add_column("Parser")
        table.add_column("Element Type")
        table.add_column("Content Preview")
        for d in docs:
            table.add_row(
                d.meta.get("document_id", "")[:12],
                d.meta.get("parser_used", ""),
                d.meta.get("element_type", ""),
                d.content[:80].replace("\n", " "),
            )
        console.print(table)
        return
    else:
        text = ""
        for d in docs:
            text += f"--- {d.meta.get('document_id', '?')} ---\n"
            text += f"Parser: {d.meta.get('parser_used', '?')}\n"
            text += f"Element: {d.meta.get('element_type', '?')}\n"
            text += d.content + "\n\n"

    if output_path:
        output_path.write_text(text)
        console.print(f"Output written to {output_path}")
    else:
        console.print(text)


@app.command()
def parse(
    file: Path = typer.Argument(
        ..., help="Path to the file to parse", exists=True
    ),
    strategy: Optional[str] = typer.Option(
        None, "--strategy", "-s", help="Force a specific parser strategy"
    ),
    output: str = typer.Option(
        "markdown", "--output", "-o", help="Output format: json|markdown|table"
    ),
    out: Optional[Path] = typer.Option(
        None, "--out", help="Write output to file instead of stdout"
    ),
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Enable DEBUG logging"
    ),
) -> None:
    """Parse a single file, auto-detecting strategy."""
    pipeline = _setup(verbose)
    result = pipeline.run(
        sources=[file],
        force_parser=strategy,
    )
    docs = result.get("documents", [])
    errors = result.get("errors", [])

    if errors:
        for f, e in errors:
            console.print(f"[red]Error: {f} -> {e}[/red]")
        raise typer.Exit(code=1)

    if not docs:
        console.print("[yellow]No documents produced[/yellow]")
        raise typer.Exit(code=2)

    _output_docs(docs, output, out)


@app.command()
def parse_dir(
    directory: Path = typer.Argument(
        ...,
        help="Directory to parse",
        exists=True,
        file_okay=False,
    ),
    recursive: bool = typer.Option(
        False, "--recursive", "-r", help="Recurse into subdirectories"
    ),
    out: Optional[Path] = typer.Option(
        None,
        "--out",
        help="Output directory for parsed files (each saved as .json)",
    ),
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Enable DEBUG logging"
    ),
) -> None:
    """Parse an entire directory, auto-routing each file by its type."""
    pipeline = _setup(verbose)

    pattern = "**/*" if recursive else "*"
    files = sorted(
        p
        for p in directory.glob(pattern)
        if p.is_file() and not p.name.startswith(".")
    )

    if not files:
        console.print("[yellow]No files found[/yellow]")
        raise typer.Exit(code=2)

    with console.status(f"Parsing {len(files)} files...") as status:
        all_docs = []
        total_errors = 0
        for f in files:
            status.update(f"Parsing {f.name}...")
            result = pipeline.run(sources=[f])
            docs = result.get("documents", [])
            errors = result.get("errors", [])
            all_docs.extend(docs)
            total_errors += len(errors)

    console.print(
        f"Parsed {len(all_docs)} documents from {len(files)} files "
        f"({total_errors} errors)"
    )

    if out:
        out.mkdir(parents=True, exist_ok=True)
        for d in all_docs:
            doc_id = d.meta.get("document_id", "unknown")
            (out / f"{doc_id}.json").write_text(
                json.dumps(
                    {"content": d.content, "meta": d.meta},
                    indent=2,
                    default=str,
                )
            )


@app.command()
def list_strategies(
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Show provider config status"
    ),
) -> None:
    """List available parser strategies and their providers."""
    table = Table(title="Available Parser Strategies")
    table.add_column("Strategy")
    table.add_column("Extensions")
    table.add_column("Default For")
    table.add_column("Type")
    table.add_column("Status" if verbose else "")

    from components.parser.routing.router import EXTENSION_STRATEGY

    all_strategies = {
        "simple": {"extensions": [], "type": "Native Haystack converters"},
        "pypdf": {"extensions": [], "type": "Native PyPDFToDocument"},
        "docling": {"extensions": [], "type": "docling-haystack integration"},
        "ocr_local": {"extensions": [], "type": "Local Tesseract"},
        "ocr_cloud": {"extensions": [], "type": "Cloud API (Mistral/LlamaParse)"},
        "code": {"extensions": [], "type": "Custom tree-sitter"},
        "tabular": {"extensions": [], "type": "Hybrid (native + pandas)"},
        "structured": {"extensions": [], "type": "Hybrid (native + custom)"},
    }

    for ext, sname in EXTENSION_STRATEGY.items():
        if sname in all_strategies:
            all_strategies[sname]["extensions"].append(ext)

    for sname, info in all_strategies.items():
        status = ""
        if verbose and sname == "ocr_cloud":
            if config.mistral_api_key:
                status += "[green]Mistral OK [/green]"
            else:
                status += "[yellow]Mistral: no key [/yellow]"
            if config.llamaparse_api_key:
                status += "[green]LlamaParse OK [/green]"
            else:
                status += "[yellow]LlamaParse: no key [/yellow]"

        exts = ", ".join(info["extensions"]) if info["extensions"] else "—"
        table.add_row(
            sname,
            exts,
            EXTENSION_STRATEGY.get(
                f".{info['extensions'][0]}", ""
            ) if info.get("extensions") else "",
            str(info["type"]),
            status,
        )

    console.print(table)


@app.command()
def inspect(
    path: Path = typer.Argument(
        ..., help="File or directory to inspect", exists=True
    ),
    dry_run: bool = typer.Option(
        True,
        "--dry-run",
        help="Show which strategy WOULD be selected (default: True)",
    ),
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Show detailed info"
    ),
) -> None:
    """Show which strategy would be selected without parsing."""
    from components.parser.routing.router import ParserRouter

    _setup(verbose)
    router = ParserRouter()

    if path.is_file():
        files = [path]
    else:
        files = sorted(
            p
            for p in path.glob("*")
            if p.is_file() and not p.name.startswith(".")
        )

    table = Table(title="Strategy Selection (dry run)")
    table.add_column("File")
    table.add_column("Extension")
    table.add_column("Selected Strategy")
    table.add_column("Reason")

    for f in files:
        strategy = router.select_strategy(f)
        ext = f.suffix.lower()
        if ext == ".pdf" and strategy in ("ocr_cloud", "ocr_local"):
            reason = "scanned PDF detection"
        elif ext in EXTENSION_STRATEGY:
            reason = "extension-based routing"
        else:
            reason = "fallback to simple"
        table.add_row(f.name, ext, strategy, reason)

    console.print(table)


@app.command()
def debug(
    document_id: str = typer.Argument(
        ..., help="Document ID to retrieve debug report for"
    ),
) -> None:
    """Open the debug report for a previously parsed document."""
    from components.parser.debug.artifact_manager import DebugArtifactManager
    import webbrowser

    manager = DebugArtifactManager()
    report_path = manager.get_debug_report(document_id)

    if not report_path:
        console.print(
            f"[red]No debug report found for document ID: "
            f"{document_id}[/red]"
        )
        raise typer.Exit(code=1)

    report_url = f"file://{Path(report_path).resolve()}"
    console.print(f"Opening debug report: {report_url}")
    webbrowser.open(report_url)


def main() -> None:
    app()


if __name__ == "__main__":
    main()

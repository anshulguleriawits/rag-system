# RAG Parser Module

Production-grade document parsing module for Retrieval-Augmented Generation (RAG) systems, built on **Haystack 2.x**. This is the first stage of the ingestion pipeline (`Source → Parser → Chunker → Embedder → Indexer`).

**Do not** chunk, embed, or store — this module produces Haystack `Document` objects that feed naturally into Haystack's splitters, embedders, and writers.

## Architecture

Every parsing strategy is a Haystack `@component` with a consistent `run(sources, meta) -> {"documents": list[Document]}` interface. A routing layer selects the best strategy per file, with automatic scanned-PDF detection, explicit override, and fallback chains.

```
File → ParserRouter
         ├─ scanned-PDF detection (pypdf heuristic)
         ├─ extension-based auto-routing
         ├─ explicit caller override
         └─ fallback chain on failure
              → strategy.run()
                   → Document[]
```

## Strategy / Extension Mapping

| Extension | Default Strategy | Override Examples |
|---|---|---|
| `.pdf` | `auto` → docling (digital) or ocr_cloud (scanned) | `--strategy docling`, `--strategy ocr_cloud --provider mistral` |
| `.docx` / `.pptx` | `docling` | `--strategy simple` |
| `.txt` / `.md` | `simple` | — |
| `.html` | `simple` | — |
| `.csv` / `.tsv` | `tabular` | — |
| `.xlsx` / `.xls` / `.parquet` | `tabular` | — |
| `.json` / `.yaml` / `.xml` | `structured` | — |
| `.py` / `.js` / `.ts` / `.go` / etc. | `code` | — |
| `.png` / `.jpg` / `.tiff` / etc. | `ocr_local` | `--strategy ocr_cloud --provider mistral` |

## Available Strategies

| Strategy | Haystack Building Block | Use Case |
|---|---|---|
| `simple` | `TextFileToDocument`, `MarkdownToDocument`, `HTMLToDocument` | Plain text, markdown, HTML |
| `pypdf` | `PyPDFToDocument` | Digital PDFs, no complex layout |
| `docling` | `DoclingConverter` (docling-haystack) | PDFs/DOCX with tables, layout, hierarchy |
| `ocr_local` | Custom (pytesseract + pdf2image) | Scanned PDFs, images — local only |
| `ocr_cloud` | `MistralOCRDocumentConverter` (mistral-haystack) + custom LlamaParse wrapper | High-quality OCR via cloud APIs |
| `code` | Custom (tree-sitter) | Source code: preserves function/class boundaries |
| `tabular` | `CSVToDocument` (native) + pandas | CSV, Excel, Parquet — schema + sample rows |
| `structured` | Custom (json/yaml/xml flatten with key paths) | JSON, YAML, XML — preserves key paths |

## Output Contract (Document Meta Schema)

Every parsed `Document` has a populated `meta` dict with these keys:

| Key | Type | Description |
|---|---|---|
| `document_id` | `str` | Unique identifier (UUID hex) |
| `source_path` | `str` | Original file path |
| `mime_type` | `str` | Detected MIME type |
| `parser_used` | `str` | Strategy name, e.g. `docling`, `ocr_cloud:mistral` |
| `parser_version` | `str` | Component version |
| `page_number` | `int \| None` | Page number (paginated formats only) |
| `section_path` | `list[str]` | Heading hierarchy, e.g. `["1. Intro", "1.2 Background"]` |
| `element_type` | `str` | `heading`, `paragraph`, `table`, `figure`, `list_item`, `code_block`, `structured`, `other` |
| `confidence` | `float \| None` | OCR confidence (0-1), `None` for digital-native |
| `parsing_duration_ms` | `int` | Time spent parsing |
| `warnings` | `list[str]` | Non-fatal issues |

## Configuration

Copy `.env.example` to `.env` and configure:

```bash
PARSER_DEFAULT_STRATEGY=auto
PARSER_OCR_CLOUD_PROVIDER=mistral    # mistral | llamaparse
MISTRAL_API_KEY=                     # Required for Mistral OCR
LLAMAPARSE_API_KEY=                  # Required for LlamaParse
PARSER_FALLBACK_CHAIN=docling,ocr_cloud,ocr_local
PARSER_SCANNED_TEXT_THRESHOLD=0.05
LOG_LEVEL=INFO
```

All config is validated at startup via `pydantic-settings`. Missing required API keys produce clear warnings.

## CLI Usage

```bash
# Parse a single file (auto-detects strategy)
python -m rag_parser.cli parse ./contract.pdf

# Force a strategy
python -m rag_parser.cli parse ./scan.pdf --strategy ocr_cloud
python -m rag_parser.cli parse ./notes.txt --strategy simple

# Batch parse a directory
python -m rag_parser.cli parse-dir ./corpus/ --recursive --out ./parsed/

# List available strategies and provider status
python -m rag_parser.cli list-strategies

# Dry-run inspection (no parsing)
python -m rag_parser.cli inspect ./scan.pdf

# Debug report for a previously parsed document
python -m rag_parser.cli debug <document_id>

# Output formats: json, markdown, table
python -m rag_parser.cli parse ./data.csv --output json
```

Exit codes: `0` = success, `1` = errors, `2` = no documents produced.

## API Usage

```bash
# Start the API server
python -m rag_parser.api

# Parse a file
curl -X POST -F "file=@contract.pdf" http://localhost:8000/parse

# Async parse (returns job_id immediately)
curl -X POST -F "file=@large_scan.pdf" http://localhost:8000/parse/async

# Poll for result
curl http://localhost:8000/parse/<job_id>

# Debug report
curl http://localhost:8000/parse/<document_id>/debug

# Health check
curl http://localhost:8000/health
```

## Python Library Usage

```python
from rag_parser.pipeline import ParsingPipeline

pipeline = ParsingPipeline()
result = pipeline.run(sources=["contract.pdf"])

for doc in result["documents"]:
    print(f"[{doc.meta['parser_used']}] {doc.content[:100]}")
```

## Debug Artifacts

For OCR-based parses, debug artifacts are generated in `./debug_output/<document_id>/`:
- `pages/page_0000.png` — Rasterized page image
- `overlays/page_0000_overlay.png` — OCR text overlaid on page
- `report.html` — Side-by-side comparison with per-page confidence

View via: `python -m rag_parser.cli debug <document_id>` or `GET /parse/<document_id>/debug`.

## How to Add a New Parser Provider

1. Create a new component in `rag_parser/components/` with `@component` and a `run()` method.
2. Register it in `ParserRouter._create_strategy()` in `rag_parser/routing/router.py`.
3. Add its config block to `ParserConfig` in `rag_parser/config.py`.
4. Add its extension mapping to `EXTENSION_STRATEGY` and the test.

No changes to the routing or fallback logic required.

## Native vs. Custom Components

| Component | Status | Notes |
|---|---|---|
| `TextFileToDocument` | Native | Haystack built-in |
| `MarkdownToDocument` | Native | Haystack built-in |
| `HTMLToDocument` | Native | Haystack built-in |
| `PyPDFToDocument` | Native | Haystack built-in |
| `DoclingConverter` | Native integration | `docling-haystack` package |
| `MistralOCRDocumentConverter` | Native integration | `mistral-haystack` package |
| LlamaParse | Custom | Async-job-based submit/poll/fetch |
| Tesseract OCR | Custom | `pytesseract` + `pdf2image` |
| Code parser | Custom | `tree-sitter` for Python; fallback line-split |
| Tabular (xlsx/parquet) | Custom | `pandas` with schema + sample rows |
| Structured (yaml/xml) | Custom | Key-path flattening |

## Deferred / Future

- **Azure Document Intelligence**: Native `AzureOCRDocumentConverter` exists in `azure-ai-documentintelligence` integration.
- **PaddleOCR**: Native `PaddleOCRVLDocumentConverter` exists — noted as an alternative for local OCR.
- **MultiFileConverter fast-path**: Haystack's `MultiFileConverter` is noted as an alternative for simple document families.
- **Vision-LLM as OCR**: Can be added as another provider behind the same component interface.
- **Confidence-based auto-escalation**: Re-parse low-confidence pages with a stronger provider.
- **Caching by content hash**: Skip re-parsing unchanged files.
- **Language detection**: Pass detected language to OCR engines.

## Running Tests

```bash
pip install pytest
python -m pytest tests/ -v
```

## Project Structure

```
rag_parser/
├── __init__.py
├── config.py              # pydantic-settings, .env loading
├── exceptions.py          # Custom exception hierarchy
├── logging_setup.py       # structlog configuration
├── meta_schema.py         # Documented meta dict schema + builder
├── pipeline.py            # ParsingPipeline orchestrator
├── cli.py                 # Typer CLI
├── api.py                 # FastAPI service
├── components/
│   ├── base.py            # BaseParserComponent
│   ├── simple.py          # Text/MD/HTML converters
│   ├── pypdf_strategy.py  # PyPDFToDocument
│   ├── docling_strategy.py# DoclingConverter
│   ├── code.py            # Tree-sitter code parser
│   ├── tabular.py         # CSV/Excel/Parquet parser
│   ├── structured.py      # JSON/YAML/XML parser
│   ├── ocr_local.py       # Tesseract OCR
│   └── ocr_cloud.py       # Mistral + LlamaParse
├── routing/
│   ├── router.py          # ParserRouter (Haystack @component)
│   └── scanned_detector.py# Scanned PDF detection heuristic
└── debug/
    └── artifact_manager.py# Debug image/overlay/report generation
```

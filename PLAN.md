# Plan: `rag-common` — Shared Foundation Package

## 1. Workspace tooling: uv workspaces

**Choice: uv workspaces** (uv 0.11.26 available, already used for venv).

Why:
- Already in the toolchain (no new dependency).
- Works seamlessly with `pip install -e` via `uv pip install`.
- `[tool.uv.workspace]` members = packages/* is zero-friction for adding siblings later.
- The root pyproject.toml keeps its existing `[project]` (rag-parser), and we add `[tool.uv.workspace]` alongside it — uv supports hybrid project+workspace roots.

Alternative considered: Poetry path deps — rejected because it would introduce Poetry alongside uv, and the existing project already uses uv.

## 2. Final folder structure

```
rag-platform/                             ← current repo root
├── pyproject.toml                        ← root: [project] rag-parser + [tool.uv.workspace]
├── packages/
│   └── rag-common/
│       ├── pyproject.toml
│       ├── README.md
│       ├── MIGRATION.md
│       ├── src/
│       │   └── rag_common/
│       │       ├── __init__.py
│       │       ├── logging.py
│       │       ├── config.py
│       │       ├── exceptions.py
│       │       ├── schemas.py
│       │       ├── observability.py
│       │       └── testing.py
│       └── tests/
│           ├── __init__.py
│           ├── test_logging.py
│           ├── test_config.py
│           ├── test_exceptions.py
│           ├── test_schemas.py
│           ├── test_observability.py
│           └── test_testing.py
├── rag_parser/                           ← untouched (migration deferred)
├── tests/                                ← existing parser tests, untouched
└── README.md                             ← existing, untouched
```

`rag-common` lives under `packages/` with a `src/` layout for clean import isolation.

## 3. Shared `meta` key conventions

Based on the existing parser's `DocumentMeta` (rag_parser/meta_schema.py) plus reserved keys for future modules.

### Active keys (populated by parser, consumed by downstream)
| Key | Type | Required | Source |
|---|---|---|---|
| `document_id` | str | yes | Generated at parse time (uuid hex) |
| `source_path` | str | yes | Original file path or filename |
| `mime_type` | str | yes | Detected MIME type |
| `parser_used` | str | yes | Strategy name (e.g. `docling`, `simple:.txt`) |
| `parser_version` | str | yes | Module version string |
| `page_number` | int \| None | no | Page within multi-page doc |
| `section_path` | list[str] | no | Hierarchical section path (e.g. `["2.1", "Introduction"]`) |
| `element_type` | str | yes | Document element type (paragraph, table, code, etc.) |
| `confidence` | float \| None | no | Parsing confidence 0-1 |
| `parsing_duration_ms` | int | yes | Wall-clock time to parse |
| `warnings` | list[str] | yes | Non-fatal issues during parsing |

### Reserved keys (documented, not yet populated — for chunker/embedder/retriever)
| Key | Type | Planned Module |
|---|---|---|
| `chunk_id` | str | rag-chunker |
| `parent_chunk_id` | str \| None | rag-chunker |
| `chunk_index` | int | rag-chunker |
| `embedding_model` | str | rag-embedder |
| `embedding_model_version` | str | rag-embedder |
| `embedding_vector` | list[float] | rag-embedder |
| `retrieval_score` | float | rag-retriever |
| `retrieval_method` | str | rag-retriever |

## 4. Exception hierarchy

```
Exception
└── RagBaseError
    ├── message: str
    ├── context: dict
    └── retryable: bool
    │
    ├── ConfigurationError          (retryable=False) — bad/missing config
    ├── RetryableError              (retryable=True)  — transient failures
    ├── TerminalError               (retryable=False) — all retries exhausted
    └── ValidationError             (retryable=False) — bad input data
```

Module-specific exceptions (existing: `ParserNotFoundError`, `ProviderAPIError`, etc.) will inherit from these base classes during the retrofit pass, not now.

## 5. Observability scope

**This pass**: implement `@timed_operation("stage_name")` decorator that:
- Logs start/end with duration using the shared logger
- Captures and re-raises exceptions (logs them too)
- Structured so swap to real OTel spans later requires changing one function body

**Defer**: OpenTelemetry tracer setup, metrics export, span propagation. Reason: no current consumers, adding OTel now adds a dependency and config surface with zero users. The decorator interface is designed so that when OTel arrives, we replace the body without changing call sites.

## 6. Open questions (resolved)

- **Q**: env prefix convention?  
  **A**: Each module uses its own prefix. `rag-parser` → `PARSER_*`, `rag-chunker` → `CHUNKER_*`, `rag-common` → `COMMON_*`. Documented in `BaseServiceSettings` pattern.
- **Q**: `.env` precedence?  
  **A**: Module-level `.env` overrides root `.env`. Rationale: module-specific settings should take priority for isolation. Documented in `BaseServiceSettings`.
- **Q**: Haystack `Secret` integration?  
  **A**: `BaseServiceSettings` will detect fields with `Secret` type annotation and automatically apply Haystack's `Secret.from_env_var()` pattern. Non-secret fields use direct pydantic-settings env var binding.
- **Q**: src layout vs flat?  
  **A**: `src/` layout for `rag-common`. Reason: prevents import confusion when installed alongside sibling packages.

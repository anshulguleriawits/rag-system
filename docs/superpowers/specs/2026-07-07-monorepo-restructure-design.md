# Monorepo Restructure: `common/` + `components/`

## Goal
Restructure the flat RAG project into a maintainable monorepo layout where shared infrastructure lives in `common/` and each RAG module (parser, chunker, embedder, retriever) lives under `components/`. The existing `rag-parser` module is the first component moved into this structure.

## Non-goals
- Changing any runtime behavior or public API of `rag-parser`
- Adding new features to `rag-parser`
- Making `common/` a pip-installable package (no `pyproject.toml` under `common/`)

## Folder structure

```
rag-platform/
├── common/                          # Shared utilities (regular Python package)
│   ├── __init__.py                  # Re-exports from submodules
│   ├── logging.py                   # get_logger, log_context, setup_logging
│   ├── config.py                    # BaseServiceSettings, fail_fast_validation
│   ├── exceptions.py                # RagBaseError + shared subclasses
│   ├── schemas.py                   # Document re-export, META_KEY_SPEC, validate_meta
│   ├── observability.py             # @timed_operation decorator
│   └── testing.py                   # Shared fixtures + mock_http_provider
├── components/
│   ├── parser/                      # (moved from rag_parser/)
│   │   ├── __init__.py
│   │   ├── api.py / cli.py / pipeline.py / config.py / exceptions.py / logging_setup.py
│   │   ├── components/              # simple.py, pypdf_strategy.py, docling_strategy.py, ocr_cloud.py, ocr_local.py, code.py, tabular.py, structured.py, base.py
│   │   ├── routing/                 # router.py, scanned_detector.py
│   │   └── debug/                   # artifact_manager.py
│   ├── chunker/                     # future
│   ├── embedder/                    # future
│   └── retriever/                   # future
├── tests/
│   ├── conftest.py                  # Shared pytest fixtures
│   ├── common/                      # Tests for common/ modules
│   │   ├── test_logging.py
│   │   ├── test_config.py
│   │   ├── test_exceptions.py
│   │   ├── test_schemas.py
│   │   ├── test_observability.py
│   │   └── test_testing.py
│   └── parser/                      # Tests for components/parser/
│       ├── conftest.py
│       ├── test_components.py
│       ├── test_routing.py
│       └── test_pipeline.py
├── pyproject.toml                   # package discovery -> components/parser
├── README.md
└── PLAN.md
```

## Import conventions

- `common/` modules use absolute imports from `common.*` (e.g. `from common.logging import get_logger`)
- `components/parser/` modules use `common.*` for shared utilities and `components.parser.*` for local imports
- All imports are absolute (no relative `..` imports) for clarity
- `logging_setup.py` kept as thin wrapper for backward compat during transition

## Migration steps

1. Create `common/` — copy files from `packages/rag-common/src/rag_common/`, strip `rag-common` branding
2. Create `components/parser/` — move `rag_parser/` into `components/parser/`
3. Update all internal imports in `components/parser/` to use new paths
4. Move tests from `packages/rag-common/tests/` and `tests/` to `tests/common/` and `tests/parser/`
5. Update `pyproject.toml` — package include paths, dependencies, workspace config
6. Remove old `rag_parser/` and `packages/` directories
7. Run full test suite, fix issues

## Backward compat

- `components/parser/logging_setup.py` stays as a re-export from `common.logging` so CLI/API entry points don't break
- All other internal imports are updated to new absolute paths

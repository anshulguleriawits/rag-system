# Plan — Monorepo Restructure

## Done

- `rag-common` folded into `common/` (no `pyproject.toml`, regular Python package)
- `rag_parser/` moved to `components/parser/` with updated imports
- Tests consolidated under root `tests/`
- `pyproject.toml` discovers `common*` and `components/parser*`

## Next

- Chunker module → `components/chunker/`
- Embedder module → `components/embedder/`
- Retriever module → `components/retriever/`

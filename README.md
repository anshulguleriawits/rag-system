# RAG Platform

Monorepo for a production-grade RAG ingestion pipeline built on **Haystack 2.x**.

```
Source → Parser → Chunker → Embedder → Indexer
```

## Structure

```
rag-platform/
├── common/                  # Shared infrastructure (logging, config, schemas)
├── components/
│   └── parser/              # Document parsing module
├── tests/
│   ├── common/              # Tests for common/
│   └── parser/              # Tests for components/parser/
├── pyproject.toml
└── README.md
```

## Quick Start

```bash
pip install -e .
python -m components.parser.cli parse ./document.pdf
```

See `components/parser/README.md` for detailed parser usage.

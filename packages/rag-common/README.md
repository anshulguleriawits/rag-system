# rag-common

Shared foundation package for the RAG platform. Cross-cutting infrastructure shared by all RAG modules (`rag-parser`, `rag-chunker`, `rag-embedder`, `rag-retriever`, `rag-orchestrator`).

**Contains no RAG-specific logic.** No parsing, chunking, embedding, or retrieval.

## What belongs here

| Module | Contents |
|---|---|
| `rag_common.logging` | Shared structured logger (`get_logger`, `log_context`), JSON/console format, contextvar-based correlation IDs |
| `rag_common.config` | `BaseServiceSettings` (extends `pydantic_settings`), `fail_fast_validation()` helper, credential-safe handling |
| `rag_common.exceptions` | `RagBaseError` hierarchy: `ConfigurationError`, `RetryableError`, `TerminalError`, `ValidationError` |
| `rag_common.schemas` | Re-exported Haystack `Document`, canonical `meta` key conventions, `validate_meta()` helper |
| `rag_common.observability` | `@timed_operation()` decorator for consistent duration logging |
| `rag_common.testing` | Shared pytest fixtures (`valid_document`, `temp_env_file`, `schema_required_keys`) and `mock_http_provider()` helper |

## What does NOT belong here

- Any parsing, chunking, embedding, or retrieval logic
- Haystack `@component` classes
- CLI commands or API endpoints
- Model weights, prompts, or provider-specific code
- Any `__init__.py` that imports from RAG-specific packages

## How another module depends on it

Add to the module's `pyproject.toml`:

```toml
dependencies = [
    "rag-common = { path = "../rag-common", develop = true }",
]
```

### Example usage

```python
from rag_common import get_logger, log_context
from rag_common import BaseServiceSettings, fail_fast_validation
from rag_common import ConfigurationError
from rag_common import Document, validate_meta
from rag_common import timed_operation

# 1. Logger
logger = get_logger(__name__)
with log_context(document_id="abc123"):
    logger.info("Processing document")

# 2. Config
class MySettings(BaseServiceSettings):
    model_config = SettingsConfigDict(env_prefix="MY_")
    api_key: str = ""

settings = MySettings()
fail_fast_validation(settings, {"api_key": "MY_API_KEY"})

# 3. Exceptions
raise ConfigurationError("MY_API_KEY is not set")

# 4. Schemas
doc = Document(content="hello", meta={"document_id": "abc", ...})
validate_meta(doc, required_keys=["document_id"])

# 5. Observability
@timed_operation("my_stage")
def my_func():
    ...
```

## Versioning

This package follows [semantic versioning](https://semver.org/). Since every RAG module depends on `rag-common`, breaking changes (public API removals, signature changes) **must** bump the major version. Additions (new public functions, new fixtures) bump minor. Bug fixes bump patch.

## Development

```bash
# Install in editable mode
uv pip install -e packages/rag-common

# Run tests
python -m pytest packages/rag-common/tests/
```

# Migration Guide: Retrofitting Existing Modules onto `rag-common`

This document describes the minimal steps to retrofit a module (like `rag-parser`) that was built before `rag-common` existed. **Do not perform these steps as part of this pass** — they are documented here so a follow-up pass can be done predictably.

## General Pattern

For each module being retrofitted, the approach is:

1. **Add `rag-common` dependency** to the module's `pyproject.toml`
2. **Replace local infrastructure** with `rag-common` equivalents
3. **Verify** — no behavior changes, just import and base-class swaps

## Step-by-step: retrofitting `rag-parser`

### 1. Add dependency

In `packages/rag-parser/pyproject.toml`:

```toml
dependencies = [
    "rag-common = { path = "../rag-common", develop = true }",
    # ... existing deps
]
```

### 2. Replace logging

**Before** (`rag_parser/logging_setup.py`):
```python
import structlog

def setup_logging():
    structlog.configure(...)

def get_logger(name):
    return structlog.get_logger(name)
```

**After**:
```python
from rag_common import get_logger  # single import, no setup_logging call

logger = get_logger(__name__)
```

Remove `setup_logging()` calls — `rag_common.logging.setup_logging()` is called once at application entry point (CLI `main()`, API `lifespan`) instead.

### 3. Replace config base class

**Before** (`rag_parser/config.py`):
```python
from pydantic_settings import BaseSettings, SettingsConfigDict

class ParserConfig(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", ...)
```

**After**:
```python
from rag_common import BaseServiceSettings

class ParserConfig(BaseServiceSettings):
    model_config = SettingsConfigDict(env_prefix="PARSER_")
```

Replace `config.validate_provider_config()` with `fail_fast_validation(settings, {"mistral_api_key": "MISTRAL_API_KEY"})`.

### 4. Replace exception base classes

**Before** (`rag_parser/exceptions.py`):
```python
class ParserError(Exception):
    ...

class ProviderAPIError(ParserError):
    ...
```

**After**:
```python
from rag_common import RagBaseError, RetryableError, ConfigurationError

class ParserError(RagBaseError):
    ...

class ProviderAPIError(ParserError, RetryableError):
    ...
```

### 5. Switch `meta` handling to use `validate_meta`

**Before**: Ad-hoc dict building in `meta_schema.py`.

**After**: Use `validate_meta(doc, required_keys=[...])` from `rag_common.schemas` in the pipeline or API layer to assert the meta contract at parse/delivery time.

### 6. Add `@timed_operation` decorator

Wrap each parser strategy's `run()` method with `@timed_operation("parse:strategy_name")` for consistent duration logging.

## Verification checklist

After retrofitting:

- [ ] `python -m pytest tests/` — all existing tests still pass (no behavior change)
- [ ] `python -m rag_parser.cli --help` — CLI still works
- [ ] `python -m rag_parser.api` — API starts without import errors
- [ ] Log output format matches `rag_common` conventions (JSON by default)
- [ ] `repr()` on config does not leak secrets
- [ ] Exceptions raised by the parser module can be caught by `RagBaseError` type checks

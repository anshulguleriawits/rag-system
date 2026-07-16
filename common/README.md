# Common — Shared Infrastructure

Reusable utilities shared across RAG platform components:

- **logging** — structlog-based structured logger (`get_logger`, `log_context`, `setup_logging`)
- **config** — `BaseServiceSettings` with env-var-based config via pydantic-settings
- **exceptions** — `RagBaseError` hierarchy: `ConfigurationError`, `RetryableError`, `TerminalError`, `ValidationError`
- **schemas** — `Document` re-export, `META_KEY_SPEC` schema, `validate_meta`
- **observability** — `@timed_operation` decorator for structured operation logging
- **testing** — pytest fixtures, `mock_http_provider`, temp env file helper

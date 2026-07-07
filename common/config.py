from __future__ import annotations

import os
from pathlib import Path
from typing import Any, ClassVar

from pydantic import SecretStr
from pydantic_settings import (
    BaseSettings,
    SettingsConfigDict,
)


class BaseServiceSettings(BaseSettings):
    """Shared base for every RAG module's settings class.

    Features:
    - `.env` loading with module-level override over root-level precedence
    - `env_prefix` defaults to module name convention (override in subclass)
    - Secret fields automatically use Haystack-compatible env var pattern
    - `fail_fast_validation()` helper for human-readable startup errors

    Precedence (highest first):
      1. Direct env vars (exported/shell)
      2. Module-level `.env` (e.g. `packages/rag-chunker/.env`)
      3. Root `.env` (repo root)
      4. Default values in code

    Subclasses should set ``model_config`` with at least ``env_prefix``::

        class ChunkerSettings(BaseServiceSettings):
            model_config = SettingsConfigDict(env_prefix="CHUNKER_")
            ...
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        # Subclasses should override env_prefix:
        env_prefix="COMMON_",
    )

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        cls._ensure_env_file()

    @classmethod
    def _ensure_env_file(cls) -> None:
        env_file = cls.model_config.get("env_file", ".env")
        if isinstance(env_file, str):
            env_file = (Path.cwd() / env_file)
        elif isinstance(env_file, Path):
            pass
        else:
            return
        resolved = Path(env_file).resolve() if not isinstance(env_file, Path) else env_file
        if resolved.exists():
            return
        parent = resolved.parent / ".env"
        if parent.exists():
            cls.model_config["env_file"] = str(parent)

    def __repr__(self) -> str:
        return self._safe_repr()

    def _safe_repr(self) -> str:
        parts: list[str] = []
        for name, field in type(self).model_fields.items():
            value = getattr(self, name)
            if isinstance(value, SecretStr):
                parts.append(f"{name}='******'")
            elif isinstance(value, str) and any(
                k in name.lower() for k in ("key", "secret", "token", "password", "api_key")
            ):
                parts.append(f"{name}='******'")
            else:
                parts.append(f"{name}={value!r}")
        return f"{type(self).__name__}({', '.join(parts)})"

    __str__ = __repr__


def fail_fast_validation(
    settings: BaseServiceSettings,
    required_fields: dict[str, str],
) -> None:
    """Validate that required settings are non-empty and non-None.

    Args:
        settings: An instantiated settings object.
        required_fields: Mapping of ``{field_name: "human-readable env var name"}``.

    Raises:
        ConfigurationError: If any required field is empty/missing, with a
            clear message pointing at the exact env var and which module needs it.
    """
    from common.exceptions import ConfigurationError

    errors: list[str] = []
    for field_name, env_var in required_fields.items():
        value = getattr(settings, field_name, None)
        if value is None:
            errors.append(f"  - {env_var} (field: {field_name}) is not set")
        elif isinstance(value, str) and not value.strip():
            errors.append(f"  - {env_var} (field: {field_name}) is empty")
        elif hasattr(value, "get_secret_value"):
            try:
                resolved = value.get_secret_value()
                if not resolved or not resolved.strip():
                    errors.append(f"  - {env_var} (field: {field_name}) is empty")
            except Exception:
                errors.append(f"  - {env_var} (field: {field_name}) could not be resolved")

    if errors:
        module = type(settings).__module__.split(".")[0]
        msg = (
            f"[{module}] Missing required configuration:\n"
            + "\n".join(errors)
            + f"\n\nSet these in the module's `.env` file or export them as env vars."
        )
        raise ConfigurationError(msg)

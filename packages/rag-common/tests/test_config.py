from __future__ import annotations

import os
from pathlib import Path

import pytest
from pydantic import SecretStr
from pydantic_settings import SettingsConfigDict

from rag_common.config import BaseServiceSettings, fail_fast_validation
from rag_common.exceptions import ConfigurationError


class TestBaseServiceSettings:
    def test_basic_instantiation(self) -> None:
        class TestSettings(BaseServiceSettings):
            model_config = SettingsConfigDict(env_prefix="TEST_")
            name: str = "default"

        settings = TestSettings()
        assert settings.name == "default"

    def test_env_var_override(self) -> None:
        os.environ["TEST_MY_KEY"] = "from_env"

        class TestSettings(BaseServiceSettings):
            model_config = SettingsConfigDict(env_prefix="TEST_")
            my_key: str = "default"

        settings = TestSettings()
        assert settings.my_key == "from_env"
        os.environ.pop("TEST_MY_KEY", None)

    def test_secret_str_masked_in_repr(self) -> None:
        class TestSettings(BaseServiceSettings):
            model_config = SettingsConfigDict(env_prefix="TEST_")
            api_key: SecretStr = SecretStr("supersecret")

        settings = TestSettings()
        rep = repr(settings)
        assert "supersecret" not in rep
        assert "******" in rep

    def test_sensitive_field_name_masked(self) -> None:
        class TestSettings(BaseServiceSettings):
            model_config = SettingsConfigDict(env_prefix="TEST_")
            my_token: str = "sensitive-value"

        settings = TestSettings()
        rep = repr(settings)
        assert "sensitive-value" not in rep
        assert "******" in rep

    def test_plain_field_visible_in_repr(self) -> None:
        class TestSettings(BaseServiceSettings):
            model_config = SettingsConfigDict(env_prefix="TEST_")
            timeout: int = 30

        settings = TestSettings()
        assert "timeout=30" in repr(settings)


class TestFailFastValidation:
    def test_passes_when_fields_set(self) -> None:
        class TestSettings(BaseServiceSettings):
            model_config = SettingsConfigDict(env_prefix="TEST_")
            api_key: str = "set-value"

        settings = TestSettings()
        fail_fast_validation(settings, {"api_key": "TEST_API_KEY"})

    def test_raises_when_field_empty(self) -> None:
        class TestSettings(BaseServiceSettings):
            model_config = SettingsConfigDict(env_prefix="TEST_")
            api_key: str = ""

        settings = TestSettings()
        with pytest.raises(ConfigurationError) as exc:
            fail_fast_validation(settings, {"api_key": "TEST_API_KEY"})
        assert "TEST_API_KEY" in str(exc.value)

    def test_raises_when_field_none(self) -> None:
        class TestSettings(BaseServiceSettings):
            model_config = SettingsConfigDict(env_prefix="TEST_")
            api_key: str | None = None

        settings = TestSettings()
        with pytest.raises(ConfigurationError) as exc:
            fail_fast_validation(settings, {"api_key": "TEST_API_KEY"})
        assert "TEST_API_KEY" in str(exc.value)
        assert "is not set" in str(exc.value)

    def test_raises_configuration_error_type(self) -> None:
        class TestSettings(BaseServiceSettings):
            model_config = SettingsConfigDict(env_prefix="TEST_")
            api_key: str = ""

        settings = TestSettings()
        with pytest.raises(ConfigurationError):
            fail_fast_validation(settings, {"api_key": "TEST_API_KEY"})

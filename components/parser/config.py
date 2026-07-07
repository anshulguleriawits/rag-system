from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic_settings import SettingsConfigDict

from common import BaseServiceSettings


class ParserConfig(BaseServiceSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        env_prefix="",
    )

    default_strategy: str = "auto"
    ocr_cloud_provider: Literal["mistral", "llamaparse"] = "mistral"
    ocr_local_engine: Literal["tesseract", "paddleocr"] = "tesseract"
    ocr_local_language: str = "eng"
    fallback_chain: str = "docling,ocr_cloud,ocr_local"
    scanned_text_threshold: float = 0.05
    debug_dir: str = "./debug_output"
    enable_debug: bool = True
    log_level: str = "INFO"

    mistral_api_key: str = ""
    llamaparse_api_key: str = ""
    llamaparse_endpoint: str = "https://api.cloud.llamaindex.ai"
    llamaparse_result_type: str = "markdown"
    llamaparse_poll_interval_seconds: int = 5
    llamaparse_timeout_seconds: int = 120

    @property
    def fallback_strategies(self) -> list[str]:
        return [s.strip() for s in self.fallback_chain.split(",") if s.strip()]

    @property
    def debug_path(self) -> Path:
        p = Path(self.debug_dir)
        p.mkdir(parents=True, exist_ok=True)
        return p

    def validate_provider_config(self) -> list[str]:
        warnings: list[str] = []
        if self.ocr_cloud_provider == "mistral" and not self.mistral_api_key:
            warnings.append(
                "PARSER_OCR_CLOUD_PROVIDER=mistral but MISTRAL_API_KEY is not set"
            )
        if self.ocr_cloud_provider == "llamaparse" and not self.llamaparse_api_key:
            warnings.append(
                "PARSER_OCR_CLOUD_PROVIDER=llamaparse but LLAMAPARSE_API_KEY is not set"
            )
        return warnings


config = ParserConfig()

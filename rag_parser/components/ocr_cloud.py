from __future__ import annotations

import time
import uuid
from pathlib import Path
from typing import Any, Literal

from haystack import Document, component
from haystack.utils import Secret

from rag_parser.config import config
from rag_parser.exceptions import ProviderAPIError
from rag_common import timed_operation

CloudProvider = Literal["mistral", "llamaparse"]


@component
class CloudOCRParser:
    """Parser for scanned/complex documents using cloud OCR/parsing APIs.

    Supports:
    - Mistral OCR (via native MistralOCRDocumentConverter)
    - LlamaParse (via custom async-job-based wrapper)

    Provider is selected via config.ocr_cloud_provider.
    """

    def __init__(self, provider: CloudProvider | None = None) -> None:
        self._version = "1.0.0"
        self._provider = provider or config.ocr_cloud_provider

    @component.output_types(documents=list[Document])
    @timed_operation("parse:ocr_cloud")
    def run(
        self,
        sources: list[Path | str],
        meta: list[dict[str, Any]] | None = None,
    ) -> dict[str, list[Document]]:
        if self._provider == "mistral":
            return self._run_mistral(sources, meta)
        elif self._provider == "llamaparse":
            return self._run_llamaparse(sources, meta)
        else:
            raise ValueError(f"Unknown cloud OCR provider: {self._provider}")

    def _run_mistral(
        self,
        sources: list[Path | str],
        meta: list[dict[str, Any]] | None = None,
    ) -> dict[str, list[Document]]:
        try:
            from haystack_integrations.components.converters.mistral import (
                MistralOCRDocumentConverter,
            )
        except ImportError:
            raise ImportError(
                "mistral-haystack is required for Mistral OCR. "
                "Install with: pip install mistral-haystack"
            )

        converter = MistralOCRDocumentConverter(
            api_key=Secret.from_env_var("MISTRAL_API_KEY"),
            model="mistral-ocr-2505",
        )

        result = converter.run(sources=sources, meta=meta)
        for d in result.get("documents", []):
            d.meta["parser_used"] = "ocr_cloud:mistral"
            d.meta["parser_version"] = self._version
            if "element_type" not in d.meta or not d.meta.get("element_type"):
                d.meta["element_type"] = "paragraph"

        return result

    def _run_llamaparse(
        self,
        sources: list[Path | str],
        meta: list[dict[str, Any]] | None = None,
    ) -> dict[str, list[Document]]:
        import httpx

        api_key = config.llamaparse_api_key
        if not api_key:
            raise ProviderAPIError(
                "LLAMAPARSE_API_KEY is not configured"
            )

        endpoint = config.llamaparse_endpoint.rstrip("/")
        result_type = config.llamaparse_result_type
        poll_interval = config.llamaparse_poll_interval_seconds
        timeout = config.llamaparse_timeout_seconds

        docs: list[Document] = []
        for i, src in enumerate(sources):
            path = Path(src)
            m = meta[i] if meta and i < len(meta) else {}

            with open(path, "rb") as f:
                files = {"file": (path.name, f, "application/octet-stream")}
                headers = {
                    "Authorization": f"Bearer {api_key}",
                    "accept": "application/json",
                }

                submit_resp = httpx.post(
                    f"{endpoint}/api/parsing/upload",
                    headers=headers,
                    files=files,
                    timeout=30,
                )
                if submit_resp.status_code != 200:
                    raise ProviderAPIError(
                        f"LlamaParse upload failed: {submit_resp.status_code} "
                        f"{submit_resp.text}"
                    )

                job_data = submit_resp.json()
                job_id = job_data.get("id") or job_data.get("job_id")

                if not job_id:
                    raise ProviderAPIError(
                        f"LlamaParse did not return a job ID: {job_data}"
                    )

                deadline = time.monotonic() + timeout
                result_data = None

                while time.monotonic() < deadline:
                    status_resp = httpx.get(
                        f"{endpoint}/api/parsing/{job_id}/status",
                        headers=headers,
                        timeout=30,
                    )
                    if status_resp.status_code != 200:
                        raise ProviderAPIError(
                            f"LlamaParse status check failed: "
                            f"{status_resp.status_code}"
                        )

                    status_data = status_resp.json()
                    status = status_data.get("status", "").lower()

                    if status == "completed":
                        result_resp = httpx.get(
                            f"{endpoint}/api/parsing/{job_id}/result",
                            headers=headers,
                            timeout=30,
                        )
                        if result_resp.status_code == 200:
                            result_data = result_resp.json()
                        break
                    elif status in ("failed", "error"):
                        raise ProviderAPIError(
                            f"LlamaParse job {job_id} failed: "
                            f"{status_data.get('error', 'unknown error')}"
                        )

                    time.sleep(poll_interval)

                if result_data is None:
                    raise TimeoutError(
                        f"LlamaParse job {job_id} did not complete "
                        f"within {timeout}s"
                    )

                content: str = ""
                pages = result_data.get("pages", result_data.get("results", []))
                if isinstance(pages, list):
                    for pg in pages:
                        pg_content = pg.get(
                            "markdown", pg.get("text", pg.get("content", ""))
                        )
                        if pg_content:
                            content += pg_content + "\n\n"
                else:
                    content = result_data.get(
                        "markdown",
                        result_data.get("text", result_data.get("content", "")),
                    )

                doc_meta = dict(m)
                doc_meta["parser_used"] = "ocr_cloud:llamaparse"
                doc_meta["parser_version"] = self._version
                doc_meta["element_type"] = "paragraph"
                doc_meta["source_path"] = str(path)
                doc_meta["document_id"] = uuid.uuid4().hex[:16]
                docs.append(Document(content=content or "[EMPTY]", meta=doc_meta))

        return {"documents": docs}

from __future__ import annotations

import json
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

import httpx
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel

from rag_parser.config import config
from rag_parser.logging_setup import get_logger, setup_logging
from rag_parser.pipeline import ParsingPipeline

setup_logging()
logger = get_logger(__name__)

pipeline = ParsingPipeline()

# In-memory job store for async parses
_jobs: dict[str, dict] = {}


class ParseResponse(BaseModel):
    document_id: str
    documents: list[dict]
    errors: list[list[str]]


class JobResponse(BaseModel):
    job_id: str
    status: str
    result: Optional[ParseResponse] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    from rag_common import fail_fast_validation

    warnings = config.validate_provider_config()
    for w in warnings:
        logger.warning(f"Configuration warning: {w}")
    if config.mistral_api_key:
        fail_fast_validation(config, {"mistral_api_key": "MISTRAL_API_KEY"})
    yield


app = FastAPI(
    title="RAG Parser API",
    description="Document parsing module for RAG systems — parse files into Haystack Documents",
    version="1.0.0",
    lifespan=lifespan,
)


@app.get("/health")
async def health() -> dict:
    """Health check endpoint, including provider config status."""
    return {
        "status": "ok",
        "version": "1.0.0",
        "providers": {
            "mistral": bool(config.mistral_api_key),
            "llamaparse": bool(config.llamaparse_api_key),
            "local_ocr": True,
        },
        "default_strategy": config.default_strategy,
    }


@app.post("/parse", response_model=ParseResponse)
async def parse_file(
    file: UploadFile = File(...),
    strategy: Optional[str] = None,
) -> dict:
    """Parse a single uploaded file.

    Accepts a file upload, optional strategy override, returns parsed Documents.
    For large/cloud-OCR files, use POST /parse/async instead.
    """
    content = await file.read()
    tmp_dir = Path(config.debug_dir) / "uploads"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    tmp_path = tmp_dir / file.filename
    tmp_path.write_bytes(content)

    try:
        result = pipeline.run(
            sources=[tmp_path],
            force_parser=strategy,
        )
        docs = result.get("documents", [])
        errors = result.get("errors", [])

        doc_id = uuid.uuid4().hex[:16]

        return {
            "document_id": doc_id,
            "documents": [
                {"content": d.content, "meta": d.meta} for d in docs
            ],
            "errors": [[f, e] for f, e in errors],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if tmp_path.exists():
            tmp_path.unlink()


@app.post("/parse/async")
async def parse_file_async(
    file: UploadFile = File(...),
    strategy: Optional[str] = None,
) -> JobResponse:
    """Submit a file for async parsing.

    Returns a job_id immediately. Poll /parse/{job_id} for results.
    """
    content = await file.read()
    job_id = uuid.uuid4().hex[:16]

    tmp_dir = Path(config.debug_dir) / "uploads"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    tmp_path = tmp_dir / file.filename
    tmp_path.write_bytes(content)

    _jobs[job_id] = {"status": "processing", "tmp_path": str(tmp_path), "strategy": strategy}

    import asyncio
    import threading

    def _process() -> None:
        try:
            result = pipeline.run(
                sources=[Path(_jobs[job_id]["tmp_path"])],
                force_parser=_jobs[job_id].get("strategy"),
            )
            docs = result.get("documents", [])
            errors = result.get("errors", [])
            _jobs[job_id] = {
                "status": "completed",
                "result": {
                    "document_id": uuid.uuid4().hex[:16],
                    "documents": [
                        {"content": d.content, "meta": d.meta} for d in docs
                    ],
                    "errors": [[f, e] for f, e in errors],
                },
            }
        except Exception as e:
            _jobs[job_id] = {"status": "failed", "error": str(e)}

    threading.Thread(target=_process, daemon=True).start()

    return JobResponse(job_id=job_id, status="processing")


@app.get("/parse/{job_id}")
async def get_parse_result(job_id: str) -> JobResponse:
    """Retrieve the result of an async parse job."""
    job = _jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return JobResponse(
        job_id=job_id,
        status=job["status"],
        result=job.get("result"),
    )


@app.get("/parse/{document_id}/debug", response_class=HTMLResponse)
async def get_debug_report(document_id: str) -> str:
    """Retrieve the debug HTML report for a parsed document."""
    from rag_parser.debug.artifact_manager import DebugArtifactManager

    manager = DebugArtifactManager()
    report_path = manager.get_debug_report(document_id)

    if not report_path:
        raise HTTPException(
            status_code=404,
            detail=f"No debug report found for {document_id}",
        )

    return Path(report_path).read_text()


if __name__ == "__main__":
    import logging

    import uvicorn

    uvicorn_loggers = [
        logging.getLogger("uvicorn"),
        logging.getLogger("uvicorn.access"),
        logging.getLogger("uvicorn.error"),
    ]
    for ul in uvicorn_loggers:
        ul.handlers.clear()
        ul.propagate = True

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_config=None,
        log_level=config.log_level.lower(),
    )

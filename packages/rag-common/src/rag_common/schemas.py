from __future__ import annotations

from typing import Any, Sequence

from haystack import Document as HaystackDocument


Document = HaystackDocument


META_KEY_SPEC: dict[str, dict[str, Any]] = {
    # --- Active keys (populated by parser) ---
    "document_id": {
        "type": str,
        "required": True,
        "description": "Unique document identifier (uuid hex, 16 chars)",
        "populated_by": "rag-parser",
        "consumed_by": ["rag-chunker", "rag-embedder", "rag-retriever"],
    },
    "source_path": {
        "type": str,
        "required": True,
        "description": "Original file path or filename",
        "populated_by": "rag-parser",
        "consumed_by": ["rag-retriever"],
    },
    "mime_type": {
        "type": str,
        "required": True,
        "description": "Detected MIME type of the source file",
        "populated_by": "rag-parser",
        "consumed_by": [],
    },
    "parser_used": {
        "type": str,
        "required": True,
        "description": "Parser strategy name (e.g. docling, simple:.txt)",
        "populated_by": "rag-parser",
        "consumed_by": [],
    },
    "parser_version": {
        "type": str,
        "required": True,
        "description": "Parser module version string",
        "populated_by": "rag-parser",
        "consumed_by": [],
    },
    "page_number": {
        "type": (int, type(None)),
        "required": False,
        "description": "Page number within a multi-page document",
        "populated_by": "rag-parser",
        "consumed_by": [],
    },
    "section_path": {
        "type": list,
        "required": False,
        "description": "Hierarchical section path (e.g. ['2.1', 'Introduction'])",
        "populated_by": "rag-parser",
        "consumed_by": [],
    },
    "element_type": {
        "type": str,
        "required": True,
        "description": "Document element type (paragraph, table, code, etc.)",
        "populated_by": "rag-parser",
        "consumed_by": [],
    },
    "confidence": {
        "type": (float, int, type(None)),
        "required": False,
        "description": "Parsing confidence score (0-1)",
        "populated_by": "rag-parser",
        "consumed_by": ["rag-retriever"],
    },
    "parsing_duration_ms": {
        "type": int,
        "required": True,
        "description": "Wall-clock time to parse in milliseconds",
        "populated_by": "rag-parser",
        "consumed_by": [],
    },
    "warnings": {
        "type": list,
        "required": True,
        "description": "Non-fatal issues encountered during parsing",
        "populated_by": "rag-parser",
        "consumed_by": [],
    },
    # --- Reserved keys (future modules) ---
    "chunk_id": {
        "type": str,
        "required": False,
        "description": "Chunk identifier within a document (RESERVED)",
        "populated_by": "rag-chunker",
        "consumed_by": ["rag-embedder"],
    },
    "parent_chunk_id": {
        "type": (str, type(None)),
        "required": False,
        "description": "Parent chunk identifier for hierarchical chunking (RESERVED)",
        "populated_by": "rag-chunker",
        "consumed_by": [],
    },
    "chunk_index": {
        "type": int,
        "required": False,
        "description": "Sequential index within the chunk sequence (RESERVED)",
        "populated_by": "rag-chunker",
        "consumed_by": [],
    },
    "embedding_model": {
        "type": str,
        "required": False,
        "description": "Name of the embedding model used (RESERVED)",
        "populated_by": "rag-embedder",
        "consumed_by": ["rag-retriever"],
    },
    "embedding_model_version": {
        "type": str,
        "required": False,
        "description": "Version of the embedding model (RESERVED)",
        "populated_by": "rag-embedder",
        "consumed_by": [],
    },
    "embedding_vector": {
        "type": list,
        "required": False,
        "description": "Embedding vector (RESERVED)",
        "populated_by": "rag-embedder",
        "consumed_by": ["rag-retriever"],
    },
    "retrieval_score": {
        "type": float,
        "required": False,
        "description": "Similarity score from retrieval (RESERVED)",
        "populated_by": "rag-retriever",
        "consumed_by": [],
    },
    "retrieval_method": {
        "type": str,
        "required": False,
        "description": "Retrieval method used (RESERVED)",
        "populated_by": "rag-retriever",
        "consumed_by": [],
    },
}


def validate_meta(
    doc: Document,
    required_keys: Sequence[str] | None = None,
) -> dict[str, Any]:
    """Validate a Document's ``meta`` dict against the shared schema.

    Args:
        doc: A Haystack ``Document`` to validate.
        required_keys: Subset of meta keys to enforce as required for this
            check. If ``None``, uses all keys marked ``required`` in
            ``META_KEY_SPEC``.

    Returns:
        The validated ``meta`` dict.

    Raises:
        ValidationError: If a required key is missing, ``None``, or the
            wrong type.
    """
    if required_keys is None:
        required_keys = [
            k for k, spec in META_KEY_SPEC.items() if spec.get("required")
        ]

    from rag_common.exceptions import ValidationError

    meta = doc.meta or {}
    errors: list[str] = []

    for key in required_keys:
        spec = META_KEY_SPEC.get(key)
        if spec is None:
            errors.append(f"Unknown meta key: {key!r} — not in META_KEY_SPEC")
            continue

        if key not in meta or meta[key] is None:
            errors.append(
                f"meta.{key} is missing or None "
                f"({spec.get('description', 'no description')})"
            )
            continue

        expected_type = spec.get("type", object)
        value = meta[key]

        if isinstance(expected_type, tuple):
            if not isinstance(value, expected_type):
                type_names = " | ".join(t.__name__ for t in expected_type)
                errors.append(
                    f"meta.{key} expected {type_names}, got {type(value).__name__}"
                )
        elif not isinstance(value, expected_type):
            errors.append(
                f"meta.{key} expected {expected_type.__name__}, "
                f"got {type(value).__name__}"
            )

    if errors:
        detail = "; ".join(errors)
        raise ValidationError(
            f"Document meta validation failed ({len(errors)} error(s)): {detail}",
            context={"errors": errors, "document_id": meta.get("document_id")},
        )

    return meta

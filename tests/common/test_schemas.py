from __future__ import annotations

import pytest
from haystack import Document

from common.exceptions import ValidationError
from common.schemas import META_KEY_SPEC, validate_meta


class TestMetaKeySpec:
    def test_required_keys_defined(self) -> None:
        required = [k for k, spec in META_KEY_SPEC.items() if spec.get("required")]
        assert "document_id" in required
        assert "source_path" in required
        assert "mime_type" in required
        assert "parser_used" in required
        assert "parser_version" in required
        assert "element_type" in required
        assert "parsing_duration_ms" in required
        assert "warnings" in required

    def test_reserved_keys_documented(self) -> None:
        assert META_KEY_SPEC["chunk_id"]["populated_by"] == "rag-chunker"
        assert META_KEY_SPEC["embedding_model"]["populated_by"] == "rag-embedder"
        assert META_KEY_SPEC["retrieval_score"]["populated_by"] == "rag-retriever"

    def test_every_key_has_spec(self) -> None:
        for key, spec in META_KEY_SPEC.items():
            assert "type" in spec
            assert "required" in spec
            assert "description" in spec
            assert "populated_by" in spec
            assert "consumed_by" in spec


class TestValidateMeta:
    def test_valid_meta_passes(self) -> None:
        doc = Document(
            content="hello",
            meta={
                "document_id": "abc123",
                "source_path": "/f.txt",
                "mime_type": "text/plain",
                "parser_used": "simple",
                "parser_version": "1.0",
                "element_type": "paragraph",
                "parsing_duration_ms": 10,
                "warnings": [],
            },
        )
        result = validate_meta(doc)
        assert result["document_id"] == "abc123"

    def test_missing_required_key_fails(self) -> None:
        doc = Document(content="hello", meta={"document_id": "abc123"})
        with pytest.raises(ValidationError) as exc:
            validate_meta(doc)
        assert "source_path" in str(exc.value)

    def test_unknown_key_in_required_fails(self) -> None:
        doc = Document(
            content="hello",
            meta={
                "document_id": "abc123",
                "source_path": "/f.txt",
                "mime_type": "text/plain",
                "parser_used": "simple",
                "parser_version": "1.0",
                "element_type": "paragraph",
                "parsing_duration_ms": 10,
                "warnings": [],
            },
        )
        with pytest.raises(ValidationError) as exc:
            validate_meta(doc, required_keys=["nonexistent"])
        assert "nonexistent" in str(exc.value)

    def test_wrong_type_fails(self) -> None:
        doc = Document(
            content="hello",
            meta={
                "document_id": "abc123",
                "source_path": "/f.txt",
                "mime_type": "text/plain",
                "parser_used": "simple",
                "parser_version": "1.0",
                "element_type": "paragraph",
                "parsing_duration_ms": "not_an_int",  # should be int
                "warnings": [],
            },
        )
        with pytest.raises(ValidationError) as exc:
            validate_meta(doc)
        assert "parsing_duration_ms" in str(exc.value)
        assert "str" in str(exc.value)

    def test_none_value_fails(self) -> None:
        doc = Document(
            content="hello",
            meta={
                "document_id": None,
                "source_path": "/f.txt",
                "mime_type": "text/plain",
                "parser_used": "simple",
                "parser_version": "1.0",
                "element_type": "paragraph",
                "parsing_duration_ms": 10,
                "warnings": [],
            },
        )
        with pytest.raises(ValidationError) as exc:
            validate_meta(doc)
        assert "document_id" in str(exc.value)

    def test_custom_required_keys(self) -> None:
        doc = Document(
            content="hello",
            meta={
                "document_id": "abc123",
                "source_path": "/f.txt",
                "mime_type": "text/plain",
                "parser_used": "simple",
                "parser_version": "1.0",
                "element_type": "paragraph",
                "parsing_duration_ms": 10,
                "warnings": [],
                "confidence": 0.95,
            },
        )
        result = validate_meta(doc, required_keys=["document_id", "confidence"])
        assert result["confidence"] == 0.95

    def test_optional_key_allowed_missing(self) -> None:
        doc = Document(
            content="hello",
            meta={
                "document_id": "abc123",
                "source_path": "/f.txt",
                "mime_type": "text/plain",
                "parser_used": "simple",
                "parser_version": "1.0",
                "element_type": "paragraph",
                "parsing_duration_ms": 10,
                "warnings": [],
                # page_number is optional, not required
            },
        )
        result = validate_meta(doc)
        # page_number is not in required keys, so should pass
        assert result is not None

    def test_re_exports_haystack_document(self) -> None:
        from common.schemas import Document as CommonDocument

        doc = CommonDocument(content="test")
        assert isinstance(doc, Document)

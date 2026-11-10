"""
Unit tests for the DocumentLoader module.
"""

import pytest
from pathlib import Path
from src.config import PROJECT_ROOT, APPROVED_DOCUMENTS_PATH
from src.rag.document_loader import DocumentLoader, LoadedDocument, DocumentSection
from src.rag.exceptions import DocumentLoadingError


def test_document_loader_catalog_loading():
    loader = DocumentLoader()
    catalog = loader.get_approved_documents_catalog()
    assert len(catalog) >= 8
    doc_ids = [entry["document_id"] for entry in catalog]
    assert "nirf_methodology_reference" in doc_ids
    assert "data_dictionary" in doc_ids
    assert "comparability_report" in doc_ids
    assert "comparability_rules" in doc_ids


def test_load_single_markdown_document():
    loader = DocumentLoader()
    doc = loader.load_document_by_id("nirf_methodology_reference")
    assert isinstance(doc, LoadedDocument)
    assert doc.document_id == "nirf_methodology_reference"
    assert doc.format == "md"
    assert len(doc.sections) > 5
    assert any("TLR" in s.title or "TLR" in s.content for s in doc.sections)


def test_load_data_dictionary_excel():
    loader = DocumentLoader()
    doc = loader.load_document_by_id("data_dictionary")
    assert isinstance(doc, LoadedDocument)
    assert doc.document_id == "data_dictionary"
    assert doc.format == "xlsx"
    # Should have overview + 40 individual field sections
    assert len(doc.sections) >= 40
    # Check that score and rank fields exist
    field_titles = [s.title for s in doc.sections]
    assert any("score" in t.lower() for t in field_titles)
    assert any("rank" in t.lower() for t in field_titles)


def test_load_comparability_rules_csv():
    loader = DocumentLoader()
    doc = loader.load_document_by_id("comparability_rules")
    assert isinstance(doc, LoadedDocument)
    assert doc.document_id == "comparability_rules"
    assert doc.format == "csv"
    assert len(doc.sections) > 0
    # Check that Engineering and College are present
    categories = [s.metadata.get("category") for s in doc.sections if "category" in s.metadata]
    assert "Engineering" in categories
    assert "College" in categories


def test_load_missing_document_raises_error():
    loader = DocumentLoader()
    with pytest.raises(DocumentLoadingError):
        loader.load_document_by_id("non_existent_doc_id_999")


def test_load_missing_manifest_raises_error(tmp_path):
    missing_manifest = tmp_path / "does_not_exist.json"
    with pytest.raises(DocumentLoadingError):
        DocumentLoader(approved_documents_path=missing_manifest)


"""Tests for DOCP-01 — Document text extraction via Docling pipeline.

Tests the POST /process endpoint of the docproc FastAPI service using
mocked Docling DocumentConverter. All heavy ML dependencies
(docling, easyocr, cv2) are stubbed in conftest.py.
"""

import sys
import types
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Helpers for building mock Docling document elements
# ---------------------------------------------------------------------------


def _make_prov(page_no: int):
    """Build a minimal provenance object with page_no."""
    return types.SimpleNamespace(page_no=page_no)


def _make_text_element(text: str, page_no: int):
    """Build a minimal document text element with text and prov."""
    return types.SimpleNamespace(
        text=text,
        prov=[_make_prov(page_no)],
    )


def _make_mock_convert_result(*elements):
    """Build a mock ConversionResult with a document containing given elements."""
    doc = types.SimpleNamespace(
        iterate_items=lambda: [(elem, 0) for elem in elements]
    )
    return types.SimpleNamespace(document=doc)


# ---------------------------------------------------------------------------
# App fixture — patches DocumentConverter so lifespan uses lightweight stubs
# ---------------------------------------------------------------------------


@pytest.fixture
def app_client(tmp_path):
    """FastAPI TestClient for the docproc app.

    Patches DocumentConverter and easyocr.Reader at import level so the
    lifespan runs without real Docling/EasyOCR model loading, but app.state
    still gets populated with real (stubbed) converter objects.
    """
    from fastapi.testclient import TestClient

    import main as docproc_main

    # Patch easyocr.Reader to avoid model download during lifespan pre-warm
    mock_reader_cls = MagicMock()
    mock_reader_cls.return_value = MagicMock()

    with patch.object(docproc_main, "easyocr") as mock_easyocr_mod:
        mock_easyocr_mod.Reader = mock_reader_cls

        with TestClient(docproc_main.app, raise_server_exceptions=True) as client:
            yield client


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_health_endpoint(app_client):
    """GET /health returns 200 with status ok."""
    response = app_client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"


def test_text_pdf_extraction(tmp_path, app_client):
    """POST /process extracts text from a text PDF using the text converter."""
    pdf_file = tmp_path / "sample.pdf"
    pdf_file.write_bytes(b"%PDF-1.4 mock")

    # Set up the stubbed converter_text on app.state to return a real-looking result
    import main as docproc_main

    elem1 = _make_text_element("Hello from page one.", page_no=1)
    elem2 = _make_text_element("Content on page two.", page_no=2)
    mock_result = _make_mock_convert_result(elem1, elem2)
    docproc_main.app.state.converter_text.convert = MagicMock(return_value=mock_result)
    docproc_main.app.state.converter_ocr.convert = MagicMock(return_value=mock_result)

    response = app_client.post(
        "/process",
        json={"file_path": str(pdf_file), "ocr_enabled": False},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert len(data["pages"]) == 2
    assert data["pages"][0]["page_no"] == 1
    assert "Hello from page one." in data["pages"][0]["text"]


def test_process_endpoint_returns_pages(tmp_path, app_client):
    """POST /process response contains required keys: status, pages, full_text, total_pages."""
    pdf_file = tmp_path / "doc.pdf"
    pdf_file.write_bytes(b"%PDF-1.4")

    import main as docproc_main

    elem = _make_text_element("Sample content.", page_no=1)
    mock_result = _make_mock_convert_result(elem)
    docproc_main.app.state.converter_ocr.convert = MagicMock(return_value=mock_result)

    response = app_client.post(
        "/process",
        json={"file_path": str(pdf_file), "ocr_enabled": True},
    )

    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "pages" in data
    assert "full_text" in data
    assert "total_pages" in data
    assert data["file_name"] == "doc.pdf"


def test_process_missing_file(app_client):
    """POST /process with a nonexistent file path returns 404."""
    response = app_client.post(
        "/process",
        json={"file_path": "/nonexistent/path/document.pdf", "ocr_enabled": True},
    )
    assert response.status_code == 404
    data = response.json()
    assert data["status"] == "error"


def test_process_unsupported_type(tmp_path, app_client):
    """POST /process with an unsupported file extension returns 400."""
    docx_file = tmp_path / "report.docx"
    docx_file.write_bytes(b"PK mock docx content")

    response = app_client.post(
        "/process",
        json={"file_path": str(docx_file), "ocr_enabled": False},
    )
    assert response.status_code == 400
    data = response.json()
    assert data["status"] == "error"
    assert "Unsupported" in data["detail"]

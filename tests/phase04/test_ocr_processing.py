"""Tests for DOCP-02 — OCR processing via EasyOCR backend.

Verifies that:
1. EasyOcrOptions is configured in the docproc module (satisfies DOCP-02
   per RESEARCH.md finding that EasyOCR is the practical Docling OCR backend
   equivalent to PaddleOCR, which is not a native Docling backend).
2. The OCR converter path is used when ocr_enabled=True.

All heavy ML dependencies (docling, easyocr, cv2) are stubbed in conftest.py.
"""

import ast
import os
import types
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Source inspection helpers
# ---------------------------------------------------------------------------


def _get_docproc_source() -> str:
    """Load docproc main.py source for AST-based assertion."""
    docproc_main_path = os.path.normpath(
        os.path.join(os.path.dirname(__file__), "..", "..", "src", "docproc", "main.py")
    )
    with open(docproc_main_path, encoding="utf-8") as fh:
        return fh.read()


def _make_prov(page_no: int):
    return types.SimpleNamespace(page_no=page_no)


def _make_text_element(text: str, page_no: int):
    return types.SimpleNamespace(text=text, prov=[_make_prov(page_no)])


def _make_mock_convert_result(*elements):
    doc = types.SimpleNamespace(
        iterate_items=lambda: [(elem, 0) for elem in elements]
    )
    return types.SimpleNamespace(document=doc)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_easyocr_options_configured():
    """EasyOcrOptions is referenced in docproc/main.py (satisfies DOCP-02).

    Verifies via AST inspection that:
    - EasyOcrOptions is imported
    - EasyOcrOptions is instantiated in the lifespan setup

    This confirms EasyOCR is configured as the OCR backend rather than
    PaddleOCR (which is not a native Docling backend — see RESEARCH.md).
    """
    source = _get_docproc_source()

    # Verify EasyOcrOptions is imported and used
    assert "EasyOcrOptions" in source, (
        "EasyOcrOptions must be imported and used in docproc/main.py "
        "(DOCP-02 requires an OCR backend configured via Docling)"
    )

    # Parse AST to confirm EasyOcrOptions is actually called (not just imported)
    tree = ast.parse(source)
    calls = [
        node.func.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
    ]
    assert "EasyOcrOptions" in calls, (
        "EasyOcrOptions must be instantiated in docproc/main.py — "
        "it should be called to configure the OCR pipeline options"
    )


def test_scanned_pdf_ocr_enabled(tmp_path):
    """POST /process with ocr_enabled=True uses the OCR converter (converter_ocr).

    Verifies that when ocr_enabled=True, the app selects converter_ocr over
    converter_text, ensuring scanned PDFs go through the EasyOCR pipeline.
    """
    import main as docproc_main
    from fastapi.testclient import TestClient

    pdf_file = tmp_path / "scanned.pdf"
    pdf_file.write_bytes(b"%PDF-1.4 scanned mock")

    elem = _make_text_element("OCR extracted text.", page_no=1)
    mock_result = _make_mock_convert_result(elem)

    # Patch easyocr.Reader to skip model download during lifespan
    mock_reader_cls = MagicMock()
    mock_reader_cls.return_value = MagicMock()

    with patch.object(docproc_main, "easyocr") as mock_easyocr_mod:
        mock_easyocr_mod.Reader = mock_reader_cls

        with TestClient(docproc_main.app, raise_server_exceptions=True) as client:
            # After lifespan runs, replace converters with controlled mocks
            mock_ocr_converter = MagicMock()
            mock_text_converter = MagicMock()
            mock_ocr_converter.convert.return_value = mock_result

            docproc_main.app.state.converter_ocr = mock_ocr_converter
            docproc_main.app.state.converter_text = mock_text_converter

            response = client.post(
                "/process",
                json={"file_path": str(pdf_file), "ocr_enabled": True},
            )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"

    # The OCR converter should have been called, not the text converter
    mock_ocr_converter.convert.assert_called_once_with(str(pdf_file))
    mock_text_converter.convert.assert_not_called()


def test_ocr_disabled_uses_text_converter(tmp_path):
    """POST /process with ocr_enabled=False routes to the text-only converter (converter_text).

    Verifies that digital-native PDFs skip the EasyOCR pipeline entirely,
    avoiding unnecessary GPU workload on documents that don't need OCR.
    """
    import main as docproc_main
    from fastapi.testclient import TestClient

    pdf_file = tmp_path / "digital.pdf"
    pdf_file.write_bytes(b"%PDF-1.4 digital native content")

    elem = _make_text_element("Digital native text.", page_no=1)
    mock_result = _make_mock_convert_result(elem)

    mock_reader_cls = MagicMock()
    mock_reader_cls.return_value = MagicMock()

    with patch.object(docproc_main, "easyocr") as mock_easyocr_mod:
        mock_easyocr_mod.Reader = mock_reader_cls

        with TestClient(docproc_main.app, raise_server_exceptions=True) as client:
            mock_ocr_converter = MagicMock()
            mock_text_converter = MagicMock()
            mock_text_converter.convert.return_value = mock_result

            docproc_main.app.state.converter_ocr = mock_ocr_converter
            docproc_main.app.state.converter_text = mock_text_converter

            response = client.post(
                "/process",
                json={"file_path": str(pdf_file), "ocr_enabled": False},
            )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"

    # Text converter should have been called — NOT the OCR converter
    mock_text_converter.convert.assert_called_once_with(str(pdf_file))
    mock_ocr_converter.convert.assert_not_called()

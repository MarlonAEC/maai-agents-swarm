"""
Stub tests for DOCP-02 (OCR via PaddleOCR backend in Docling).

These stubs will be filled in by Plan 01 (docproc service implementation).
"""

import pytest


@pytest.mark.xfail(reason="stub — implementation in Plan 01 (docproc service)")
def test_scanned_pdf_ocr_enabled():
    """Docling uses PaddleOCR for scanned PDFs when ocr_enabled=True."""
    assert False


@pytest.mark.xfail(reason="stub — implementation in Plan 01 (docproc service)")
def test_easyocr_options_configured():
    """OCR pipeline options are configured correctly in the docproc service."""
    assert False

"""Stub tests for DOCP-02 — OCR processing via EasyOCR backend in Docling.

Covers:
  - Scanned PDFs route through Docling with OCR enabled
  - EasyOCR pipeline options are configured correctly in docproc service

These stubs will be filled in by Plan 01 (docproc service implementation).
"""
import pytest


@pytest.mark.xfail(reason="stub — implementation in Plan 01")
def test_scanned_pdf_ocr_enabled():
    """Docling processes a scanned PDF with do_ocr=True, returning extracted text."""
    assert False


@pytest.mark.xfail(reason="stub — implementation in Plan 01")
def test_easyocr_options_configured():
    """PipelineOptions are configured with EasyOCR as the OCR backend."""
    assert False

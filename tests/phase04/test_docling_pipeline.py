"""
Stub tests for DOCP-01 (Docling text extraction).

These stubs will be filled in by Plan 01 (docproc service implementation).
"""

import pytest


@pytest.mark.xfail(reason="stub — implementation in Plan 01 (docproc service)")
def test_text_pdf_extraction():
    """Docling extracts text from a text-based PDF without OCR."""
    assert False


@pytest.mark.xfail(reason="stub — implementation in Plan 01 (docproc service)")
def test_process_endpoint_returns_pages():
    """POST /process returns pages list with page_no and text fields."""
    assert False

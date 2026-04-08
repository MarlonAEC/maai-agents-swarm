"""Stub tests for DOCP-01 — Docling text extraction pipeline.

Covers:
  - Text PDF extraction via Docling DocumentConverter
  - /process endpoint returns structured pages payload

These stubs will be filled in by Plan 01 (docproc service implementation).
"""
import pytest


@pytest.mark.xfail(reason="stub — implementation in Plan 01")
def test_text_pdf_extraction():
    """Docling extracts text pages from a text-based PDF without OCR."""
    assert False


@pytest.mark.xfail(reason="stub — implementation in Plan 01")
def test_process_endpoint_returns_pages():
    """POST /process returns a JSON list of page dicts with text and page_no fields."""
    assert False

"""Phase 4 test fixtures — document ingestion and RAG."""

import os
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

# Add src/core_api and src/docproc to sys.path for imports
CORE_API_DIR = str(Path(__file__).resolve().parent.parent.parent / "src" / "core_api")
DOCPROC_DIR = str(Path(__file__).resolve().parent.parent.parent / "src" / "docproc")
if CORE_API_DIR not in sys.path:
    sys.path.insert(0, CORE_API_DIR)
if DOCPROC_DIR not in sys.path:
    sys.path.insert(0, DOCPROC_DIR)

# Stub heavy dependencies that may not be installed in test env
# (same pattern as tests/conftest.py from Phase 3)
for mod_name in [
    "docling",
    "docling.document_converter",
    "docling.datamodel.pipeline_options",
    "docling.datamodel.base_models",
    "easyocr",
    "llama_index",
    "llama_index.core",
    "llama_index.core.node_parser",
    "llama_index.embeddings.ollama",
    "llama_index.vector_stores.qdrant",
    "qdrant_client",
    "arq",
    "arq.connections",
    "arq.jobs",
    "redis",
    "redis.asyncio",
]:
    if mod_name not in sys.modules:
        sys.modules[mod_name] = MagicMock()


@pytest.fixture
def sample_pages():
    """Sample docproc response pages for testing."""
    return [
        {"page_no": 1, "text": "This is page one content.", "has_ocr": False},
        {"page_no": 2, "text": "This is page two with OCR text.", "has_ocr": True},
    ]


@pytest.fixture
def test_client_id():
    """Test client ID for per-client isolation tests."""
    return "test_client_01"


@pytest.fixture
def sample_file_name():
    """Sample file name for ingestion tests."""
    return "test_document.pdf"

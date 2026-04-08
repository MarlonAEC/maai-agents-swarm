"""Phase 4 test fixtures.

Sets up the Python path and injects stubs for heavy ML dependencies
(docling, easyocr, opencv) that are not installed in the test environment.
This allows the docproc module to be imported and tested without the full
Docling + EasyOCR installation.
"""

import os
import sys
import types

import pytest

# ---------------------------------------------------------------------------
# Path setup
# ---------------------------------------------------------------------------

_DOCPROC_DIR = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "..", "src", "docproc")
)
if _DOCPROC_DIR not in sys.path:
    sys.path.insert(0, _DOCPROC_DIR)

PROJECT_ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))


# ---------------------------------------------------------------------------
# Docling stubs — injected when docling is not installed
# ---------------------------------------------------------------------------


def _inject_docling_stubs() -> None:
    """Inject minimal docling stubs into sys.modules.

    Provides just enough surface area for docproc main.py to be imported
    and tested without the full Docling + EasyOCR installation.
    """

    # --- docling.datamodel.base_models ---
    class InputFormat:
        PDF = "pdf"

    base_models_mod = types.ModuleType("docling.datamodel.base_models")
    base_models_mod.InputFormat = InputFormat  # type: ignore[attr-defined]

    # --- docling.datamodel.pipeline_options ---
    class EasyOcrOptions:
        def __init__(self, lang=None, use_gpu=False, force_full_page_ocr=False):
            self.lang = lang or ["en"]
            self.use_gpu = use_gpu
            self.force_full_page_ocr = force_full_page_ocr

    class PdfPipelineOptions:
        def __init__(self, do_ocr=False, do_table_structure=False, ocr_options=None):
            self.do_ocr = do_ocr
            self.do_table_structure = do_table_structure
            self.ocr_options = ocr_options

    pipeline_options_mod = types.ModuleType("docling.datamodel.pipeline_options")
    pipeline_options_mod.EasyOcrOptions = EasyOcrOptions  # type: ignore[attr-defined]
    pipeline_options_mod.PdfPipelineOptions = PdfPipelineOptions  # type: ignore[attr-defined]

    # --- docling.document_converter ---
    class PdfFormatOption:
        def __init__(self, pipeline_options=None):
            self.pipeline_options = pipeline_options

    class ConversionResult:
        def __init__(self, document):
            self.document = document

    class DocumentConverter:
        def __init__(self, format_options=None):
            self.format_options = format_options

        def convert(self, file_path: str) -> ConversionResult:
            """Default stub — returns empty document. Override in tests."""
            doc = types.SimpleNamespace(iterate_items=lambda: [])
            return ConversionResult(document=doc)

    doc_converter_mod = types.ModuleType("docling.document_converter")
    doc_converter_mod.DocumentConverter = DocumentConverter  # type: ignore[attr-defined]
    doc_converter_mod.PdfFormatOption = PdfFormatOption  # type: ignore[attr-defined]
    doc_converter_mod.ConversionResult = ConversionResult  # type: ignore[attr-defined]

    # --- docling.datamodel ---
    datamodel_mod = types.ModuleType("docling.datamodel")
    datamodel_mod.base_models = base_models_mod  # type: ignore[attr-defined]
    datamodel_mod.pipeline_options = pipeline_options_mod  # type: ignore[attr-defined]

    # --- docling (top-level) ---
    docling_mod = types.ModuleType("docling")
    docling_mod.datamodel = datamodel_mod  # type: ignore[attr-defined]
    docling_mod.document_converter = doc_converter_mod  # type: ignore[attr-defined]

    sys.modules.setdefault("docling", docling_mod)
    sys.modules.setdefault("docling.datamodel", datamodel_mod)
    sys.modules.setdefault("docling.datamodel.base_models", base_models_mod)
    sys.modules.setdefault("docling.datamodel.pipeline_options", pipeline_options_mod)
    sys.modules.setdefault("docling.document_converter", doc_converter_mod)


def _inject_easyocr_stub() -> None:
    """Inject a minimal easyocr stub."""

    class Reader:
        def __init__(self, lang_list=None, gpu=False):
            self.lang_list = lang_list or ["en"]
            self.gpu = gpu

        def readtext(self, image):
            return []

    easyocr_mod = types.ModuleType("easyocr")
    easyocr_mod.Reader = Reader  # type: ignore[attr-defined]
    sys.modules.setdefault("easyocr", easyocr_mod)


def _inject_cv2_stub() -> None:
    """Inject a minimal cv2 stub for opencv-python-headless."""
    cv2_mod = types.ModuleType("cv2")
    sys.modules.setdefault("cv2", cv2_mod)


# Inject stubs before any docproc imports
_inject_docling_stubs()
_inject_easyocr_stub()
_inject_cv2_stub()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def project_root() -> str:
    return PROJECT_ROOT

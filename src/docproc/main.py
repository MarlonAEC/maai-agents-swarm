"""
MAAI Docproc Service — FastAPI application entrypoint.

Exposes:
  GET  /health   — liveness probe
  POST /process  — document processing via Docling + EasyOCR

Lifespan:
  1. Create two DocumentConverter instances (OCR and text-only)
  2. Pre-warm EasyOCR models by instantiating Reader to trigger model download

NOTE on DOCP-02: Using EasyOCR (not PaddleOCR) per RESEARCH.md finding that
PaddleOCR is not a native Docling OCR backend. EasyOCR is the practical
equivalent within Docling's OCR backend framework.
"""

import os
from contextlib import asynccontextmanager
from pathlib import Path

import easyocr
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import EasyOcrOptions, PdfPipelineOptions
from docling.document_converter import DocumentConverter, PdfFormatOption
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from logging_config import get_logger

# Load environment variables from .env / client.env before anything else.
load_dotenv()

logger = get_logger(__name__)

# Supported file extensions for document processing
SUPPORTED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg", ".tiff", ".bmp"}


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------


class ProcessRequest(BaseModel):
    """Request body for POST /process."""

    file_path: str
    ocr_enabled: bool = True


class PageResult(BaseModel):
    """Text content and metadata for a single document page."""

    page_no: int
    text: str
    has_ocr: bool


class ProcessResponse(BaseModel):
    """Response from POST /process on success."""

    status: str
    file_name: str
    pages: list[PageResult]
    full_text: str
    total_pages: int


# ---------------------------------------------------------------------------
# Application lifespan — initialise converters and pre-warm EasyOCR models
# ---------------------------------------------------------------------------


@asynccontextmanager
async def lifespan(app: FastAPI):  # type: ignore[type-arg]
    use_gpu_env = os.getenv("DOCPROC_USE_GPU", "false").lower()
    use_gpu = use_gpu_env in ("1", "true", "yes")

    logger.info("Initialising Docling converters (use_gpu=%s)", use_gpu)

    # OCR-enabled converter — uses EasyOCR backend (satisfies DOCP-02 per RESEARCH.md)
    ocr_options = EasyOcrOptions(lang=["en"], use_gpu=use_gpu, force_full_page_ocr=True)
    pdf_pipeline_options_ocr = PdfPipelineOptions(
        do_ocr=True,
        do_table_structure=True,
        ocr_options=ocr_options,
    )
    converter_ocr = DocumentConverter(
        format_options={
            InputFormat.PDF: PdfFormatOption(pipeline_options=pdf_pipeline_options_ocr),
        }
    )

    # Text-only converter — no OCR overhead for digital-native PDFs
    converter_text = DocumentConverter()

    app.state.converter_ocr = converter_ocr
    app.state.converter_text = converter_text

    # Pre-warm EasyOCR model download so the first request is not slow.
    # (Research Pitfall 4 — model download happens on first Reader instantiation.)
    try:
        easyocr.Reader(["en"], gpu=use_gpu)
        logger.info("EasyOCR models pre-loaded")
    except Exception as exc:  # noqa: BLE001
        logger.warning("EasyOCR pre-warm failed (non-fatal): %s", exc)

    logger.info("Docproc service started")
    yield
    logger.info("Docproc service shutting down")


# ---------------------------------------------------------------------------
# FastAPI application
# ---------------------------------------------------------------------------

app = FastAPI(
    title="MAAI Docproc Service",
    description="Document processing sidecar — Docling + EasyOCR",
    version="0.1.0",
    lifespan=lifespan,
)


@app.get("/health", tags=["ops"])
async def health() -> dict:
    """Liveness probe — returns 200 OK when the service is ready."""
    return {"status": "ok"}


@app.post("/process", tags=["processing"])
async def process_document(request: ProcessRequest) -> JSONResponse:
    """Process a document file and return extracted text with page-level metadata.

    Accepts a path on the shared maai-uploads volume, processes it through
    Docling (text extraction) with optional EasyOCR (for scanned pages), and
    returns structured text with page metadata.

    Returns:
        ProcessResponse on success.
        HTTP 404 if the file does not exist.
        HTTP 400 if the file extension is not supported.
        HTTP 500 if processing fails.
    """
    file_path = Path(request.file_path)

    # Validate file exists
    if not file_path.exists():
        return JSONResponse(
            status_code=404,
            content={"status": "error", "detail": f"File not found: {request.file_path}"},
        )

    # Validate file extension
    ext = file_path.suffix.lower()
    if ext not in SUPPORTED_EXTENSIONS:
        return JSONResponse(
            status_code=400,
            content={
                "status": "error",
                "detail": (
                    f"Unsupported file type '{ext}'. "
                    f"Supported: {sorted(SUPPORTED_EXTENSIONS)}"
                ),
            },
        )

    logger.info(
        "Processing file: %s (ocr_enabled=%s)", file_path.name, request.ocr_enabled
    )

    try:
        # Choose converter based on OCR flag
        converter = (
            app.state.converter_ocr if request.ocr_enabled else app.state.converter_text
        )

        result = converter.convert(str(file_path))
        doc = result.document

        # Collect text per page by iterating document items
        pages_text: dict[int, list[str]] = {}
        pages_has_ocr: dict[int, bool] = {}

        for element, _level in doc.iterate_items():
            text = getattr(element, "text", None)
            if not text:
                continue

            # Extract page number from provenance; default to page 1 if unavailable
            page_no: int = 1
            prov = getattr(element, "prov", None)
            if prov and len(prov) > 0:
                page_no = getattr(prov[0], "page_no", 1) or 1

            pages_text.setdefault(page_no, []).append(text)
            # Mark page as OCR-processed if ocr_enabled was requested
            pages_has_ocr[page_no] = request.ocr_enabled

        # Build ordered list of PageResult objects
        page_results: list[PageResult] = []
        for page_no in sorted(pages_text.keys()):
            page_text = "\n".join(pages_text[page_no])
            page_results.append(
                PageResult(
                    page_no=page_no,
                    text=page_text,
                    has_ocr=pages_has_ocr.get(page_no, False),
                )
            )

        full_text = "\n\n".join(p.text for p in page_results)

        response = ProcessResponse(
            status="success",
            file_name=file_path.name,
            pages=page_results,
            full_text=full_text,
            total_pages=len(page_results),
        )

        logger.info(
            "Processed %s: %d pages extracted", file_path.name, len(page_results)
        )
        return JSONResponse(content=response.model_dump())

    except Exception as exc:  # noqa: BLE001
        logger.exception("Failed to process %s: %s", file_path.name, exc)
        return JSONResponse(
            status_code=500,
            content={"status": "error", "detail": str(exc)},
        )

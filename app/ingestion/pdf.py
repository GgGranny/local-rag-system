import os
import re
import logging

import numpy as np

from PIL import Image

os.environ["FLAGS_use_onednn"] = "0"
os.environ["FLAGS_enable_pir_api"] = "0"
os.environ["PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK"] = "True"

from pathlib import Path

import fitz

logger = logging.getLogger(__name__)

_ocr_engine = None


def get_ocr_engine():
    """
    Create the OCR engine only once.

    PaddleOCR initialization is expensive, so we reuse
    the same instance for subsequent pages/documents.
    """
    global _ocr_engine
    if _ocr_engine is None:
        # Importing PaddleOCR is expensive; normal application startup should
        # not pay that cost unless a scanned PDF needs OCR.
        from paddleocr import PaddleOCR

        logger.info("[OCR] Initializing PaddleOCR...")
        _ocr_engine = PaddleOCR(
            lang="en",
            enable_mkldnn=False
        )
        logger.info("[OCR] PaddleOCR initialized.")

    return _ocr_engine


def needs_ocr(native_text: str) -> bool:
    """
    Determine whether OCR is needed for extracted native text.

    OCR is required when the native text is:
    - Empty or whitespace-only
    - Very short (likely incomplete)
    - Mostly repeated whitespace (layout artifact)
    - Contains a high proportion of non-readable characters
    - Suspiciously short relative to what might be on the page

    Returns True if OCR should be attempted, False otherwise.
    """
    if not native_text or not native_text.strip():
        return True

    stripped = native_text.strip()

    # Check for very short text (likely insufficient)
    if len(stripped) < 30:
        return True

    # Check for pages consisting mostly of repeated whitespace/line patterns
    # e.g., many lines with only a few characters each
    lines = stripped.split("\n")
    if len(lines) > 0:
        non_empty_lines = [l for l in lines if l.strip()]
        if len(non_empty_lines) > 0 and len(stripped) / len(non_empty_lines) < 3:
            # Very few characters per non-empty line: likely layout artifact
            return True

    # Check for high proportion of non-printable or suspicious characters
    # (control characters, excessive special symbols)
    non_printable = sum(1 for c in native_text if ord(c) < 32 and c not in "\n\r\t")
    if len(native_text) > 0 and non_printable / len(native_text) > 0.3:
        return True

    return False


def parse_ocr_result(result) -> str:
    """
    Extract recognized text from a PaddleOCR 3.7.0 result.

    The installed PaddleOCR version returns a list of dict-like objects
    (OCRResult). Each item has a ``rec_texts`` key at the top level
    (accessible via ``.json`` dict or direct dict access).

    Returns a clean string (possibly empty) containing the concatenated
    recognized text from all result items.
    """
    if result is None:
        return ""

    if isinstance(result, list):
        all_texts = []
        for item in result:
            if item is None:
                continue
            # PaddleOCR 3.7.0 items are dict-like with .json attribute
            # and also support direct dict access.
            try:
                data = item.json if hasattr(item, "json") else item
            except Exception:
                continue

            if not isinstance(data, dict):
                continue

            # rec_texts is at the top level in PaddleOCR 3.7.0
            rec_texts = data.get("rec_texts", [])
            if not isinstance(rec_texts, list):
                continue

            for text in rec_texts:
                try:
                    text = str(text).strip()
                    if text:
                        all_texts.append(text)
                except Exception:
                    continue

        return "\n".join(all_texts)

    # Fallback: try direct dict access
    if isinstance(result, dict):
        rec_texts = result.get("rec_texts", [])
        if isinstance(rec_texts, list):
            all_texts = []
            for text in rec_texts:
                try:
                    text = str(text).strip()
                    if text:
                        all_texts.append(text)
                except Exception:
                    continue
            return "\n".join(all_texts)

    return ""


def extract_page_with_ocr(
    page,
    page_number: int,
    filename: str = ""
) -> dict:
    """
    Render a PDF page as an image and run PaddleOCR.

    Returns a dict with keys:
        - text: extracted text string (may be empty if OCR fails)
        - extraction_method: "ocr" or "native+ocr"
    """
    logger.info(f"[OCR] Processing page {page_number} of {filename}...")

    try:
        pixmap = page.get_pixmap(
            matrix=fitz.Matrix(2, 2),
            alpha=False
        )
        # PaddleOCR 3.7.0 accepts numpy.ndarray or file path (str).
        # Render as numpy array for best compatibility.
        image_array = numpy_image_from_pixmap(pixmap)

        ocr = get_ocr_engine()
        result = ocr.predict(image_array)

        ocr_text = parse_ocr_result(result)

        logger.info(
            f"[OCR] Page {page_number}: "
            f"OCR extracted {len(ocr_text)} characters"
        )

        return {
            "page_number": page_number,
            "text": ocr_text,
            "extraction_method": "ocr",
        }

    except Exception as exc:
        logger.error(
            f"[OCR] Failed on page {page_number} of {filename}: {exc}"
        )
        return {
            "page_number": page_number,
            "text": "",
            "extraction_method": "failed",
        }


def numpy_image_from_pixmap(pixmap) -> np.ndarray:
    """
    Convert a PyMuPDF pixmap to a numpy array suitable for PaddleOCR.

    PaddleOCR 3.7.0 supports numpy.ndarray input directly.
    """
    try:
        # pixmap.tobytes() returns raw RGB bytes
        bytes_data = pixmap.tobytes("rgb")
        width = pixmap.width
        height = pixmap.height
        image_array = np.frombuffer(bytes_data, dtype=np.uint8)
        image_array = image_array.reshape(
            (height, width, 3)
        )
        return image_array
    except Exception as exc:
        logger.error(
            f"[OCR] Failed to convert pixmap to numpy array: {exc}"
        )
        return np.array([])


def extract_page_images(pdf, page, page_number: int) -> list[dict]:
    """Extract browser-safe embedded visuals and retain page placement data."""
    images = []
    seen_xrefs = set()
    for image_index, image_info in enumerate(page.get_images(full=True)):
        xref = image_info[0]
        if xref in seen_xrefs:
            continue
        seen_xrefs.add(xref)
        try:
            extracted = pdf.extract_image(xref)
            extension = extracted.get("ext", "png").lower()
            image_data = extracted["image"]
            if extension not in {"png", "jpg", "jpeg", "gif", "webp"}:
                pixmap = fitz.Pixmap(pdf, xref)
                image_data = pixmap.tobytes("png")
                extension = "png"
            rects = page.get_image_rects(xref)
            images.append({
                "data": image_data,
                "extension": extension,
                "page_number": page_number,
                "image_index": image_index,
                # A normalized coordinate remains meaningful in the source
                # viewer without exposing PDF page geometry to the browser.
                "vertical_position": (
                    float(rects[0].y0 / page.rect.height)
                    if rects and page.rect.height
                    else None
                ),
                "source_kind": "embedded",
            })
        except Exception as exc:
            logger.warning("[PDF] Could not extract image on page %s: %s", page_number, exc)
    return images


def extract_pdf_pages(
    file_path: str,
    min_text_length: int = 30
) -> list[dict]:
    """
    Extract a PDF page-by-page.

    Strategy:
    1. Try PyMuPDF native text extraction.
    2. If the text is suspiciously short OR fails quality checks, use PaddleOCR.
    3. Return page-level metadata with extraction method.

    Each returned dict contains:
        - page_number: page number (1-indexed)
        - text: extracted text content
        - extraction_method: "pymupdf", "ocr", "native+ocr", or "failed"
    """
    pages = []
    pdf = fitz.open(file_path)
    try:
        for page_number, page in enumerate(
            pdf,
            start=1
        ):
            native_text = page.get_text(
                "text"
            ).strip()

            logger.info(
                f"[PDF] Page {page_number}: "
                f"native text length={len(native_text)}"
            )

            if needs_ocr(native_text):
                # Use OCR for this page
                logger.info(
                    f"[PDF] Page {page_number}: "
                    f"insufficient/native text, trying OCR"
                )

                # Use filename only if available (fallback to basename)
                import os as os_path
                display_filename = (
                    os_path.path.basename(file_path)
                    if file_path
                    else "unknown.pdf"
                )

                ocr_result = extract_page_with_ocr(
                    page,
                    page_number,
                    display_filename
                )

                pages.append({
                    "page_number": ocr_result["page_number"],
                    "text": ocr_result["text"],
                    "extraction_method": ocr_result["extraction_method"],
                    # Keep the rendered source page beside OCR text.  The UI
                    # can show it, but must not pretend to pixel-highlight it.
                    "images": [{
                        "data": page.get_pixmap(
                            matrix=fitz.Matrix(1.5, 1.5), alpha=False
                        ).tobytes("png"),
                        "extension": "png",
                        "page_number": page_number,
                        "image_index": 0,
                        "vertical_position": 0.0,
                        "source_kind": "ocr_page",
                    }],
                })

                if not ocr_result["text"].strip():
                    logger.warning(
                        f"[PDF] Page {page_number}: "
                        f"OCR returned no text, marking as failed"
                    )
            else:
                # Use native PyMuPDF extraction
                pages.append({
                    "page_number": page_number,
                    "text": native_text,
                    "extraction_method": "pymupdf",
                    "images": extract_page_images(pdf, page, page_number),
                })

                logger.info(
                    f"[PDF] Page {page_number}: "
                    f"PyMuPDF native extraction"
                )

    finally:
        pdf.close()

    return pages

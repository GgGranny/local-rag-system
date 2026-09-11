import os

os.environ["FLAGS_use_onednn"] = "0"
os.environ["FLAGS_enable_pir_api"] = "0"
os.environ["PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK"] = "True"

from pathlib import Path

import fitz


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

        print("[OCR] Initializing PaddleOCR...")
        _ocr_engine = PaddleOCR(
            lang="en",
            enable_mkldnn=False
        )
        print("[OCR] PaddleOCR initialized.")

    return _ocr_engine


def extract_page_with_ocr(
    page,
    page_number: int
) -> str:
    """
    Render a PDF page as an image and run PaddleOCR.
    """
    print(
        f"[OCR] Processing page {page_number}..."
    )
    pixmap = page.get_pixmap(
        matrix=fitz.Matrix(2, 2),
        alpha=False
    )
    image_bytes = pixmap.tobytes(
        "png"
    )
    ocr = get_ocr_engine()
    result = ocr.predict(
        image_bytes
    )

    texts = []
    for item in result:
        if not hasattr(item, "json"):
            continue
        data = item.json
        if isinstance(data, str):
            continue
        if "res" not in data:
            continue
        res = data["res"]
        rec_texts = res.get(
            "rec_texts",
            []
        )

        for text in rec_texts:
            text = str(text).strip()
            if text:
                texts.append(text)
    return "\n".join(texts)


def extract_pdf_pages(
    file_path: str,
    min_text_length: int = 30
) -> list[dict]:
    """
    Extract a PDF page-by-page.

    Strategy:
    1. Try PyMuPDF native text extraction.
    2. If the text is suspiciously short, use PaddleOCR.
    3. Return page-level metadata.
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
            if len(native_text) >= min_text_length:
                pages.append({
                    "page_number": page_number,
                    "text": native_text,
                    "extraction_method": "pymupdf",
                })

                print(
                    f"[PDF] Page {page_number}: "
                    f"PyMuPDF"
                )
                continue

            print(
                f"[PDF] Page {page_number}: "
                f"insufficient native text, "
                f"trying OCR"
            )

            ocr_text = extract_page_with_ocr(
                page,
                page_number
            )

            pages.append({
                "page_number": page_number,
                "text": ocr_text,
                "extraction_method": "paddleocr",
            })

    finally:
        pdf.close()

    return pages

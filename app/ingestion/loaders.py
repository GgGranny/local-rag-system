from pathlib import Path
import csv

import fitz
from docx import Document as DocxDocument
from app.ingestion.pdf import extract_pdf_pages


def load_txt(file_path: str) -> str:
    """
    Extract text from a TXT file.
    """
    path = Path(file_path)
    return path.read_text(
        encoding="utf-8",
        errors="ignore"
    )


def load_csv(file_path: str) -> str:
    """
    Extract CSV data and convert it into
    readable text for later RAG processing.
    """
    rows = []
    with open(
        file_path,
        "r",
        encoding="utf-8",
        errors="ignore",
        newline=""
    ) as file:
        reader = csv.reader(file)
        for row in reader:
            rows.append(" | ".join(row))

    return "\n".join(rows)


def load_docx(file_path: str) -> str:
    """
    Extract paragraphs from a DOCX file.
    """
    document = DocxDocument(file_path)
    paragraphs = []
    for paragraph in document.paragraphs:
        text = paragraph.text.strip()
        if text:
            paragraphs.append(text)
    return "\n".join(paragraphs)


def load_pdf(file_path: str) -> list[dict]:
    """
    Extract PDF content page-by-page.
    """

    return extract_pdf_pages(file_path)

def extract_text(file_path: str):
    """
    Select the appropriate loader based on
    the file extension.
    """
    extension = Path(
        file_path
    ).suffix.lower()

    if extension == ".txt":
        return load_txt(file_path)

    if extension == ".csv":
        return load_csv(file_path)

    if extension == ".docx":
        return load_docx(file_path)

    if extension == ".pdf":
        return load_pdf(file_path)

    raise ValueError(
        f"Unsupported file type: {extension}"
    )
    """
    Select the appropriate loader based on
    the file extension.
    """
    extension = Path(
        file_path
    ).suffix.lower()

    if extension == ".txt":
        return load_txt(file_path)

    if extension == ".csv":
        return load_csv(file_path)

    if extension == ".docx":
        return load_docx(file_path)

    if extension == ".pdf":
        return load_pdf(file_path)

    raise ValueError(
        f"Unsupported file type: {extension}"
    )
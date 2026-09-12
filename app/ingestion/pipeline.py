import uuid
from pathlib import Path

from app.config import Config
from app.extensions import db

from app.models import (
    Document,
    DocumentChunk,
    DocumentImage,
    DocumentSourcePage,
)

from app.ingestion.loaders import extract_text

from app.ingestion.chunking import (
    create_documents,
    chunk_documents,
)


IMAGE_MIME_TYPES = {
    "png": "image/png",
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "gif": "image/gif",
    "webp": "image/webp",
}


def replace_document_images(document: Document, pages: list[dict]) -> None:
    """Persist extracted source visuals without exposing their filesystem path."""
    image_directory = Path(Config.SOURCE_IMAGE_FOLDER)
    image_directory.mkdir(parents=True, exist_ok=True)

    for existing in DocumentImage.query.filter_by(document_id=document.id).all():
        asset_path = image_directory / existing.stored_filename
        if asset_path.is_file():
            asset_path.unlink()
        db.session.delete(existing)

    image_count = 0
    for page in pages:
        for image in page.get("images", []):
            data = image.get("data")
            extension = str(image.get("extension", "png")).lower()
            if not data or extension not in IMAGE_MIME_TYPES:
                continue
            stored_filename = f"{document.id}_{uuid.uuid4().hex}.{extension}"
            (image_directory / stored_filename).write_bytes(data)
            db.session.add(DocumentImage(
                document_id=document.id,
                image_id=f"source_image_{uuid.uuid4().hex}",
                stored_filename=stored_filename,
                mime_type=IMAGE_MIME_TYPES[extension],
                page_number=image.get("page_number"),
                image_index=image.get("image_index", image_count),
                vertical_position=image.get("vertical_position"),
                source_kind=image.get("source_kind", "embedded"),
            ))
            image_count += 1

    print(f"[INGESTION] Preserved {image_count} source images.")


def replace_document_source_pages(document: Document, pages: list[dict]) -> None:
    """Store unchunked page text for a readable, continuous source view."""
    DocumentSourcePage.query.filter_by(document_id=document.id).delete(
        synchronize_session=False
    )
    for page in pages:
        db.session.add(DocumentSourcePage(
            document_id=document.id,
            page_number=page.get("page_number", 1),
            content=page.get("text", ""),
            extraction_method=page.get("extraction_method", "native"),
        ))

from app.retrieval.vector_store import (
    index_chunks,
    delete_document_chunks,
)

from app.retrieval.bm25_store import (
    rebuild_bm25_index,
)


def process_document(document_id: int):

    document = db.session.get(
        Document,
        document_id
    )

    if not document:

        raise ValueError(
            f"Document {document_id} not found."
        )

    if document.status not in {
        "APPROVED",
        "PROCESSING",
    }:

        raise ValueError(
            "Document cannot be processed "
            f"from status: {document.status}"
        )

    try:

        document.status = "PROCESSING"

        db.session.commit()

        print(
            f"[INGESTION] Processing: "
            f"{document.filename}"
        )

        # --------------------------------------------------
        # EXTRACTION
        # --------------------------------------------------

        print(
            f"[INGESTION] Extracting: "
            f"{document.filename}"
        )

        extracted_content = extract_text(
            document.file_path
        )

        if document.file_type == "pdf":

            pages = extracted_content

        else:

            pages = [
                {
                    "page_number": 1,
                    "text": extracted_content,
                    "extraction_method": "native",
                }
            ]

        print(
            f"[INGESTION] Extracted "
            f"{len(pages)} content units."
        )

        # Preserve visuals from every page, even when a chart/figure-only
        # page has no retrievable text.  Textless pages are excluded only
        # from chunk creation below.
        source_pages = pages

        # Remove empty pages/content from the retrieval pipeline.
        pages = [
            page
            for page in pages
            if page.get(
                "text",
                ""
            ).strip()
        ]

        if not pages:

            raise ValueError(
                "No readable text was extracted "
                "from the document."
            )

        replace_document_images(document, source_pages)
        replace_document_source_pages(document, source_pages)

        # --------------------------------------------------
        # CREATE PAGE DOCUMENTS
        # --------------------------------------------------

        documents = create_documents(
            extracted_pages=pages,
            document_id=document.id,
            filename=document.filename,

            # Retain uploader information for audit metadata. Retrieval access
            # is based on COMPLETED status, not uploader ownership.
            user_id=document.uploaded_by,
        )

        if not documents:

            raise ValueError(
                "No LangChain documents were created "
                "from extracted content."
            )

        print(
            f"[INGESTION] Created "
            f"{len(documents)} page documents."
        )

        # --------------------------------------------------
        # CHUNKING
        # --------------------------------------------------

        chunks = chunk_documents(
            documents,
            document_id=document.id,
        )

        if not chunks:

            raise ValueError(
                "No chunks were created."
            )

        print(
            f"[INGESTION] Created "
            f"{len(chunks)} chunks."
        )

        # --------------------------------------------------
        # REMOVE OLD DATABASE CHUNKS
        # --------------------------------------------------

        old_chunks = (
            DocumentChunk.query
            .filter_by(
                document_id=document.id
            )
            .all()
        )

        for old_chunk in old_chunks:

            db.session.delete(
                old_chunk
            )

        if old_chunks:

            db.session.flush()

            print(
                f"[INGESTION] Removed "
                f"{len(old_chunks)} old database chunks."
            )

        # --------------------------------------------------
        # SAVE NEW CHUNKS TO SQLITE
        # --------------------------------------------------

        for chunk in chunks:

            metadata = chunk.metadata

            db_chunk = DocumentChunk(

                document_id=document.id,

                chunk_id=metadata[
                    "chunk_id"
                ],

                content=chunk.page_content,

                page_number=metadata.get(
                    "page_number"
                ),

                chunk_index=metadata[
                    "chunk_index"
                ],

                extraction_method=metadata.get(
                    "extraction_method"
                ),

                content_type=metadata.get(
                    "content_type",
                    "chunk"
                ),
            )

            db.session.add(
                db_chunk
            )

        db.session.commit()

        print(
            f"[INGESTION] Saved "
            f"{len(chunks)} chunks to SQLite."
        )

        # --------------------------------------------------
        # REMOVE OLD CHROMA VECTORS
        # --------------------------------------------------

        delete_document_chunks(
            document.id
        )

        # --------------------------------------------------
        # INDEX NEW CHUNKS IN CHROMA
        # --------------------------------------------------

        print(
            f"[INGESTION] Indexing "
            f"{len(chunks)} chunks in Chroma."
        )

        index_chunks(
            chunks
        )

        print(
            "[INGESTION] Chroma indexing complete."
        )

        # --------------------------------------------------
        # MARK COMPLETED
        # --------------------------------------------------

        document.status = "COMPLETED"

        db.session.commit()

        print(
            f"[INGESTION] Document marked "
            f"COMPLETED: {document.filename}"
        )

        # --------------------------------------------------
        # REBUILD BM25
        # --------------------------------------------------

        print(
            "[INGESTION] Rebuilding BM25 index."
        )

        rebuild_bm25_index()

        print(
            "[INGESTION] BM25 rebuild complete."
        )

        print(
            f"[INGESTION] Completed: "
            f"{document.filename}"
        )

        return chunks

    except Exception as exc:

        print(
            f"[INGESTION] Failed: "
            f"{document_id}"
        )

        print(
            f"[INGESTION] Error: {exc}"
        )

        db.session.rollback()

        failed_document = db.session.get(
            Document,
            document_id
        )

        if failed_document:

            failed_document.status = "FAILED"

            db.session.commit()

        raise


def remove_document_index(document_id: int) -> None:
    """Remove all persisted retrieval data for a document and refresh BM25."""
    delete_document_chunks(document_id)
    DocumentChunk.query.filter_by(document_id=document_id).delete(
        synchronize_session=False
    )
    db.session.commit()
    rebuild_bm25_index()

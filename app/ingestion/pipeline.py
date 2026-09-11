from app.extensions import db

from app.models import (
    Document,
    DocumentChunk,
)

from app.ingestion.loaders import extract_text

from app.ingestion.chunking import (
    create_documents,
    chunk_documents,
)

from app.retrieval.vector_store import (
    index_chunks,
    delete_document_chunks,
)

from app.retrieval.bm25_store import (
    rebuild_bm25_index,
)


def process_document(document_id: int):
    """
    Process one approved document.

    Pipeline:

        APPROVED
            ↓
        PROCESSING
            ↓
        Extraction
            ↓
        LangChain Documents
            ↓
        Chunking
            ↓
        Save chunks to SQLite
            ↓
        Remove old Chroma vectors
            ↓
        Generate embeddings
            ↓
        Store vectors in Chroma
            ↓
        COMPLETED
            ↓
        Rebuild BM25

    If anything fails:

        PROCESSING
            ↓
        FAILED
    """

    # ==================================================
    # 1. Get document
    # ==================================================

    document = db.session.get(
        Document,
        document_id
    )

    if not document:
        raise ValueError(
            f"Document {document_id} not found."
        )

    # ==================================================
    # 2. Validate document status
    # ==================================================

    if document.status not in {
        "APPROVED",
        "PROCESSING",
    }:
        raise ValueError(
            "Document cannot be processed "
            f"from status: {document.status}"
        )

    try:

        # ==================================================
        # STEP 1: Mark document as PROCESSING
        # ==================================================

        document.status = "PROCESSING"

        db.session.commit()

        print(
            f"[INGESTION] Processing: "
            f"{document.filename}"
        )

        # ==================================================
        # STEP 2: Extract document content
        # ==================================================

        print(
            f"[INGESTION] Extracting: "
            f"{document.filename}"
        )

        extracted_content = extract_text(
            document.file_path
        )

        # ==================================================
        # STEP 3: Normalize extracted content
        # ==================================================
        #
        # PDF:
        #
        # [
        #     {
        #         "page_number": 1,
        #         "text": "...",
        #         "extraction_method": "pymupdf"
        #     },
        #     {
        #         "page_number": 2,
        #         "text": "...",
        #         "extraction_method": "paddleocr"
        #     }
        # ]
        #
        # TXT / CSV / DOCX:
        #
        # "entire extracted text..."
        #
        # We convert non-PDF files into the same
        # page-like structure.
        # ==================================================

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

        # ==================================================
        # STEP 4: Remove empty content
        # ==================================================

        pages = [
            page
            for page in pages
            if page.get("text", "").strip()
        ]

        if not pages:

            raise ValueError(
                "No readable text was extracted "
                "from the document."
            )

        # ==================================================
        # STEP 5: Convert to LangChain Documents
        # ==================================================

        documents = create_documents(
            extracted_pages=pages,
            document_id=document.id,
            filename=document.filename,
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

        # ==================================================
        # STEP 6: Chunk the documents
        # ==================================================

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

        # ==================================================
        # STEP 7: Remove old database chunks
        # ==================================================
        #
        # This is important when the same document
        # is processed again.
        #
        # Example:
        #
        # Previous:
        #     chunk_1
        #     chunk_2
        #     chunk_3
        #
        # New:
        #     chunk_1
        #     chunk_2
        #
        # Without deleting old chunks, chunk_3 would
        # remain in SQLite.
        # ==================================================

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

        # ==================================================
        # STEP 8: Save new chunks to SQLite
        # ==================================================

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

        # Save chunks before vector indexing.

        db.session.commit()

        print(
            f"[INGESTION] Saved "
            f"{len(chunks)} chunks to SQLite."
        )

        # ==================================================
        # STEP 9: Remove old Chroma vectors
        # ==================================================
        #
        # This prevents stale vectors from an older
        # version of the document from remaining
        # searchable.
        # ==================================================

        print(
            f"[INGESTION] Removing old vectors "
            f"for document {document.id}."
        )

        delete_document_chunks(
            document.id
        )

        # ==================================================
        # STEP 10: Generate embeddings + Chroma
        # ==================================================

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

        # ==================================================
        # STEP 11: Mark document as COMPLETED
        # ==================================================

        document.status = "COMPLETED"

        db.session.commit()

        print(
            f"[INGESTION] Document marked "
            f"COMPLETED: {document.filename}"
        )

        # ==================================================
        # STEP 12: Rebuild BM25
        # ==================================================
        #
        # BM25 only indexes chunks belonging to
        # COMPLETED documents.
        #
        # Therefore the document must be marked
        # COMPLETED before rebuilding BM25.
        # ==================================================

        print(
            "[INGESTION] Rebuilding BM25 index."
        )

        rebuild_bm25_index()

        print(
            "[INGESTION] BM25 rebuild complete."
        )

        # ==================================================
        # DONE
        # ==================================================

        print(
            f"[INGESTION] Completed: "
            f"{document.filename}"
        )

        return chunks

    except Exception as exc:

        # ==================================================
        # ERROR HANDLING
        # ==================================================

        print(
            f"[INGESTION] Failed: "
            f"{document_id}"
        )

        print(
            f"[INGESTION] Error: {exc}"
        )

        # --------------------------------------------------
        # Roll back any uncommitted database changes.
        # --------------------------------------------------

        db.session.rollback()

        # --------------------------------------------------
        # Retrieve document again after rollback.
        # --------------------------------------------------

        failed_document = db.session.get(
            Document,
            document_id
        )

        if failed_document:

            failed_document.status = "FAILED"

            db.session.commit()

        # --------------------------------------------------
        # Re-raise original exception.
        #
        # This allows the caller to see the actual
        # processing error.
        # --------------------------------------------------

        raise
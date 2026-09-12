import re

from rank_bm25 import BM25Okapi
from sqlalchemy.orm import joinedload

from app.models import (
    Document,
    DocumentChunk,
)


_bm25 = None
_chunks = []


def tokenize(text):

    return re.findall(
        r"\b\w+\b",
        text.lower()
    )


def _chunk_to_dict(chunk: DocumentChunk, document) -> dict:
    """
    Convert a DocumentChunk ORM object and its related Document
    into a plain dictionary safe for process-level caching.

    This prevents detached-ORMRelationship errors when the
    SQLAlchemy session closes and code later accesses chunk-level
    or document-level attributes.
    """
    return {
        "chunk_id": chunk.chunk_id,

        "document_id": chunk.document_id,

        "filename": document.filename if document else "Unknown",

        "content": chunk.content,

        "page_number": chunk.page_number,

        "chunk_index": chunk.chunk_index,

        "extraction_method": chunk.extraction_method,

        "content_type": chunk.content_type,

        "status": document.status if document else "FAILED",

        "user_id": document.uploaded_by if document else None,
    }


def build_bm25_index():

    global _bm25
    global _chunks

    print(
        "[BM25] Building index..."
    )

    query = (
        DocumentChunk.query
        .join(Document)
        .options(joinedload(DocumentChunk.document))
        .filter(
            Document.status == "COMPLETED"
        )
    )

    chunks_with_doc = query.all()

    if not chunks_with_doc:

        _bm25 = None

        print(
            "[BM25] No completed chunks found."
        )

        return

    # Convert ORM objects to plain dicts while the session is active.
    # This is the preferred boundary per AGENTS.md §24 so that
    # process-level caches never hold detached SQLAlchemy objects.
    _chunks = [
        _chunk_to_dict(chunk, chunk.document)
        for chunk in chunks_with_doc
    ]

    corpus = [
        tokenize(chunk_dict["content"])
        for chunk_dict in _chunks
    ]

    _bm25 = BM25Okapi(
        corpus
    )

    print(
        f"[BM25] Indexed "
        f"{len(_chunks)} chunks."
    )


def get_bm25_index():

    global _bm25

    if _bm25 is None:

        build_bm25_index()

    return _bm25


def search_bm25(
    query,
    k=5,
    user_id=None,
    is_admin=False,
    document_ids=None,
):
    """Search completed documents in the shared knowledge base."""

    global _chunks

    bm25 = get_bm25_index()

    if bm25 is None:

        return []

    query_tokens = tokenize(
        query
    )

    if not query_tokens:
        return []

    scores = bm25.get_scores(
        query_tokens
    )

    ranked_indices = sorted(
        range(len(scores)),
        key=lambda index: scores[index],
        reverse=True
    )

    results = []

    for index in ranked_indices:

        if len(results) >= k:
            break

        score = float(
            scores[index]
        )

        chunk_dict = _chunks[index]

        # BM25 scores can be negative for a very small corpus even when a
        # query token matches.  Score sign is not evidence of no match.
        # Check lexical overlap explicitly and retain the ranked match.
        if not set(query_tokens).intersection(tokenize(chunk_dict["content"])):
            continue

        # Use plain dict fields instead of ORM relationship
        # to avoid "not bound to a Session" errors when the
        # original SQLAlchemy session has closed.
        document_id = chunk_dict.get("document_id")
        document_status = chunk_dict.get("status")

        if not document_id:
            continue

        if document_status != "COMPLETED":
            continue

        if document_ids and document_id not in document_ids:
            continue

        # ----------------------------------------------
        # NORMALIZED RESULT
        # ----------------------------------------------

        results.append({
            "chunk_id": chunk_dict["chunk_id"],

            # Keep the same plain document shape used by the vector
            # serializer.  This must include the passage: a BM25-only hit
            # still needs to be usable as LLM context and a citation source.
            "document": {
                "page_content": chunk_dict["content"],
                "metadata": {
                    "document_id": document_id,
                    "status": document_status,
                    "filename": chunk_dict.get("filename", "Unknown"),
                    "page_number": chunk_dict.get("page_number"),
                    "chunk_index": chunk_dict.get("chunk_index"),
                    "extraction_method": chunk_dict.get("extraction_method"),
                    "content_type": chunk_dict.get("content_type"),
                    "user_id": chunk_dict.get("user_id"),
                },
            },

            "score": score,
        })

    return results


def rebuild_bm25_index():

    global _bm25
    global _chunks

    _bm25 = None
    _chunks = []

    build_bm25_index()

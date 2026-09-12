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


def build_bm25_index():

    global _bm25
    global _chunks

    print(
        "[BM25] Building index..."
    )

    query = (
        DocumentChunk.query
        .join(Document)
        # BM25 keeps chunks in a process-level cache after this session ends.
        # Load the parent document now so search_bm25 never triggers a lazy
        # relationship lookup on a detached DocumentChunk instance.
        .options(joinedload(DocumentChunk.document))
        .filter(
            Document.status == "COMPLETED"
        )
    )

    chunks = query.all()

    _chunks = chunks

    if not chunks:

        _bm25 = None

        print(
            "[BM25] No completed chunks found."
        )

        return

    corpus = [
        tokenize(chunk.content)
        for chunk in chunks
    ]

    _bm25 = BM25Okapi(
        corpus
    )

    print(
        f"[BM25] Indexed "
        f"{len(chunks)} chunks."
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

        if score <= 0:
            continue

        chunk = _chunks[index]

        document = chunk.document

        if not document:
            continue

        if document.status != "COMPLETED":
            continue

        if document_ids and document.id not in document_ids:
            continue

        # ----------------------------------------------
        # NORMALIZED RESULT
        # ----------------------------------------------

        results.append({
            "chunk_id": chunk.chunk_id,

            # Keep SQLAlchemy object internal.
            "document": chunk,

            "score": score,
        })

    return results


def rebuild_bm25_index():

    global _bm25
    global _chunks

    _bm25 = None
    _chunks = []

    build_bm25_index()

import re

from rank_bm25 import BM25Okapi

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
):
    """
    Search BM25 while enforcing document ownership.

    Normal user:
        COMPLETED + uploaded_by == user_id

    Admin:
        COMPLETED documents from all users.
    """

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

        # ----------------------------------------------
        # OWNERSHIP CHECK
        # ----------------------------------------------

        document = chunk.document

        if not document:
            continue

        if document.status != "COMPLETED":
            continue

        if not is_admin:

            if user_id is None:
                continue

            if document.uploaded_by != user_id:
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
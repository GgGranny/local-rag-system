import re
from rank_bm25 import BM25Okapi
from app.models import DocumentChunk


# --------------------------------------------------
# In-memory BM25 index
# --------------------------------------------------
#
# BM25 does not need to be recreated for every query.
# We build the index and keep it in memory.
#
# Later we can add persistent/cached indexing if needed.
# --------------------------------------------------

_bm25 = None
_chunks = []


def tokenize(text: str) -> list[str]:
    """
    Convert text into tokens for BM25.

    Example:

        "Python is a programming language."

    becomes:

        ["python", "is", "a", "programming", "language"]
    """

    return re.findall(
        r"\b\w+\b",
        text.lower()
    )


def build_bm25_index():
    """
    Build the BM25 index from all document chunks
    stored in SQLite.

    Only COMPLETED documents are indexed.
    """

    global _bm25
    global _chunks

    chunks = (
        DocumentChunk.query
        .join(DocumentChunk.document)
        .filter_by(status="COMPLETED")
        .all()
    )

    if not chunks:

        _bm25 = None
        _chunks = []

        print(
            "[BM25] No completed document chunks found."
        )

        return

    _chunks = chunks

    tokenized_corpus = [
        tokenize(chunk.content)
        for chunk in chunks
    ]

    _bm25 = BM25Okapi(
        tokenized_corpus
    )

    print(
        f"[BM25] Indexed "
        f"{len(chunks)} chunks."
    )


def get_bm25_index():
    """
    Return the current BM25 index.

    Build it automatically if it doesn't exist.
    """

    global _bm25

    if _bm25 is None:

        build_bm25_index()

    return _bm25


def search_bm25(
    query: str,
    k: int = 5
):
    """
    Search the BM25 index.

    Returns:

        [
            {
                "chunk": DocumentChunk,
                "score": float
            }
        ]
    """

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

    ranked_indexes = sorted(
        range(len(scores)),
        key=lambda index: scores[index],
        reverse=True
    )

    results = []

    for index in ranked_indexes[:k]:

        score = float(
            scores[index]
        )

        # Ignore zero-score results.
        if score <= 0:
            continue

        results.append({
            "chunk": _chunks[index],
            "score": score,
        })

    return results


def rebuild_bm25_index():
    """
    Force a complete BM25 index rebuild.

    Useful after:
        - document approval
        - document deletion
        - document re-processing
        - document rejection
    """

    build_bm25_index()

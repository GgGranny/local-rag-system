from app.retrieval.vector_store import (
    get_vector_store,
)

from app.retrieval.bm25_store import (
    search_bm25,
)


def normalize_scores(
    results: list[dict]
) -> list[dict]:
    """
    Normalize scores to a 0-1 range using min-max
    normalization.

    Input:
        [
            {"chunk": ..., "score": 10.5},
            {"chunk": ..., "score": 5.2},
        ]

    Output:
        [
            {"chunk": ..., "score": 1.0},
            {"chunk": ..., "score": 0.0},
        ]
    """

    if not results:
        return []

    scores = [
        result["score"]
        for result in results
    ]

    minimum = min(scores)
    maximum = max(scores)

    # If every result has the same score,
    # give them equal normalized scores.
    if maximum == minimum:

        for result in results:
            result["normalized_score"] = 1.0

        return results

    for result in results:

        result["normalized_score"] = (
            result["score"] - minimum
        ) / (
            maximum - minimum
        )

    return results


def search_vector(
    query: str,
    k: int = 5
) -> list[dict]:

    vector_store = get_vector_store()

    results = (
        vector_store
        .similarity_search_with_score(
            query,
            k=k,
            filter={
                "status": "COMPLETED"
            }
        )
    )

    formatted_results = []

    for document, score in results:

        chunk_id = document.metadata.get(
            "chunk_id"
        )

        if not chunk_id:
            continue

        formatted_results.append({
            "chunk_id": chunk_id,
            "document": document,
            "score": float(score),
        })

    return formatted_results

def search_hybrid(
    query: str,
    k: int = 5,
    vector_weight: float = 0.7,
    bm25_weight: float = 0.3,
) -> list[dict]:
    """
    Perform hybrid retrieval using:

        Chroma semantic search
        +
        BM25 keyword search

    The final score is:

        final_score =
            vector_score * vector_weight
            +
            bm25_score * bm25_weight

    Results from both systems are merged using
    the stable chunk_id.
    """

    if not query or not query.strip():

        return []

    if vector_weight < 0 or bm25_weight < 0:

        raise ValueError(
            "Retrieval weights cannot be negative."
        )

    total_weight = (
        vector_weight +
        bm25_weight
    )

    if total_weight <= 0:

        raise ValueError(
            "At least one retrieval weight "
            "must be greater than zero."
        )

    # Normalize weights so they always sum to 1.
    vector_weight = (
        vector_weight /
        total_weight
    )

    bm25_weight = (
        bm25_weight /
        total_weight
    )

    # --------------------------------------------------
    # 1. Vector search
    # --------------------------------------------------

    vector_results = search_vector(
        query=query,
        k=k
    )

    # Chroma returns distance values.
    #
    # Lower distance = more similar.
    #
    # We therefore convert distance into a
    # similarity-like score.
    #
    # similarity = 1 / (1 + distance)
    #
    # Higher = better.
    # --------------------------------------------------

    for result in vector_results:

        distance = result["score"]

        result["score"] = (
            1.0 /
            (1.0 + max(distance, 0.0))
        )

    vector_results = normalize_scores(
        vector_results
    )

    # --------------------------------------------------
    # 2. BM25 search
    # --------------------------------------------------

    bm25_results = search_bm25(
        query=query,
        k=k
    )

    bm25_results = [
        {
            "chunk_id": result["chunk"].chunk_id,
            "document": result["chunk"],
            "score": result["score"],
        }
        for result in bm25_results
    ]

    bm25_results = normalize_scores(
        bm25_results
    )

    # --------------------------------------------------
    # 3. Merge results
    # --------------------------------------------------

    merged = {}

    # Vector results
    for result in vector_results:

        chunk_id = result["chunk_id"]

        merged[chunk_id] = {
            "chunk_id": chunk_id,
            "document": result["document"],
            "vector_score": result[
                "normalized_score"
            ],
            "bm25_score": 0.0,
        }

    # BM25 results
    for result in bm25_results:

        chunk_id = result["chunk_id"]

        if chunk_id not in merged:

            merged[chunk_id] = {
                "chunk_id": chunk_id,
                "document": result["document"],
                "vector_score": 0.0,
                "bm25_score": result[
                    "normalized_score"
                ],
            }

        else:

            merged[chunk_id][
                "bm25_score"
            ] = result[
                "normalized_score"
            ]

    # --------------------------------------------------
    # 4. Calculate final hybrid score
    # --------------------------------------------------

    final_results = []

    for result in merged.values():

        final_score = (
            result["vector_score"]
            * vector_weight
            +
            result["bm25_score"]
            * bm25_weight
        )

        result["score"] = final_score

        final_results.append(
            result
        )

    # --------------------------------------------------
    # 5. Sort by final score
    # --------------------------------------------------

    final_results.sort(
        key=lambda result: result["score"],
        reverse=True
    )

    # --------------------------------------------------
    # 6. Return top K
    # --------------------------------------------------

    return final_results[:k]
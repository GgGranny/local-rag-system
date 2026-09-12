from app.retrieval.vector_store import (
    get_vector_store,
)

from app.retrieval.bm25_store import (
    search_bm25,
)


def normalize_scores(results):

    if not results:
        return results

    scores = [
        float(
            result.get(
                "score",
                0.0
            )
        )
        for result in results
    ]

    minimum = min(scores)
    maximum = max(scores)

    if maximum == minimum:

        for result in results:

            result["normalized_score"] = (
                1.0
                if maximum > 0
                else 0.0
            )

        return results

    for result in results:

        score = float(
            result.get(
                "score",
                0.0
            )
        )

        result["normalized_score"] = (
            (score - minimum)
            / (maximum - minimum)
        )

    return results


def search_vector(
    query,
    k=5,
    user_id=None,
    is_admin=False,
    document_ids=None,
):
    """Search the shared vector knowledge base of completed documents."""

    vector_store = get_vector_store()

    # --------------------------------------------------
    # CHROMA FILTER
    # --------------------------------------------------

    filter_parts = [{"status": "COMPLETED"}]
    if document_ids:
        filter_parts.append({"document_id": {"$in": document_ids}})

    search_filter = filter_parts[0] if len(filter_parts) == 1 else {"$and": filter_parts}

    results = (
        vector_store
        .similarity_search_with_score(
            query,
            k=k,
            filter=search_filter,
        )
    )

    formatted_results = []

    for document, distance in results:

        metadata = (
            document.metadata
            if isinstance(
                document.metadata,
                dict
            )
            else {}
        )

        chunk_id = metadata.get(
            "chunk_id"
        )

        if not chunk_id:
            continue

        distance = max(
            float(distance),
            0.0
        )

        similarity = (
            1.0 / (1.0 + distance)
        )

        formatted_results.append({
            "chunk_id": chunk_id,

            "document": document,

            "score": similarity,
        })

    return formatted_results


def search_hybrid(
    query,
    k=5,
    user_id=None,
    is_admin=False,
    document_ids=None,
    vector_weight=0.7,
    bm25_weight=0.3,
):
    """
    Hybrid vector + BM25 retrieval.

    Both retrieval systems use the shared completed-document access rule.
    """

    vector_results = search_vector(
        query=query,
        k=k,
        user_id=user_id,
        is_admin=is_admin,
        document_ids=document_ids,
    )

    bm25_results = search_bm25(
        query=query,
        k=k,
        user_id=user_id,
        is_admin=is_admin,
        document_ids=document_ids,
    )

    # --------------------------------------------------
    # NORMALIZE
    # --------------------------------------------------

    vector_results = normalize_scores(
        vector_results
    )

    bm25_results = normalize_scores(
        bm25_results
    )

    # --------------------------------------------------
    # MERGE
    # --------------------------------------------------

    merged = {}

    # Vector results

    for result in vector_results:

        chunk_id = result[
            "chunk_id"
        ]

        merged[chunk_id] = {
            "chunk_id": chunk_id,

            "document": result[
                "document"
            ],

            "vector_score":
                result.get(
                    "normalized_score",
                    0.0
                ),

            "bm25_score": 0.0,
        }

    # BM25 results

    for result in bm25_results:

        chunk_id = result[
            "chunk_id"
        ]

        if chunk_id not in merged:

            merged[chunk_id] = {
                "chunk_id": chunk_id,

                "document": result[
                    "document"
                ],

                "vector_score": 0.0,

                "bm25_score":
                    result.get(
                        "normalized_score",
                        0.0
                    ),
            }

        else:

            merged[chunk_id][
                "bm25_score"
            ] = result.get(
                "normalized_score",
                0.0
            )

    # --------------------------------------------------
    # HYBRID SCORE
    # --------------------------------------------------

    final_results = []

    for result in merged.values():

        vector_score = float(
            result.get(
                "vector_score",
                0.0
            )
        )

        bm25_score = float(
            result.get(
                "bm25_score",
                0.0
            )
        )

        final_score = (
            vector_score * vector_weight
            +
            bm25_score * bm25_weight
        )

        final_results.append({
            "chunk_id":
                result["chunk_id"],

            "document":
                result["document"],

            "score":
                final_score,

            "vector_score":
                vector_score,

            "bm25_score":
                bm25_score,
        })

    final_results.sort(
        key=lambda result:
            result["score"],
        reverse=True
    )

    return final_results[:k]


def serialize_retrieval_results(
    results
):
    """
    Convert retrieval results into plain
    dictionaries safe for LangGraph checkpoints.
    """

    serialized = []

    for result in results:

        document = result[
            "document"
        ]

        # --------------------------------------------------
        # LangChain Document
        # --------------------------------------------------

        if hasattr(
            document,
            "page_content"
        ):

            content = (
                document.page_content
            )

            metadata = getattr(
                document,
                "metadata",
                {}
            )

        # --------------------------------------------------
        # SQLAlchemy DocumentChunk
        # --------------------------------------------------

        else:

            content = document.content

            metadata = {
                "filename": (
                    document.document.filename
                    if document.document
                    else "Unknown"
                ),

                "page_number":
                    document.page_number,

                "extraction_method":
                    document.extraction_method,

                "content_type":
                    document.content_type,

                "document_id":
                    document.document_id,

                "user_id":
                    document.document.uploaded_by
                    if document.document
                    else None,

                "status":
                    document.document.status
                    if document.document
                    else None,
            }

        if not isinstance(
            metadata,
            dict
        ):

            metadata = {}

        serialized.append({
            "chunk_id":
                result["chunk_id"],

            "content":
                content,

            "metadata":
                metadata,

            "score":
                float(
                    result.get(
                        "score",
                        0.0
                    )
                ),

            "vector_score":
                float(
                    result.get(
                        "vector_score",
                        0.0
                    )
                ),

            "bm25_score":
                float(
                    result.get(
                        "bm25_score",
                        0.0
                    )
                ),
        })

    return serialized

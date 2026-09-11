from app import create_app

from app.retrieval.hybrid import search_hybrid


app = create_app()


with app.app_context():

    results = search_hybrid(
        query="artificial intelligence",
        k=5
    )

    print(
        f"\nFound {len(results)} results.\n"
    )

    for index, result in enumerate(
        results,
        start=1
    ):

        document = result["document"]

        print(
            f"========== RESULT {index} =========="
        )

        print(
            f"Final score: "
            f"{result['score']:.4f}"
        )

        print(
            f"Vector score: "
            f"{result['vector_score']:.4f}"
        )

        print(
            f"BM25 score: "
            f"{result['bm25_score']:.4f}"
        )

        print(
            f"Chunk ID: "
            f"{result['chunk_id']}"
        )

        print(
            f"Page: "
            f"{document.metadata.get('page_number')}"
        )

        print(
            f"Filename: "
            f"{document.metadata.get('filename')}"
        )

        print()

        print(
            document.page_content[:500]
        )

        print()
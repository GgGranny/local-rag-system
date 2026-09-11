from app import create_app
from app.chat.service import ask_question


app = create_app()


with app.app_context():

    result = ask_question(
        "What is this document about?",
        k=5
    )

    print(
        "\n========== ANSWER ==========\n"
    )

    print(
        result["answer"]
    )

    print(
        "\n========== SOURCES ==========\n"
    )

    for source in result["sources"]:

        print(
            f"{source['citation']} "
            f"{source['filename']} "
            f"page={source['page_number']} "
            f"chunk={source['chunk_id']} "
            f"score={source['score']}"
        )
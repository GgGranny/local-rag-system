from app import create_app
from app.chat.graph import build_graph

from langchain_core.messages import HumanMessage


app = create_app()

with app.app_context():

    graph = build_graph()

    config = {
        "configurable": {
            "thread_id": "conversation-test-1"
        }
    }

    # --------------------------------
    # TURN 1
    # --------------------------------

    result_1 = graph.invoke(
        {
            "messages": [
                HumanMessage(
                    content="What is this document about?"
                )
            ]
        },
        config=config
    )

    print(
        "\n========== TURN 1 ==========\n"
    )

    print(
        result_1.get("answer")
    )

    print(
        "\nStandalone question:"
    )

    print(
        result_1.get(
            "standalone_question"
        )
    )

    # --------------------------------
    # TURN 2
    # --------------------------------

    result_2 = graph.invoke(
        {
            "messages": [
                HumanMessage(
                    content="Who created it?"
                )
            ]
        },
        config=config
    )

    print(
        "\n========== TURN 2 ==========\n"
    )

    print(
        result_2.get("answer")
    )

    print(
        "\nStandalone question:"
    )

    print(
        result_2.get(
            "standalone_question"
        )
    )

    print(
        "\n========== SOURCES ==========\n"
    )

    for source in result_2.get(
        "sources",
        []
    ):
        print(source)
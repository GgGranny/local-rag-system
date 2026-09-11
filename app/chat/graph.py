from langgraph.graph import (
    StateGraph,
    START,
    END,
)

from app.chat.state import RAGState
from app.chat.checkpointer import get_checkpointer


def test_node(
    state: RAGState
) -> RAGState:

    question = state.get(
        "question",
        ""
    )

    print(
        f"[GRAPH] Received question: "
        f"{question}"
    )

    return {
        "standalone_question": question
    }


def build_graph():

    builder = StateGraph(
        RAGState
    )

    builder.add_node(
        "test_node",
        test_node
    )

    builder.add_edge(
        START,
        "test_node"
    )

    builder.add_edge(
        "test_node",
        END
    )

    checkpointer = get_checkpointer()

    graph = builder.compile(
        checkpointer=checkpointer
    )

    return graph
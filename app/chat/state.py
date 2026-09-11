from typing import Annotated

from langchain_core.messages import AnyMessage

from langgraph.graph.message import add_messages

from typing_extensions import TypedDict


class RAGState(
    TypedDict,
    total=False
):

    # --------------------------------------------------
    # USER / ACCESS CONTEXT
    # --------------------------------------------------

    user_id: int

    is_admin: bool

    # --------------------------------------------------
    # CONVERSATION MEMORY
    # --------------------------------------------------

    messages: Annotated[
        list[AnyMessage],
        add_messages
    ]

    # --------------------------------------------------
    # RETRIEVAL QUESTION
    # --------------------------------------------------

    standalone_question: str

    # --------------------------------------------------
    # SERIALIZABLE RETRIEVAL RESULTS
    # --------------------------------------------------

    retrieved_documents: list[dict]

    # --------------------------------------------------
    # RAG CONTEXT
    # --------------------------------------------------

    context: str

    # --------------------------------------------------
    # FINAL ANSWER
    # --------------------------------------------------

    answer: str

    # --------------------------------------------------
    # CITATION SOURCES
    # --------------------------------------------------

    sources: list[dict]
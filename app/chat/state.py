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

    selected_document_ids: list[int]

    # The previous completed turn's selection.  This is retrieval context,
    # not chat history, and is deliberately only primitive data so it is safe
    # for the LangGraph checkpoint.
    previous_selected_document_ids: list[int]

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

    original_query: str

    query_for_retrieval: str

    needs_rewrite: bool

    document_context_changed: bool

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

from typing import Annotated

from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages
from typing_extensions import TypedDict


class RAGState(TypedDict, total=False):

    # Conversation memory
    messages: Annotated[
        list[AnyMessage],
        add_messages
    ]

    # Standalone question used for retrieval
    standalone_question: str

    # Serializable retrieval results only
    retrieved_documents: list[dict]

    # RAG context
    context: str

    # Final answer
    answer: str

    # Citation/source information
    sources: list[dict]
from typing import TypedDict


class RAGState(TypedDict, total=False):
    # Current user question
    question: str

    # Question rewritten using conversation context
    standalone_question: str

    # Retrieved chunks
    retrieved_documents: list

    # Formatted context sent to the LLM
    context: str

    # Final generated answer
    answer: str

    # Sources used for the answer
    sources: list
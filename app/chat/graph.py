from langgraph.graph import (
    StateGraph,
    START,
    END,
)
from langchain_core.messages import (
    HumanMessage,
    AIMessage,
)
from app.chat.state import RAGState
from app.chat.checkpointer import get_checkpointer
from app.retrieval.hybrid import (
    search_hybrid,
    serialize_retrieval_results,
)
from app.chat.service import (
    build_context,
    build_rag_prompt,
    get_document_metadata,
    serialize_retrieval_results,
)
from app.chat.llm import generate_answer


def rewrite_query(
    state: RAGState
) -> RAGState:

    messages = state.get(
        "messages",
        []
    )

    if not messages:
        raise ValueError(
            "No conversation messages found."
        )

    current_question = messages[-1].content.strip()

    if not current_question:
        raise ValueError(
            "Question cannot be empty."
        )
    previous_messages = messages[:-1]

    # No previous conversation.
    if not previous_messages:
        print(
            f"[GRAPH] First question: "
            f"{current_question}"
        )

        return {
            "standalone_question": current_question
        }
    conversation = []
    for message in previous_messages:
        role = (
            "User"
            if isinstance(message, HumanMessage)
            else "Assistant"
        )

        conversation.append(
            f"{role}: {message.content}"
        )

    conversation_text = "\n".join(
        conversation
    )

    prompt = f"""
    You are a question rewriting component
    for a document-based RAG system.

    Your job is to rewrite the user's latest
    question into a standalone question that
    can be searched against documents.

    Rules:

    1. Use the conversation history to understand
    references such as "it", "they", "this",
    "that", or "the previous one".
    2. Do not answer the question.
    3. Do not add information that is not present
    in the conversation.
    4. If the latest question is already standalone,
    return it unchanged.
    5. Return ONLY the rewritten question.
    6. Do not include explanations.
    7. Do not include quotation marks.

    Conversation history:
    --------------------

    {conversation_text}

    --------------------

    Latest user question:
    {current_question}

    Standalone retrieval question:
    """

    print(
        "[GRAPH] Rewriting follow-up question..."
    )

    standalone_question = generate_answer(
        prompt
    ).strip()

    print(
        f"[GRAPH] Standalone question: "
        f"{standalone_question}"
    )

    return {
        "standalone_question":
            standalone_question
    }


def retrieve(
    state: RAGState
) -> RAGState:

    question = state[
        "standalone_question"
    ]

    print(
        f"[GRAPH] Retrieving: "
        f"{question}"
    )

    results = search_hybrid(
        query=question,
        k=5
    )

    print(
        f"[GRAPH] Retrieved "
        f"{len(results)} chunks."
    )

    serialized_results = (
        serialize_retrieval_results(
            results
        )
    )

    return {
        "retrieved_documents":
            serialized_results
    }

def build_context_node(
    state: RAGState
) -> RAGState:

    results = state.get(
        "retrieved_documents",
        []
    )

    context = build_context(
        results
    )

    print(
        f"[GRAPH] Context length: "
        f"{len(context)} characters."
    )

    return {
        "context": context
    }


def generate_answer_node(
    state: RAGState
) -> RAGState:

    question = state[
        "standalone_question"
    ]

    context = state.get(
        "context",
        ""
    )

    if not context:

        answer = (
            "I could not find relevant "
            "information in the uploaded "
            "documents."
        )

        return {
            "answer": answer,
            "sources": [],
            "messages": [
                AIMessage(
                    content=answer
                )
            ],
        }

    prompt = build_rag_prompt(
        question=question,
        context=context,
    )

    print(
        "[GRAPH] Generating answer..."
    )

    answer = generate_answer(
        prompt
    )

    results = state.get(
        "retrieved_documents",
        []
    )

    sources = []

    for index, result in enumerate(
        results,
        start=1
    ):

        metadata = result.get(
            "metadata",
            {}
        )

        sources.append({
            "citation": f"[{index}]",

            "chunk_id": result.get(
                "chunk_id"
            ),

            "filename": metadata.get(
                "filename",
                "Unknown"
            ),

            "page_number": metadata.get(
                "page_number"
            ),

            "score": result.get(
                "score",
                0.0
            ),
        })

    return {
        "answer": answer,

        "sources": sources,

        "messages": [
            AIMessage(
                content=answer
            )
        ],
    }


def build_graph():

    builder = StateGraph(
        RAGState
    )

    builder.add_node(
        "rewrite_query",
        rewrite_query
    )

    builder.add_node(
        "retrieve",
        retrieve
    )

    builder.add_node(
        "build_context",
        build_context_node
    )

    builder.add_node(
        "generate_answer",
        generate_answer_node
    )

    builder.add_edge(
        START,
        "rewrite_query"
    )

    builder.add_edge(
        "rewrite_query",
        "retrieve"
    )

    builder.add_edge(
        "retrieve",
        "build_context"
    )

    builder.add_edge(
        "build_context",
        "generate_answer"
    )

    builder.add_edge(
        "generate_answer",
        END
    )

    checkpointer = get_checkpointer()

    return builder.compile(
        checkpointer=checkpointer
    )
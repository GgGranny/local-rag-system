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

from app.chat.checkpointer import (
    get_checkpointer,
)

from app.retrieval.hybrid import (
    search_hybrid,
    serialize_retrieval_results,
)

from app.chat.service import (
    build_context,
    build_rag_prompt,
)

from app.chat.llm import (
    generate_answer,
)
from app.monitoring.service import measured, record, trace_node


# ======================================================
# QUERY DECISION / REWRITING
# ======================================================

FOLLOW_UP_MARKERS = (
    "\\bit\\b",
    "\\bits\\b",
    "\\bthey\\b",
    "\\bthem\\b",
    "\\btheir\\b",
    "\\bthat\\b",
    "\\bthose\\b",
    "\\bprevious\\b",
    "\\bthe previous\\b",
    "\\bfirst (?:topic|point|example)\\b",
    "\\bsecond (?:topic|point|example)\\b",
    "\\blast (?:topic|point|example)\\b",
    "\\bwhat about\\b",
)


def needs_conversation_rewrite(question: str) -> bool:
    """Return true only for explicit conversational references.

    History existing is not enough evidence that a question is a follow-up.
    The deliberately small heuristic avoids a second LLM call for ordinary,
    self-contained document questions while preserving rewriting for pronouns
    and references such as "its", "that", or "the second point".
    """
    import re

    normalized = " ".join(question.lower().split())
    return any(re.search(marker, normalized) for marker in FOLLOW_UP_MARKERS)


@trace_node("rag.query.classification")
def decide_query(
    state: RAGState,
) -> RAGState:
    messages = state.get("messages", [])
    if not messages:
        raise ValueError("No conversation messages found.")

    original_query = messages[-1].content.strip()
    if not original_query:
        raise ValueError("Question cannot be empty.")

    current_document_ids = sorted(state.get("selected_document_ids", []))
    previous_document_ids = state.get("previous_selected_document_ids")
    has_history = len(messages) > 1
    # Older checkpoints do not have this field.  When history exists but its
    # document scope is unknown, prefer a fresh retrieval context rather than
    # risk rewriting with evidence from a prior selection.
    document_context_changed = has_history and (
        previous_document_ids is None
        or sorted(previous_document_ids) != current_document_ids
    )

    # A different selection creates a new retrieval context.  Keep visible
    # chat history, but never use its prior document evidence to expand the
    # new query.
    needs_rewrite = (
        has_history
        and not document_context_changed
        and needs_conversation_rewrite(original_query)
    )

    print(f"[CHAT] Original query: {original_query}")
    print(f"[CHAT] Previous documents: {previous_document_ids or []}")
    print(f"[CHAT] Current documents: {current_document_ids}")
    print(
        "[CHAT] Query type: "
        f"{'FOLLOW_UP' if needs_rewrite else 'INDEPENDENT'}"
    )
    print(f"[CHAT] Rewrite required: {needs_rewrite}")

    record(
        query_type="follow_up" if needs_rewrite else "independent",
        rewrite_used=needs_rewrite,
        retrieval_query=original_query,
    )
    return {
        "original_query": original_query,
        "query_for_retrieval": original_query,
        "standalone_question": original_query,
        "needs_rewrite": needs_rewrite,
        "document_context_changed": document_context_changed,
    }

@trace_node("rag.query.rewrite")
def rewrite_query(
    state: RAGState
) -> RAGState:
    messages = state.get("messages", [])
    current_question = state["original_query"]
    previous_messages = messages[:-1]

    # --------------------------------------------------
    # BUILD HISTORY
    # --------------------------------------------------

    conversation = []

    # Only the latest exchanges are relevant to a real follow-up.  This keeps
    # a long conversation from becoming accidental document context.
    for message in previous_messages[-6:]:

        role = (
            "User"
            if isinstance(
                message,
                HumanMessage
            )
            else "Assistant"
        )

        conversation.append(
            f"{role}: {message.content}"
        )

    conversation_text = "\n".join(
        conversation
    )

    # --------------------------------------------------
    # REWRITE PROMPT
    # --------------------------------------------------

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

    standalone_question = generate_answer(prompt).strip()

    # A failed/local model response must not turn a valid short follow-up
    # into an empty retrieval query.  The original question remains the
    # safest retrieval query in that case.
    if not standalone_question:
        standalone_question = current_question
    record(retrieval_query=standalone_question)

    print(
        f"[GRAPH] Standalone question: "
        f"{standalone_question}"
    )

    return {
        "standalone_question": standalone_question,
        "query_for_retrieval": standalone_question,
    }


def route_after_query_decision(state: RAGState) -> str:
    return "rewrite_query" if state.get("needs_rewrite") else "retrieve"


# ======================================================
# RETRIEVAL
# ======================================================

@trace_node("rag.retrieval")
def retrieve(
    state: RAGState
) -> RAGState:

    question = state.get("query_for_retrieval") or state["original_query"]

    user_id = state.get(
        "user_id"
    )

    is_admin = state.get(
        "is_admin",
        False
    )

    selected_document_ids = state.get(
        "selected_document_ids",
        []
    )

    print(
        f"[GRAPH] Retrieving: "
        f"{question}"
    )
    print(f"[CHAT] Retrieval document IDs: {selected_document_ids}")

    print(
        f"[GRAPH] User ID: "
        f"{user_id}"
    )

    print(
        f"[GRAPH] Admin: "
        f"{is_admin}"
    )

    results = search_hybrid(
        query=question,
        k=5,
        user_id=user_id,
        is_admin=is_admin,
        document_ids=selected_document_ids,
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
    record(retrieved_chunks=serialized_results, retrieval_query=question)

    return {
        "retrieved_documents":
            serialized_results
    }


# ======================================================
# BUILD CONTEXT
# ======================================================

@trace_node("rag.context.build")
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

    record(context=context)
    return {
        "context": context
    }


# ======================================================
# GENERATE ANSWER
# ======================================================

@trace_node("rag.generation")
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

    # --------------------------------------------------
    # NO CONTEXT
    # --------------------------------------------------

    if not context:

        answer = (
            "I could not find relevant "
            "information in the uploaded "
            "documents."
        )

        record(prompt=None, answer=answer, citations=[])
        return {
            "answer": answer,

            "sources": [],

            "messages": [
                AIMessage(
                    content=answer
                )
            ],

            "previous_selected_document_ids": list(
                state.get("selected_document_ids", [])
            ),
        }

    # --------------------------------------------------
    # GENERATE
    # --------------------------------------------------

    with measured("rag.prompt.build"):
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

    # --------------------------------------------------
    # SOURCES
    # --------------------------------------------------

    results = state.get(
        "retrieved_documents",
        []
    )

    sources = []

    with measured("rag.citations"):
        for index, result in enumerate(
            results,
            start=1
        ):

            metadata = result.get(
                "metadata",
                {}
            )

            sources.append({
                "citation":
                    f"[{index}]",

                "chunk_id":
                    result.get(
                        "chunk_id"
                    ),

                "filename":
                    metadata.get(
                        "filename",
                        "Unknown"
                    ),

                "page_number":
                    metadata.get(
                        "page_number"
                    ),

                "score":
                    result.get(
                        "score",
                        0.0
                    ),

                "content": result.get("content", ""),

                "extraction_method": metadata.get("extraction_method"),

                "document_id": metadata.get("document_id"),
            })

    record(answer=answer, citations=sources)
    return {
        "answer": answer,

        "sources": sources,

        "messages": [
            AIMessage(
                content=answer
            )
        ],

        "previous_selected_document_ids": list(
            state.get("selected_document_ids", [])
        ),
    }


# ======================================================
# BUILD GRAPH
# ======================================================

def build_graph():

    builder = StateGraph(
        RAGState
    )

    builder.add_node("decide_query", decide_query)
    builder.add_node("rewrite_query", rewrite_query)

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
        "decide_query"
    )

    builder.add_conditional_edges(
        "decide_query",
        route_after_query_decision,
        {
            "rewrite_query": "rewrite_query",
            "retrieve": "retrieve",
        },
    )

    builder.add_edge("rewrite_query", "retrieve")

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

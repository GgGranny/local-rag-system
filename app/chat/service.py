from app.retrieval.hybrid import search_hybrid
from app.chat.llm import generate_answer


def get_document_metadata(document) -> dict:
    if hasattr(document, "page_content"):
        return document.metadata or {}

    if hasattr(document, "document"):
        return {
            "filename": (
                document.document.filename
                if document.document
                else "Unknown"
            ),
            "page_number": document.page_number,
            "extraction_method": document.extraction_method,
            "content_type": document.content_type,
        }

    return {}


def build_context(results: list[dict]) -> str:
    if not results:
        return ""

    context_parts = []

    for index, result in enumerate(results, start=1):

        document = result["document"]

        # -----------------------------------------
        # Get content
        # -----------------------------------------

        if hasattr(document, "page_content"):
            content = document.page_content
        elif hasattr(document, "content"):
            content = document.content
        else:
            content = str(document)

        # -----------------------------------------
        # Get metadata
        # -----------------------------------------

        metadata = get_document_metadata(document)

        # -----------------------------------------
        # Source information
        # -----------------------------------------

        filename = metadata.get(
            "filename",
            "Unknown"
        )

        page_number = metadata.get(
            "page_number"
        )

        source_label = filename

        if page_number:
            source_label += (
                f", page {page_number}"
            )

        # -----------------------------------------
        # Build source context
        # -----------------------------------------

        context_parts.append(
            f"[Source {index}: {source_label}]\n"
            f"{content}\n"
        )

    return "\n".join(context_parts)

def build_rag_prompt(
    question: str,
    context: str
) -> str:
    """
    Build the prompt used by the local LLM.
    """

    return f"""
You are a helpful document question-answering assistant.

Your task is to answer the user's question using
ONLY the information contained in the provided context.

Rules:

1. Use only the provided context.
2. Do not invent or assume information.
3. If the context does not contain enough information
   to answer the question, clearly say that the answer
   is not available in the provided documents.
4. Give a concise and clear answer.
5. When using information from a source, include its
   citation in the form [1], [2], [3], etc.
6. Place each citation immediately after the statement
   supported by that source.
7. Do not put all citations at the end of the answer.

Context:
--------------------

{context}

--------------------

User Question:
{question}

Answer:
"""


def ask_question(
    question: str,
    k: int = 5
) -> dict:
    """
    Complete RAG pipeline:

        Question
            ↓
        Hybrid Retrieval
            ↓
        Context
            ↓
        LLM
            ↓
        Answer + Sources
    """

    if not question or not question.strip():
        raise ValueError(
            "Question cannot be empty."
        )

    question = question.strip()

    # ==================================================
    # STEP 1: Retrieve relevant chunks
    # ==================================================

    print(
        f"[RAG] Searching for: {question}"
    )

    results = search_hybrid(
        query=question,
        k=k
    )

    print(
        f"[RAG] Retrieved "
        f"{len(results)} chunks."
    )

    # ==================================================
    # STEP 2: Handle no results
    # ==================================================

    if not results:

        return {
            "answer": (
                "I could not find relevant "
                "information in the uploaded documents."
            ),
            "sources": [],
        }

    # ==================================================
    # STEP 3: Build context
    # ==================================================

    context = build_context(
        results
    )

    # ==================================================
    # STEP 4: Build RAG prompt
    # ==================================================

    prompt = build_rag_prompt(
        question=question,
        context=context
    )

    # ==================================================
    # STEP 5: Generate answer
    # ==================================================

    print(
        "[RAG] Generating answer..."
    )

    answer = generate_answer(
        prompt
    )

    # ==================================================
    # STEP 6: Prepare source information
    # ==================================================

    sources = []

    for index, result in enumerate(
        results,
        start=1
    ):

        document = result["document"]

        metadata = get_document_metadata(document)

        sources.append({
            "citation": f"[{index}]",
            "chunk_id": result[
                "chunk_id"
            ],
            "filename": metadata.get(
                "filename",
                "Unknown"
            ),
            "page_number": metadata.get(
                "page_number"
            ),
            "score": result[
                "score"
            ],
        })

    # ==================================================
    # STEP 7: Return complete RAG result
    # ==================================================

    return {
        "answer": answer,
        "sources": sources,
    }
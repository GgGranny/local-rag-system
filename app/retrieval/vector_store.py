from pathlib import Path

from langchain_chroma import Chroma
from langchain_ollama import OllamaEmbeddings

from app.config import Config


_embeddings = None
_vector_store = None


def get_embeddings():
    """
    Return the shared Ollama embedding model.
    """

    global _embeddings

    if _embeddings is None:

        print(
            "[VECTOR] Loading embedding model: "
            f"{Config.OLLAMA_EMBEDDING_MODEL}"
        )

        _embeddings = OllamaEmbeddings(
            model=Config.OLLAMA_EMBEDDING_MODEL
        )

    return _embeddings


def get_vector_store():
    """
    Return the shared Chroma vector store.
    """

    global _vector_store

    if _vector_store is None:

        persist_directory = Path(
            Config.CHROMA_PERSIST_DIRECTORY
        )

        persist_directory.mkdir(
            parents=True,
            exist_ok=True
        )

        _vector_store = Chroma(
            collection_name=(
                Config.CHROMA_COLLECTION_NAME
            ),
            embedding_function=get_embeddings(),
            persist_directory=str(
                persist_directory
            ),
        )

    return _vector_store


def delete_document_chunks(
    document_id: int
):
    """
    Delete all Chroma chunks belonging
    to one document.
    """
    vector_store = get_vector_store()
    print(
        f"[VECTOR] Removing vectors for "
        f"document {document_id}..."
    )
    results = vector_store.get(
        where={
            "document_id": document_id
        }
    )
    ids = results.get(
        "ids",
        []
    )

    if not ids:
        print(
            f"[VECTOR] No vectors found for "
            f"document {document_id}."
        )
        return
    vector_store.delete(
        ids=ids
    )
    print(
        f"[VECTOR] Removed "
        f"{len(ids)} vectors."
    )


def index_chunks(chunks):
    """
    Add LangChain Document chunks to Chroma.
    """
    if not chunks:
        return
    vector_store = get_vector_store()

    ids = []
    for chunk in chunks:
        chunk_id = chunk.metadata.get(
            "chunk_id"
        )
        if not chunk_id:
            raise ValueError(
                "Chunk is missing chunk_id."
            )
        ids.append(chunk_id)

    print(
        f"[VECTOR] Indexing "
        f"{len(chunks)} chunks..."
    )

    vector_store.add_documents(
        documents=chunks,
        ids=ids,
    )

    print(
        f"[VECTOR] Indexed "
        f"{len(chunks)} chunks."
    )
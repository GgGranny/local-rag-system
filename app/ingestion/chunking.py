from langchain_core.documents import Document
from langchain_text_splitters import CharacterTextSplitter


def create_documents(
    extracted_pages,
    document_id,
    filename,
    user_id,
):
    """
    Convert extracted pages into LangChain Documents.

    Each page keeps metadata that will later be used for:
    - citations
    - source display
    - ownership filtering
    - retrieval
    """

    documents = []

    for page in extracted_pages:

        text = page.get(
            "text",
            ""
        ).strip()

        if not text:
            continue

        metadata = {
            "document_id": document_id,

            "filename": filename,

            "page_number": page.get(
                "page_number"
            ),

            "extraction_method": page.get(
                "extraction_method",
                "native"
            ),

            "content_type": "page",

            "status": "COMPLETED",

            # Important for user-isolated RAG
            "user_id": user_id,
        }

        document = Document(
            page_content=text,
            metadata=metadata,
        )

        documents.append(document)

    return documents


def chunk_documents(
    documents,
    document_id,
):
    """
    Split page documents into chunks.

    Stable chunk IDs are generated so that
    citations can later point back to the
    exact chunk.
    """

    splitter = CharacterTextSplitter(
        separator="\n",
        chunk_size=1000,
        chunk_overlap=150,
        length_function=len,
    )

    chunks = []

    for document in documents:

        split_documents = splitter.split_documents(
            [document]
        )

        page_number = document.metadata.get(
            "page_number"
        )

        for chunk_index, chunk in enumerate(
            split_documents
        ):

            chunk_id = (
                f"doc_{document_id}"
                f"_page_{page_number}"
                f"_chunk_{chunk_index}"
            )

            chunk.metadata.update({
                "document_id": document_id,

                "filename": document.metadata.get(
                    "filename",
                    "Unknown"
                ),

                "page_number": page_number,

                "extraction_method":
                    document.metadata.get(
                        "extraction_method"
                    ),

                "content_type": "chunk",

                "status": "COMPLETED",

                # Preserve ownership metadata
                "user_id": document.metadata.get(
                    "user_id"
                ),

                "chunk_id": chunk_id,

                "chunk_index": chunk_index,
            })

            chunks.append(chunk)

    return chunks
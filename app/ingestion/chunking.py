from langchain_core.documents import Document
from langchain_text_splitters import CharacterTextSplitter


def create_documents(
    extracted_pages: list[dict],
    document_id: int,
    filename: str
) -> list[Document]:

    documents = []
    for page in extracted_pages:
        text = page["text"].strip()
        if not text:
            continue
        document = Document(
            page_content=text,
            metadata={
                "document_id": document_id,
                "filename": filename,
                "page_number": page["page_number"],
                "extraction_method": page[
                    "extraction_method"
                ],
                "content_type": "page",
                "status": "COMPLETED",
            }
        )

        documents.append(document)

    return documents


def chunk_documents(
    documents: list[Document],
    document_id: int,
    chunk_size: int = 1000,
    chunk_overlap: int = 150
) -> list[Document]:

    splitter = CharacterTextSplitter(
        separator="\n",
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len,
    )

    chunks = splitter.split_documents(
        documents
    )

    # Keep track of chunks independently
    # for each page.
    page_chunk_counts = {}

    for chunk in chunks:

        page_number = chunk.metadata.get(
            "page_number"
        )

        page_chunk_counts.setdefault(
            page_number,
            0
        )

        page_chunk_counts[
            page_number
        ] += 1

        chunk_index = page_chunk_counts[
            page_number
        ]

        chunk.metadata[
            "chunk_index"
        ] = chunk_index

        chunk.metadata[
            "chunk_id"
        ] = (
            f"doc_{document_id}"
            f"_page_{page_number}"
            f"_chunk_{chunk_index}"
        )

        chunk.metadata[
            "content_type"
        ] = "chunk"

    return chunks
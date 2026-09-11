from app.ingestion.loaders import extract_text
from app.ingestion.chunking import (
    create_documents,
    chunk_documents,
)


file_path = "data/uploads/3436ccba69004138bffdfaaa212850f9.pdf"

# 1. Extract
pages = extract_text(file_path)

# 2. Convert pages into LangChain Documents
documents = create_documents(
    extracted_pages=pages,
    document_id=1,
    filename="YOUR_FILE_NAME.pdf",
)

# 3. Chunk
chunks = chunk_documents(
    documents
)

print(
    f"\nPages extracted: {len(documents)}"
)

print(
    f"Chunks created: {len(chunks)}"
)

for chunk in chunks[:5]:

    print("\n============================")
    print("CHUNK")
    print("============================")

    print(chunk.page_content[:500])

    print("\nMETADATA:")
    print(chunk.metadata)
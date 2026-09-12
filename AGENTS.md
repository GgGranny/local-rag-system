RAG Application — Codex Engineering Instructions

1. Project Overview

This project is a local, document-grounded RAG (Retrieval-Augmented Generation) application.

The application allows authenticated users to:

Log in.

Upload documents.

Wait for administrator approval when required.

Select completed documents as retrieval sources.

Chat with the shared document knowledge base.

Ask follow-up questions using conversation memory.

View clickable citations and source content.

Administrators can:

Log in through the admin portal.

Create and manage users.

Review uploaded documents.

Approve or reject user documents.

Upload documents directly without approval.

Monitor document processing.

Use the same chat/RAG functionality as normal users.

Critical access rule

All documents with COMPLETED status are part of one shared RAG knowledge base.

A completed document uploaded by User A can be retrieved by User B and by the administrator. A completed document uploaded by the administrator can be retrieved by all authenticated users.

uploaded_by is retained for:

audit/history

uploader information

"My Uploads" UI

management/ownership decisions

future permission features

It is not a retrieval restriction.

The application runs locally and uses Ollama for local AI models.

2. Technology Stack

Backend / Web

Python

Flask

Flask-SQLAlchemy

Flask sessions

Jinja templates

HTML

CSS

Vanilla JavaScript

Browser fetch()

Database

SQLite

SQLite stores application state such as:

users

documents

document processing status

document chunks

conversations

metadata

LangGraph checkpoint state is stored separately in:

data/rag_checkpoints.db

RAG

LangChain

LangGraph

ChromaDB

BM25 (rank-bm25)

Ollama

langchain-ollama

langchain-chroma

Document processing

PyMuPDF (fitz) for PDF native text extraction

PaddleOCR for OCR fallback

python-docx for DOCX

TXT extraction

CSV extraction

Chunking

Use:

CharacterTextSplitter

Do not replace it with another chunking strategy unless explicitly requested.

Retrieval

Use hybrid retrieval:

Vector Search + BM25

Both retrieval systems must use the same document-access rules.

3. Technology Restrictions

Do NOT introduce:

React

Next.js

FastAPI

Axios

Spring Boot

Node.js backend

Groq

OpenAI API

hosted LLMs

unless explicitly requested.

The frontend must remain:

Flask + Jinja + HTML + CSS + Vanilla JavaScript

The AI models should run locally through Ollama.

Use fetch() for browser API requests.

Do not replace Flask with another framework.

4. Current Models

The current default Ollama models are:

OLLAMA_EMBEDDING_MODEL=qwen3-embedding:0.6b
OLLAMA_CHAT_MODEL=qwen3:1.7b

Do not silently replace these models.

Model names must remain configurable through environment variables.

If a coding-agent model is being selected outside the application itself, prefer a strong coding/reasoning model such as Nemotron 3.5 Lightning for complex repository work. This does not change the application's Ollama model configuration.

5. Architecture

High-level flow:

                         ┌─────────────────────┐
                         │       Browser       │
                         │ HTML/CSS/JS/Jinja   │
                         └──────────┬──────────┘
                                    │
                                    ▼
                         ┌─────────────────────┐
                         │       Flask         │
                         │   Web Application   │
                         └──────────┬──────────┘
                                    │
                ┌───────────────────┼───────────────────┐
                │                   │                   │
                ▼                   ▼                   ▼
          ┌───────────┐      ┌────────────┐      ┌───────────┐
          │   Auth    │      │ Documents  │      │   Chat    │
          └───────────┘      └─────┬──────┘      └─────┬─────┘
                                   │                   │
                                   ▼                   │
                            ┌──────────────┐           │
                            │   Approval   │           │
                            │   Workflow   │           │
                            └──────┬───────┘           │
                                   │                   │
                              APPROVED                │
                                   │                   │
                                   ▼                   │
                            ┌──────────────┐           │
                            │  Ingestion   │           │
                            └──────┬───────┘           │
                                   │                   │
                 ┌─────────────────┼─────────────────┐ │
                 │                 │                 │ │
                 ▼                 ▼                 ▼ │
              PyMuPDF          PaddleOCR          Loaders
                 │              fallback         DOCX/TXT/CSV
                 └─────────────────┼─────────────────┘
                                   │
                                   ▼
                         CharacterTextSplitter
                                   │
                                   ▼
                                Chunks
                                   │
                     ┌─────────────┴─────────────┐
                     ▼                           ▼
                  Chroma                       BM25
               Vector Store                   Index
                     │                           │
                     └─────────────┬─────────────┘
                                   ▼
                           Hybrid Retrieval
                                   │
                                   ▼
                              LangGraph
                                   │
                                   ▼
                             Ollama LLM
                                   │
                                   ▼
                         Answer + Citations

6. Current Project Structure

The current application is organized approximately as:

rag-app/
├── README.md
├── AGENTS.md
├── .env
├── .env.example
├── .gitignore
├── requirements.txt
├── run.py
│
├── app/
│   ├── __init__.py
│   ├── config.py
│   ├── extensions.py
│   │
│   ├── models/
│   │   ├── __init__.py
│   │   ├── user.py
│   │   ├── document.py
│   │   ├── chunk.py
│   │   └── conversation.py
│   │
│   ├── auth/
│   │   ├── __init__.py
│   │   ├── routes.py
│   │   └── decorators.py
│   │
│   ├── admin/
│   │   ├── __init__.py
│   │   └── routes.py
│   │
│   ├── documents/
│   │   ├── __init__.py
│   │   └── routes.py
│   │
│   ├── ingestion/
│   │   ├── __init__.py
│   │   ├── loaders.py
│   │   ├── pdf.py
│   │   ├── chunking.py
│   │   └── pipeline.py
│   │
│   ├── retrieval/
│   │   ├── __init__.py
│   │   ├── vector_store.py
│   │   ├── bm25_store.py
│   │   └── hybrid.py
│   │
│   ├── chat/
│   │   ├── __init__.py
│   │   ├── routes.py
│   │   ├── llm.py
│   │   ├── service.py
│   │   ├── state.py
│   │   ├── checkpointer.py
│   │   └── graph.py
│   │
│   ├── templates/
│   │   ├── base.html
│   │   ├── auth/
│   │   │   └── login.html
│   │   ├── admin/
│   │   │   ├── dashboard.html
│   │   │   ├── documents.html
│   │   │   └── users.html
│   │   └── chat/
│   │       └── chat.html
│   │
│   └── static/
│       ├── css/
│       │   └── style.css
│       └── js/
│           └── app.js
│
├── data/
│   ├── rag.db
│   ├── rag_checkpoints.db
│   ├── uploads/
│   └── chroma_db/
│
└── test/

Do not create every possible module in advance.

Create files/directories only when their functionality is actually implemented.

7. Development Philosophy

Build incrementally.

Do NOT implement the entire system in one step.

For every feature:

Inspect existing code.

Understand the current behavior.

Implement the smallest required change.

Run the application or relevant tests.

Fix errors.

Confirm the feature works.

Only then move to the next logical feature.

Do not jump ahead unnecessarily.

8. Existing-Code Preservation Rule

This is one of the most important rules.

Before modifying code:

Inspect the existing implementation.

Identify which parts already work.

Reuse working components.

Modify only what is necessary.

Do not rewrite unrelated files.

Do not replace working APIs without a clear reason.

Do not introduce a new framework for a small problem.

Preserve existing route names and response formats unless the requested feature requires a change.

If something is broken, fix the root cause instead of rewriting the architecture.

9. Authentication

There are two roles:

ADMIN
USER

There is no public registration.

Users are created by administrators.

The default administrator is created automatically at startup if no admin exists.

Environment variables:

DEFAULT_ADMIN_USERNAME=admin
DEFAULT_ADMIN_PASSWORD=admin123

Passwords must always be hashed.

Use:

generate_password_hash()
check_password_hash()

Never store plaintext passwords.

10. Session Authentication

Use Flask sessions.

After successful login:

session.clear()
session["user_id"] = user.id
session["role"] = user.role

Protected routes must verify the authenticated user.

Inactive users must not access protected routes.

11. Authorization

Use reusable decorators:

login_required
admin_required

Normal users must NOT be able to:

approve documents

reject documents

create administrators

access the admin dashboard

perform admin-only document management

Administrators can:

manage users

review documents

approve/reject documents

upload documents

access chat

manage documents according to admin permissions

Authorization must always be enforced server-side.

Hiding a button in JavaScript is not authorization.

12. Document Lifecycle

The lifecycle is:

PENDING
   │
   ├── APPROVED
   │      │
   │      ▼
   │  PROCESSING
   │      │
   │      ▼
   │  COMPLETED
   │
   ├── REJECTED
   │
   └── FAILED

Only COMPLETED documents are searchable.

The following are never searchable:

PENDING
APPROVED
PROCESSING
REJECTED
FAILED

APPROVED means approval has happened; it does not mean the document is already available to RAG.

13. User Upload Workflow

For a normal user:

UPLOAD
  ↓
Create DB record
  ↓
PENDING
  ↓
Admin approval
  ↓
APPROVED
  ↓
PROCESSING
  ↓
EXTRACTION
  ↓
CHUNKING
  ↓
EMBEDDING
  ↓
CHROMA + BM25
  ↓
COMPLETED

Before approval:

do not create embeddings

do not add to Chroma

do not add to BM25

do not allow RAG retrieval

14. Admin Upload Workflow

Admin uploads bypass manual approval:

UPLOAD
  ↓
APPROVED
  ↓
PROCESSING
  ↓
EXTRACTION
  ↓
CHUNKING
  ↓
EMBEDDING
  ↓
CHROMA + BM25
  ↓
COMPLETED

Once completed, the document is immediately part of the shared RAG knowledge base.

15. Shared Document Access — CRITICAL

This replaces any previous owner-only retrieval rule.

Retrieval access

All authenticated users and admins can retrieve all documents where:

status == COMPLETED

There is no condition like:

uploaded_by == current_user.id

for normal RAG retrieval.

For example:

User A uploads A.pdf
User B uploads B.pdf
Admin uploads C.pdf

After all three are COMPLETED:

User A → can retrieve A.pdf, B.pdf, C.pdf
User B → can retrieve A.pdf, B.pdf, C.pdf
Admin  → can retrieve A.pdf, B.pdf, C.pdf

Uploader identity still matters

uploaded_by is retained for:

audit

uploader display

"My Uploads"

admin management

future ownership features

It must not be used to hide completed documents from RAG retrieval.

Important distinction

RAG access ≠ management permission

A user may retrieve another user's completed document without being allowed to delete, reject, reprocess, or administer that document.

16. Selected Document Retrieval

The chat UI allows users to select documents.

When selected document IDs are supplied:

retrieve only from:
    COMPLETED documents
    AND selected document IDs

The backend must validate every selected ID.

A selected document is valid for RAG only if:

The document exists.

The document status is COMPLETED.

The authenticated user is allowed to use the shared RAG knowledge base.

Because completed documents are shared, uploader identity must not be checked.

If no documents are selected:

retrieve from all COMPLETED shared documents

This rule must be enforced in:

vector retrieval

BM25 retrieval

hybrid retrieval

Do not filter one retriever differently from the other.

17. Supported Documents

Initial formats:

.pdf
.doc
.docx
.txt
.csv

The ingestion architecture should remain extensible.

Do not hard-code the system around PDF only.

18. PDF Processing

Use PyMuPDF (fitz) first.

Strategy:

PDF page
   ↓
PyMuPDF native text extraction
   ↓
Is text sufficient?
   ├── YES → use native text
   └── NO
         ↓
      rasterize page
         ↓
      PaddleOCR
         ↓
      OCR text

Do not OCR every page unnecessarily.

19. OCR

Use PaddleOCR as the fallback engine.

OCR is appropriate when:

native text is missing

native text is suspiciously short

the PDF is scanned

the page is image-based

Each page should retain:

extraction_method = native

or:

extraction_method = paddleocr

Prefer singleton/lazy OCR initialization so the model is not repeatedly initialized.

Current PaddleOCR setup includes compatibility environment flags where required by the installed version. Do not remove working compatibility settings without testing the installed PaddleOCR version.

20. Tables

Table processing is separate from ordinary OCR.

Do not assume OCR preserves table structure.

Future intended approach:

PDF
 ↓
Table detection
 ↓
Table extraction
 ↓
Structured representation
 ↓
RAG-friendly text representation
 ↓
Chunking
 ↓
Embedding

Where possible, retain both:

Structured/table representation.

Natural-language representation.

Example:

Name,Age,Department
John,25,IT
Sarah,28,HR

can also become:

Name: John
Age: 25
Department: IT

Name: Sarah
Age: 28
Department: HR

Do not introduce advanced table extraction until the basic ingestion pipeline is stable.

21. Chunking

Use:

CharacterTextSplitter

Current intended configuration:

CharacterTextSplitter(
    separator="\n",
    chunk_size=1000,
    chunk_overlap=150,
    length_function=len,
)

Do not change chunking parameters casually because retrieval behavior depends on them.

Every chunk must preserve traceable metadata.

Minimum metadata:

document_id
filename
page_number
chunk_id
chunk_index
content_type
extraction_method
status

Uploader metadata may be retained for provenance, but must not become an unintended retrieval restriction.

22. Chroma

Use persistent Chroma.

Current path:

data/chroma_db/

Current collection:

my_documents

Use:

langchain-chroma

Embedding model:

qwen3-embedding:0.6b

Chroma must contain only content that is eligible for RAG.

When a document is deleted, its vectors must be deleted.

When a document is no longer COMPLETED, it must not remain retrievable.

23. BM25

Use rank-bm25.

BM25 complements semantic retrieval.

Useful for:

exact terms

names

technical terminology

numbers

identifiers

rare phrases

The BM25 index must use the same shared-access rules as Chroma:

COMPLETED documents only

and, when selected document IDs are provided:

selected document IDs only

Do not accidentally reintroduce:

uploaded_by == current_user.id

into BM25.

24. SQLAlchemy Session Rule

Never allow detached SQLAlchemy objects to leak into retrieval logic.

A common failure is:

Parent instance <DocumentChunk ...> is not bound to a Session;
lazy load operation of attribute 'document' cannot proceed

This usually happens when code accesses:

chunk.document

after the SQLAlchemy session has closed.

Preferred fix

When loading chunks that need the related document, eagerly load the relationship:

from sqlalchemy.orm import joinedload

chunks = (
    DocumentChunk.query
    .options(joinedload(DocumentChunk.document))
    .join(Document)
    .filter(Document.status == "COMPLETED")
    .all()
)

Do not fix this by randomly calling merge() or add() on detached objects.

Better retrieval boundary

Convert ORM objects into plain dictionaries while the session is active:

{
    "chunk_id": chunk.chunk_id,
    "document_id": chunk.document_id,
    "filename": chunk.document.filename,
    "content": chunk.content,
    "page_number": chunk.page_number,
    "chunk_index": chunk.chunk_index,
    "extraction_method": chunk.extraction_method,
}

The retrieval and LangGraph layers should preferably operate on plain serializable data rather than SQLAlchemy ORM instances.

This makes:

Database
   ↓
ORM query
   ↓
plain dictionaries
   ↓
retrieval
   ↓
LangGraph

the preferred boundary.

25. Hybrid Retrieval

Architecture:

User Query
    │
    ├───────────────┐
    ▼               ▼
Vector Search     BM25
    │               │
    └───────┬───────┘
            ▼
      Combine Results
            ▼
        Normalize
            ▼
       Rank / Merge
            ▼
       Top Chunks

Current intended weighting:

Vector = 0.7
BM25   = 0.3

Chroma distance may be converted into a similarity score such as:

1 / (1 + distance)

then normalized before combining.

Do not replace hybrid retrieval with vector-only retrieval unless explicitly requested.

26. Retrieval Debugging

When debugging retrieval, inspect:

Question
   ↓
Standalone / rewritten question
   ↓
Vector results
   ↓
BM25 results
   ↓
Merged results
   ↓
Final context
   ↓
Prompt
   ↓
LLM response

Do not immediately blame the LLM.

First verify whether the correct chunk was retrieved.

Log useful information such as:

[RETRIEVAL] Vector results: 5
[RETRIEVAL] BM25 results: 5
[RETRIEVAL] Hybrid results: 5

Do not print entire document contents unnecessarily.

27. LangGraph State

Current conceptual state includes:

user_id
is_admin
selected_document_ids
messages
standalone_question
retrieved_documents
context
answer
sources

user_id and is_admin represent authenticated request context.

They must not be interpreted as uploader-based RAG restrictions.

selected_document_ids is the retrieval scope when the user explicitly selects files.

28. LangGraph Workflow

Preferred graph:

START
  ↓
rewrite_query
  ↓
retrieve
  ↓
build_context
  ↓
generate_answer
  ↓
END

For follow-up questions:

Conversation History
       ↓
Rewrite / Understand Question
       ↓
Hybrid Retrieval
       ↓
Context
       ↓
Answer

Do not introduce unnecessary agents or multi-agent architecture.

This is a RAG application, not a multi-agent system.

29. Conversation Memory

Example:

User:
What is the refund policy?

Assistant:
The refund period is 30 days. [1]

User:
What about digital products?

Assistant:
The policy states... [2]

Conversation history helps interpret follow-up questions.

However:

Conversation history != document evidence

Documents remain the source of truth.

Use LangGraph checkpointing.

Checkpoint database:

data/rag_checkpoints.db

Each conversation should use a stable thread ID.

30. RAG Answering

The LLM must answer from retrieved document context.

The system prompt should enforce:

use retrieved context

do not invent unsupported facts

say when the answer is not present

preserve source references

use conversation history only for conversational understanding

do not treat conversation memory as authoritative evidence

Current local chat model:

qwen3:1.7b

31. Citations

Every retrieved chunk must be traceable to its source.

Frontend citations should look like:

The refund period is 30 days. [1]

and:

Digital products are excluded. [2]

Citation numbers must correspond to actual retrieved source chunks.

Never generate fake citations.

Prefer source metadata containing:

document_id
filename
page_number
chunk_id

32. Source Panel

The chat UI must remain a three-column layout:

┌──────────────┬─────────────────────────┬──────────────────┐
│ Documents    │          Chat           │     Sources      │
│              │                         │                  │
│ Upload       │ User question           │ [1] Document     │
│              │                         │     content      │
│ Documents    │ Assistant answer [1]    │                  │
│              │                         │ [2] Document     │
│              │                         │     content      │
└──────────────┴─────────────────────────┴──────────────────┘

Clicking [1] should:

Open the corresponding source in the right panel.

Show the original relevant source content.

Highlight the cited text where possible.

Scroll the relevant content into view.

Do not open a new browser tab.

Do not use PDF.js unless explicitly requested.

33. Document Sidebar / Selection

The left side of chat should allow users to:

see available documents

see upload status

select documents for retrieval

distinguish their own uploads from shared documents where useful

see processing state

upload documents

Recommended conceptual organization:

My Uploads
  ├── document A
  └── document B

Shared Documents
  ├── document C
  ├── document D
  └── document E

A completed document from another user is selectable.

Pending/rejected/failed/processing documents must not be selectable for RAG.

Do not use UI state as the security boundary. The backend must validate selected document IDs.

34. Upload Status UI

Uploading a document should show a status box.

Example:

document.pdf

Waiting for approval

For admin uploads:

document.pdf

Processing...

The status UI should support a more detailed progress view where practical:

Upload
  ✓

Approval
  ✓

Extraction
  ✓

OCR
  ✓ / not required

Chunking
  ✓

Embedding
  ...

Chroma
  ...

BM25
  ...

Completed

Do not fake progress.

Only display a stage as completed when the backend actually completed it.

User uploads should clearly indicate that administrator approval is required.

Admin uploads should not wait for approval.

35. Chat Generation State

While an answer is being generated, the UI should clearly indicate that the assistant is working.

For example:

Generating...

or:

Thinking...

The state must disappear when the request finishes or fails.

Do not leave the UI permanently stuck in a loading state after an exception.

36. Security

Security is a first-class requirement.

Implement:

password hashing

session authentication

role-based authorization

secure filenames

upload validation

file size limits

allowed extensions

path traversal protection

server-side document ID validation

server-side selected-document validation

CSRF protection where appropriate

safe error messages

no arbitrary filesystem access

no exposure of internal server paths

Never trust client-provided:

filename
user_id
document_id
role
selected_document_ids

Always validate them server-side.

Important

Do not confuse shared RAG access with management permissions.

A normal user can retrieve any COMPLETED document, but this does not grant them permission to administer that document.

37. File Upload Security

Never concatenate a raw user filename directly into a filesystem path.

Use secure filename handling.

Validate:

extension
file type where appropriate
file size
filename

Store uploaded files under:

data/uploads/

Users must not be able to access arbitrary files on the server.

38. Configuration

Use .env for configurable values.

Example:

FLASK_SECRET_KEY=change-this-secret-key

DEFAULT_ADMIN_USERNAME=admin
DEFAULT_ADMIN_PASSWORD=admin123

CHROMA_PERSIST_DIRECTORY=data/chroma_db
CHROMA_COLLECTION_NAME=my_documents

OLLAMA_EMBEDDING_MODEL=qwen3-embedding:0.6b
OLLAMA_CHAT_MODEL=qwen3:1.7b

Never commit .env.

.env.example must contain safe example values.

The default admin password is only appropriate for local development.

39. Database

SQLite is the application database.

Current database:

data/rag.db

Expected core models:

User
Document
DocumentChunk
Conversation

Add models only when necessary.

Do not create unnecessary tables.

40. Code Organization

Routes

Routes should handle:

HTTP requests

authentication checks

validation

calling services

returning JSON/templates

Routes should not contain large RAG pipelines.

Services

Business logic belongs in services.

Ingestion

Extraction and processing belong in ingestion modules.

Retrieval

Vector, BM25, and hybrid retrieval belong in retrieval modules.

Chat / RAG

LangGraph, LLM calls, context construction, and conversation handling belong in chat/RAG modules.

Models

SQLAlchemy models should contain database structure and small domain helpers.

41. Error Handling

Never silently swallow exceptions.

Bad:

try:
    ...
except:
    pass

Prefer:

try:
    ...
except Exception as exc:
    logger.exception("Document processing failed")

Document failures should update:

FAILED

where appropriate.

Do not expose stack traces to normal users.

For debugging, logs should contain enough information to locate the failing stage.

42. Logging

Use clear stage prefixes.

Examples:

[AUTH]
[UPLOAD]
[DOCUMENT]
[INGESTION]
[OCR]
[CHUNKING]
[EMBEDDING]
[CHROMA]
[BM25]
[RETRIEVAL]
[RAG]
[CHAT]
[CHECKPOINT]

Example:

[INGESTION] Processing document 12
[OCR] Page 3 requires OCR
[CHUNKING] Created 42 chunks
[EMBEDDING] Indexing 42 chunks
[RETRIEVAL] Vector results: 5
[RETRIEVAL] BM25 results: 5
[RAG] Generating answer

Do not log entire document contents or sensitive information.

43. Ingestion Debugging

Debug ingestion in this order:

File
 ↓
File type
 ↓
Extraction
 ↓
Extracted text
 ↓
Chunks
 ↓
Chunk metadata
 ↓
Embeddings
 ↓
Chroma
 ↓
BM25
 ↓
COMPLETED

Log counts for:

pages

extracted characters

OCR pages

chunks

embeddings

indexed chunks

Do not print entire documents.

44. Metadata Rule

Metadata is essential for:

citations

source viewer

debugging

retrieval filtering

document management

Every chunk must remain traceable:

document
  ↓
page
  ↓
chunk
  ↓
retrieval result
  ↓
citation

Do not strip metadata during:

chunking

embedding

retrieval

ranking

context construction

answer generation

45. Testing Strategy

Test every major layer.

Prioritize:

Authentication
Authorization
Document upload
Document status workflow
Shared document access
Selected document filtering
File validation
PDF extraction
OCR fallback
Chunk metadata
Chroma indexing
BM25 indexing
Hybrid retrieval
Citation mapping
RAG responses
Conversation memory
Source viewer

Required shared-access test

Use at least:

User A
User B
Admin

Scenario:

User A uploads a document containing ALPHA-123.

Admin approves and processes it.

User B uploads a document containing BETA-456.

Admin approves and processes it.

Admin uploads a third document and it is processed directly.

User A can retrieve information from A, B, and admin documents.

User B can retrieve information from A, B, and admin documents.

Admin can retrieve all completed documents.

Selecting only A's document retrieves only A's document.

Selecting only B's document retrieves only B's document.

Pending/rejected/failed/processing documents never retrieve.

Deleting a document removes it from RAG.

Citations map to the correct source.

Follow-up questions preserve conversation context.

SQLAlchemy detached-object regression test

Ensure retrieval code does not fail with:

Parent instance <DocumentChunk ...> is not bound to a Session

When related document information is needed, either:

eager-load the relationship, or

serialize the data while the session is active.

46. Development Phases

The original broad phases are retained, but the current project is beyond the foundation stage.

Phase 1 — Foundation

Flask

configuration

SQLite

SQLAlchemy

User

default admin

login/logout

sessions

authorization

Completed/working foundation should not be rewritten.

Phase 2 — User Management

admin user list

create users

activate/deactivate users

password handling

Phase 3 — Document Upload

upload UI

validation

storage

PENDING status

document list

Phase 4 — Admin Approval

admin document list

approve

reject

status updates

Phase 5 — Basic Ingestion

TXT

CSV

DOCX

PDF with PyMuPDF

CharacterTextSplitter

metadata

Phase 6 — OCR

scanned PDF detection

PaddleOCR fallback

extraction metadata

OCR error handling

Phase 7 — Tables

table detection/extraction

structured representation

RAG-friendly representation

Phase 8 — Chroma

Ollama embeddings

persistent Chroma

indexing

cleanup

completed-document filtering

Phase 9 — BM25

BM25 indexing

rebuilding

completed-document filtering

Phase 10 — Hybrid Retrieval

vector + BM25

scoring

merging

selected-document filtering

shared completed-document access

Phase 11 — RAG + Ollama

context construction

prompt

grounded answer

sources

Phase 12 — LangGraph

state

graph

checkpointing

conversation memory

follow-up question rewriting

Phase 13 — Chat UI

three-column layout

conversations

document selection

upload status

generation state

clickable citations

source panel

source highlighting

Phase 14 — Evaluation

RAGAS

ground-truth dataset

retrieval quality

faithfulness

context precision

context recall

answer relevance

Do not implement future phases merely because they are listed here. Work only on the requested phase/feature.

47. Current Development Priorities

When modifying the current application, prioritize in this order:

1. Keep existing working authentication
2. Keep document approval workflow
3. Ensure completed documents are shared
4. Ensure selected documents constrain retrieval
5. Fix retrieval/session issues
6. Make upload/processing status visible
7. Improve chat generation state
8. Complete citations/source viewer
9. Improve admin UI
10. Improve RAG evaluation

Do not rebuild the system from scratch.

48. Dependency Rules

Do not add dependencies casually.

Before adding a package:

Check whether the current stack already solves the problem.

Determine whether the package is actually necessary.

Add it only when justified.

Update requirements.txt.

Test the application after adding it.

Avoid duplicate libraries.

For example, do not add another PDF library when PyMuPDF already satisfies the requirement unless a specific missing capability requires it.

49. Frontend Rules

Use:

Jinja
HTML
CSS
Vanilla JavaScript
fetch()

Do not introduce React.

Do not introduce Axios.

Keep JavaScript readable and modular.

Preserve the existing three-column chat layout.

Do not redesign working pages unnecessarily.

50. UI Principles

The UI should be:

clean

modern

simple

responsive

functional

easy to understand

Prioritize functionality and reliability over decorative UI.

Important states must be visible:

uploading
waiting for approval
approved
processing
extracting
chunking
embedding
indexing
completed
failed
generating

Do not fake backend progress.

51. RAG Quality Principles

The target pipeline is:

Correct Retrieval
       ↓
Relevant Context
       ↓
Grounded Answer
       ↓
Traceable Citation

If the information is not present in the retrieved context, the assistant should say it cannot find the answer rather than hallucinating.

A confident answer is not a successful RAG answer if the supporting evidence was not retrieved.

52. Retrieval Access Invariant

This invariant must always remain true:

RAG-eligible document
    =
status == COMPLETED

Default retrieval:

all COMPLETED documents

Selected retrieval:

COMPLETED AND document_id IN selected_document_ids

Never:

COMPLETED AND uploaded_by == current_user.id

unless a future feature explicitly introduces private documents.

If such a feature is introduced later, it must be explicitly designed rather than accidentally emerging from existing retrieval code.

53. Deletion / Reprocessing Invariant

When a document is deleted:

SQLite Document
   ↓
delete DocumentChunk rows
   ↓
delete Chroma vectors
   ↓
remove from BM25 representation
   ↓
document no longer searchable

When a document is reprocessed:

old chunks must be cleaned up

old vectors must be cleaned up

new chunks must be indexed

BM25 must reflect the new content

status must accurately reflect the current processing result

Avoid stale index entries.

54. If Something Is Broken

Do not immediately rewrite the architecture.

First determine:

What failed?
Where did it fail?
What is the exact error?
Which module owns that behavior?
Is the failure caused by data, session state, retrieval, ingestion, or UI?

Then fix the smallest root cause.

For example, for:

Parent instance <DocumentChunk ...> is not bound to a Session

inspect relationship loading and session lifetime before changing retrieval architecture.

55. Codex Working Procedure

When asked to implement a feature:

Step 1

Inspect relevant existing files.

Step 2

Briefly identify what needs to change.

Step 3

Implement only the requested feature/fix.

Step 4

Preserve unrelated working functionality.

Step 5

Run relevant tests or the application.

Step 6

If an error occurs, fix it before claiming completion.

Step 7

Report:

Changed:
- file 1
- file 2

Why:
- short explanation

Test:
- command/result

Next:
- next logical step

Do not silently make unrelated improvements.

56. Never Do These Things Without Explicit Request

Do not:

migrate Flask to FastAPI

migrate Flask/Jinja to React

replace SQLite with PostgreSQL

replace Chroma

remove BM25

replace CharacterTextSplitter

replace PyMuPDF

replace PaddleOCR

replace Ollama with a hosted API

introduce Redis

introduce Celery

introduce Kubernetes

introduce microservices

introduce multi-agent architecture

rewrite the entire project

change the default embedding model

change the default chat model

make completed documents private based on uploader

trust client-provided document access

fake processing progress

unless explicitly requested.

57. Final Engineering Rule

The most important rule:

Preserve working functionality, make the smallest correct change, test it, and only then extend the system.

The current RAG architecture is:

Flask
  ↓
SQLite / SQLAlchemy
  ↓
Authentication
  ↓
Documents + Approval
  ↓
PyMuPDF / PaddleOCR / Loaders
  ↓
CharacterTextSplitter
  ↓
Chunks + Metadata
  ↓
Chroma + BM25
  ↓
Shared Completed-Document Retrieval
  ↓
Hybrid Retrieval
  ↓
LangGraph
  ↓
Ollama
  ↓
Grounded Answer
  ↓
Citations
  ↓
NotebookLM-style Chat UI

The central retrieval rule is:

COMPLETED documents are shared across all authenticated users and admin.

Uploader identity is for management/audit, not RAG visibility.

Always preserve traceability:

document
  → page
  → chunk
  → retrieval result
  → citation

And always preserve the separation:

RAG retrieval permission
        ≠
document management permission
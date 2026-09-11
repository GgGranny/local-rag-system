# RAG Application — Codex Engineering Instructions

## 1. Project Overview

This project is a local, document-grounded RAG (Retrieval-Augmented Generation) application.

The application allows users to:

* Log in to the system.
* Upload documents.
* Wait for administrator approval.
* Chat with approved and processed documents.
* Ask follow-up questions using conversation memory.
* View citations/sources used to generate answers.

Administrators can:

* Log in through the admin portal.
* Create and manage users.
* Review uploaded documents.
* Approve or reject user documents.
* Upload documents directly without approval.
* Monitor document processing.
* Use the same chat/RAG functionality as normal users.

The system is intended to run locally and use local AI models through Ollama.

---

# 2. Core Technology Stack

Use the following technologies unless there is a strong technical reason not to.

### Backend / Web

* Python
* Flask
* Flask-SQLAlchemy
* Flask sessions
* HTML
* CSS
* Vanilla JavaScript

### Database

* SQLite

SQLite stores application state such as:

* users
* documents
* document processing status
* conversations
* messages
* metadata required by the application

### RAG

* LangChain
* LangGraph
* ChromaDB
* BM25
* Ollama
* `langchain-ollama`
* `langchain-chroma`

### Document processing

* PyMuPDF (`fitz`) for PDF text extraction
* PaddleOCR for OCR fallback
* DOC/DOCX extraction
* TXT extraction
* CSV extraction

### Chunking

Use:

```text
CharacterTextSplitter
```

Do not introduce a different chunking strategy unless explicitly requested.

### Retrieval

Use hybrid retrieval:

```text
Vector Search + BM25
```

The final retriever should combine semantic similarity with lexical matching.

---

# 3. Important Technology Restrictions

## DO NOT use

* React
* Next.js
* FastAPI
* Axios
* Spring Boot
* Node.js backend
* External hosted LLMs unless explicitly requested
* Groq unless explicitly requested
* OpenAI API unless explicitly requested

The frontend must remain:

```text
Flask + Jinja templates + HTML + CSS + Vanilla JavaScript
```

The AI models should run locally through Ollama.

---

# 4. Architecture

The high-level architecture is:

```text
                         ┌─────────────────────┐
                         │       Browser       │
                         │ HTML/CSS/JS         │
                         └──────────┬──────────┘
                                    │
                                    ▼
                         ┌─────────────────────┐
                         │       Flask         │
                         │ Web Application     │
                         └──────────┬──────────┘
                                    │
              ┌─────────────────────┼─────────────────────┐
              │                     │                     │
              ▼                     ▼                     ▼
        ┌───────────┐         ┌───────────┐        ┌────────────┐
        │   Auth    │         │ Documents │        │    Chat    │
        └───────────┘         └─────┬─────┘        └─────┬──────┘
                                    │                     │
                                    ▼                     │
                            ┌───────────────┐             │
                            │ Approval      │             │
                            │ Workflow      │             │
                            └───────┬───────┘             │
                                    │                     │
                              APPROVED ONLY              │
                                    │                     │
                                    ▼                     │
                            ┌───────────────┐             │
                            │  Ingestion    │             │
                            └───────┬───────┘             │
                                    │                     │
                 ┌──────────────────┼──────────────────┐  │
                 │                  │                  │  │
                 ▼                  ▼                  ▼  │
             PyMuPDF            PaddleOCR          Loaders│
             PDF Text            OCR Fallback       DOC/TXT/CSV
                 │                  │                  │
                 └──────────────────┼──────────────────┘
                                    │
                                    ▼
                         ┌─────────────────────┐
                         │ CharacterTextSplitter│
                         └──────────┬──────────┘
                                    │
                                    ▼
                              ┌───────────┐
                              │  Chunks   │
                              └─────┬─────┘
                                    │
                     ┌──────────────┴──────────────┐
                     ▼                             ▼
              ┌─────────────┐               ┌─────────────┐
              │   Chroma    │               │    BM25     │
              │ Vector DB   │               │   Index     │
              └──────┬──────┘               └──────┬──────┘
                     │                             │
                     └──────────────┬──────────────┘
                                    ▼
                         ┌─────────────────────┐
                         │ Hybrid Retrieval    │
                         └──────────┬──────────┘
                                    │
                                    ▼
                            ┌──────────────┐
                            │ Ollama LLM   │
                            └──────┬───────┘
                                   │
                                   ▼
                         Answer + Citations
```

---

# 5. Project Structure

Use a modular structure.

The exact structure can evolve as the application grows, but follow this general organization:

```text
rag-app/
│
├── AGENTS.md
├── README.md
├── requirements.txt
├── .env
├── .env.example
├── .gitignore
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
│   │   ├── conversation.py
│   │   └── message.py
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
│   │   ├── routes.py
│   │   └── services.py
│   │
│   ├── ingestion/
│   │   ├── __init__.py
│   │   ├── pipeline.py
│   │   ├── loaders.py
│   │   ├── pdf.py
│   │   ├── ocr.py
│   │   ├── tables.py
│   │   └── chunking.py
│   │
│   ├── retrieval/
│   │   ├── __init__.py
│   │   ├── vector.py
│   │   ├── bm25.py
│   │   └── hybrid.py
│   │
│   ├── rag/
│   │   ├── __init__.py
│   │   ├── graph.py
│   │   ├── state.py
│   │   ├── prompts.py
│   │   └── service.py
│   │
│   ├── chat/
│   │   ├── __init__.py
│   │   └── routes.py
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
│   ├── uploads/
│   ├── chroma/
│   └── indexes/
│
└── tests/
```

Do not create every directory immediately.

Create directories only when their functionality is implemented.

---

# 6. Development Philosophy

Build the application incrementally.

Do NOT implement the entire RAG system in one step.

Each phase must:

1. Implement one logical feature.
2. Run the application.
3. Test the feature.
4. Fix errors.
5. Confirm the feature works.
6. Only then move to the next phase.

Do not jump ahead.

---

# 7. Current Development Phase

The application is currently in the foundation/authentication phase.

Current goals:

```text
Flask
  ↓
SQLite
  ↓
User model
  ↓
Admin model/role
  ↓
Login
  ↓
Session authentication
  ↓
Role authorization
  ↓
Admin dashboard
```

Do NOT implement:

* Chroma
* BM25
* OCR
* embeddings
* RAG
* LangGraph
* document ingestion

until the authentication foundation is confirmed working.

---

# 8. Authentication Requirements

There are two roles:

```text
ADMIN
USER
```

There is no public registration.

Users are created by administrators.

The default administrator is created automatically when the application starts if no admin exists.

Environment variables:

```env
DEFAULT_ADMIN_USERNAME=admin
DEFAULT_ADMIN_PASSWORD=admin123
```

Passwords must always be hashed.

Never store plaintext passwords in the database.

Use Werkzeug password hashing:

```python
generate_password_hash()
check_password_hash()
```

---

# 9. Session Authentication

Use Flask sessions.

After successful login:

```python
session.clear()

session["user_id"] = user.id
session["role"] = user.role
```

Authenticated routes must verify that the session contains a valid user.

Inactive users must not be allowed to access protected routes.

---

# 10. Authorization

Create reusable decorators.

At minimum:

```text
login_required
admin_required
```

Normal users must NOT be able to:

* approve documents
* reject documents
* create administrators
* access admin dashboard
* access other users' private documents

Administrators can:

* manage users
* review documents
* approve/reject documents
* upload documents
* access chat

Authorization must always be enforced on the server.

Do not rely only on hiding buttons in JavaScript.

---

# 11. Document Workflow

Document lifecycle:

```text
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
```

## User upload

When a normal user uploads a document:

```text
UPLOAD
   ↓
Create DB record
   ↓
PENDING
```

Nothing should be indexed yet.

Do NOT:

* create embeddings
* add to Chroma
* add to BM25

until an administrator approves the document.

---

# 12. Admin Upload

When an administrator uploads a document:

```text
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
```

Admin uploads do not require manual approval.

---

# 13. Retrieval Restrictions

The RAG system must only retrieve content from documents whose status is:

```text
COMPLETED
```

Never retrieve from:

```text
PENDING
PROCESSING
REJECTED
FAILED
```

If a document is rejected or deleted, its indexed content must not remain searchable.

---

# 14. Supported Documents

Initial supported formats:

```text
.pdf
.doc
.docx
.txt
.csv
```

The architecture should make it possible to add more formats later.

Do not hard-code the ingestion pipeline around PDF only.

---

# 15. PDF Processing

Use PyMuPDF (`fitz`) as the primary PDF extraction library.

Processing strategy:

```text
PDF
 ↓
PyMuPDF native text extraction
 ↓
Is extracted text sufficient?
 ├── YES → use extracted text
 └── NO
       ↓
   Rasterize page
       ↓
   PaddleOCR
       ↓
   OCR text
```

Do not OCR every page unnecessarily.

Native PDF text extraction should be attempted first.

---

# 16. OCR

Use PaddleOCR as the fallback OCR engine.

OCR should primarily be used when:

* the page contains little/no native text
* the PDF is scanned
* the PDF page is image-based

Each extracted page should retain metadata such as:

```text
extraction_method = pymupdf
```

or:

```text
extraction_method = paddleocr
```

OCR initialization should avoid repeatedly creating the OCR model.

Prefer a singleton/lazy initialization pattern.

---

# 17. Tables

Table extraction is separate from normal OCR.

Do not assume OCR automatically preserves table structure.

The intended table pipeline is:

```text
PDF
 ↓
Table detection
 ↓
Table extraction
 ↓
CSV representation
 ↓
Normalized text representation
 ↓
Chunking
 ↓
Embedding
```

For RAG, table data should have both:

1. Structured representation where possible.
2. Natural-language/text representation for semantic retrieval.

Example:

```text
CSV:

Name,Age,Department
John,25,IT
Sarah,28,HR
```

Can additionally become:

```text
Name: John
Age: 25
Department: IT

Name: Sarah
Age: 28
Department: HR
```

This makes table content easier for retrieval.

Do not implement advanced table extraction until the basic ingestion pipeline is working.

---

# 18. Chunking

Use:

```text
CharacterTextSplitter
```

Chunk metadata must be preserved.

At minimum, metadata should include:

```text
document_id
filename
page_number
chunk_id
content_type
extraction_method
```

Potential future metadata:

```text
table_id
source_type
file_type
```

Never create chunks without traceable source metadata.

---

# 19. Chroma

Use Chroma as the persistent vector database.

Current intended path:

```text
data/chroma/
```

Use:

```text
langchain-chroma
```

The embedding model should be provided by Ollama.

Current preferred embedding model:

```text
qwen3-embedding:0.6b
```

Do not replace the embedding model unless explicitly requested.

---

# 20. BM25

Use BM25 as the lexical retrieval component.

The purpose of BM25 is to complement semantic vector retrieval.

Vector search is good for:

```text
semantic similarity
```

BM25 is useful for:

```text
exact terms
names
keywords
technical terminology
numbers
rare phrases
```

---

# 21. Hybrid Retrieval

The intended retrieval architecture:

```text
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
       Rank / Merge
            ▼
      Context Chunks
            ▼
         Ollama
```

Do not replace hybrid retrieval with vector-only retrieval unless explicitly requested.

---

# 22. Ollama

Use local Ollama models.

The application should communicate with Ollama through:

```text
langchain-ollama
```

Do not introduce cloud LLM APIs by default.

Keep model names configurable through environment variables where appropriate.

Example:

```env
OLLAMA_LLM_MODEL=
OLLAMA_EMBEDDING_MODEL=qwen3-embedding:0.6b
```

Never hard-code credentials for external services.

---

# 23. RAG Answering

The LLM must answer using retrieved document context.

The system prompt should enforce:

* use retrieved context
* do not invent unsupported facts
* clearly indicate when the answer is not present
* preserve source references
* answer follow-up questions using conversation history plus retrieved context

The model should not treat conversation memory as authoritative document evidence.

---

# 24. Conversation Memory

The application should support conversational questions.

Example:

```text
User:
What is the refund policy?

Assistant:
The refund period is 30 days. [1]

User:
What about digital products?

Assistant:
For digital products, the policy states... [2]
```

The second question may require the previous conversation to understand what "digital products" refers to.

However:

```text
Conversation history ≠ source of truth
```

Documents remain the source of truth.

Use LangGraph checkpointing for persistent conversation state.

Planned checkpoint database:

```text
data/rag_checkpoints.db
```

---

# 25. LangGraph

Use LangGraph for the RAG workflow and checkpointed conversation state.

Keep graph state explicit.

A conceptual flow:

```text
START
  ↓
Receive Question
  ↓
Load Conversation State
  ↓
Understand / Rewrite Query if Necessary
  ↓
Hybrid Retrieval
  ↓
Build Context
  ↓
Generate Answer
  ↓
Attach Sources
  ↓
Save Conversation State
  ↓
END
```

Do not introduce unnecessary agents or complex multi-agent architecture.

This is a RAG application, not a multi-agent system.

---

# 26. Citations

Every retrieved chunk must have enough metadata to trace it back to the original document.

The frontend should eventually display citations such as:

```text
The company provides a 30-day refund period. [1]
```

and:

```text
Digital products are excluded from refunds. [2]
```

Citations should correspond to actual retrieved source chunks.

Do not generate fake citation numbers.

---

# 27. Source Panel

The chat interface should eventually have three columns:

```text
┌──────────────┬─────────────────────────┬──────────────────┐
│              │                         │                  │
│ Documents    │          Chat           │     Sources      │
│              │                         │                  │
│ Upload       │ User question           │ [1] Document     │
│              │                         │     content      │
│ My documents │ Assistant answer [1]    │                  │
│              │                         │ [2] Document     │
│              │                         │     content      │
└──────────────┴─────────────────────────┴──────────────────┘
```

Future citation behavior:

```text
Click [1]
   ↓
Open source in right panel
   ↓
Show original relevant content
   ↓
Highlight cited text
   ↓
Scroll source into view
```

Do not open a new browser tab.

Do not use PDF.js unless explicitly requested.

---

# 28. Security

Security is a first-class requirement.

Implement:

* password hashing
* session authentication
* role-based authorization
* secure filenames
* upload validation
* file size limits
* allowed file extensions
* path traversal protection
* ownership checks
* CSRF protection where appropriate
* safe error messages
* no arbitrary filesystem access
* no exposure of internal server paths

Never trust:

```text
filename
user_id
document_id
role
```

coming from the client.

Always validate them server-side.

---

# 29. File Upload Security

Never directly concatenate user-provided filenames into filesystem paths.

Use secure filename handling.

Validate:

```text
extension
MIME/type where appropriate
file size
filename
```

Store uploaded files under:

```text
data/uploads/
```

Users must not be able to access arbitrary files on the server.

---

# 30. Configuration

Use `.env` for configurable values.

Example:

```env
FLASK_SECRET_KEY=change-this-secret-key

DEFAULT_ADMIN_USERNAME=admin
DEFAULT_ADMIN_PASSWORD=admin123

OLLAMA_LLM_MODEL=
OLLAMA_EMBEDDING_MODEL=qwen3-embedding:0.6b
```

Do not commit `.env`.

`.env.example` should contain safe example values.

The default admin password is only suitable for local development.

---

# 31. Database

SQLite is the application database.

Keep database models separated by domain.

Expected models:

```text
User
Document
Conversation
Message
```

Additional models can be introduced when necessary.

Do not create unnecessary database tables.

---

# 32. Code Organization Rules

Keep responsibilities separated.

### Routes

Routes should handle:

* HTTP requests
* authentication checks
* input validation
* calling services
* returning responses/templates

Routes should NOT contain large RAG pipelines.

### Services

Business logic belongs in services.

### Ingestion

Document extraction and processing belong in ingestion modules.

### Retrieval

Retrieval logic belongs in retrieval modules.

### RAG

LangGraph and answer generation belong in RAG modules.

### Models

SQLAlchemy models should contain database structure and small domain helpers.

---

# 33. Error Handling

Do not silently swallow exceptions.

Bad:

```python
try:
    ...
except:
    pass
```

Prefer:

```python
try:
    ...
except Exception as exc:
    logger.exception("Document processing failed")
```

Document failures should update document status:

```text
FAILED
```

where appropriate.

Store enough information to diagnose the failure.

Do not expose sensitive stack traces to normal users.

---

# 34. Logging

Use useful structured/logged messages for important operations.

Examples:

```text
[AUTH]
[UPLOAD]
[DOCUMENT]
[INGESTION]
[OCR]
[EMBEDDING]
[RETRIEVAL]
[RAG]
```

Example:

```text
[INGESTION] Processing document 12
[OCR] Page 3 requires OCR
[EMBEDDING] Creating embeddings for 42 chunks
[RETRIEVAL] Vector results: 5
[RETRIEVAL] BM25 results: 5
```

Avoid excessive logging of document contents or sensitive information.

---

# 35. Testing Strategy

Every major component should eventually have tests.

Prioritize:

```text
Authentication
Authorization
Document status workflow
File validation
PDF extraction
OCR fallback
Chunk metadata
Retrieval
Citation mapping
RAG responses
Conversation memory
```

Before moving to the next development phase, manually verify the current phase works.

---

# 36. Development Phases

Follow this order.

## Phase 1 — Foundation

Implement:

* Flask application
* configuration
* SQLite
* SQLAlchemy
* User model
* default admin
* login
* logout
* sessions
* role authorization
* admin dashboard

Stop and test.

---

## Phase 2 — User Management

Implement:

* admin user list
* create user
* activate/deactivate user
* delete user if required
* password handling

Stop and test.

---

## Phase 3 — Document Upload

Implement:

* upload UI
* file validation
* document model
* upload storage
* PENDING status
* user document list

At this stage do NOT implement embeddings.

Stop and test.

---

## Phase 4 — Admin Document Approval

Implement:

* admin document list
* pending documents
* approve
* reject
* status updates

Stop and test.

---

## Phase 5 — Basic Ingestion

Implement:

* TXT
* CSV
* DOC/DOCX
* PDF using PyMuPDF
* CharacterTextSplitter
* metadata

Do not implement hybrid retrieval yet.

Stop and test.

---

## Phase 6 — OCR

Add:

* scanned PDF detection
* PaddleOCR fallback
* extraction metadata
* OCR error handling

Do not redesign the entire ingestion pipeline.

Stop and test.

---

## Phase 7 — Table Processing

Add table extraction separately.

Convert extracted tables to:

```text
CSV
```

and:

```text
RAG-friendly text
```

Stop and test.

---

## Phase 8 — Embeddings + Chroma

Add:

* Ollama embeddings
* Chroma persistence
* chunk indexing
* document filtering
* cleanup of stale vectors

Stop and test.

---

## Phase 9 — BM25

Add:

* BM25 index
* indexing
* persistence/rebuilding strategy
* document filtering

Stop and test.

---

## Phase 10 — Hybrid Retrieval

Combine:

```text
Chroma
+
BM25
```

Evaluate retrieval quality.

Stop and test.

---

## Phase 11 — RAG + Ollama

Add:

* RAG prompt
* context construction
* Ollama LLM
* grounded answers
* source metadata

Stop and test.

---

## Phase 12 — LangGraph Memory

Add:

* graph state
* checkpointing
* conversation history
* follow-up question handling

Stop and test.

---

## Phase 13 — Chat UI

Implement:

* three-column layout
* chat history
* streaming if appropriate
* citations
* source panel
* source highlighting

Stop and test.

---

## Phase 14 — Evaluation

Add evaluation using RAGAS.

Evaluate:

* retrieval quality
* answer relevance
* faithfulness
* context precision
* context recall

Use a ground-truth dataset.

---

# 37. Existing Code Preservation Rule

This project is being developed incrementally.

Before modifying existing code:

1. Inspect the current implementation.
2. Understand why it exists.
3. Reuse working components.
4. Modify only what is necessary.
5. Do not rewrite unrelated files.
6. Do not replace working APIs without a reason.
7. Do not introduce a new framework to solve a small problem.

If a working implementation already exists, preserve it unless the requested feature requires a change.

---

# 38. Dependency Rules

Do not add dependencies casually.

Before adding a package:

1. Determine whether the existing stack can solve the problem.
2. Check whether the package is actually necessary.
3. Add it only if justified.
4. Update `requirements.txt`.

Avoid dependency duplication.

For example, do not add another PDF library when PyMuPDF already satisfies the requirement unless there is a specific missing capability.

---

# 39. Frontend Rules

Use:

```text
HTML
CSS
Vanilla JavaScript
```

Do not introduce React.

Keep JavaScript modular and readable.

Use Flask routes for server-side rendering and standard browser requests for API-style interactions.

Do not introduce Axios.

---

# 40. UI Principles

The UI should be:

* clean
* simple
* functional
* responsive
* easy to understand

Do not over-design the interface before the backend functionality works.

Prioritize functionality first.

---

# 41. RAG Quality Principles

The goal is not simply to make the LLM answer questions.

The goal is:

```text
Correct retrieval
        ↓
Relevant context
        ↓
Grounded answer
        ↓
Traceable citation
```

If the required information is not present in retrieved documents, the system should say that it cannot find the answer rather than hallucinating.

---

# 42. Retrieval Debugging

When debugging RAG, inspect each stage separately:

```text
Question
   ↓
Query
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
```

Do not immediately blame the LLM.

First determine whether the correct chunk was retrieved.

---

# 43. Ingestion Debugging

When debugging ingestion:

```text
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
Chroma/BM25
```

Log the number of:

* pages
* extracted characters
* chunks
* embeddings
* indexed documents

Do not print entire documents unnecessarily.

---

# 44. Important Metadata Rule

Metadata is critical for citations and debugging.

Every chunk must remain traceable to:

```text
document
→ page
→ chunk
→ extraction method
```

Do not strip metadata during:

* chunking
* embedding
* retrieval
* reranking
* answer generation

---

# 45. Do Not Overengineer

Prefer:

```text
simple
explicit
testable
modular
```

over:

```text
complex
abstract
over-engineered
```

Do not introduce:

* microservices
* Kubernetes
* Redis
* Celery
* message queues
* complex agent frameworks

unless a future requirement actually justifies them.

This is currently a local Flask RAG application.

---

# 46. Codex Working Procedure

When asked to implement a feature:

### Step 1

Inspect the relevant existing files.

### Step 2

Explain briefly what needs to change.

### Step 3

Implement only the requested phase.

### Step 4

Do not modify unrelated working functionality.

### Step 5

Run/test the relevant code where possible.

### Step 6

Report:

```text
Changed:
- file 1
- file 2

Why:
- short explanation

Test:
- command/result

Next:
- next logical step
```

Do not jump multiple phases ahead.

---

# 47. If Something Is Broken

Do not immediately rewrite the architecture.

First determine:

```text
What failed?
Where did it fail?
What is the actual error?
Which file owns that behavior?
```

Then make the smallest appropriate fix.

Prefer fixing the root cause over adding workarounds.

---

# 48. Current Known Foundation

The application currently uses:

```text
Flask
Flask-SQLAlchemy
SQLite
Werkzeug
python-dotenv
```

The database is intended to live at:

```text
data/rag.db
```

The default admin is configured through:

```env
DEFAULT_ADMIN_USERNAME=admin
DEFAULT_ADMIN_PASSWORD=admin123
```

The application entry point is:

```text
run.py
```

Run locally with:

```bash
python run.py
```

Expected development URL:

```text
http://127.0.0.1:5000
```

---

# 49. Final Rule

The most important rule for this project:

> Build the RAG system from the foundation upward. Do not add advanced RAG functionality until the simpler layer underneath it is working and tested.

Development order:

```text
Flask
 ↓
SQLite
 ↓
Authentication
 ↓
Authorization
 ↓
Users
 ↓
Documents
 ↓
Approval
 ↓
Ingestion
 ↓
OCR / Tables
 ↓
Chunking
 ↓
Embeddings
 ↓
Chroma
 ↓
BM25
 ↓
Hybrid Retrieval
 ↓
Ollama
 ↓
RAG
 ↓
LangGraph Memory
 ↓
Citations
 ↓
UI
 ↓
Evaluation
```

Always preserve working functionality while extending the system.

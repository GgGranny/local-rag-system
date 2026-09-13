import os
from pathlib import Path

from dotenv import load_dotenv


# Project root directory
BASE_DIR = Path(__file__).resolve().parent.parent

# Data directory
DATA_DIR = BASE_DIR / "data"

# Make sure data directory exists
DATA_DIR.mkdir(parents=True, exist_ok=True)

# Load .env from project root
load_dotenv(BASE_DIR / ".env")

#upload dir create
UPLOAD_DIR = DATA_DIR / "uploads"

UPLOAD_DIR.mkdir(
    parents=True,
    exist_ok=True
)

SOURCE_IMAGE_DIR = DATA_DIR / "source_images"
SOURCE_IMAGE_DIR.mkdir(parents=True, exist_ok=True)

CHROMA_DIR = BASE_DIR / "data" / "chroma_db"
CHROMA_DIR.mkdir(
    parents=True,
    exist_ok=True
)



def get_database_uri() -> str:
    database_url = os.getenv("DATABASE_URL")

    if not database_url:
        return f"sqlite:///{(DATA_DIR / 'rag.db').as_posix()}"

    if database_url.startswith("sqlite:///"):
        database_path = Path(database_url.removeprefix("sqlite:///"))
        if not database_path.is_absolute():
            database_path = (BASE_DIR / database_path).resolve()
            return f"sqlite:///{database_path.as_posix()}"

    return database_url


class Config:

    UPLOAD_FOLDER = str(UPLOAD_DIR)
    SOURCE_IMAGE_FOLDER = str(SOURCE_IMAGE_DIR)

    MAX_CONTENT_LENGTH = 20 * 1024 * 1024
    
    SECRET_KEY = os.getenv(
        "FLASK_SECRET_KEY",
        "local-development-secret-change-me"
    )

    # SQLite database path
    DB_PATH = DATA_DIR / "rag.db"

    # Windows-safe SQLite URI
    SQLALCHEMY_DATABASE_URI = get_database_uri()

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Default admin credentials
    DEFAULT_ADMIN_USERNAME = os.getenv(
        "DEFAULT_ADMIN_USERNAME",
        "admin"
    )

    DEFAULT_ADMIN_PASSWORD = os.getenv(
        "DEFAULT_ADMIN_PASSWORD",
        "admin123"
    )

    CHROMA_PERSIST_DIRECTORY = str(
    BASE_DIR / "data" / "chroma_db"
    )

    CHROMA_COLLECTION_NAME = os.getenv(
        "CHROMA_COLLECTION_NAME",
        "my_documents"
    )

    OLLAMA_EMBEDDING_MODEL = os.getenv(
        "OLLAMA_EMBEDDING_MODEL",
        "qwen3-embedding:0.6b"
    )

    OLLAMA_CHAT_MODEL = os.getenv(
    "OLLAMA_CHAT_MODEL",
    "qwen3:1.7b"
)

    # Applies to both grounded answers and the lightweight rewrite call.  A
    # failed local model must return control to the Flask request instead of
    # leaving the chat UI generating indefinitely.
    OLLAMA_REQUEST_TIMEOUT = float(
        os.getenv("OLLAMA_REQUEST_TIMEOUT", "120")
    )

    # Optional observability, with sensitive content disabled by default.
    MONITORING_ENABLED = os.getenv("MONITORING_ENABLED", "true").lower() == "true"
    PHOENIX_ENABLED = os.getenv("PHOENIX_ENABLED", "false").lower() == "true"
    PHOENIX_ENDPOINT = os.getenv("PHOENIX_ENDPOINT", "http://localhost:6006")
    PHOENIX_PROJECT_NAME = os.getenv("PHOENIX_PROJECT_NAME", "local-rag")
    PHOENIX_CAPTURE_CONTENT = os.getenv("PHOENIX_CAPTURE_CONTENT", "false").lower() == "true"
    PHOENIX_CAPTURE_RETRIEVED_CONTEXT = os.getenv("PHOENIX_CAPTURE_RETRIEVED_CONTEXT", "false").lower() == "true"
    PHOENIX_CAPTURE_PROMPTS = os.getenv("PHOENIX_CAPTURE_PROMPTS", "false").lower() == "true"
    # These aliases describe application-database retention separately from
    # Phoenix export.  Existing PHOENIX_CAPTURE_* values remain compatible.
    MONITORING_STORE_CONTENT = os.getenv(
        "MONITORING_STORE_CONTENT", os.getenv("PHOENIX_CAPTURE_CONTENT", "false")
    ).lower() == "true"
    MONITORING_STORE_CONTEXT = os.getenv(
        "MONITORING_STORE_CONTEXT", os.getenv("PHOENIX_CAPTURE_RETRIEVED_CONTEXT", "false")
    ).lower() == "true"
    MONITORING_STORE_PROMPTS = os.getenv(
        "MONITORING_STORE_PROMPTS", os.getenv("PHOENIX_CAPTURE_PROMPTS", "false")
    ).lower() == "true"
    MONITORING_STORE_RETRIEVED_CHUNKS = os.getenv(
        "MONITORING_STORE_RETRIEVED_CHUNKS", os.getenv("MONITORING_STORE_CONTEXT", "false")
    ).lower() == "true"
    MONITORING_STORE_GENERATED_ANSWERS = os.getenv(
        "MONITORING_STORE_GENERATED_ANSWERS", os.getenv("MONITORING_STORE_CONTENT", "false")
    ).lower() == "true"
    MONITORING_STORE_CITATIONS = os.getenv(
        "MONITORING_STORE_CITATIONS", os.getenv("MONITORING_STORE_CONTENT", "false")
    ).lower() == "true"
    RAGAS_AUTO_EVALUATION_ENABLED = os.getenv("RAGAS_AUTO_EVALUATION_ENABLED", "false").lower() == "true"
    RAGAS_ENABLED = os.getenv("RAGAS_ENABLED", "false").lower() == "true"
    RAGAS_ANSWER_RELEVANCY_ENABLED = os.getenv("RAGAS_ANSWER_RELEVANCY_ENABLED", "false").lower() == "true"
    RAGAS_EVALUATOR_MODEL = os.getenv("RAGAS_EVALUATOR_MODEL", OLLAMA_CHAT_MODEL)
    RAGAS_EVALUATION_MODE = os.getenv("RAGAS_EVALUATION_MODE", "manual")
    RAGAS_ANSWER_RELEVANCY_GOOD_THRESHOLD = float(os.getenv("RAGAS_ANSWER_RELEVANCY_GOOD_THRESHOLD", "0.80"))
    RAGAS_ANSWER_RELEVANCY_WARNING_THRESHOLD = float(os.getenv("RAGAS_ANSWER_RELEVANCY_WARNING_THRESHOLD", "0.60"))
    RAG_GROUNDEDNESS_THRESHOLD = float(os.getenv("RAG_GROUNDEDNESS_THRESHOLD", "0.7"))
    OLLAMA_INPUT_COST_PER_1K_TOKENS = float(os.getenv("OLLAMA_INPUT_COST_PER_1K_TOKENS", "0"))
    OLLAMA_OUTPUT_COST_PER_1K_TOKENS = float(os.getenv("OLLAMA_OUTPUT_COST_PER_1K_TOKENS", "0"))

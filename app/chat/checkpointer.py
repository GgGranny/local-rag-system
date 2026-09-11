import sqlite3
from langgraph.checkpoint.sqlite import SqliteSaver
from app.config import DATA_DIR


CHECKPOINT_DB = DATA_DIR / "rag_checkpoints.db"


_connection = None
_checkpointer = None


def get_checkpointer():

    global _connection
    global _checkpointer

    if _checkpointer is None:

        print(
            f"[CHECKPOINT] Database: "
            f"{CHECKPOINT_DB}"
        )

        _connection = sqlite3.connect(
            str(CHECKPOINT_DB),
            check_same_thread=False
        )

        _checkpointer = SqliteSaver(
            _connection
        )

        _checkpointer.setup()

        print(
            "[CHECKPOINT] SQLite checkpoint "
            "storage initialized."
        )

    return _checkpointer
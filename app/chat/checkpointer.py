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


def delete_thread_checkpoints(thread_id: str) -> None:
    """Remove only the persisted LangGraph state for one conversation."""
    connection = get_checkpointer() and _connection
    if connection is None:
        return
    # These are LangGraph's SQLite tables.  Keeping this explicit prevents a
    # chat delete from ever touching the shared document database.
    for table in ("checkpoint_writes", "checkpoint_blobs", "checkpoints"):
        try:
            connection.execute(f"DELETE FROM {table} WHERE thread_id = ?", (thread_id,))
        except sqlite3.OperationalError:
            # Older LangGraph versions may not create every table.
            continue
    connection.commit()

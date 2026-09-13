"""Small SQLite compatibility migration for monitoring tables.

The project intentionally does not use Alembic.  `create_all()` does not add
columns to an existing SQLite table, so preserve current installations with a
minimal idempotent upgrade.
"""

from sqlalchemy import inspect, text

from app.extensions import db


_EVALUATION_COLUMNS = {
    "conversation_id": "INTEGER",
    "message_id": "VARCHAR(36)",
    "user_id": "INTEGER",
    "metric_name": "VARCHAR(80) NOT NULL DEFAULT 'answer_relevancy'",
    "evaluator_model": "VARCHAR(120)",
    "ragas_version": "VARCHAR(40)",
    "duration_ms": "FLOAT",
    "evaluated_at": "DATETIME",
    "original_user_question": "TEXT",
    "final_retrieval_query": "TEXT",
    "generated_answer": "TEXT",
}


def ensure_monitoring_schema() -> None:
    if db.engine.dialect.name != "sqlite" or "rag_evaluations" not in inspect(db.engine).get_table_names():
        return
    columns = {item["name"] for item in inspect(db.engine).get_columns("rag_evaluations")}
    for name, definition in _EVALUATION_COLUMNS.items():
        if name not in columns:
            db.session.execute(text(f"ALTER TABLE rag_evaluations ADD COLUMN {name} {definition}"))
    db.session.commit()

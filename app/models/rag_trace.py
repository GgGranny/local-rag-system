import uuid
from datetime import datetime

from app.extensions import db


class RAGTrace(db.Model):
    """A durable, serializable record of one RAG execution."""

    __tablename__ = "rag_traces"

    id = db.Column(db.Integer, primary_key=True)
    trace_id = db.Column(db.String(36), nullable=False, unique=True, index=True,
                         default=lambda: str(uuid.uuid4()))
    conversation_id = db.Column(db.Integer, db.ForeignKey("conversations.id"), index=True)
    message_id = db.Column(db.String(36), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    user_role = db.Column(db.String(20), nullable=False)
    status = db.Column(db.String(20), nullable=False, default="RUNNING", index=True)
    started_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, index=True)
    completed_at = db.Column(db.DateTime, nullable=True, index=True)
    total_ms = db.Column(db.Float, nullable=True)
    query_type = db.Column(db.String(30), nullable=True)
    rewrite_used = db.Column(db.Boolean, nullable=False, default=False)
    selected_document_ids_json = db.Column(db.Text, nullable=False, default="[]")
    original_query = db.Column(db.Text, nullable=True)
    retrieval_query = db.Column(db.Text, nullable=True)
    retrieved_chunks_json = db.Column(db.Text, nullable=True)
    context_text = db.Column(db.Text, nullable=True)
    prompt_text = db.Column(db.Text, nullable=True)
    answer_text = db.Column(db.Text, nullable=True)
    citations_json = db.Column(db.Text, nullable=True)
    stage_timings_json = db.Column(db.Text, nullable=False, default="{}")
    model_name = db.Column(db.String(120), nullable=True)
    embedding_model_name = db.Column(db.String(120), nullable=True)
    prompt_tokens = db.Column(db.Integer, nullable=True)
    completion_tokens = db.Column(db.Integer, nullable=True)
    token_estimated = db.Column(db.Boolean, nullable=False, default=False)
    estimated_cost = db.Column(db.Float, nullable=True)
    error_stage = db.Column(db.String(80), nullable=True)
    error_type = db.Column(db.String(120), nullable=True)
    error_message = db.Column(db.String(500), nullable=True)
    phoenix_status = db.Column(db.String(30), nullable=True)

    user = db.relationship("User", backref="rag_traces")
    conversation = db.relationship("Conversation", backref="rag_traces")


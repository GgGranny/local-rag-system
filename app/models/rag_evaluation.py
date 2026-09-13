from datetime import datetime

from app.extensions import db


class RAGEvaluation(db.Model):
    """Optional RAGAS/manual score associated with one trace."""

    __tablename__ = "rag_evaluations"

    id = db.Column(db.Integer, primary_key=True)
    trace_id = db.Column(db.String(36), db.ForeignKey("rag_traces.trace_id"), nullable=False, index=True)
    conversation_id = db.Column(db.Integer, db.ForeignKey("conversations.id"), nullable=True, index=True)
    message_id = db.Column(db.String(36), nullable=True, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True, index=True)
    status = db.Column(db.String(20), nullable=False, default="PENDING", index=True)
    method = db.Column(db.String(40), nullable=False, default="manual")
    metric_name = db.Column(db.String(80), nullable=False, default="answer_relevancy")
    evaluator_model = db.Column(db.String(120), nullable=True)
    ragas_version = db.Column(db.String(40), nullable=True)
    duration_ms = db.Column(db.Float, nullable=True)
    evaluated_at = db.Column(db.DateTime, nullable=True, index=True)
    # Keep the exact inputs used for this run.  A trace is immutable in normal
    # operation, but retaining these values makes the evaluation auditable even
    # when content-retention settings later change.
    original_user_question = db.Column(db.Text, nullable=True)
    final_retrieval_query = db.Column(db.Text, nullable=True)
    generated_answer = db.Column(db.Text, nullable=True)
    faithfulness = db.Column(db.Float, nullable=True)
    answer_relevance = db.Column(db.Float, nullable=True)
    context_precision = db.Column(db.Float, nullable=True)
    context_recall = db.Column(db.Float, nullable=True)
    answer_correctness = db.Column(db.Float, nullable=True)
    reference_answer = db.Column(db.Text, nullable=True)
    error_message = db.Column(db.String(500), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, index=True)

    trace = db.relationship("RAGTrace", backref="evaluations")
    conversation = db.relationship("Conversation")
    user = db.relationship("User")

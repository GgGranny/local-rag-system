from datetime import datetime

from app.extensions import db


class RAGEvaluation(db.Model):
    """Optional RAGAS/manual score associated with one trace."""

    __tablename__ = "rag_evaluations"

    id = db.Column(db.Integer, primary_key=True)
    trace_id = db.Column(db.String(36), db.ForeignKey("rag_traces.trace_id"), nullable=False, index=True)
    status = db.Column(db.String(20), nullable=False, default="PENDING", index=True)
    method = db.Column(db.String(40), nullable=False, default="manual")
    faithfulness = db.Column(db.Float, nullable=True)
    answer_relevance = db.Column(db.Float, nullable=True)
    context_precision = db.Column(db.Float, nullable=True)
    context_recall = db.Column(db.Float, nullable=True)
    answer_correctness = db.Column(db.Float, nullable=True)
    reference_answer = db.Column(db.Text, nullable=True)
    error_message = db.Column(db.String(500), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, index=True)

    trace = db.relationship("RAGTrace", backref="evaluations")


from datetime import datetime

from app.extensions import db


class DocumentChunk(db.Model):
    __tablename__ = "document_chunks"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    document_id = db.Column(
        db.Integer,
        db.ForeignKey("documents.id"),
        nullable=False,
        index=True
    )

    chunk_id = db.Column(
        db.String(150),
        nullable=False,
        unique=True,
        index=True
    )

    content = db.Column(
        db.Text,
        nullable=False
    )

    page_number = db.Column(
        db.Integer,
        nullable=True
    )

    chunk_index = db.Column(
        db.Integer,
        nullable=False
    )

    extraction_method = db.Column(
        db.String(50),
        nullable=True
    )

    content_type = db.Column(
        db.String(50),
        nullable=False,
        default="chunk"
    )

    created_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow
    )

    document = db.relationship(
        "Document",
        backref="chunks"
    )

    def __repr__(self):
        return (
            f"<DocumentChunk "
            f"{self.chunk_id}>"
        )
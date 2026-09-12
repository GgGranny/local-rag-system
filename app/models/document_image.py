from datetime import datetime

from app.extensions import db


class DocumentImage(db.Model):
    """A private extracted visual asset belonging to one source document."""

    __tablename__ = "document_images"

    id = db.Column(db.Integer, primary_key=True)
    document_id = db.Column(db.Integer, db.ForeignKey("documents.id"), nullable=False, index=True)
    image_id = db.Column(db.String(150), nullable=False, unique=True, index=True)
    stored_filename = db.Column(db.String(255), nullable=False, unique=True)
    mime_type = db.Column(db.String(100), nullable=False)
    page_number = db.Column(db.Integer, nullable=True, index=True)
    image_index = db.Column(db.Integer, nullable=False, default=0)
    vertical_position = db.Column(db.Float, nullable=True)
    source_kind = db.Column(db.String(30), nullable=False, default="embedded")
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    document = db.relationship("Document", backref="images")

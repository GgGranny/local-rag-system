from datetime import datetime

from app.extensions import db


class DocumentSourcePage(db.Model):
    """Canonical extracted text for the continuous source viewer.

    Retrieval continues to use DocumentChunk.  Keeping the page text separate
    prevents CharacterTextSplitter overlap from becoming duplicated visible
    text in the source panel.
    """

    __tablename__ = "document_source_pages"

    id = db.Column(db.Integer, primary_key=True)
    document_id = db.Column(
        db.Integer, db.ForeignKey("documents.id"), nullable=False, index=True
    )
    page_number = db.Column(db.Integer, nullable=False)
    content = db.Column(db.Text, nullable=False)
    extraction_method = db.Column(db.String(50), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    document = db.relationship("Document", backref="source_pages")


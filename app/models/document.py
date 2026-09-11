from datetime import datetime

from app.extensions import db


class Document(db.Model):
    __tablename__ = "documents"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    filename = db.Column(
        db.String(255),
        nullable=False
    )

    stored_filename = db.Column(
        db.String(255),
        nullable=False,
        unique=True
    )

    file_path = db.Column(
        db.String(500),
        nullable=False
    )

    file_type = db.Column(
        db.String(50),
        nullable=False
    )

    status = db.Column(
        db.String(30),
        nullable=False,
        default="PENDING"
    )

    uploaded_by = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=False
    )

    created_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow
    )

    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )

    uploader = db.relationship(
        "User",
        backref="documents"
    )

    def __repr__(self):
        return (
            f"<Document "
            f"{self.id} "
            f"{self.filename} "
            f"{self.status}>"
        )
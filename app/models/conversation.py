from datetime import datetime
from app.extensions import db


class Conversation(db.Model):

    __tablename__ = "conversations"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=False,
        index=True
    )

    thread_id = db.Column(
        db.String(100),
        unique=True,
        nullable=False,
        index=True
    )

    title = db.Column(
        db.String(255),
        nullable=False,
        default="New conversation"
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

    user = db.relationship(
        "User",
        backref="conversations"
    )

    def __repr__(self):
        return (
            f"<Conversation "
            f"{self.id} "
            f"{self.thread_id}>"
        )
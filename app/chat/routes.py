from flask import (
    Blueprint,
    current_app,
    request,
    jsonify,
    session,
)

from datetime import datetime
import uuid
from langchain_core.messages import HumanMessage
from app.auth.decorators import login_required
from app.extensions import db
from app.models import Conversation, Document, User
from app.chat.graph import build_graph
from app.chat.checkpointer import delete_thread_checkpoints
from app.monitoring.service import begin_execution, measured
from flask import render_template


chat_bp = Blueprint(
    "chat",
    __name__,
    url_prefix="/chat"
)


_graph = None


def conversation_for_request(thread_id):
    """Load a conversation under the server-side owner/admin policy."""
    conversation = Conversation.query.filter_by(thread_id=thread_id).first()
    if not conversation:
        return None
    user = db.session.get(User, session["user_id"])
    if not user or (not user.is_admin and conversation.user_id != user.id):
        return None
    return conversation


def serialize_conversation(conversation):
    return {
        "id": conversation.id,
        "thread_id": conversation.thread_id,
        "title": conversation.title,
        "owner": conversation.user.username if conversation.user else None,
        "owner_id": conversation.user_id,
        "created_at": conversation.created_at.isoformat(),
        "updated_at": conversation.updated_at.isoformat(),
    }


def enrich_sources_with_images(sources):
    """Attach a stable page visual when an OCR/image-backed source has one."""
    from app.models import DocumentImage

    page_keys = {
        (source.get("document_id"), source.get("page_number"))
        for source in sources
        if source.get("document_id") is not None and source.get("page_number") is not None
    }
    if not page_keys:
        return sources
    document_ids = {key[0] for key in page_keys}
    images = DocumentImage.query.filter(DocumentImage.document_id.in_(document_ids)).all()
    by_page = {}
    for image in images:
        by_page.setdefault((image.document_id, image.page_number), image)
    for source in sources:
        image = by_page.get((source.get("document_id"), source.get("page_number")))
        if image:
            source["image_id"] = image.image_id
            source["source_type"] = image.source_kind
            source["is_ocr"] = image.source_kind == "ocr_page"
    return sources


def get_graph():
    global _graph

    if _graph is None:
        print("[CHAT] Building LangGraph...")
        _graph = build_graph()

    return _graph

@chat_bp.route("/", methods=["GET"])
@login_required
def chat():
    return render_template(
        "chat/chat.html"
    )


@chat_bp.route("/conversations", methods=["POST"])
@login_required
def create_conversation():

    user_id = session["user_id"]

    thread_id = str(uuid.uuid4())

    conversation = Conversation(
        user_id=user_id,
        thread_id=thread_id,
        title="New conversation",
    )

    db.session.add(conversation)
    db.session.commit()

    return jsonify({
        "id": conversation.id,
        "thread_id": conversation.thread_id,
        "title": conversation.title,
    }), 201


@chat_bp.route("/conversations", methods=["GET"])
@login_required
def list_conversations():

    user_id = session["user_id"]

    user = db.session.get(User, user_id)
    query = Conversation.query
    if not user or not user.is_admin:
        query = query.filter_by(user_id=user_id)
    conversations = (
        query
        .order_by(
            Conversation.updated_at.desc()
        )
        .all()
    )

    return jsonify([
        serialize_conversation(conversation)
        for conversation in conversations
    ])


@chat_bp.route(
    "/ask",
    methods=["POST"]
)
@login_required
def ask():

    data = request.get_json(
        silent=True
    )

    if not data:

        return jsonify({
            "error":
                "Request body is required."
        }), 400

    question = data.get(
        "question",
        ""
    ).strip()

    if not question:

        return jsonify({
            "error":
                "Question cannot be empty."
        }), 400

    thread_id = data.get(
        "thread_id"
    )

    if not thread_id:

        return jsonify({
            "error":
                "thread_id is required."
        }), 400

    selected_document_ids = data.get("document_ids", [])
    if selected_document_ids is None:
        selected_document_ids = []
    if (
        not isinstance(selected_document_ids, list)
        or any(isinstance(item, bool) for item in selected_document_ids)
    ):
        return jsonify({
            "error": "document_ids must be a list of document IDs."
        }), 400
    try:
        selected_document_ids = sorted({int(item) for item in selected_document_ids})
    except (TypeError, ValueError):
        return jsonify({
            "error": "document_ids must contain only integers."
        }), 400

    # --------------------------------------------------
    # AUTHENTICATED USER
    # --------------------------------------------------

    user_id = session[
        "user_id"
    ]

    user = db.session.get(
        User,
        user_id
    )

    if not user:

        return jsonify({
            "error":
                "User not found."
        }), 401

    if selected_document_ids:
        selected_documents = Document.query.filter(
            Document.id.in_(selected_document_ids),
            Document.status == "COMPLETED",
        ).all()
        valid_document_ids = {document.id for document in selected_documents}
        if valid_document_ids != set(selected_document_ids):
            return jsonify({
                "error": "Every selected document must exist and be completed."
            }), 400

    # --------------------------------------------------
    # CONVERSATION OWNERSHIP
    # --------------------------------------------------

    conversation = conversation_for_request(thread_id)

    if not conversation:

        return jsonify({
            "error":
                "Conversation not found."
        }), 404

    # --------------------------------------------------
    # GRAPH
    # --------------------------------------------------

    graph = get_graph()

    config = {
        "configurable": {
            "thread_id":
                conversation.thread_id
        }
    }

    execution = begin_execution(
        user_id=user.id,
        user_role=user.role,
        conversation_id=conversation.id,
        selected_document_ids=selected_document_ids,
        question=question,
    )
    try:

        with measured("rag.request", user_id=user.id, conversation_id=conversation.id):
            result = graph.invoke(
                {
                    "messages": [
                        HumanMessage(
                            content=question
                        )
                    ],

                # Retained as chat context for auditing. Completed documents
                # are shared, so retrieval is status-based rather than owner-based.
                "user_id": user.id,

                "is_admin":
                    user.role == "ADMIN",

                    "selected_document_ids": selected_document_ids,
                },
                config=config
            )

        with measured("rag.persistence"):
            if conversation.title == "New conversation":
                conversation.title = question[:100]
            conversation.updated_at = datetime.utcnow()
            db.session.commit()

        result["sources"] = enrich_sources_with_images(result.get("sources", []))
        execution.complete(result)

        return jsonify({

            "answer":
                result.get(
                    "answer",
                    ""
                ),

            "sources":
                result.get(
                    "sources",
                    []
                ),

            "thread_id":
                conversation.thread_id,

            "standalone_question":
                result.get(
                    "standalone_question",
                    question
                ),
        })

    except Exception as exc:

        db.session.rollback()
        execution.fail(exc)

        print(
            f"[CHAT] Error: {exc}"
        )

        return jsonify({
            "error":
                "Failed to generate "
                "an answer."
        }), 500

@chat_bp.route(
    "/conversations/<string:thread_id>",
    methods=["GET"]
)
@login_required
def get_conversation(thread_id):

    conversation = conversation_for_request(thread_id)

    if not conversation:
        return jsonify({
            "error": "Conversation not found."
        }), 404

    # -----------------------------
    # Get LangGraph
    # -----------------------------

    graph = get_graph()

    config = {
        "configurable": {
            "thread_id": thread_id
        }
    }

    # -----------------------------
    # Read checkpoint state
    # -----------------------------

    try:

        state = graph.get_state(
            config
        )

        values = state.values

        messages = values.get(
            "messages",
            []
        )

        serialized_messages = []

        for message in messages:

            message_type = (
                message.type
                if hasattr(message, "type")
                else "unknown"
            )

            serialized_messages.append({
                "role": (
                    "user"
                    if message_type == "human"
                    else "assistant"
                ),
                "content": str(
                    message.content
                ),
            })

        sources = enrich_sources_with_images(list(values.get("sources", [])))
        payload = serialize_conversation(conversation)
        payload.update({"messages": serialized_messages, "sources": sources})
        return jsonify(payload)

    except Exception as exc:

        print(
            f"[CHAT] Failed to load "
            f"conversation: {exc}"
        )

        return jsonify({
            "error": (
                "Failed to load "
                "conversation."
            )
        }), 500


@chat_bp.route("/conversations/<string:thread_id>", methods=["DELETE"])
@login_required
def delete_conversation(thread_id):
    """Delete an owned conversation; admins may manage conversations."""
    conversation = conversation_for_request(thread_id)
    if not conversation:
        return jsonify({"error": "Conversation not found."}), 404
    checkpoint_thread_id = conversation.thread_id
    try:
        delete_thread_checkpoints(checkpoint_thread_id)
        db.session.delete(conversation)
        db.session.commit()
    except Exception:
        db.session.rollback()
        current_app.logger.exception("[CHAT] Failed to delete conversation %s", thread_id)
        return jsonify({"error": "Failed to delete conversation."}), 500
    return jsonify({"deleted": True, "thread_id": checkpoint_thread_id})

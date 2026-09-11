from flask import (
    Blueprint,
    request,
    jsonify,
    session,
)

from datetime import datetime
import uuid
from langchain_core.messages import HumanMessage
from app.auth.decorators import login_required
from app.extensions import db
from app.models import Conversation
from app.chat.graph import build_graph
from flask import render_template


chat_bp = Blueprint(
    "chat",
    __name__,
    url_prefix="/chat"
)


_graph = None


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

    conversations = (
        Conversation.query
        .filter_by(user_id=user_id)
        .order_by(
            Conversation.updated_at.desc()
        )
        .all()
    )

    return jsonify([
        {
            "id": conversation.id,
            "thread_id": conversation.thread_id,
            "title": conversation.title,
            "created_at": (
                conversation.created_at.isoformat()
            ),
            "updated_at": (
                conversation.updated_at.isoformat()
            ),
        }
        for conversation in conversations
    ])


@chat_bp.route("/ask", methods=["POST"])
@login_required
def ask():

    data = request.get_json(
        silent=True
    )

    if not data:
        return jsonify({
            "error": "Request body is required."
        }), 400

    question = data.get(
        "question",
        ""
    ).strip()

    if not question:
        return jsonify({
            "error": "Question cannot be empty."
        }), 400

    thread_id = data.get(
        "thread_id"
    )

    if not thread_id:
        return jsonify({
            "error": "thread_id is required."
        }), 400

    # -----------------------------
    # Verify conversation ownership
    # -----------------------------

    user_id = session["user_id"]

    conversation = (
        Conversation.query
        .filter_by(
            thread_id=thread_id,
            user_id=user_id,
        )
        .first()
    )

    if not conversation:
        return jsonify({
            "error": "Conversation not found."
        }), 404

    # -----------------------------
    # Get LangGraph
    # -----------------------------

    graph = get_graph()

    # -----------------------------
    # LangGraph checkpoint config
    # -----------------------------

    config = {
        "configurable": {
            "thread_id": conversation.thread_id
        }
    }

    try:

        # -----------------------------
        # Run RAG graph
        # -----------------------------

        result = graph.invoke(
            {
                "messages": [
                    HumanMessage(
                        content=question
                    )
                ]
            },
            config=config
        )

        # -----------------------------
        # Update conversation timestamp
        # -----------------------------

        conversation.updated_at = (
            datetime.utcnow()
        )

        db.session.commit()

        # -----------------------------
        # Return response
        # -----------------------------

        return jsonify({
            "answer": result.get(
                "answer",
                ""
            ),

            "sources": result.get(
                "sources",
                []
            ),

            "thread_id": (
                conversation.thread_id
            ),

            "standalone_question":
                result.get(
                    "standalone_question",
                    question
                ),
        })

    except Exception as exc:

        db.session.rollback()

        print(
            f"[CHAT] Error: {exc}"
        )

        return jsonify({
            "error": (
                "Failed to generate "
                "an answer."
            )
        }), 500


@chat_bp.route(
    "/conversations/<string:thread_id>",
    methods=["GET"]
)
@login_required
def get_conversation(thread_id):

    user_id = session["user_id"]

    # -----------------------------
    # Verify ownership
    # -----------------------------

    conversation = (
        Conversation.query
        .filter_by(
            thread_id=thread_id,
            user_id=user_id,
        )
        .first()
    )

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

        return jsonify({
            "id": conversation.id,
            "thread_id": conversation.thread_id,
            "title": conversation.title,
            "messages": serialized_messages,
        })

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
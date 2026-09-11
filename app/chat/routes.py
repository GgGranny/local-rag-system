from flask import Blueprint, render_template

from app.auth.decorators import login_required


chat_bp = Blueprint(
    "chat",
    __name__,
    url_prefix=""
)


@chat_bp.route("/")
@login_required
def home():

    return render_template(
        "chat/chat.html"
    )


@chat_bp.route("/chat")
@login_required
def chat():

    return render_template(
        "chat/chat.html"
    )
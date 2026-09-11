import uuid
from pathlib import Path
from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    session,
    flash,
    current_app,
)
from werkzeug.utils import secure_filename
from app.auth.decorators import login_required
from app.extensions import db
from app.models import Document


documents_bp = Blueprint(
    "documents",
    __name__,
    url_prefix="/documents"
)


ALLOWED_EXTENSIONS = {
    "pdf",
    "doc",
    "docx",
    "txt",
    "csv",
}


def allowed_file(filename):
    if "." not in filename:
        return False

    extension = filename.rsplit(
        ".",
        1
    )[1].lower()

    return extension in ALLOWED_EXTENSIONS


@documents_bp.route("/upload", methods=["POST"])
@login_required
def upload():

    if "file" not in request.files:
        flash(
            "No file selected.",
            "error"
        )
        return redirect(url_for("chat.chat"))

    file = request.files["file"]

    if not file or not file.filename:
        flash(
            "No file selected.",
            "error"
        )
        return redirect(url_for("chat.chat"))

    if not allowed_file(file.filename):
        flash(
            "Unsupported file type.",
            "error"
        )
        return redirect(url_for("chat.chat"))

    original_filename = secure_filename(
        file.filename
    )

    extension = Path(
        original_filename
    ).suffix.lower()

    stored_filename = (
        f"{uuid.uuid4().hex}"
        f"{extension}"
    )

    upload_dir = Path(
        current_app.config["UPLOAD_FOLDER"]
    )

    file_path = upload_dir / stored_filename

    file.save(file_path)

    document = Document(
        filename=original_filename,
        stored_filename=stored_filename,
        file_path=str(file_path),
        file_type=extension.lstrip("."),
        status="PENDING",
        uploaded_by=session["user_id"],
    )

    db.session.add(document)
    db.session.commit()

    flash(
        "Document uploaded and is waiting for admin approval.",
        "success"
    )

    return redirect(url_for("chat.chat"))


@documents_bp.route("/mine", methods=["GET"])
@login_required
def my_documents():

    user_id = session["user_id"]

    documents = (
        Document.query
        .filter_by(uploaded_by=user_id)
        .order_by(
            Document.created_at.desc()
        )
        .all()
    )

    return jsonify([
        {
            "id": document.id,
            "filename": document.filename,
            "file_type": document.file_type,
            "status": document.status,
            "created_at": document.created_at.isoformat(),
            "updated_at": document.updated_at.isoformat(),
        }
        for document in documents
    ])
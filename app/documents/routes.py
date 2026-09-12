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
    jsonify,
)
from werkzeug.utils import secure_filename
from app.auth.decorators import login_required
from sqlalchemy import or_
from app.extensions import db
from app.models import Document, User
from app.ingestion.pipeline import process_document


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


def wants_json_response() -> bool:
    """Support both the chat's fetch upload and regular form submissions."""
    return (
        request.accept_mimetypes.best == "application/json"
        or request.headers.get("X-Requested-With") == "XMLHttpRequest"
    )


def upload_error(message: str, status_code: int = 400):
    if wants_json_response():
        return jsonify({"error": message}), status_code
    flash(message, "error")
    return redirect(url_for("chat.chat"))


@documents_bp.route("/upload", methods=["POST"])
@login_required
def upload():

    if "file" not in request.files:
        return upload_error("No file selected.")

    file = request.files["file"]

    if not file or not file.filename:
        return upload_error("No file selected.")

    if not allowed_file(file.filename):
        return upload_error("Unsupported file type.")

    original_filename = secure_filename(
        file.filename
    )

    if not original_filename:
        return upload_error("The filename is invalid.")

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

    try:
        file.save(file_path)
    except OSError:
        current_app.logger.exception("[DOC] Failed to save upload")
        return upload_error("The file could not be saved.", 500)

    user = db.session.get(User, session["user_id"])
    if not user:
        return upload_error("User not found.", 401)

    is_admin = user.role == "ADMIN"

    document = Document(
        filename=original_filename,
        stored_filename=stored_filename,
        file_path=str(file_path),
        file_type=extension.lstrip("."),
        status="APPROVED" if is_admin else "PENDING",
        uploaded_by=user.id,
    )

    db.session.add(document)
    db.session.commit()

    if is_admin:
        try:
            process_document(document.id)
        except Exception:
            current_app.logger.exception(
                "[DOC] Admin upload processing failed for document %s",
                document.id,
            )
            message = "Document uploaded, but processing failed. An admin can retry it."
            final_status = "FAILED"
        else:
            message = "Document uploaded and processed successfully."
            final_status = "COMPLETED"
    else:
        message = "Document uploaded and is waiting for admin approval."
        final_status = "PENDING"

    payload = {
        "message": message,
        "document": {
            "id": document.id,
            "filename": document.filename,
            "status": final_status,
        },
    }
    if wants_json_response():
        return jsonify(payload), 201

    flash(message, "success" if final_status != "FAILED" else "error")
    return redirect(url_for("chat.chat"))


@documents_bp.route("/chunks/<string:chunk_id>", methods=["GET"])
@login_required
def get_chunk(chunk_id):
    """Return a cited source from the shared completed knowledge base."""
    from app.models import DocumentChunk

    chunk = DocumentChunk.query.filter_by(chunk_id=chunk_id).first()
    if not chunk:
        return jsonify({"error": "Source not found."}), 404

    user = db.session.get(User, session["user_id"])
    if not user:
        return jsonify({"error": "Source not found."}), 404

    if chunk.document.status != "COMPLETED":
        return jsonify({"error": "Source not found."}), 404

    return jsonify({
        "chunk_id": chunk.chunk_id,
        "document_id": chunk.document_id,
        "filename": chunk.document.filename,
        "page_number": chunk.page_number,
        "content": chunk.content,
        "extraction_method": chunk.extraction_method,
        "content_type": chunk.content_type,
    })


@documents_bp.route("/mine", methods=["GET"])
@login_required
def my_documents():
    """List a user's uploads plus every shared completed document."""
    user_id = session["user_id"]

    user = db.session.get(User, user_id)
    if not user:
        return jsonify({"error": "User not found."}), 401

    query = Document.query
    if not user.is_admin:
        query = query.filter(
            or_(
                Document.uploaded_by == user_id,
                Document.status == "COMPLETED",
            )
        )

    documents = query.order_by(Document.created_at.desc()).all()

    return jsonify([
        {
            "id": document.id,
            "filename": document.filename,
            "file_type": document.file_type,
            "status": document.status,
            "uploaded_by": document.uploaded_by,
            "uploader": document.uploader.username if document.uploader else None,
            "is_mine": document.uploaded_by == user_id,
            "created_at": document.created_at.isoformat(),
            "updated_at": document.updated_at.isoformat(),
        }
        for document in documents
    ])

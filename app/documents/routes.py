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
    send_file,
    url_for,
)
from werkzeug.utils import secure_filename
from app.auth.decorators import login_required
from sqlalchemy import or_
from app.extensions import db
from app.models import (
    Document,
    DocumentChunk,
    DocumentImage,
    DocumentSourcePage,
    User,
)
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


@documents_bp.route("/<int:document_id>/source", methods=["GET"])
@login_required
def get_document_source(document_id):
    """Return a completed document's ordered source chunks for the viewer.

    The viewer uses this only to build a continuous HTML representation.  It
    intentionally exposes no filesystem path or original uploaded file.
    Completed documents follow the application's shared-RAG access rule.
    """
    document = db.session.get(Document, document_id)
    if not document or document.status != "COMPLETED":
        return jsonify({"error": "Source not found."}), 404

    chunks = (
        DocumentChunk.query
        .filter_by(document_id=document.id)
        .order_by(DocumentChunk.page_number, DocumentChunk.chunk_index)
        .all()
    )
    images = (
        DocumentImage.query
        .filter_by(document_id=document.id)
        .order_by(DocumentImage.page_number, DocumentImage.vertical_position, DocumentImage.image_index)
        .all()
    )
    source_pages = (
        DocumentSourcePage.query
        .filter_by(document_id=document.id)
        .order_by(DocumentSourcePage.page_number)
        .all()
    )

    def image_payload(image):
        return {
            "image_id": image.image_id,
            "page_number": image.page_number,
            "image_index": image.image_index,
            "vertical_position": image.vertical_position,
            "source_kind": image.source_kind,
            "url": url_for("documents.get_source_image", image_id=image.image_id),
        }

    # One visual is rendered for a PDF page, regardless of how many text
    # chunks, OCR detections, or embedded assets belong to it.  Older
    # ingestions without a saved page render retain their full embedded image
    # assets as a compatibility fallback.
    page_visuals = []
    images_by_page = {}
    for image in images:
        images_by_page.setdefault(image.page_number, []).append(image)
    for page_number, page_images in images_by_page.items():
        full_page = next(
            (image for image in page_images if image.source_kind in {"ocr_page", "pdf_page"}),
            None,
        )
        if full_page:
            page_visuals.append(image_payload(full_page))
        else:
            page_visuals.extend(image_payload(image) for image in page_images)

    return jsonify({
        "document_id": document.id,
        "filename": document.filename,
        "images": [image_payload(image) for image in images],
        "page_visuals": page_visuals,
        "pages": [
            {
                "page_number": page.page_number,
                "content": page.content,
                "extraction_method": page.extraction_method,
            }
            for page in source_pages
        ],
        "chunks": [
            {
                "chunk_id": chunk.chunk_id,
                "content": chunk.content,
                "page_number": chunk.page_number,
                "chunk_index": chunk.chunk_index,
                "extraction_method": chunk.extraction_method,
                "content_type": chunk.content_type,
            }
            for chunk in chunks
        ],
    })


@documents_bp.route("/images/<string:image_id>", methods=["GET"])
@login_required
def get_source_image(image_id):
    """Serve a preserved source visual only after document access validation."""
    image = DocumentImage.query.filter_by(image_id=image_id).first()
    if not image or image.document.status != "COMPLETED":
        return jsonify({"error": "Source image not found."}), 404

    image_path = Path(current_app.config["SOURCE_IMAGE_FOLDER"]) / image.stored_filename
    if not image_path.is_file():
        current_app.logger.warning("[DOCUMENT] Missing source image %s", image_id)
        return jsonify({"error": "Source image not found."}), 404

    return send_file(image_path, mimetype=image.mime_type, conditional=True)


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

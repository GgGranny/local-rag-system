from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    session,
    current_app,
)

from app.auth.decorators import admin_required
from app.extensions import db
from app.models import User, Document
from app.ingestion.pipeline import process_document, remove_document_index, delete_document


admin_bp = Blueprint(
    "admin",
    __name__,
    url_prefix="/admin"
)


@admin_bp.route("")
@admin_required
def dashboard():
    users = User.query.order_by(
        User.created_at.desc()
    ).all()

    document_counts = {
        status: Document.query.filter_by(status=status).count()
        for status in ("PENDING", "PROCESSING", "COMPLETED", "FAILED")
    }

    return render_template(
        "admin/dashboard.html",
        users=users,
        document_counts=document_counts,
    )


@admin_bp.route("/users/create", methods=["POST"])
@admin_required
def create_user():

    username = request.form.get(
        "username",
        ""
    ).strip()

    password = request.form.get(
        "password",
        ""
    )

    if not username or not password:
        flash(
            "Username and password are required.",
            "error"
        )

        return redirect(
            url_for("admin.dashboard")
        )

    existing_user = User.query.filter_by(
        username=username
    ).first()

    if existing_user:
        flash(
            "Username already exists.",
            "error"
        )

        return redirect(
            url_for("admin.dashboard")
        )

    user = User(
        username=username,
        role="USER",
        is_active=True
    )

    user.set_password(password)

    db.session.add(user)
    db.session.commit()

    flash(
        f"User '{username}' created successfully.",
        "success"
    )

    return redirect(
        url_for("admin.dashboard")
    )


@admin_bp.route("/users/<int:user_id>/toggle", methods=["POST"])
@admin_required
def toggle_user(user_id):
    user = db.session.get(User, user_id)
    if not user:
        flash("User not found.", "error")
    elif user.id == session["user_id"]:
        flash("You cannot deactivate your own account.", "error")
    else:
        user.is_active = not user.is_active
        db.session.commit()
        flash(f"User '{user.username}' updated.", "success")
    return redirect(url_for("admin.dashboard"))


@admin_bp.route("/users/<int:user_id>/delete", methods=["POST"])
@admin_required
def delete_user(user_id):
    user = db.session.get(User, user_id)
    if not user:
        flash("User not found.", "error")
    elif user.id == session["user_id"]:
        flash("You cannot delete your own account.", "error")
    elif user.is_admin:
        flash("Administrator accounts cannot be deleted here.", "error")
    elif user.documents or user.conversations:
        flash("Users with documents or conversations cannot be deleted.", "error")
    else:
        db.session.delete(user)
        db.session.commit()
        flash(f"User '{user.username}' deleted.", "success")
    return redirect(url_for("admin.dashboard"))


# ---------------------------------------------------------
# DOCUMENT MANAGEMENT
# ---------------------------------------------------------

@admin_bp.route("/documents")
@admin_required
def documents():

    documents = Document.query.order_by(
        Document.created_at.desc()
    ).all()

    return render_template(
        "admin/documents.html",
        documents=documents
    )


def _validated_bulk_document_ids():
    values = request.form.getlist("document_ids")
    if not values:
        raise ValueError("Select at least one document.")
    try:
        ids = [int(value) for value in values]
    except (TypeError, ValueError):
        raise ValueError("Document IDs must be valid integers.") from None
    if any(document_id <= 0 for document_id in ids) or len(ids) != len(set(ids)):
        raise ValueError("Document IDs must be unique positive integers.")
    found = {item.id for item in Document.query.filter(Document.id.in_(ids)).all()}
    if found != set(ids):
        raise LookupError("One or more selected documents no longer exist.")
    return ids


@admin_bp.route("/documents/<int:document_id>/delete", methods=["POST"])
@admin_required
def delete_document_route(document_id):
    try:
        filename = delete_document(document_id)
    except LookupError:
        flash("Document not found.", "error")
    except Exception:
        current_app.logger.exception("[DOCUMENT] Failed to delete document %s", document_id)
        flash("Document deletion failed; no success was recorded.", "error")
    else:
        flash(f"'{filename}' was deleted with its retrieval and source assets.", "success")
    return redirect(url_for("admin.documents"))


@admin_bp.route("/documents/bulk-delete", methods=["POST"])
@admin_required
def bulk_delete_documents():
    names = []
    try:
        document_ids = _validated_bulk_document_ids()
        for document_id in document_ids:
            names.append(delete_document(document_id))
    except (ValueError, LookupError) as exc:
        flash(str(exc), "error")
    except Exception:
        current_app.logger.exception("[DOCUMENT] Failed to bulk delete documents")
        flash(
            f"Bulk deletion stopped after deleting {len(names)} document(s); "
            "check the logs before retrying the remaining selection.",
            "error",
        )
    else:
        flash(f"Deleted {len(names)} document{'s' if len(names) != 1 else ''}.", "success")
    return redirect(url_for("admin.documents"))


@admin_bp.route(
    "/documents/<int:document_id>/approve",
    methods=["POST"]
)
@admin_required
def approve_document(document_id):

    document = db.session.get(
        Document,
        document_id
    )

    if not document:
        flash(
            "Document not found.",
            "error"
        )

        return redirect(
            url_for("admin.documents")
        )

    if document.status != "PENDING":
        flash(
            "Only pending documents can be approved.",
            "error"
        )

        return redirect(
            url_for("admin.documents")
        )

    document.status = "APPROVED"
    db.session.commit()

    try:
        process_document(
            document.id
        )
        flash(
            f"'{document.filename}' approved and processed successfully.",
            "success"
        )
    except Exception:
        db.session.rollback()
        current_app.logger.exception("[DOC] Approval processing failed")
        flash(
            f"'{document.filename}' was approved, "
            f"but processing failed.",
            "error"
        )

    return redirect(
        url_for("admin.documents")
    )


@admin_bp.route(
    "/documents/<int:document_id>/reject",
    methods=["POST"]
)
@admin_required
def reject_document(document_id):

    document = db.session.get(
        Document,
        document_id
    )

    if not document:
        flash(
            "Document not found.",
            "error"
        )

        return redirect(
            url_for("admin.documents")
        )

    if document.status != "PENDING":
        flash(
            "Only pending documents can be rejected.",
            "error"
        )

        return redirect(
            url_for("admin.documents")
        )

    document.status = "REJECTED"
    db.session.commit()
    remove_document_index(document.id)

    flash(
        f"'{document.filename}' rejected.",
        "success"
    )

    return redirect(
        url_for("admin.documents")
    )


@admin_bp.route("/documents/<int:document_id>/reprocess", methods=["POST"])
@admin_required
def reprocess_document(document_id):
    document = db.session.get(Document, document_id)
    if not document:
        flash("Document not found.", "error")
        return redirect(url_for("admin.documents"))
    if document.status not in {"FAILED", "COMPLETED"}:
        flash("Only failed or completed documents can be reprocessed.", "error")
        return redirect(url_for("admin.documents"))

    document.status = "APPROVED"
    db.session.commit()
    try:
        process_document(document.id)
    except Exception:
        db.session.rollback()
        current_app.logger.exception("[DOC] Reprocessing failed")
        flash(f"'{document.filename}' could not be processed.", "error")
    else:
        flash(f"'{document.filename}' was reprocessed.", "success")
    return redirect(url_for("admin.documents"))

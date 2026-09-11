from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash,
)

from app.auth.decorators import admin_required
from app.extensions import db
from app.models import User, Document
from app.ingestion.pipeline import process_document


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

    return render_template(
        "admin/dashboard.html",
        users=users
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

    flash(
        f"'{document.filename}' rejected.",
        "success"
    )

    return redirect(
        url_for("admin.documents")
    )
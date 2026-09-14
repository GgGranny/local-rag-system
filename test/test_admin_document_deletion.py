from pathlib import Path

from app import create_app
from app.config import Config
from app.extensions import db
from app.ingestion.pipeline import delete_document
from app.models import Document, DocumentChunk, DocumentImage, DocumentSourcePage, User


def make_app(tmp_path):
    app = create_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": f"sqlite:///{(tmp_path / 'admin.db').as_posix()}"})
    with app.app_context():
        admin = User(username="admin-delete", role="ADMIN", is_active=True); admin.set_password("password")
        user = User(username="user-delete", role="USER", is_active=True); user.set_password("password")
        db.session.add_all([admin, user]); db.session.commit()
        document = Document(filename="remove.pdf", stored_filename="remove.pdf", file_path="remove.pdf", file_type="pdf", status="COMPLETED", uploaded_by=user.id)
        db.session.add(document); db.session.commit()
        return app, admin.id, user.id, document.id


def login(client, user_id, role):
    with client.session_transaction() as state:
        state["user_id"] = user_id
        state["role"] = role


def test_delete_routes_are_admin_only(tmp_path):
    app, admin_id, user_id, document_id = make_app(tmp_path)
    client = app.test_client()
    assert client.post(f"/admin/documents/{document_id}/delete").status_code == 302
    login(client, user_id, "USER")
    assert client.post(f"/admin/documents/{document_id}/delete").status_code == 403
    assert client.post("/admin/documents/bulk-delete", data={"document_ids": [document_id]}).status_code == 403


def test_admin_single_and_bulk_routes_only_send_valid_requested_ids(tmp_path, monkeypatch):
    app, admin_id, _, document_id = make_app(tmp_path)
    with app.app_context():
        document = db.session.get(Document, document_id)
        second = Document(filename="second.txt", stored_filename="second.txt", file_path="second.txt", file_type="txt", status="PENDING", uploaded_by=document.uploaded_by)
        db.session.add(second); db.session.commit(); second_id = second.id
    deleted = []
    monkeypatch.setattr("app.admin.routes.delete_document", lambda document_id: deleted.append(document_id) or "deleted")
    client = app.test_client(); login(client, admin_id, "ADMIN")
    assert client.post(f"/admin/documents/{document_id}/delete").status_code == 302
    assert client.post("/admin/documents/bulk-delete", data={"document_ids": [second_id]}).status_code == 302
    assert deleted == [document_id, second_id]
    assert client.post("/admin/documents/bulk-delete", data={"document_ids": [second_id, second_id]}).status_code == 302
    assert deleted == [document_id, second_id]


def test_cleanup_removes_only_document_owned_rows_and_managed_files(tmp_path, monkeypatch):
    app, _, _, document_id = make_app(tmp_path)
    upload_dir, image_dir = tmp_path / "uploads", tmp_path / "images"
    upload_dir.mkdir(); image_dir.mkdir()
    upload_file, image_file = upload_dir / "remove.pdf", image_dir / "page.png"
    upload_file.write_bytes(b"upload"); image_file.write_bytes(b"image")
    monkeypatch.setattr(Config, "UPLOAD_FOLDER", str(upload_dir))
    monkeypatch.setattr(Config, "SOURCE_IMAGE_FOLDER", str(image_dir))
    monkeypatch.setattr("app.ingestion.pipeline.delete_document_chunks", lambda document_id: None)
    monkeypatch.setattr("app.ingestion.pipeline.rebuild_bm25_index", lambda: None)
    with app.app_context():
        document = db.session.get(Document, document_id); document.file_path = str(upload_file)
        db.session.add_all([
            DocumentChunk(document_id=document_id, chunk_id="delete-chunk", content="content", chunk_index=0),
            DocumentSourcePage(document_id=document_id, page_number=1, content="content"),
            DocumentImage(document_id=document_id, image_id="delete-image", stored_filename="page.png", mime_type="image/png"),
        ])
        db.session.commit()
        assert delete_document(document_id) == "remove.pdf"
        assert db.session.get(Document, document_id) is None
        assert DocumentChunk.query.filter_by(document_id=document_id).count() == 0
        assert DocumentSourcePage.query.filter_by(document_id=document_id).count() == 0
        assert DocumentImage.query.filter_by(document_id=document_id).count() == 0
    assert not upload_file.exists() and not image_file.exists()

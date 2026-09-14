from app import create_app
from app.extensions import db
from app.models import Document, DocumentChunk, DocumentImage, User


def make_app(tmp_path):
    app = create_app({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": f"sqlite:///{(tmp_path / 'source.db').as_posix()}",
    })
    with app.app_context():
        user = User(username="source-user", role="USER", is_active=True)
        user.set_password("password")
        db.session.add(user)
        db.session.flush()
        document = Document(
            filename="visual.pdf", stored_filename="visual.pdf", file_path="safe.pdf",
            file_type="pdf", status="COMPLETED", uploaded_by=user.id,
        )
        db.session.add(document)
        db.session.flush()
        db.session.add_all([
            DocumentChunk(document_id=document.id, chunk_id="page-1-a", content="First chunk", page_number=1, chunk_index=0),
            DocumentChunk(document_id=document.id, chunk_id="page-1-b", content="Second chunk", page_number=1, chunk_index=1),
            DocumentImage(document_id=document.id, image_id="page-render", stored_filename="page.png", mime_type="image/png", page_number=1, source_kind="pdf_page"),
            DocumentImage(document_id=document.id, image_id="embedded", stored_filename="figure.png", mime_type="image/png", page_number=1, source_kind="embedded"),
        ])
        db.session.commit()
        return app, user.id, document.id


def test_source_api_prefers_one_complete_page_visual_over_chunk_or_embedded_fragments(tmp_path):
    app, user_id, document_id = make_app(tmp_path)
    client = app.test_client()
    with client.session_transaction() as state:
        state["user_id"] = user_id
        state["role"] = "USER"
    response = client.get(f"/documents/{document_id}/source")
    assert response.status_code == 200
    payload = response.get_json()
    assert [item["image_id"] for item in payload["page_visuals"]] == ["page-render"]
    assert payload["page_visuals"][0]["source_kind"] == "pdf_page"


def test_source_visual_response_does_not_expose_storage_paths(tmp_path):
    app, user_id, document_id = make_app(tmp_path)
    client = app.test_client()
    with client.session_transaction() as state:
        state["user_id"] = user_id
        state["role"] = "USER"
    payload = client.get(f"/documents/{document_id}/source").get_json()
    assert "stored_filename" not in payload["page_visuals"][0]
    assert payload["page_visuals"][0]["url"].startswith("/documents/images/")

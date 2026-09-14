from app import create_app
from app.extensions import db
from app.models import Conversation, User


def make_app(tmp_path):
    app = create_app({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": f"sqlite:///{(tmp_path / 'chat.db').as_posix()}",
    })
    with app.app_context():
        for username, role in (("alice", "USER"), ("bob", "USER")):
            user = User(username=username, role=role, is_active=True)
            user.set_password("password")
            db.session.add(user)
        db.session.commit()
    return app


def login(client, user):
    with client.session_transaction() as state:
        state["user_id"] = user.id
        state["role"] = user.role


def test_new_conversation_is_unique_and_owned(tmp_path):
    app = make_app(tmp_path)
    with app.app_context():
        alice = User.query.filter_by(username="alice").one()
        alice_id = alice.id
    client = app.test_client()
    login(client, type("UserRef", (), {"id": alice_id, "role": "USER"})())
    first = client.post("/chat/conversations")
    second = client.post("/chat/conversations")
    assert first.status_code == 201 and second.status_code == 201
    assert first.json["thread_id"] != second.json["thread_id"]
    with app.app_context():
        assert Conversation.query.filter_by(user_id=alice_id).count() == 2


def test_user_cannot_read_or_delete_another_users_conversation(tmp_path, monkeypatch):
    app = make_app(tmp_path)
    with app.app_context():
        alice = User.query.filter_by(username="alice").one()
        bob = User.query.filter_by(username="bob").one()
        conversation = Conversation(user_id=alice.id, thread_id="alice-thread", title="Alice chat")
        db.session.add(conversation)
        db.session.commit()
        bob_id = bob.id
    client = app.test_client()
    login(client, type("UserRef", (), {"id": bob_id, "role": "USER"})())
    assert client.get("/chat/conversations/alice-thread").status_code == 404
    assert client.delete("/chat/conversations/alice-thread").status_code == 404


def test_owner_delete_removes_conversation_without_touching_documents(tmp_path, monkeypatch):
    app = make_app(tmp_path)
    with app.app_context():
        alice = User.query.filter_by(username="alice").one()
        conversation = Conversation(user_id=alice.id, thread_id="delete-thread", title="Delete me")
        db.session.add(conversation)
        db.session.commit()
        alice_id = alice.id
    monkeypatch.setattr("app.chat.routes.delete_thread_checkpoints", lambda thread_id: None)
    client = app.test_client()
    login(client, type("UserRef", (), {"id": alice_id, "role": "USER"})())
    assert client.delete("/chat/conversations/delete-thread").get_json()["deleted"] is True
    with app.app_context():
        assert Conversation.query.filter_by(thread_id="delete-thread").first() is None

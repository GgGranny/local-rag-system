"""Authorization and empty-state coverage for the admin monitoring surface."""

from app import create_app
from app.extensions import db
from app.models import User


def make_app(tmp_path):
    app = create_app({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": f"sqlite:///{(tmp_path / 'monitoring.db').as_posix()}",
    })
    with app.app_context():
        user = User(username="monitoring-user", role="USER", is_active=True)
        user.set_password("password")
        db.session.add(user)
        db.session.commit()
    return app


def login_as(client, user_id, role):
    with client.session_transaction() as session:
        session["user_id"] = user_id
        session["role"] = role


def test_monitoring_requires_admin(tmp_path):
    app = make_app(tmp_path)
    with app.app_context():
        user = User.query.filter_by(username="monitoring-user").one()
        user_id = user.id
    client = app.test_client()
    login_as(client, user_id, "USER")
    assert client.get("/admin/monitoring/api/overview").status_code == 403


def test_admin_can_read_empty_monitoring_overview(tmp_path):
    app = make_app(tmp_path)
    with app.app_context():
        admin = User.query.filter_by(role="ADMIN").first()
        admin_id = admin.id
    client = app.test_client()
    login_as(client, admin_id, "ADMIN")
    response = client.get("/admin/monitoring/api/overview?window=15m")
    assert response.status_code == 200
    assert response.get_json()["requests"] >= 0

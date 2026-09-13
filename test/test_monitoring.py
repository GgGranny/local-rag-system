"""Authorization and empty-state coverage for the admin monitoring surface."""

from app import create_app
from app.extensions import db
from app.models import RAGEvaluation, RAGTrace, User
from app.monitoring.ragas_service import run_answer_relevancy


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


def make_trace(app, *, question="What is the policy?", answer="The policy is 30 days."):
    with app.app_context():
        user = User.query.filter_by(username="monitoring-user").one()
        trace = RAGTrace(
            trace_id="00000000-0000-0000-0000-000000000001",
            message_id="00000000-0000-0000-0000-000000000002",
            conversation_id=None, user_id=user.id, user_role="USER", status="SUCCESS",
            original_query=question, retrieval_query="rewritten policy question", answer_text=answer,
        )
        db.session.add(trace)
        db.session.commit()
        return trace.trace_id


def test_manual_evaluation_persists_exact_trace_inputs(tmp_path):
    app = make_app(tmp_path)
    trace_id = make_trace(app)
    with app.app_context():
        trace = RAGTrace.query.filter_by(trace_id=trace_id).one()
        item = run_answer_relevancy(trace)
        assert item.status == "NOT_CONFIGURED"
        assert item.original_user_question == "What is the policy?"
        assert item.final_retrieval_query == "rewritten policy question"
        assert item.generated_answer == "The policy is 30 days."
        assert item.answer_relevance is None
        assert item.evaluated_at is not None


def test_evaluation_api_is_admin_only_and_reports_no_zero_score(tmp_path):
    app = make_app(tmp_path)
    trace_id = make_trace(app)
    with app.app_context():
        user = User.query.filter_by(username="monitoring-user").one()
        admin = User.query.filter_by(role="ADMIN").first()
        db.session.add(RAGEvaluation(
            trace_id=trace_id, message_id="00000000-0000-0000-0000-000000000002",
            user_id=user.id, status="FAILED", method="manual", metric_name="answer_relevancy",
            error_message="Evaluator unavailable",
        ))
        db.session.commit()
        admin_id, user_id = admin.id, user.id
    client = app.test_client()
    login_as(client, user_id, "USER")
    assert client.get("/admin/monitoring/api/evaluations/answer-relevancy").status_code == 403
    assert client.post(f"/admin/monitoring/api/traces/{trace_id}/evaluations/answer-relevancy").status_code == 403
    login_as(client, admin_id, "ADMIN")
    payload = client.get("/admin/monitoring/api/evaluations/answer-relevancy").get_json()
    assert payload["items"][0]["score"] is None
    overview = client.get("/admin/monitoring/api/overview?window=24h").get_json()["evaluation"]
    assert overview["average_answer_relevance"] is None
    assert overview["failed"] == 1

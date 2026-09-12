"""Admin-only monitoring APIs and the trace explorer UI."""

from datetime import datetime

from flask import Blueprint, jsonify, render_template, request
from sqlalchemy.orm import joinedload

from app.auth.decorators import admin_required
from app.config import Config
from app.extensions import db
from app.models import Conversation, RAGEvaluation, RAGTrace, User
from app.monitoring.metrics import overview, parse_window, trace_payload


monitoring_bp = Blueprint("monitoring", __name__, url_prefix="/admin/monitoring")
_WINDOWS = {"15m", "1h", "24h", "7d"}


def _window():
    value = request.args.get("window", "24h")
    if value not in _WINDOWS:
        return None, (jsonify({"error": "window must be one of: 15m, 1h, 24h, 7d."}), 400)
    return parse_window(value), None


def _page():
    try:
        value = int(request.args.get("page", 1))
        per_page = int(request.args.get("per_page", 25))
    except ValueError:
        return None, None, (jsonify({"error": "page and per_page must be integers."}), 400)
    if value < 1 or not 1 <= per_page <= 100:
        return None, None, (jsonify({"error": "page must be positive and per_page must be 1-100."}), 400)
    return value, per_page, None


@monitoring_bp.route("", methods=["GET"])
@admin_required
def dashboard():
    return render_template("admin/monitoring.html")


@monitoring_bp.route("/traces/<string:trace_id>", methods=["GET"])
@admin_required
def trace_detail(trace_id):
    # Resolve on the server so an invalid URL is a real 404 rather than a
    # blank client-side panel.
    trace = RAGTrace.query.filter_by(trace_id=trace_id).first_or_404()
    return render_template("admin/trace_detail.html", trace=trace)


@monitoring_bp.route("/api/overview", methods=["GET"])
@admin_required
def api_overview():
    window, error = _window()
    if error:
        return error
    payload = overview(window)
    evaluations = RAGEvaluation.query.filter_by(status="COMPLETED").all()
    faithfulness = [item.faithfulness for item in evaluations if item.faithfulness is not None]
    relevance = [item.answer_relevance for item in evaluations if item.answer_relevance is not None]
    payload["evaluation"] = {
        "count": len(evaluations),
        "average_faithfulness": round(sum(faithfulness) / len(faithfulness), 3) if faithfulness else None,
        "average_answer_relevance": round(sum(relevance) / len(relevance), 3) if relevance else None,
    }
    since = datetime.utcnow() - window
    traces = RAGTrace.query.filter(RAGTrace.started_at >= since).all()
    reported = [item for item in traces if item.prompt_tokens is not None or item.completion_tokens is not None]
    payload["token_usage"] = {
        "prompt_tokens": sum(item.prompt_tokens or 0 for item in reported) if reported else None,
        "completion_tokens": sum(item.completion_tokens or 0 for item in reported) if reported else None,
        "reported_trace_count": len(reported),
        "unknown_trace_count": len(traces) - len(reported),
        "estimated_cost": round(sum(item.estimated_cost or 0 for item in reported), 6) if reported else None,
        "cost_rate_configured": bool(
            Config.OLLAMA_INPUT_COST_PER_1K_TOKENS or Config.OLLAMA_OUTPUT_COST_PER_1K_TOKENS
        ),
    }
    return jsonify(payload)


@monitoring_bp.route("/api/traces", methods=["GET"])
@admin_required
def api_traces():
    page, per_page, error = _page()
    if error:
        return error
    query = RAGTrace.query.order_by(RAGTrace.started_at.desc())
    status = request.args.get("status")
    if status in {"SUCCESS", "FAILED", "RUNNING"}:
        query = query.filter_by(status=status)
    result = query.paginate(page=page, per_page=per_page, error_out=False)
    items = [trace_payload(item) for item in result.items]
    for item in items:
        item["detail_url"] = request.url_root.rstrip("/") + "/admin/monitoring/traces/" + item["trace_id"]
    return jsonify({"items": items, "page": page,
                    "per_page": per_page, "total": result.total, "pages": result.pages})


@monitoring_bp.route("/api/traces/<string:trace_id>", methods=["GET"])
@admin_required
def api_trace(trace_id):
    trace = RAGTrace.query.filter_by(trace_id=trace_id).first()
    if not trace:
        return jsonify({"error": "Trace not found."}), 404
    payload = trace_payload(trace, include_content=True)
    payload["evaluations"] = [{
        "id": item.id, "status": item.status, "method": item.method,
        "faithfulness": item.faithfulness, "answer_relevance": item.answer_relevance,
        "context_precision": item.context_precision, "context_recall": item.context_recall,
        "answer_correctness": item.answer_correctness, "created_at": item.created_at.isoformat(),
        "error_message": item.error_message,
    } for item in trace.evaluations]
    return jsonify(payload)


@monitoring_bp.route("/api/conversations", methods=["GET"])
@admin_required
def api_conversations():
    page, per_page, error = _page()
    if error:
        return error
    query = Conversation.query.options(joinedload(Conversation.user)).order_by(Conversation.updated_at.desc())
    user_id = request.args.get("user_id")
    if user_id:
        try:
            query = query.filter(Conversation.user_id == int(user_id))
        except ValueError:
            return jsonify({"error": "user_id must be an integer."}), 400
    result = query.paginate(page=page, per_page=per_page, error_out=False)
    items = []
    for conversation in result.items:
        latest = RAGTrace.query.filter_by(conversation_id=conversation.id).order_by(RAGTrace.started_at.desc()).first()
        items.append({"id": conversation.id, "thread_id": conversation.thread_id, "title": conversation.title,
                      "user": conversation.user.username, "user_id": conversation.user_id,
                      "updated_at": conversation.updated_at.isoformat(), "created_at": conversation.created_at.isoformat(),
                      "latest_trace_id": latest.trace_id if latest else None,
                      "last_status": latest.status if latest else None, "total_ms": latest.total_ms if latest else None})
    return jsonify({"items": items, "page": page, "per_page": per_page, "total": result.total, "pages": result.pages})


@monitoring_bp.route("/api/evaluations", methods=["GET"])
@admin_required
def api_evaluations():
    page, per_page, error = _page()
    if error:
        return error
    result = RAGEvaluation.query.order_by(RAGEvaluation.created_at.desc()).paginate(page=page, per_page=per_page, error_out=False)
    return jsonify({"items": [{"id": item.id, "trace_id": item.trace_id, "status": item.status,
                                 "method": item.method, "faithfulness": item.faithfulness,
                                 "answer_relevance": item.answer_relevance, "context_precision": item.context_precision,
                                 "context_recall": item.context_recall, "created_at": item.created_at.isoformat()}
                                for item in result.items], "page": page, "total": result.total, "pages": result.pages})

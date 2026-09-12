import json
import math
from collections import Counter, defaultdict
from datetime import datetime, timedelta

from app.config import Config
from app.models import RAGTrace


STAGE_DISPLAY = {
    "rag.request": ("Total request", "End-to-end request handling."),
    "rag.query.classification": ("Understand the question", "Determines whether the question is independent or a follow-up."),
    "rag.query.rewrite": ("Rewrite follow-up question", "Reformulates a follow-up for document retrieval."),
    "rag.retrieval": ("Search relevant documents", "Retrieves chunks from the shared completed-document knowledge base."),
    "rag.context.build": ("Prepare source context", "Builds the source context sent to the model."),
    "rag.prompt.build": ("Build model prompt", "Builds the grounded Ollama prompt."),
    "rag.generation": ("Generate answer", "Runs the local Ollama model."),
    "rag.citations": ("Prepare citations", "Maps returned chunks to citation metadata."),
    "rag.persistence": ("Save response", "Persists the conversation update."),
}


def display_stage(name: str) -> dict:
    label, description = STAGE_DISPLAY.get(name, (name, "Recorded monitoring stage."))
    return {"internal_name": name, "label": label, "description": description}


def parse_window(value: str | None) -> timedelta:
    return {"15m": timedelta(minutes=15), "1h": timedelta(hours=1),
            "24h": timedelta(hours=24), "7d": timedelta(days=7)}.get(value or "24h", timedelta(hours=24))


def percentile(values, point):
    if not values:
        return None
    values = sorted(values)
    position = (len(values) - 1) * point
    lower, upper = math.floor(position), math.ceil(position)
    if lower == upper:
        return round(values[lower], 2)
    return round(values[lower] + (values[upper] - values[lower]) * (position - lower), 2)


def _availability(value, enabled: bool, *, applicable: bool = True):
    """Make privacy and missing-data states distinguishable to the UI."""
    if not applicable:
        return {"available": False, "reason": "not_applicable", "value": None}
    if value is not None:
        return {"available": True, "reason": None, "value": value}
    if not enabled:
        return {"available": False, "reason": "privacy_disabled", "value": None}
    return {"available": False, "reason": "not_collected", "value": None}


def trace_payload(trace: RAGTrace, include_content=False):
    def load(value, fallback):
        try: return json.loads(value or fallback)
        except (TypeError, ValueError): return json.loads(fallback)
    data = {
        "trace_id": trace.trace_id, "message_id": trace.message_id,
        "conversation_id": trace.conversation_id, "user_id": trace.user_id,
        "user_role": trace.user_role, "status": trace.status,
        "started_at": trace.started_at.isoformat(),
        "completed_at": trace.completed_at.isoformat() if trace.completed_at else None,
        "total_ms": trace.total_ms, "query_type": trace.query_type,
        "rewrite_used": trace.rewrite_used,
        "selected_document_ids": load(trace.selected_document_ids_json, "[]"),
        "model_name": trace.model_name, "embedding_model_name": trace.embedding_model_name,
        "stage_timings": load(trace.stage_timings_json, "{}"),
        "error": {"stage": trace.error_stage, "type": trace.error_type,
                  "message": trace.error_message} if trace.error_type else None,
        "phoenix_status": trace.phoenix_status,
        "prompt_tokens": trace.prompt_tokens,
        "completion_tokens": trace.completion_tokens,
        "token_estimated": trace.token_estimated,
        "estimated_cost": trace.estimated_cost,
    }
    data["stages"] = [
        {**display_stage(name), "duration_ms": duration}
        for name, duration in data["stage_timings"].items()
        if isinstance(duration, (int, float))
    ]
    data["tokens"] = {
        "prompt": _availability(trace.prompt_tokens, True),
        "completion": _availability(trace.completion_tokens, True),
        "total": _availability(
            (trace.prompt_tokens or 0) + (trace.completion_tokens or 0)
            if trace.prompt_tokens is not None or trace.completion_tokens is not None else None,
            True,
        ),
        "estimated": trace.token_estimated,
    }
    if include_content:
        data.update({
            "original_query": _availability(trace.original_query, Config.MONITORING_STORE_CONTENT),
            "retrieval_query": _availability(trace.retrieval_query, Config.MONITORING_STORE_CONTENT),
            "retrieved_chunks": _availability(
                load(trace.retrieved_chunks_json, "[]") if trace.retrieved_chunks_json is not None else None,
                Config.MONITORING_STORE_CONTEXT,
            ),
            "context": _availability(trace.context_text, Config.MONITORING_STORE_CONTEXT),
            "prompt": _availability(trace.prompt_text, Config.MONITORING_STORE_PROMPTS),
            "answer": _availability(trace.answer_text, Config.MONITORING_STORE_CONTENT),
            "citations": load(trace.citations_json, "[]"),
        })
    return data


def overview(window: timedelta):
    since = datetime.utcnow() - window
    traces = RAGTrace.query.filter(RAGTrace.started_at >= since).all()
    completed = [trace for trace in traces if trace.status == "SUCCESS"]
    failed = [trace for trace in traces if trace.status == "FAILED"]
    latencies = [trace.total_ms for trace in completed if trace.total_ms is not None]
    stage_values = defaultdict(list)
    for trace in completed:
        try: timings = json.loads(trace.stage_timings_json or "{}")
        except ValueError: timings = {}
        for name, duration in timings.items():
            if isinstance(duration, (int, float)): stage_values[name].append(duration)
    errors = Counter((trace.error_stage or "unknown") for trace in failed)
    buckets = Counter(trace.started_at.strftime("%Y-%m-%d %H:00") for trace in traces)
    return {
        "window_seconds": int(window.total_seconds()), "requests": len(traces),
        "successes": len(completed), "failures": len(failed),
        "error_rate": round(len(failed) / len(traces), 4) if traces else 0,
        "qps": round(len(traces) / window.total_seconds(), 5),
        "latency": {"average": round(sum(latencies) / len(latencies), 2) if latencies else None,
                    "p50": percentile(latencies, .5), "p90": percentile(latencies, .9),
                    "p95": percentile(latencies, .95), "p99": percentile(latencies, .99),
                    "max": max(latencies) if latencies else None},
        "errors_by_stage": dict(errors),
        "requests_over_time": [{"time": key, "count": value} for key, value in sorted(buckets.items())],
        "stages": [{**display_stage(name), "average_ms": round(sum(values) / len(values), 2),
                    "p50_ms": percentile(values, .5), "p95_ms": percentile(values, .95),
                    "count": len(values)} for name, values in stage_values.items()],
    }

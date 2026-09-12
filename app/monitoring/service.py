import json
import logging
import time
import uuid
from functools import wraps
from contextvars import ContextVar
from datetime import datetime

from flask import current_app

from app.config import Config
from app.extensions import db
from app.models import RAGTrace

logger = logging.getLogger(__name__)
_execution: ContextVar["TraceExecution | None"] = ContextVar("rag_execution", default=None)


def _safe_json(value):
    return json.dumps(value, ensure_ascii=False, default=str)


def _sanitized_error(exc: Exception) -> str:
    return str(exc).replace("\n", " ")[:500]


class PhoenixBridge:
    """Best-effort Phoenix export; application tracing never depends on it."""

    def __init__(self):
        self.tracer = None
        self.error = None
        if not Config.PHOENIX_ENABLED:
            return
        try:
            from phoenix.otel import register  # Optional dependency.
            from opentelemetry import trace

            register(
                project_name=Config.PHOENIX_PROJECT_NAME,
                endpoint=Config.PHOENIX_ENDPOINT,
            )
            self.tracer = trace.get_tracer("local-rag.monitoring")
        except Exception as exc:  # Phoenix must never make chat unavailable.
            self.error = _sanitized_error(exc)
            logger.warning("[PHOENIX] Disabled: %s", self.error)

    def span(self, name: str, attributes: dict):
        if not self.tracer:
            return _NoopSpan()
        try:
            return self.tracer.start_as_current_span(name, attributes=attributes)
        except Exception as exc:
            logger.warning("[PHOENIX] Span failed: %s", _sanitized_error(exc))
            return _NoopSpan()


class _NoopSpan:
    def __enter__(self): return self
    def __exit__(self, *_args): return False
    def set_attribute(self, *_args): pass
    def record_exception(self, *_args): pass


_phoenix = PhoenixBridge()


class TraceExecution:
    def __init__(self, *, user_id: int, user_role: str, conversation_id: int,
                 selected_document_ids: list[int], question: str):
        self.trace_id = str(uuid.uuid4())
        self.message_id = str(uuid.uuid4())
        self.started_at = datetime.utcnow()
        self.started_perf = time.perf_counter()
        self.user_id = user_id
        self.user_role = user_role
        self.conversation_id = conversation_id
        self.selected_document_ids = selected_document_ids
        self.question = question
        self.stage_timings = {}
        self.data = {"retrieved_chunks": [], "citations": []}
        self.current_stage = "rag.request"

    def stage(self, name: str, **attributes):
        return _MeasuredStage(self, name, attributes)

    def complete(self, result: dict) -> None:
        self.data["answer"] = result.get("answer", "")
        self.data["citations"] = result.get("sources", [])
        self._persist("SUCCESS")

    def fail(self, exc: Exception, stage: str | None = None) -> None:
        self._persist("FAILED", exc, stage or self.current_stage)

    def _persist(self, status: str, exc: Exception | None = None, error_stage: str | None = None):
        if not Config.MONITORING_ENABLED:
            return
        try:
            completed_at = datetime.utcnow()
            total_ms = (time.perf_counter() - self.started_perf) * 1000
            prompt = self.data.get("prompt") if Config.MONITORING_STORE_PROMPTS else None
            context = self.data.get("context") if Config.MONITORING_STORE_CONTEXT else None
            prompt_tokens = self.data.get("prompt_tokens")
            completion_tokens = self.data.get("completion_tokens")
            estimated_cost = None
            if prompt_tokens is not None or completion_tokens is not None:
                estimated_cost = (
                    (float(prompt_tokens or 0) / 1000) * Config.OLLAMA_INPUT_COST_PER_1K_TOKENS
                    + (float(completion_tokens or 0) / 1000) * Config.OLLAMA_OUTPUT_COST_PER_1K_TOKENS
                )
            trace = RAGTrace(
                trace_id=self.trace_id, message_id=self.message_id,
                conversation_id=self.conversation_id, user_id=self.user_id,
                user_role=self.user_role, status=status, started_at=self.started_at,
                completed_at=completed_at, total_ms=total_ms,
                query_type=self.data.get("query_type"),
                rewrite_used=bool(self.data.get("rewrite_used")),
                selected_document_ids_json=_safe_json(self.selected_document_ids),
                original_query=self.question if Config.MONITORING_STORE_CONTENT else None,
                retrieval_query=self.data.get("retrieval_query") if Config.MONITORING_STORE_CONTENT else None,
                retrieved_chunks_json=_safe_json(self.data["retrieved_chunks"]) if Config.MONITORING_STORE_RETRIEVED_CHUNKS else None,
                context_text=context, prompt_text=prompt,
                answer_text=self.data.get("answer") if Config.MONITORING_STORE_GENERATED_ANSWERS else None,
                citations_json=_safe_json(self.data["citations"]) if Config.MONITORING_STORE_CITATIONS else None,
                stage_timings_json=_safe_json(self.stage_timings),
                model_name=Config.OLLAMA_CHAT_MODEL,
                embedding_model_name=Config.OLLAMA_EMBEDDING_MODEL,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                token_estimated=bool(self.data.get("token_estimated", False)),
                estimated_cost=estimated_cost,
                error_stage=error_stage,
                error_type=type(exc).__name__ if exc else None,
                error_message=_sanitized_error(exc) if exc else None,
                phoenix_status="EXPORTED" if _phoenix.tracer else ("UNAVAILABLE" if Config.PHOENIX_ENABLED else "DISABLED"),
            )
            db.session.add(trace)
            db.session.commit()
        except Exception as persist_exc:
            db.session.rollback()
            logger.exception("[MONITORING] Trace persistence failed: %s", _sanitized_error(persist_exc))


class _MeasuredStage:
    def __init__(self, execution: TraceExecution, name: str, attributes: dict):
        self.execution, self.name, self.attributes = execution, name, attributes
        self.started = None
        self.span = None

    def __enter__(self):
        self.execution.current_stage = self.name
        self.started = time.perf_counter()
        attributes = {"rag.trace_id": self.execution.trace_id, **self.attributes}
        self.span = _phoenix.span(self.name, attributes)
        self.span.__enter__()
        return self

    def __exit__(self, exc_type, exc, traceback):
        duration = (time.perf_counter() - self.started) * 1000
        self.execution.stage_timings[self.name] = round(duration, 3)
        if exc:
            self.span.record_exception(exc)
        self.span.set_attribute("rag.duration_ms", duration)
        return self.span.__exit__(exc_type, exc, traceback)


def begin_execution(**kwargs) -> TraceExecution:
    execution = TraceExecution(**kwargs)
    _execution.set(execution)
    return execution


def current_execution() -> TraceExecution | None:
    return _execution.get()


def record(**values) -> None:
    execution = current_execution()
    if execution:
        execution.data.update(values)


def measured(name: str, **attributes):
    execution = current_execution()
    return execution.stage(name, **attributes) if execution else _NoopSpan()


def trace_node(name: str):
    """Measure a LangGraph node without storing tracing objects in graph state."""
    def decorator(function):
        @wraps(function)
        def wrapped(*args, **kwargs):
            with measured(name):
                return function(*args, **kwargs)
        return wrapped
    return decorator

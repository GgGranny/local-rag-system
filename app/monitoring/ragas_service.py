"""Manual, local-only RAGAS answer-relevancy evaluation."""

import asyncio
import importlib.metadata
import math
import time
from datetime import datetime

from langchain_ollama import ChatOllama, OllamaEmbeddings

from app.config import Config
from app.extensions import db
from app.models import RAGEvaluation, RAGTrace
from app.monitoring.service import export_evaluation


def ragas_version() -> str:
    return importlib.metadata.version("ragas")


def _installed_ragas_version() -> str | None:
    try:
        return ragas_version()
    except importlib.metadata.PackageNotFoundError:
        return None


def evaluation_payload(item: RAGEvaluation) -> dict:
    return {
        "evaluation_id": item.id,
        "trace_id": item.trace_id,
        "conversation_id": item.conversation_id,
        "message_id": item.message_id,
        "user_id": item.user_id,
        "metric": item.metric_name,
        "score": item.answer_relevance,
        "status": item.status,
        "method": item.method,
        "model": item.evaluator_model,
        "ragas_version": item.ragas_version,
        "duration_ms": item.duration_ms,
        "evaluated_at": (item.evaluated_at or item.created_at).isoformat(),
        "error": item.error_message,
    }


def _ragas_api():
    """Load the RAGAS 0.4 single-turn API without importing it at startup.

    RAGAS has changed its public metric surface between releases.  This
    application deliberately probes the installed package at evaluation time,
    so a dependency mismatch becomes a durable failed evaluation rather than
    an import failure in chat or monitoring routes.
    """
    try:
        from ragas.dataset_schema import SingleTurnSample
        from ragas.embeddings.base import LangchainEmbeddingsWrapper
        from ragas.llms.base import LangchainLLMWrapper
        from ragas.metrics._answer_relevance import AnswerRelevancy
    except Exception as exc:
        raise RuntimeError(
            "The installed RAGAS package cannot load the 0.4 AnswerRelevancy "
            f"API: {str(exc).replace(chr(10), ' ')[:300]}"
        ) from exc
    return SingleTurnSample, LangchainEmbeddingsWrapper, LangchainLLMWrapper, AnswerRelevancy


def _make_metric(api):
    """Build the RAGAS 0.4 legacy-compatible metric with local Ollama only."""
    _sample, LangchainEmbeddingsWrapper, LangchainLLMWrapper, AnswerRelevancy = api

    llm = ChatOllama(
        model=Config.RAGAS_EVALUATOR_MODEL,
        temperature=0,
        client_kwargs={"timeout": Config.OLLAMA_REQUEST_TIMEOUT},
    )
    # Ollama reports `done_reason`, not LangChain's standard finish_reason.
    # The request has completed when ChatOllama returns a result, so this
    # avoids falsely treating a successful local call as unfinished.
    wrapped_llm = LangchainLLMWrapper(
        llm, is_finished_parser=lambda _result: True, bypass_n=True
    )
    embeddings = OllamaEmbeddings(model=Config.OLLAMA_EMBEDDING_MODEL)
    return AnswerRelevancy(
        llm=wrapped_llm,
        embeddings=LangchainEmbeddingsWrapper(embeddings),
        strictness=3,
    )


def run_answer_relevancy(trace: RAGTrace) -> RAGEvaluation:
    """Persist one manual result for this exact trace; never affects chat."""
    # One current answer-relevancy record per trace avoids a dashboard average
    # being inflated by repeated button clicks. A deliberate rerun refreshes
    # the same durable record and its exact input snapshot.
    item = RAGEvaluation.query.filter_by(
        trace_id=trace.trace_id, metric_name="answer_relevancy"
    ).order_by(RAGEvaluation.created_at.desc()).first()
    if item is None:
        item = RAGEvaluation(trace_id=trace.trace_id, metric_name="answer_relevancy")
        db.session.add(item)
    item.conversation_id = trace.conversation_id
    item.message_id = trace.message_id
    item.user_id = trace.user_id
    item.status = "PENDING"
    item.method = "manual"
    item.evaluator_model = Config.RAGAS_EVALUATOR_MODEL
    item.ragas_version = _installed_ragas_version()
    item.answer_relevance = None
    item.duration_ms = None
    item.evaluated_at = None
    item.error_message = None
    item.original_user_question = (trace.original_query or "").strip() or None
    item.final_retrieval_query = (trace.retrieval_query or "").strip() or None
    item.generated_answer = (trace.answer_text or "").strip() or None
    db.session.commit()

    if not Config.RAGAS_ENABLED or not Config.RAGAS_ANSWER_RELEVANCY_ENABLED:
        item.status = "NOT_CONFIGURED"
        item.error_message = "Answer-relevancy evaluation is disabled by configuration."
        item.evaluated_at = datetime.utcnow()
        db.session.commit()
        export_evaluation(trace, item)
        return item
    question = item.original_user_question or ""
    answer = item.generated_answer or ""
    if not question or not answer:
        item.status = "MISSING_INPUT"
        item.error_message = "The trace is missing the original user question or generated answer."
        item.evaluated_at = datetime.utcnow()
        db.session.commit()
        export_evaluation(trace, item)
        return item

    started = time.perf_counter()
    try:
        api = _ragas_api()
        SingleTurnSample = api[0]
        item.status = "RUNNING"
        db.session.commit()
        sample = SingleTurnSample(user_input=question, response=answer)
        score = asyncio.run(_make_metric(api).single_turn_ascore(sample))
        score = float(score)
        if not math.isfinite(score):
            raise ValueError("RAGAS returned a non-finite answer-relevancy score.")
        item.answer_relevance = score
        item.status = "COMPLETED"
    except Exception as exc:
        item.status = "FAILED"
        item.error_message = str(exc).replace("\n", " ")[:500]
    finally:
        item.duration_ms = round((time.perf_counter() - started) * 1000, 3)
        item.evaluated_at = datetime.utcnow()
        db.session.commit()
        export_evaluation(trace, item)
    return item

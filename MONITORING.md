# RAG Monitoring

The admin-only monitoring screen is available at `/admin/monitoring`. It records a durable trace for each `/chat/ask` execution without changing the chat response format or the LangGraph workflow.

## Configuration

All settings are optional. Safe defaults keep content capture disabled.

```env
PHOENIX_ENABLED=false
PHOENIX_ENDPOINT=http://localhost:6006
PHOENIX_PROJECT_NAME=local-rag
PHOENIX_CAPTURE_CONTENT=false
PHOENIX_CAPTURE_RETRIEVED_CONTEXT=false
PHOENIX_CAPTURE_PROMPTS=false
MONITORING_STORE_CONTENT=false
MONITORING_STORE_CONTEXT=false
MONITORING_STORE_PROMPTS=false
MONITORING_STORE_RETRIEVED_CHUNKS=false
MONITORING_STORE_GENERATED_ANSWERS=false
MONITORING_STORE_CITATIONS=false
RAGAS_AUTO_EVALUATION_ENABLED=false
RAG_GROUNDEDNESS_THRESHOLD=0.7
OLLAMA_INPUT_COST_PER_1K_TOKENS=0
OLLAMA_OUTPUT_COST_PER_1K_TOKENS=0
```

To export to Arize Phoenix, install Phoenix and its OpenTelemetry integration in the active virtual environment, start Phoenix at the configured endpoint, then set `PHOENIX_ENABLED=true`. Phoenix export is best-effort: connection or export failures are logged and never fail a chat request.

## Data and privacy

`rag_traces` stores trace metadata, timings, result status, citations, and optional content. Full questions/answers require `MONITORING_STORE_CONTENT`; retrieved chunks/context require `MONITORING_STORE_CONTEXT`; prompts require `MONITORING_STORE_PROMPTS`. The equivalent `PHOENIX_CAPTURE_*` settings remain backward-compatible defaults. Do not enable these values where the stored data would violate your local privacy policy.

Local retention and Phoenix export are separate. `MONITORING_STORE_*` controls the SQLite trace record used by the admin trace-detail page. `PHOENIX_CAPTURE_*` controls Phoenix content export only. In this local development workspace, the active `.env` enables the local retention settings so administrators can inspect complete future traces while Phoenix remains optional.

The trace-detail API represents each retained content field as `{ "available": true, "value": ..., "reason": null }`. Missing fields distinguish `disabled_by_configuration`, `not_collected` (the request ended before the stage), and `missing_from_trace` (for example, a trace created before retention was enabled). Existing redacted traces cannot be restored after enabling retention.

The trace captures the request, query classification, optional rewrite, retrieval, context build, prompt build, generation, citation construction, and persistence timings. Token counts are stored only when the installed Ollama integration reports them. Costs are configured estimates, not local-inference bills.

## Evaluation

The UI distinguishes evaluated and unevaluated traces. RAGAS 0.4.3 is installed, but its modern faithfulness metric requires an instructor-compatible evaluator. The existing local `ChatOllama` integration is not that adapter, so automatic RAGAS evaluation remains disabled rather than emitting fabricated scores. `rag_evaluations` is available for a compatible local/offline evaluator to persist faithfulness, relevance, context precision/recall, and correctness results.

## Manual answer relevancy

RAGAS 0.4.3 exposes the legacy-compatible `AnswerRelevancy` metric (`answer_relevancy`). The admin trace page can run it manually with the local `ChatOllama` evaluator and local `OllamaEmbeddings`; it evaluates the exact stored `original_query` and `answer_text` for that trace. It does not use the rewritten retrieval query as the question.

RAGAS 0.4.3 uses `SingleTurnSample(user_input=<original question>, response=<generated answer>)` and `single_turn_ascore`. The application probes that installed API at evaluation time and records a safe `FAILED` result if it cannot be imported or is incompatible; this never affects chat. The current local environment has a RAGAS/langchain-community compatibility problem (`langchain_community.chat_models.vertexai` is absent), so live evaluation requires correcting that installed dependency before enabling RAGAS. No cloud model is used.

Enable it with `RAGAS_ENABLED=true`, `RAGAS_ANSWER_RELEVANCY_ENABLED=true`, `RAGAS_EVALUATOR_MODEL=qwen3:1.7b`, and `RAGAS_EVALUATION_MODE=manual`. A result is persisted in `rag_evaluations` with its trace, conversation, message, user, evaluator model, RAGAS version, duration, and status. The score ranges from 0 to 1; values at or above `.80` are shown as high relevance and below `.60` as low relevance by the configured application thresholds. It measures whether the answer addresses the question, not factual correctness or grounding.

Manual evaluation requires both `MONITORING_STORE_CONTENT=true` and `MONITORING_STORE_GENERATED_ANSWERS=true` for new traces; otherwise the result is `MISSING_INPUT`. Each trace has one current `answer_relevancy` record, which preserves the exact original question, final retrieval query, and generated answer used in the run. The admin-only `GET /admin/monitoring/api/evaluations/answer-relevancy` endpoint supports `trace_id`, `conversation_id`, `user_id`, `evaluator_model`, `status`, `date_from`, `date_to`, `page`, and `per_page`; `POST /admin/monitoring/api/traces/<trace_id>/evaluations/answer-relevancy` runs it. The dashboard shows average, completed/pending/failed/unevaluated counts, low scores, and a time trend. Phoenix export is best-effort and does not affect SQLite persistence.

## Verification

Run the focused checks with:

```powershell
python -m compileall app
python -m pytest test\test_monitoring.py -q
```

The monitoring APIs require the existing `admin_required` decorator; normal users receive HTTP 403.

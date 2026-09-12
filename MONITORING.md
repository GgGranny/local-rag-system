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

## Verification

Run the focused checks with:

```powershell
python -m compileall app
python -m pytest test\test_monitoring.py -q
```

The monitoring APIs require the existing `admin_required` decorator; normal users receive HTTP 403.

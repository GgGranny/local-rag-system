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
RAGAS_AUTO_EVALUATION_ENABLED=false
RAG_GROUNDEDNESS_THRESHOLD=0.7
OLLAMA_INPUT_COST_PER_1K_TOKENS=0
OLLAMA_OUTPUT_COST_PER_1K_TOKENS=0
```

To export to Arize Phoenix, install Phoenix and its OpenTelemetry integration in the active virtual environment, start Phoenix at the configured endpoint, then set `PHOENIX_ENABLED=true`. Phoenix export is best-effort: connection or export failures are logged and never fail a chat request.

## Data and privacy

`rag_traces` stores trace metadata, timings, result status, citations, and optional content. Full questions/answers require `PHOENIX_CAPTURE_CONTENT`; retrieved chunks/context require `PHOENIX_CAPTURE_RETRIEVED_CONTEXT`; prompts require `PHOENIX_CAPTURE_PROMPTS`. Do not enable these values where the stored data would violate your local privacy policy.

The trace captures the request, query classification, optional rewrite, retrieval, context build, prompt build, generation, citation construction, and persistence timings. Token counts are stored only when the installed Ollama integration reports them. Costs are configured estimates, not local-inference bills.

## Evaluation

The UI distinguishes evaluated and unevaluated traces. This repository currently contains no RAGAS runner or compatible RAGAS dependency, so automatic RAGAS evaluation remains disabled and no heuristic is presented as a RAGAS score. `rag_evaluations` is available for a compatible offline/manual evaluator to persist faithfulness, relevance, context precision/recall, and correctness results.

## Verification

Run the focused checks with:

```powershell
python -m compileall app
python -m pytest test\test_monitoring.py -q
```

The monitoring APIs require the existing `admin_required` decorator; normal users receive HTTP 403.

from langchain_ollama import ChatOllama
from app.config import Config
from app.monitoring.service import record


_llm = None


def get_llm():
    """
    Return the shared local Ollama chat model.
    """
    global _llm
    if _llm is None:
        print(
            "[LLM] Loading Ollama model: "
            f"{Config.OLLAMA_CHAT_MODEL}"
        )
        _llm = ChatOllama(
            model=Config.OLLAMA_CHAT_MODEL,
            temperature=0.3,
            client_kwargs={
                "timeout": Config.OLLAMA_REQUEST_TIMEOUT,
            },
        )
    return _llm


def generate_answer(
    prompt: str
) -> str:
    """
    Generate a response from the local Ollama model.
    """
    if not prompt or not prompt.strip():
        raise ValueError(
            "Prompt cannot be empty."
        )
    llm = get_llm()
    response = llm.invoke(prompt)
    metadata = getattr(response, "response_metadata", {}) or {}
    usage = metadata.get("usage") or metadata.get("usage_metadata") or {}
    record(
        prompt=prompt,
        prompt_tokens=usage.get("prompt_tokens") or usage.get("input_tokens"),
        completion_tokens=usage.get("completion_tokens") or usage.get("output_tokens"),
        token_estimated=False,
    )
    return response.content

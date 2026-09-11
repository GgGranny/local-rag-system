from langchain_ollama import ChatOllama
from app.config import Config


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
    response = llm.invoke(
        prompt
    )
    return response.content
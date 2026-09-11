from app.chat.graph import build_graph


graph = build_graph()


config = {
    "configurable": {
        "thread_id": "test-conversation-1"
    }
}


result = graph.invoke(
    {
        "question": "What is this document about?"
    },
    config=config
)


print("\n========== RESULT ==========\n")

print(result)


print("\n========== STANDALONE QUESTION ==========\n")

print(
    result.get(
        "standalone_question"
    )
)
from app.chat.llm import generate_answer



context = """
Python is a high-level programming language
known for its simple syntax and readability.

Python is commonly used for web development,
data science, automation, artificial intelligence,
and machine learning.
"""


question = """
What is Python commonly used for?
"""


prompt = f"""
You are a helpful document question-answering assistant.

Answer the user's question using ONLY the provided context.

If the answer cannot be found in the context,
say that the information is not available
in the provided documents.

Do not invent facts.

Context:
--------------------
{context}
--------------------

Question:
{question}

Answer:
"""


answer = generate_answer(
    prompt
)

print("\n========== ANSWER ==========\n")

print(answer)
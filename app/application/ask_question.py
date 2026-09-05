from app.domain.interfaces import LLM, VectorStore
from app.embeddings import embed
from app.models import QuestionLog

from app.pricing import estimate_cost
from app.logging_config import logger

class AskQuestionUseCase:
    def __init__(self, llm: LLM, vector_store: VectorStore):
        self.llm = llm
        self.vector_store = vector_store

    def execute(self, question: str, db, user_id: int) -> dict:
        question_embedding = embed(question)
        chunks = self.vector_store.similarity_search(question_embedding, top_k=4)

        context = "\n\n".join(chunk["content"] for chunk in chunks)

        system_prompt = (
            "You are a medical knowledge assistant. Answer the user's question using ONLY the "
            "context provided below. If the context does not contain enough information to answer "
            "the question, say clearly: 'I don't have enough information to answer this.' "
            "Do not use any outside knowledge.\n\n"
            f"Context:\n{context}"
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": question},
        ]

        response = self.llm.generate(messages)

        question_log = QuestionLog(user_id=user_id, question=question, answer=response.content)
        db.add(question_log)
        db.commit()

        sources = [
            {"title": chunk["document_title"], "source": chunk["document_source"]}
            for chunk in chunks
        ]
        
        cost = estimate_cost(response.prompt_tokens, response.completion_tokens)
        logger.info(
            "llm call completed",
            extra={"context": {
                "use_case": "ask_question",
                "prompt_tokens": response.prompt_tokens,
                "completion_tokens": response.completion_tokens,
                "estimated_cost_usd": cost,
            }},
        )

        return {
            "answer": response.content,
            "sources": sources,
            "retrieved_chunks": chunks,
            "prompt_tokens": response.prompt_tokens,
            "completion_tokens": response.completion_tokens,
        }
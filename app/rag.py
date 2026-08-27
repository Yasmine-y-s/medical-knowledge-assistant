import os
from sqlalchemy.orm import Session
from openai import OpenAI
from app.embeddings import embed
from app.models import Chunk

client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])


def answer_question(question: str, db: Session) -> dict:
    question_embedding = embed(question)

    top_chunks = (
        db.query(Chunk)
        .order_by(Chunk.embedding.cosine_distance(question_embedding))
        .limit(4)
        .all()
    )

    context = "\n\n".join(chunk.content for chunk in top_chunks)

    system_prompt = (
        "You are a medical knowledge assistant. Answer the user's question using ONLY the "
        "context provided below. If the context does not contain enough information to answer "
        "the question, say clearly: 'I don't have enough information to answer this.' "
        "Do not use any outside knowledge.\n\n"
        f"Context:\n{context}"
    )

    completion = client.chat.completions.create(
        model="gpt-5-nano",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": question},
        ],
    )

    answer = completion.choices[0].message.content
    
    usage = completion.usage

    sources = [
        {
            "title": chunk.document.title,
            "source": chunk.document.source,
            "filename": chunk.document.filename
        }
        for chunk in top_chunks
    ]

    retrieved_chunks = [
        {
            "chunk_id": chunk.id,
            "document_id": chunk.document_id,
            "document_title": chunk.document.title,
            "document_source": chunk.document.source,
            "content": chunk.content,
        }
        for chunk in top_chunks
    ]

    return {
        "answer": answer,
        "sources": sources,
        "retrieved_chunks": retrieved_chunks,
        "prompt_tokens": usage.prompt_tokens,
        "completion_tokens": usage.completion_tokens
    }
import os
from sqlalchemy.orm import Session
from openai import OpenAI
from app.embeddings import embed
from app.models import Chunk, QuestionLog
import json
from app.tools import TOOL_SCHEMAS, search_documents, get_document, search_previous_questions, calculate_score

client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])


def answer_question(question: str, db: Session, user_id: int) -> dict:
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
    
    question_log = QuestionLog(
    user_id=user_id,
    question=question,
    answer=answer
    )

    db.add(question_log)
    db.commit()
    
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
    
AVAILABLE_TOOLS = {
    "search_documents": lambda args, db, user_id: search_documents(args["query"], db),
    "get_document": lambda args, db, user_id: get_document(args["document_id"], db),
    "search_previous_questions": lambda args, db, user_id: search_previous_questions(args["keyword"], user_id, db),
    "calculate_score": lambda args, db, user_id: calculate_score(args["distances"]),
}


def answer_with_agent(question: str, db, user_id: int, max_iterations: int = 5) -> dict:
    messages = [
        {"role": "system", "content": "You are a medical knowledge assistant. You must ALWAYS call search_documents "
            "at least once before answering any question about medical conditions, symptoms, "
            "or treatments — even if you believe you already know the answer. Base your final "
            "answer ONLY on the content returned by your tools, never on your own general "
            "knowledge. If the retrieved content does not contain enough information, say "
            "clearly: 'I don't have enough information to answer this.' Other tools "
            "(search_previous_questions, get_document, calculate_score) are available to use "
            "as appropriate, in addition to search_documents."
        "Do not use any outside knowledge."},
        {"role": "user", "content": question},
    ]
    
    collected_sources = []

    for iteration in range(max_iterations):
        force_search = (iteration == 0)
        completion = client.chat.completions.create(
            model="gpt-5-nano",
            messages=messages,
            tools=TOOL_SCHEMAS,
            tool_choice=(
            {"type": "function", "function": {"name": "search_documents"}}
            if force_search
            else "auto"
        ),
        )

        message = completion.choices[0].message
        messages.append(message)

        if not message.tool_calls:
            question_log = QuestionLog(user_id=user_id, question=question, answer=message.content)
            db.add(question_log)
            db.commit()
            return {"answer": message.content, "sources": collected_sources, "iterations": iteration + 1}

        for tool_call in message.tool_calls:
            tool_name = tool_call.function.name
            
            print(f"[Iteration {iteration + 1}] Model called: {tool_name}({tool_call.function.arguments})")

            try:
                arguments = json.loads(tool_call.function.arguments)
            except json.JSONDecodeError:
                result = {"error": f"Could not parse arguments for {tool_name}"}
            else:
                tool_function = AVAILABLE_TOOLS.get(tool_name)
                if tool_function is None:
                    result = {"error": f"Unknown tool: {tool_name}"}
                else:
                    result = tool_function(arguments, db, user_id)
                    
                    if tool_name == "search_documents" and "chunks" in result:
                        for chunk in result["chunks"]:
                            collected_sources.append({
                                "title": chunk["document_title"],
                                "source": chunk["document_source"],
                            })

            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": json.dumps(result),
            })

    return {"answer": "I wasn't able to complete this within the allowed steps.", "iterations": max_iterations}
from sqlalchemy.orm import Session

from app.embeddings import embed
from app.models import DocumentDB, QuestionLog


def search_documents(query: str, vector_store) -> dict:
    if not isinstance(query, str) or not query.strip():
        return {"error": "search_documents requires a non-empty query string"}

    try:
        query_embedding = embed(query)
        chunks = vector_store.similarity_search(query_embedding, top_k=4)
        return {"chunks": chunks}
    except Exception as e: # noqa: BLE001 — tool functions must never raise; broad catch is intentional
        return {"error": f"search_documents failed: {e!s}"}
    
def get_document(document_id: int, db: Session) -> dict:
    try:
        document_id = int(document_id)
    except (ValueError, TypeError):
        return {"error": f"'{document_id}' is not a valid document id"}

    document = db.query(DocumentDB).filter(DocumentDB.id == document_id).first()

    if document is None:
        return {"error": f"No document found with id {document_id}"}

    return {
        "id": document.id,
        "title": document.title,
        "condition": document.condition,
        "source": document.source,
        "source_url": document.source_url,
    }
    
def search_previous_questions(keyword: str, user_id: int, db: Session) -> dict:
    if not isinstance(keyword, str) or not keyword.strip():
        return {"error": "search_previous_questions requires a non-empty keyword string"}

    try:
        matches = (
            db.query(QuestionLog)
            .filter(
                QuestionLog.user_id == user_id,
                QuestionLog.question.ilike(f"%{keyword}%"),
            )
            .all()
        )

        return {
            "matches": [
                {"question": m.question, "answer": m.answer, "asked_at": str(m.created_at)}
                for m in matches
            ]
        }

    except Exception as e: # noqa: BLE001 — tool functions must never raise; broad catch is intentional
        return {"error": f"search_previous_questions failed: {e!s}"}
    
def calculate_score(distances: list[float]) -> dict:
    try:
        if not distances:
            return {"error": "calculate_score requires at least one distance value"}

        distances = [float(d) for d in distances]
        avg_distance = sum(distances) / len(distances)
        confidence = max(0.0, min(1.0, 1 - avg_distance)) * 100

        return {"confidence_score": round(confidence, 1)}

    except (ValueError, TypeError) as e:
        return {"error": f"calculate_score received invalid input: {e!s}"}
    
TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "search_documents",
            "description": "Search the medical document corpus for chunks relevant to a topic or question. Use this when you need to find information to answer a medical question.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query or question to find relevant document chunks for.",
                    }
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_document",
            "description": "Fetch full metadata for one specific document by its id. Use this when you already know a document's id and need its title, source, or URL.",
            "parameters": {
                "type": "object",
                "properties": {
                    "document_id": {"type": "integer", "description": "The id of the document to fetch."}
                },
                "required": ["document_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_previous_questions",
            "description": "Search this user's past questions for ones containing a given keyword. "
            "Use this when the user asks whether they've asked something before, OR when "
            "the user's question references a prior exchange (e.g. 'you said earlier...', "
            "'what about...', 'but you mentioned...') without restating the original topic. "
            "In that case, extract the likely topic keyword from the user's phrasing yourself "
            "and search with that.",
            "parameters": {
                "type": "object",
                "properties": {
                    "keyword": {"type": "string", "description": "A keyword to search for in past questions."}
                },
                "required": ["keyword"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "calculate_score",
            "description": "Compute a 0-100 confidence score from a list of cosine distances returned by search_documents. Use this when the user asks how confident or reliable an answer is.",
            "parameters": {
                "type": "object",
                "properties": {
                    "distances": {
                        "type": "array",
                        "items": {"type": "number"},
                        "description": "The distance values from a prior search_documents call.",
                    }
                },
                "required": ["distances"],
            },
        },
    },
]
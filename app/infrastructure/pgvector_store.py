from sqlalchemy.orm import Session

from app.domain.interfaces import VectorStore
from app.models import Chunk


class PgVectorStore(VectorStore):
    def __init__(self, db: Session):
        self.db = db

    def similarity_search(self, embedding, top_k=4):
        results = (
            self.db.query(Chunk, Chunk.embedding.cosine_distance(embedding).label("distance"))
            .order_by("distance")
            .limit(top_k)
            .all()
        )

        return [
            {
                "chunk_id": chunk.id,
                "document_id": chunk.document_id,
                "document_title": chunk.document.title,
                "document_source": chunk.document.source,
                "content": chunk.content,
                "distance": float(distance),
            }
            for chunk, distance in results
        ]
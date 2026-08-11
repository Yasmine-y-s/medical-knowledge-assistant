from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from fastapi import Depends
from sqlalchemy.orm import Session
from app.database import get_db, engine, Base
from app.models import DocumentDB

app = FastAPI()

Base.metadata.create_all(bind=engine)

class DocumentCreate(BaseModel):
    title: str
    condition: str
    source: str
    source_url: str
    filename: str

class Document(DocumentCreate):
    id: int
    
class QuestionIn(BaseModel):
    question: str
    
class QuestionOut(BaseModel):
    answer: str
    sources: list[str] = []

@app.post("/documents", response_model=Document, status_code=201)
def create_document(payload: DocumentCreate, db: Session = Depends(get_db)):
    doc = DocumentDB(**payload.model_dump())
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return doc

@app.get("/documents", response_model=list[Document])
def list_documents(db: Session = Depends(get_db)):
    documents = db.query(DocumentDB).all()
    return documents

@app.get("/documents/{document_id}", response_model=Document)
def get_document(document_id: int, db: Session = Depends(get_db)):
    doc = db.query(DocumentDB).filter(DocumentDB.id == document_id).first()

    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found")

    return doc

@app.delete("/documents/{document_id}", status_code=204)
def delete_document(document_id: int, db: Session = Depends(get_db)):
    doc = db.query(DocumentDB).filter(DocumentDB.id == document_id).first()

    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found")

    db.delete(doc)
    db.commit()

@app.post("/questions", response_model=QuestionOut)
def ask_question(payload: QuestionIn):
    return QuestionOut(
        answer=f"RAG not implemented yet. You asked: '{payload.question}'",
        sources=[]
    )
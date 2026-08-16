from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from fastapi import Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import DocumentDB

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

app = FastAPI(
    title="Medical Knowledge Assistant",
    description="Evidence-backed Q&A over a small medical document corpus.",
    version="0.1.0",
)

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={"error": {"code": 422, "message": "Invalid request data", "details": exc.errors()}},
    )

@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"code": exc.status_code, "message": exc.detail}},
    )

@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"error": {"code": 500, "message": "Internal server error"}},
    )
class DocumentCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    condition: str = Field(pattern=r'^[a-z0-9-]+$')
    source: str = Field(min_length=1, max_length=100)
    source_url: str = Field(pattern=r'^https?://')
    filename: str = Field(pattern=r'^[\w\-]+\.pdf$')

class Document(DocumentCreate):
    id: int
    
class QuestionIn(BaseModel):
    question: str
    
class QuestionOut(BaseModel):
    answer: str
    sources: list[str] = []

@app.post("/documents", response_model=Document, status_code=201, tags=["Documents"],
          summary="Create a document", description="Registers a new document's metadata in the corpus.")
def create_document(payload: DocumentCreate, db: Session = Depends(get_db)):
    doc = DocumentDB(**payload.model_dump())
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return doc

@app.get("/documents", response_model=list[Document], tags=["Documents"],
         summary="List documents", description="Returns every document currently registered.")
def list_documents(db: Session = Depends(get_db)):
    documents = db.query(DocumentDB).all()
    return documents

@app.get("/documents/{document_id}", response_model=Document, tags=["Documents"],
         summary="Get a document", description="Fetches a single document by its id.")
def get_document(document_id: int, db: Session = Depends(get_db)):
    doc = db.query(DocumentDB).filter(DocumentDB.id == document_id).first()

    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found")

    return doc

@app.delete("/documents/{document_id}", status_code=204, tags=["Documents"],
            summary="Delete a document", description="Removes a document by its id.")
def delete_document(document_id: int, db: Session = Depends(get_db)):
    doc = db.query(DocumentDB).filter(DocumentDB.id == document_id).first()

    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found")

    db.delete(doc)
    db.commit()

@app.post("/questions", response_model=QuestionOut, tags=["Questions"],
          summary="Ask a question", description="Placeholder")
def ask_question(payload: QuestionIn):
    return QuestionOut(
        answer=f"RAG not implemented yet. You asked: '{payload.question}'",
        sources=[]
    )
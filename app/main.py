from fastapi import FastAPI, HTTPException

from fastapi import Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.domain.interfaces import LLM
from app.models import DocumentDB
from app.models import UserDB

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

import bcrypt

from datetime import datetime, timedelta, timezone
import jwt
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

import os
from dotenv import load_dotenv

from pgvector.sqlalchemy import Vector
from app.models import Chunk
from app.embeddings import embed

from openai import OpenAI

from app.rag import answer_question, answer_with_agent

from app.presentation.schemas import (
    DocumentCreate, Document, UserCreate, UserOut,
    LoginRequest, QuestionIn, SourceOut, QuestionOut,
)

from app.infrastructure.openai_llm import OpenAILLM
from app.infrastructure.pgvector_store import PgVectorStore
from app.application.ask_question import AskQuestionUseCase
from app.application.ask_agent import AskAgentUseCase

from sqlalchemy import text

import time
from app.logging_config import logger

import traceback

llm = OpenAILLM()

def get_llm() -> LLM:
    return llm

load_dotenv()
client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

app = FastAPI(
    title="Medical Knowledge Assistant",
    description="Evidence-backed Q&A over a small medical document corpus.",
    version="0.1.0",
)

@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    elapsed_ms = (time.perf_counter() - start) * 1000

    logger.info(
        "request completed",
        extra={"context": {
            "path": request.url.path,
            "method": request.method,
            "status_code": response.status_code,
            "latency_ms": round(elapsed_ms, 2),
        }},
    )
    return response

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
    logger.error(
        "unhandled exception",
        extra={"context": {
            "path": request.url.path,
            "method": request.method,
            "exception_type": type(exc).__name__,
            "exception_message": str(exc),
            "traceback": traceback.format_exc(),
        }},
    )
    return JSONResponse(
        status_code=500,
        content={"error": {"code": 500, "message": "Internal server error"}},
    )
    
def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))

@app.post("/register", response_model=UserOut, status_code=201, tags=["Auth"],
          summary="Register a new user", description="Creates a new user account with a hashed password.")
def register(payload: UserCreate, db: Session = Depends(get_db)):
    existing = db.query(UserDB).filter(UserDB.email == payload.email).first()
    if existing is not None:
        raise HTTPException(status_code=400, detail="Email already registered")

    user = UserDB(
        email=payload.email,
        hashed_password=hash_password(payload.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user    

@app.post("/login", tags=["Auth"],
          summary="Log in", description="Verifies credentials.")
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(UserDB).filter(UserDB.email == payload.email).first()

    if user is None or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token = create_access_token(user.id)
    return {"access_token": token, "token_type": "bearer"}

load_dotenv()

SECRET_KEY = os.environ["SECRET_KEY"]
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]

def create_access_token(user_id: int) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {"sub": str(user_id), "exp": expire}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

security = HTTPBearer()
    
def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security), db: Session = Depends(get_db)) -> UserDB:
    token = credentials.credentials
    credentials_exception = HTTPException(
        status_code=401,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except jwt.PyJWTError:
        raise credentials_exception

    user = db.query(UserDB).filter(UserDB.id == int(user_id)).first()
    if user is None:
        raise credentials_exception
    return user

@app.post("/documents", response_model=Document, status_code=201, tags=["Documents"],
          summary="Create a document", description="Registers a new document's metadata in the corpus.")
def create_document(payload: DocumentCreate, db: Session = Depends(get_db), user: UserDB = Depends(get_current_user)):
    doc = DocumentDB(**payload.model_dump(), user_id=user.id)
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return doc

@app.get("/documents", response_model=list[Document], tags=["Documents"],
         summary="List documents", description="Returns every document currently registered.")
def list_documents(db: Session = Depends(get_db), user: UserDB = Depends(get_current_user)):
    documents = db.query(DocumentDB).all()
    return documents

@app.get("/documents/{document_id}", response_model=Document, tags=["Documents"],
         summary="Get a document", description="Fetches a single document by its id.")
def get_document(document_id: int, db: Session = Depends(get_db), user: UserDB = Depends(get_current_user)):
    doc = db.query(DocumentDB).filter(DocumentDB.id == document_id).first()

    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found")

    return doc

@app.delete("/documents/{document_id}", status_code=204, tags=["Documents"],
            summary="Delete a document", description="Removes a document by its id.")
def delete_document(document_id: int, db: Session = Depends(get_db), user: UserDB = Depends(get_current_user)):
    doc = db.query(DocumentDB).filter(DocumentDB.id == document_id, DocumentDB.user_id == user.id).first()

    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found")

    db.delete(doc)
    db.commit()
    
@app.post("/questions", response_model=QuestionOut, tags=["Questions"],
          summary="Ask a question", description="Answers a question using the document corpus via RAG.")
def ask_question(payload: QuestionIn, db: Session = Depends(get_db), user: UserDB = Depends(get_current_user), llm: LLM = Depends(get_llm)):
    vector_store = PgVectorStore(db)
    use_case = AskQuestionUseCase(llm=llm, vector_store=vector_store)
    result = use_case.execute(payload.question, db, user.id)

    return QuestionOut(
        answer=result["answer"],
        sources=[SourceOut(title=s["title"], source=s["source"]) for s in result["sources"]],
    )
    
@app.post("/agent-questions", response_model=QuestionOut, tags=["Questions"],
          summary="Ask a question using the AI agent", description="Answers a question using an LLM agent with tool access.")
def ask_agent_question(payload: QuestionIn, db: Session = Depends(get_db), user: UserDB = Depends(get_current_user), llm: LLM = Depends(get_llm)):
    vector_store = PgVectorStore(db)
    use_case = AskAgentUseCase(llm=llm, vector_store=vector_store)
    result = use_case.execute(payload.question, db, user.id)

    return QuestionOut(
        answer=result["answer"],
        sources=[SourceOut(title=s["title"], source=s["source"]) for s in result["sources"]],
    )

@app.get("/health", tags=["meta"])
def health(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
        return {"status": "ok"}
    except Exception:
        return JSONResponse(status_code=503, content={"status": "unhealthy", "detail": "database unreachable"})
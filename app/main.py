from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from fastapi import Depends
from sqlalchemy.orm import Session
from app.database import get_db
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
class UserCreate(BaseModel):
    email: str = Field(pattern=r'^[^@\s]+@[^@\s]+\.[^@\s]+$')
    password: str = Field(min_length=8)

class UserOut(BaseModel):
    id: int
    email: str
    created_at: datetime
    
class QuestionIn(BaseModel):
    question: str
    
class QuestionOut(BaseModel):
    answer: str
    sources: list[str] = []
    
class LoginRequest(BaseModel):
    email: str
    password: str
    
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
          summary="Ask a question", description="Placeholder")
def ask_question(payload: QuestionIn):
    return QuestionOut(
        answer=f"RAG not implemented yet. You asked: '{payload.question}'",
        sources=[]
    )
    



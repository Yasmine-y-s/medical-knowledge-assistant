from pydantic import BaseModel, Field
from datetime import datetime

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
    question: str = Field(min_length=1)
    
class SourceOut(BaseModel):
    title: str
    source: str
    
class QuestionOut(BaseModel):
    answer: str
    sources: list[SourceOut] = []
    
class LoginRequest(BaseModel):
    email: str
    password: str
from sqlalchemy import Column, Integer, String
from app.database import Base

class DocumentDB(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True)
    title = Column(String, nullable=False)
    condition = Column(String, nullable=False)
    source = Column(String, nullable=False)
    source_url = Column(String, nullable=False)
    filename = Column(String, nullable=False)
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.main import app
from app.database import Base, get_db
from app.main import get_current_user
from app.models import UserDB

TEST_DATABASE_URL = "postgresql+psycopg2://mka:mka@localhost:5432/medical_knowledge_assistant_test"

engine = create_engine(TEST_DATABASE_URL)
TestingSessionLocal = sessionmaker(bind=engine)

@pytest.fixture(autouse=True)
def setup_database():
    Base.metadata.create_all(bind=engine)

    db = TestingSessionLocal()
    test_user = UserDB(email="test@example.com", hashed_password="fake")
    db.add(test_user)
    db.commit()
    db.refresh(test_user)
    db.close()

    yield

    Base.metadata.drop_all(bind=engine)
    
def override_get_current_user():
    db = TestingSessionLocal()
    user = db.query(UserDB).filter(UserDB.email == "test@example.com").first()
    db.close()
    return user

app.dependency_overrides[get_current_user] = override_get_current_user

def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db



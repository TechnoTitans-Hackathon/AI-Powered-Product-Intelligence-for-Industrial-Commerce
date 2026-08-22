import os
import pytest

# Ensure this runs before ANY application code is imported
# Removed mock mode override for real tests

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient
from backend.core.db import Base, get_db
from backend.db.seeds.official_seeds import seed_official_knowledge
from backend.core.config import ensure_directories
from backend.main import app

TEST_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    ensure_directories()
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        seed_official_knowledge(db)
        from backend.knowledge.baseline_knowledge import initialize_baseline_knowledge
        initialize_baseline_knowledge(db)
    finally:
        db.close()
    yield
    Base.metadata.drop_all(bind=engine)

@pytest.fixture
def db_session():
    connection = engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)

    yield session

    session.close()
    transaction.rollback()
    connection.close()

@pytest.fixture
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()

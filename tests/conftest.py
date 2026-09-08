# tests/conftest.py
import sys
import os
import pytest
from typing import Generator
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from unittest.mock import MagicMock, patch

# Ensure project root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.main import app
from backend.db.base import Base
from backend.db.session import get_db
from backend.models.user import User
from backend.models.analysis import Analysis
from backend.models.audit import AuditLog
from backend.core.security import hash_password, create_access_token
from backend.core.concurrency import slot_manager

# Isolated SQLite in-memory database for fast, independent test execution
SQLITE_TEST_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLITE_TEST_URL,
    connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="session", autouse=True)
def setup_test_database():
    """Create all database tables on the isolated test engine."""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    """Provides a fresh, clean database session per test with automatic cleanup."""
    connection = engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)

    yield session

    session.close()
    if transaction.is_active:
        transaction.rollback()
    connection.close()


@pytest.fixture
def client(db_session: Session) -> Generator[TestClient, None, None]:
    """FastAPI TestClient with overridden get_db dependency pointing to isolated test DB."""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    slot_manager.reset()

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()
    slot_manager.reset()


@pytest.fixture
def test_user(db_session: Session) -> User:
    """Creates and returns a standard active test user."""
    user = User(
        email="test_user@mediscan.ai",
        full_name="Standard Test User",
        password_hash=hash_password("Password123!"),
        is_active=True,
        is_superuser=False
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def test_superuser(db_session: Session) -> User:
    """Creates and returns an active superuser."""
    superuser = User(
        email="admin_user@mediscan.ai",
        full_name="Admin Test User",
        password_hash=hash_password("Password123!"),
        is_active=True,
        is_superuser=True
    )
    db_session.add(superuser)
    db_session.commit()
    db_session.refresh(superuser)
    return superuser


@pytest.fixture
def auth_headers(test_user: User) -> dict:
    """Returns valid Authorization Bearer header for test_user."""
    token = create_access_token(test_user.id)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def superuser_headers(test_superuser: User) -> dict:
    """Returns valid Authorization Bearer header for test_superuser."""
    token = create_access_token(test_superuser.id)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def mock_pipeline_result() -> dict:
    """Synthetic clinical analysis result for instant testing."""
    return {
        "card": {
            "user_text": "Cough and mild fever",
            "ocr_text": "MUCOLEM 10mg",
            "llm_output": "Based on the provided information, the medicine is suitable.\n\n### Suggested Alternatives\n* Menthol Lozenges\n\n### ⚠️ Important Warning\nConsult a physician."
        },
        "meta": {
            "mismatch": None,
            "mismatch_details": "Mismatch check not performed."
        }
    }


@pytest.fixture
def mock_pipeline(mock_pipeline_result: dict):
    """Mocks backend.main.get_pipeline to return instant synthetic results."""
    mock_instance = MagicMock()
    mock_instance.run.return_value = mock_pipeline_result
    with patch("backend.main.get_pipeline", return_value=mock_instance) as p:
        yield mock_instance


@pytest.fixture
def mock_transcriber():
    """Mocks backend.main.get_transcriber to return instant synthetic audio transcripts."""
    mock_instance = MagicMock()
    mock_instance.transcribe_audio_file.return_value = "I have had a severe dry cough for three days."
    with patch("backend.main.get_transcriber", return_value=mock_instance) as t:
        yield mock_instance

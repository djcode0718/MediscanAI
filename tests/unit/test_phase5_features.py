# tests/unit/test_phase5_features.py
import pytest
from pydantic import ValidationError
from backend.core.config import Settings
from backend.core.middleware import CorrelationIdMiddleware, REQUEST_ID_REGEX


def test_production_cors_rejects_wildcard():
    """Verify that in production APP_ENV, wildcard '*' CORS origin raises ValidationError."""
    with pytest.raises(ValidationError) as exc_info:
        Settings(
            APP_ENV="production",
            JWT_SECRET_KEY="test-secret-key-12345",
            CORS_ORIGINS=["*"]
        )
    assert "CORS wildcard '*' is not permitted when APP_ENV is 'production'" in str(exc_info.value)


def test_production_cors_rejects_empty_origins():
    """Verify that in production APP_ENV, empty CORS_ORIGINS raises ValidationError."""
    with pytest.raises(ValidationError) as exc_info:
        Settings(
            APP_ENV="production",
            JWT_SECRET_KEY="test-secret-key-12345",
            CORS_ORIGINS=[]
        )
    assert "CORS_ORIGINS cannot be empty in production" in str(exc_info.value)


def test_production_cors_allows_explicit_origins():
    """Verify that in production APP_ENV, explicit valid origins are accepted."""
    s = Settings(
        APP_ENV="production",
        JWT_SECRET_KEY="test-secret-key-12345",
        CORS_ORIGINS=["https://app.mediscanai.com", "https://mediscanai.com"]
    )
    assert s.CORS_ORIGINS == ["https://app.mediscanai.com", "https://mediscanai.com"]


def test_development_cors_allows_wildcard():
    """Verify that in development APP_ENV, wildcard '*' is permitted for local convenience."""
    s = Settings(
        APP_ENV="development",
        JWT_SECRET_KEY="test-secret-key-12345",
        CORS_ORIGINS=["http://localhost:5173", "*"]
    )
    assert "*" in s.CORS_ORIGINS


def test_request_id_regex():
    """Verify regex acceptance and rejection of request ID formats."""
    assert REQUEST_ID_REGEX.match("req-12345-abc_DEF")
    assert REQUEST_ID_REGEX.match("a" * 64)
    assert not REQUEST_ID_REGEX.match("")
    assert not REQUEST_ID_REGEX.match("a" * 65)
    assert not REQUEST_ID_REGEX.match("req<script>")
    assert not REQUEST_ID_REGEX.match("req id with spaces")

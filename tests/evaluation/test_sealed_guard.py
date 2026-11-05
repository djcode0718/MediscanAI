"""
Tests for Sealed Dataset Access Guard (Phase 3 Part A).
"""

from pathlib import Path
import pytest
from evaluation.e2e.sealed_guard import (
    assert_sealed_authorized,
    SealedAccessForbiddenError,
    SEALED_DIR,
    AUTH_FILE,
)


def test_sealed_access_without_auth_file_raises_error():
    """Accessing sealed dataset without SEALED_AUTHORIZED raises SealedAccessForbiddenError."""
    # Ensure authorization file does not exist
    if AUTH_FILE.exists():
        AUTH_FILE.unlink()

    sealed_file = SEALED_DIR / "sealed_test_115.jsonl"
    with pytest.raises(SealedAccessForbiddenError, match="ACCESS DENIED"):
        assert_sealed_authorized(sealed_file)


def test_unsealed_path_allowed_without_auth_file():
    """Accessing dev or other data directories is never blocked."""
    dev_file = Path("evaluation/e2e/dataset/dev_subset_40.json")
    # Should not raise
    assert_sealed_authorized(dev_file)


def test_sealed_access_with_auth_file_succeeds(tmp_path):
    """When SEALED_AUTHORIZED exists, sealed access succeeds."""
    sealed_file = SEALED_DIR / "sealed_test_115.jsonl"
    try:
        AUTH_FILE.touch()
        # Should not raise
        assert_sealed_authorized(sealed_file)
    finally:
        if AUTH_FILE.exists():
            AUTH_FILE.unlink()

"""
MediScanAI Sealed Test Dataset Access Guard (Phase 3 Part A).

Strictly protects evaluation/e2e/data/sealed/ from accidental reads during dev/validation evaluations.
Any access to sealed datasets raises PermissionError unless SEALED_AUTHORIZED exists.
"""

from pathlib import Path
from typing import Union

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SEALED_DIR = REPO_ROOT / "evaluation/e2e/data/sealed"
AUTH_FILE = REPO_ROOT / "evaluation/e2e/data/SEALED_AUTHORIZED"


class SealedAccessForbiddenError(PermissionError):
    """Raised when an evaluation script attempts to read sealed test data without authorization."""
    pass


def assert_sealed_authorized(target_path: Union[str, Path]) -> None:
    """
    Verifies if target_path points to sealed data.
    If target_path is within SEALED_DIR, checks whether SEALED_AUTHORIZED exists.
    Raises SealedAccessForbiddenError if unauthorized.
    """
    p = Path(target_path).resolve()
    sealed_dir_resolved = SEALED_DIR.resolve()

    # Check if target_path is inside sealed directory
    try:
        p.relative_to(sealed_dir_resolved)
        is_sealed = True
    except ValueError:
        is_sealed = False

    if is_sealed:
        if not AUTH_FILE.exists():
            raise SealedAccessForbiddenError(
                f"ACCESS DENIED: Attempted to read sealed dataset '{p.name}' without explicit authorization. "
                f"Sealed test data cannot be accessed unless '{AUTH_FILE}' is present."
            )

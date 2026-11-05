"""
Test No Benchmark Leakage (Revision 2.4).
Verifies that no benchmark case IDs or hardcoded fictitious entity names from the dev or validation
cohorts leak into application runtime code (app/).

GOVERNANCE RESTRICTION NOTE:
In compliance with strict evaluator governance, evaluation/e2e/data/sealed/ is NEVER accessed.
Sealed data checks are recorded as NOT RUN due to sealed data governance restriction.
Only permitted dev and validation entity-name fields are verified.
"""

import os
import re
from pathlib import Path
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
APP_DIR = REPO_ROOT / "app"

# Fictitious entity names and case IDs from dev/validation benchmark sets
BENCHMARK_PROBE_ENTITIES = [
    "novaproxin",
    "valerionex",
    "glycozempra",
    "xanthroflurane",
    "zephyroflam",
    "corvastatine",
    "nonexistentdrug",
]


def test_no_benchmark_leakage_in_app():
    """
    Asserts that no benchmark probe entity names or case IDs appear in app/ runtime code.
    Fails if hardcoded fictitious names or case IDs appear in app/.
    """
    leaks = []

    # Compile regex for case IDs and probe entities
    case_id_pattern = re.compile(r"\bE2E-\d{3}\b")
    probe_pattern = re.compile(
        rf"\b({'|'.join(re.escape(e) for e in BENCHMARK_PROBE_ENTITIES)})\b",
        re.I,
    )

    for root, _, files in os.walk(APP_DIR):
        for f in files:
            if not f.endswith(".py"):
                continue
            fpath = Path(root) / f
            rel_path = fpath.relative_to(REPO_ROOT)
            with open(fpath, "r", encoding="utf-8") as fh:
                for line_no, line in enumerate(fh, 1):
                    # Check for benchmark probe names
                    probe_match = probe_pattern.search(line)
                    if probe_match:
                        leaks.append(
                            f"{rel_path}:{line_no} leaked benchmark entity '{probe_match.group(0)}': {line.strip()}"
                        )
                    # Check for case IDs
                    case_match = case_id_pattern.search(line)
                    if case_match:
                        leaks.append(
                            f"{rel_path}:{line_no} leaked benchmark case ID '{case_match.group(0)}': {line.strip()}"
                        )

    assert len(leaks) == 0, (
        f"Benchmark leakage detected in app/ source code ({len(leaks)} instances):\n"
        + "\n".join(f"  - {leak}" for leak in leaks)
        + "\n\n(Note: Sealed data check was NOT RUN in accordance with sealed data governance restriction.)"
    )

"""
MediScanAI Run Manifest Generator (Phase 2).

Produces manifest.json at run start and finalizes it at run end for evaluation runs.
Ensures every run is auditable, reproducible, and verifiable.
"""

import hashlib
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from evaluation.e2e.cache_v2 import get_installed_package_versions

REPO_ROOT = Path(__file__).resolve().parent.parent.parent


def compute_file_sha256(file_path: Path) -> str:
    """Compute SHA256 of a file if it exists."""
    p = Path(file_path)
    if not p.is_file():
        return "missing"
    h = hashlib.sha256()
    with open(p, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def get_git_state() -> Dict[str, Any]:
    """Inspect current git commit SHA, dirty flag, and diff hash."""
    sha = "unknown"
    dirty = False
    diff_hash = "clean"

    try:
        res = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=5,
        )
        if res.returncode == 0:
            sha = res.stdout.strip()
    except Exception:
        pass

    try:
        res_status = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=5,
        )
        if res_status.returncode == 0 and res_status.stdout.strip():
            dirty = True
            res_diff = subprocess.run(
                ["git", "diff", "HEAD"],
                cwd=REPO_ROOT,
                capture_output=True,
                timeout=10,
            )
            diff_bytes = res_diff.stdout if res_diff.returncode == 0 else b""
            diff_hash = hashlib.sha256(diff_bytes).hexdigest()
    except Exception:
        pass

    return {
        "commit_sha": sha,
        "dirty": dirty,
        "diff_hash": diff_hash,
    }


class RunManifest:
    """Manages creation, incremental updates, and finalization of manifest.json."""

    def __init__(
        self,
        run_dir: Path,
        candidate_id: str,
        run_id: Optional[str] = None,
        dataset_path: Optional[Path] = None,
        input_answers_path: Optional[Path] = None,
        judge_config: Optional[Dict[str, Any]] = None,
        probe_result_path: Optional[Path] = None,
        cache_mode: str = "default",  # default, no_cache, refresh_cache
    ):
        self.run_dir = Path(run_dir)
        self.run_dir.mkdir(parents=True, exist_ok=True)
        self.candidate_id = candidate_id
        self.run_id = run_id or f"{candidate_id}_{int(time.time())}"
        self.dataset_path = Path(dataset_path) if dataset_path else None
        self.input_answers_path = Path(input_answers_path) if input_answers_path else None
        self.judge_config = judge_config or {}
        self.probe_result_path = str(probe_result_path.relative_to(REPO_ROOT)) if probe_result_path and probe_result_path.exists() else str(probe_result_path) if probe_result_path else None
        self.cache_mode = cache_mode

        self.start_iso = datetime.now(timezone.utc).isoformat()
        self.start_time_monotonic = time.monotonic()

        self.cache_stats = {"hits": 0, "misses": 0, "bypassed": 0}
        self.status_counts: Dict[str, int] = {}
        self.git_state = get_git_state()
        self.packages = get_installed_package_versions()

        # Count dataset cases if dataset exists
        self.dataset_case_count = 0
        if self.dataset_path and self.dataset_path.exists():
            try:
                with open(self.dataset_path, "r", encoding="utf-8") as f:
                    self.dataset_case_count = sum(1 for line in f if line.strip())
            except Exception:
                pass

        self._write_initial()

    def record_cache_event(self, event_type: str) -> None:
        """event_type: hit/hits, miss/misses, bypassed"""
        key = event_type.lower().strip()
        if key == "hit":
            key = "hits"
        elif key == "miss":
            key = "misses"
        if key in self.cache_stats:
            self.cache_stats[key] += 1

    def record_case_status(self, status: str) -> None:
        self.status_counts[status] = self.status_counts.get(status, 0) + 1

    def set_status_counts(self, counts: Dict[str, int]) -> None:
        self.status_counts = dict(counts)

    def _build_manifest_dict(self, finalized: bool = False) -> Dict[str, Any]:
        end_iso = datetime.now(timezone.utc).isoformat() if finalized else None
        duration = round(time.monotonic() - self.start_time_monotonic, 2)

        output_files = {}
        if finalized:
            for p in self.run_dir.iterdir():
                if p.is_file() and p.name != "manifest.json":
                    output_files[p.name] = compute_file_sha256(p)

        return {
            "run_id": self.run_id,
            "candidate_id": self.candidate_id,
            "finalized": finalized,
            "git": self.git_state,
            "command_line": " ".join(sys.argv),
            "package_versions": self.packages,
            "judge_config": self.judge_config,
            "probe_result_path": self.probe_result_path,
            "dataset": {
                "path": str(self.dataset_path) if self.dataset_path else None,
                "sha256": compute_file_sha256(self.dataset_path) if self.dataset_path else None,
                "case_count": self.dataset_case_count,
            },
            "input_answers_file": {
                "path": str(self.input_answers_path) if self.input_answers_path else None,
                "sha256": compute_file_sha256(self.input_answers_path) if self.input_answers_path else None,
            },
            "cache_mode": self.cache_mode,
            "cache_stats": self.cache_stats,
            "status_counts": self.status_counts,
            "timestamps": {
                "start_time": self.start_iso,
                "end_time": end_iso,
                "duration_seconds": duration,
            },
            "output_files": output_files,
        }

    def _write_initial(self) -> None:
        data = self._build_manifest_dict(finalized=False)
        manifest_path = self.run_dir / "manifest.json"
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def finalize(self) -> Path:
        data = self._build_manifest_dict(finalized=True)
        manifest_path = self.run_dir / "manifest.json"
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return manifest_path

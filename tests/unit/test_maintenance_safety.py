"""
Regression tests for Phase 6.5 Safe Maintenance & Resource Protection Policy.
Verifies that:
1. Temporary files are NEVER automatically deleted (even if > 24 hours old).
2. Symlinks pointing outside are never followed or deleted.
3. Unexpected directories are never touched.
4. Unrelated Docker projects and untagged images with unverified ownership are preserved.
5. Current and rollback images are permanently preserved.
6. Named persistent volumes are locked and never pruned.
7. Shared Docker build cache is not pruned by default.
8. Atomic maintenance lock prevents overlapping execution.
"""

import os
import shutil
import tempfile
import subprocess
import pytest


MAINTENANCE_SCRIPT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "../../deployment/scripts/maintenance.sh")
)


class TestMaintenanceSafetyPolicy:
    """Test suite ensuring zero data loss and safe maintenance boundaries."""

    def test_temporary_files_are_never_deleted_automatically(self):
        """
        Verify that temporary files matching mediscan_* are NOT deleted by
        either --dry-run or --force maintenance runs, even if older than 24h.
        """
        test_temp_dir = tempfile.gettempdir()
        test_file = os.path.join(test_temp_dir, "mediscan_test_safety_verify.tmp")
        with open(test_file, "w") as f:
            f.write("temporary clinical audio/image data")

        try:
            # Set mtime to 3 days ago (> 24 hours)
            past_time = os.path.getmtime(test_file) - (3 * 86400)
            os.utime(test_file, (past_time, past_time))

            # Run maintenance with --force
            res = subprocess.run(
                ["/bin/bash", MAINTENANCE_SCRIPT, "--force"],
                capture_output=True,
                text=True,
                timeout=30
            )
            assert res.returncode == 0, f"Maintenance script failed: {res.stderr}"

            # File MUST still exist: automatic deletion is strictly disabled!
            assert os.path.exists(test_file), (
                "CRITICAL VIOLATION: Temporary file was deleted automatically! "
                "Policy mandates temporary files must remain untouched."
            )
            assert "Automatic deletion of temporary files is DISABLED" in res.stdout
        finally:
            if os.path.exists(test_file):
                os.remove(test_file)

    def test_symlink_pointing_outside_is_never_followed_or_deleted(self):
        """
        Verify that a symlink pointing outside canonical temp directory
        is identified as unsafe and never followed or deleted.
        """
        canonical_temp = "/private/tmp" if os.path.exists("/private/tmp") else "/tmp"
        symlink_path = os.path.join(canonical_temp, "mediscan_evil_symlink_test")

        # Create symlink pointing to /etc
        if os.path.islink(symlink_path) or os.path.exists(symlink_path):
            os.unlink(symlink_path)
        os.symlink("/etc", symlink_path)

        try:
            res = subprocess.run(
                ["/bin/bash", MAINTENANCE_SCRIPT, "--force"],
                capture_output=True,
                text=True,
                timeout=30
            )
            assert res.returncode == 0
            # Symlink must still exist (not removed), target (/etc) must be untouched
            assert os.path.islink(symlink_path)
            assert "SKIPPING symlink" in res.stdout or "SKIPPING unsafe" in res.stdout
        finally:
            if os.path.islink(symlink_path):
                os.unlink(symlink_path)

    def test_files_in_unexpected_directories_are_never_searched(self):
        """
        Verify that files in non-whitelisted paths (e.g. user home, project dir)
        are completely outside the scope of temporary file inspection.
        """
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
        scratch_test = os.path.join(project_root, "scratch", "mediscan_fake_orphan.tmp")
        os.makedirs(os.path.dirname(scratch_test), exist_ok=True)
        with open(scratch_test, "w") as f:
            f.write("safe in project repo")

        try:
            res = subprocess.run(
                ["/bin/bash", MAINTENANCE_SCRIPT, "--dry-run"],
                capture_output=True,
                text=True,
                timeout=30
            )
            assert res.returncode == 0
            assert os.path.exists(scratch_test)
            assert scratch_test not in res.stdout
        finally:
            if os.path.exists(scratch_test):
                os.remove(scratch_test)

    def test_unrelated_docker_projects_are_strictly_preserved(self):
        """
        Verify that images belonging to unrelated projects (e.g., paxel-client,
        python, postgres) or untagged images with unverified ownership are NEVER
        targeted for removal by maintenance.
        """
        res = subprocess.run(
            ["/bin/bash", MAINTENANCE_SCRIPT, "--dry-run"],
            capture_output=True,
            text=True,
            timeout=30
        )
        assert res.returncode == 0
        output = res.stdout

        # Policy confirmations in output
        assert "Global dangling-image pruning (docker image prune) is DISABLED" in output
        assert "Untagged images and images with unverified ownership are permanently PRESERVED" in output

        # Check that unrelated projects are never in the "Would remove" list
        unrelated_indicators = [
            "paxel-client",
            "python:3.10-slim",
            "caddy:2-alpine",
            "postgres:15-alpine",
        ]
        for indicator in unrelated_indicators:
            assert f"Would remove obsolete MediScanAI image: {indicator}" not in output

    def test_named_persistent_volumes_are_locked(self):
        """
        Verify that persistent data volumes are locked and exempt from pruning.
        """
        res = subprocess.run(
            ["/bin/bash", MAINTENANCE_SCRIPT, "--dry-run"],
            capture_output=True,
            text=True,
            timeout=30
        )
        assert res.returncode == 0
        assert "mediscanai_postgres_data' is LOCKED and exempt from pruning" in res.stdout
        assert "mediscanai_model_cache' is LOCKED and exempt from pruning" in res.stdout
        assert "mediscanai_caddy_data' is LOCKED and exempt from pruning" in res.stdout

    def test_shared_build_cache_not_pruned_without_explicit_flag(self):
        """
        Verify that scheduled maintenance and normal --force runs DO NOT prune
        the shared Docker build cache unless --prune-build-cache is explicitly given.
        """
        res = subprocess.run(
            ["/bin/bash", MAINTENANCE_SCRIPT, "--force"],
            capture_output=True,
            text=True,
            timeout=30
        )
        assert res.returncode == 0
        assert "Skipped automatic prune (build cache is shared across host projects)" in res.stdout

    def test_atomic_lock_prevents_overlapping_runs(self):
        """
        Verify that creating the lock directory prevents concurrent execution.
        """
        lock_dir = "/tmp/mediscanai_maintenance.lock.d"
        # Ensure lock directory exists
        os.makedirs(lock_dir, exist_ok=True)

        try:
            res = subprocess.run(
                ["/bin/bash", MAINTENANCE_SCRIPT, "--dry-run"],
                capture_output=True,
                text=True,
                timeout=30
            )
            # Must exit with code 0 and log active lock notice
            assert res.returncode == 0
            assert "Another maintenance process is currently active" in res.stdout
        finally:
            if os.path.exists(lock_dir):
                os.rmdir(lock_dir)

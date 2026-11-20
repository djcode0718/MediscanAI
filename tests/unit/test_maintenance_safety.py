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

    @staticmethod
    def _run_with_mock_docker(
        args=None,
        images=None,
        container_images=None,
        container_ids=None,
        ancestor_in_use=None,
        current_deploy=None,
        history_lines=None,
        env_extra=None,
    ):
        """
        Runs maintenance.sh in an isolated environment with a mocked Docker CLI.
        Returns: (subprocess.CompletedProcess, rmi_log_contents)
        """
        args = args if args is not None else ["--force"]
        temp_dir = tempfile.mkdtemp(prefix="mediscan_mock_docker_")
        bin_dir = os.path.join(temp_dir, "bin")
        os.makedirs(bin_dir, exist_ok=True)

        images_file = os.path.join(temp_dir, "images.txt")
        c_images_file = os.path.join(temp_dir, "container_images.txt")
        c_ids_file = os.path.join(temp_dir, "container_ids.txt")
        ancestor_file = os.path.join(temp_dir, "ancestor_in_use.txt")
        rmi_log = os.path.join(temp_dir, "rmi.log")

        with open(images_file, "w") as f:
            if images:
                for img in images:
                    f.write(f"{img[0]}\t{img[1]}\t{img[2]}\n")

        with open(c_images_file, "w") as f:
            if container_images:
                for ci in container_images:
                    f.write(f"{ci}\n")

        with open(c_ids_file, "w") as f:
            if container_ids:
                for cid in container_ids:
                    f.write(f"{cid}\n")

        with open(ancestor_file, "w") as f:
            if ancestor_in_use:
                for anc in ancestor_in_use:
                    f.write(f"{anc}\n")

        # Create isolated deployment directory
        deploy_dir = os.path.join(temp_dir, "deployment")
        scripts_dir = os.path.join(deploy_dir, "scripts")
        os.makedirs(scripts_dir, exist_ok=True)

        if current_deploy is not None:
            with open(os.path.join(deploy_dir, ".current_deployment"), "w") as f:
                f.write(current_deploy.strip() + "\n")
        if history_lines is not None:
            with open(os.path.join(deploy_dir, ".deployment_history"), "w") as f:
                f.write("\n".join(history_lines) + "\n")

        # Mock docker CLI script
        docker_script = os.path.join(bin_dir, "docker")
        with open(docker_script, "w") as f:
            f.write(f"""#!/usr/bin/env bash
cmd="$1"
shift || true
case "$cmd" in
    info)
        exit 0
        ;;
    images)
        if [ -f "{images_file}" ]; then
            cat "{images_file}"
        fi
        exit 0
        ;;
    ps)
        for arg in "$@"; do
            if [[ "$arg" == *"ancestor="* ]]; then
                anc="${{arg#*ancestor=}}"
                if [ -f "{ancestor_file}" ]; then
                    if grep -Fq "$anc" "{ancestor_file}"; then
                        echo "c_mock_in_use_123"
                    fi
                fi
                exit 0
            fi
            if [[ "$arg" == *"{{.Image}}"* ]]; then
                if [ -f "{c_images_file}" ]; then
                    cat "{c_images_file}"
                fi
                exit 0
            fi
            if [[ "$arg" == *"{{.ID}}"* ]]; then
                if [ -f "{c_ids_file}" ]; then
                    cat "{c_ids_file}"
                fi
                exit 0
            fi
        done
        exit 0
        ;;
    inspect)
        target="${{1:-}}"
        for arg in "$@"; do
            if [[ "$arg" == *"{{.Id}}"* ]]; then
                echo "sha256:mock_sha_${{target}}"
                exit 0
            elif [[ "$arg" == *"{{.Image}}"* ]]; then
                echo "sha256:mock_sha_${{target}}"
                exit 0
            fi
        done
        echo "{{}}"
        exit 0
        ;;
    rmi)
        echo "$*" >> "{rmi_log}"
        exit 0
        ;;
    builder)
        exit 0
        ;;
    *)
        exit 0
        ;;
esac
""")
        os.chmod(docker_script, 0o755)

        # Copy maintenance.sh to isolated scripts_dir
        isolated_script = os.path.join(scripts_dir, "maintenance.sh")
        shutil.copy(MAINTENANCE_SCRIPT, isolated_script)
        os.chmod(isolated_script, 0o755)

        env = os.environ.copy()
        env["PATH"] = f"{bin_dir}:{env.get('PATH', '')}"
        env["RETENTION_DAYS"] = "7"
        if env_extra:
            env.update(env_extra)

        try:
            res = subprocess.run(
                ["/bin/bash", isolated_script] + args,
                capture_output=True,
                text=True,
                env=env,
                timeout=25,
            )
            rmi_output = ""
            if os.path.exists(rmi_log):
                with open(rmi_log, "r") as f:
                    rmi_output = f.read()
            return res, rmi_output
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_exact_canonical_repository_accepted(self):
        """
        Verify that exact canonical repositories ('mediscanai-backend' and
        'ghcr.io/djcode0718/mediscanai-backend') are evaluated and obsolete versions
        can be pruned in force mode when not protected.
        """
        mock_images = [
            ("img_canon_local", "mediscanai-backend", "obsolete_local"),
            ("img_canon_ghcr", "ghcr.io/djcode0718/mediscanai-backend", "obsolete_ghcr"),
        ]
        res, rmi_log = self._run_with_mock_docker(
            args=["--force"],
            images=mock_images,
            current_deploy="mediscanai-backend:active_production",
        )
        assert res.returncode == 0
        # Both canonical obsolete images should be removed
        assert "Removed obsolete MediScanAI image: mediscanai-backend:obsolete_local (img_canon_local)" in res.stdout
        assert "Removed obsolete MediScanAI image: ghcr.io/djcode0718/mediscanai-backend:obsolete_ghcr (img_canon_ghcr)" in res.stdout
        assert "img_canon_local" in rmi_log
        assert "img_canon_ghcr" in rmi_log

    def test_repository_with_embedded_substring_rejected(self):
        """
        Verify that repositories with 'mediscanai-backend' embedded as a substring
        in a longer unrelated name are rejected and never removed.
        """
        mock_images = [
            ("img_embed_1", "my-mediscanai-backend-tool", "latest"),
            ("img_embed_2", "prefix/mediscanai-backend-runner", "v1"),
            ("img_embed_3", "internal/corp-mediscanai-backend-extra", "1.0"),
        ]
        res, rmi_log = self._run_with_mock_docker(
            args=["--force"],
            images=mock_images,
            current_deploy="mediscanai-backend:prod",
        )
        assert res.returncode == 0
        for img_id, repo, tag in mock_images:
            assert f"Skipped image (ownership unverified; non-canonical repository '{repo}')" in res.stdout
            assert img_id not in rmi_log

    def test_repository_with_similar_prefix_or_suffix_rejected(self):
        """
        Verify that repositories with similar prefix or suffix (e.g. not-mediscanai-backend,
        mediscanai-backend-service, mediscanai-backend-worker) are rejected as non-canonical.
        """
        mock_images = [
            ("img_pref", "not-mediscanai-backend", "v1.0"),
            ("img_suff_1", "mediscanai-backend-service", "2.0"),
            ("img_suff_2", "mediscanai-backend-worker", "prod"),
        ]
        res, rmi_log = self._run_with_mock_docker(
            args=["--force"],
            images=mock_images,
            current_deploy="mediscanai-backend:prod",
        )
        assert res.returncode == 0
        for img_id, repo, tag in mock_images:
            assert f"Skipped image (ownership unverified; non-canonical repository '{repo}')" in res.stdout
            assert img_id not in rmi_log

    def test_image_with_unknown_ownership_preserved(self):
        """
        Verify that images with unknown ownership (e.g., untagged <none>:<none> or
        unrelated projects like paxel-client) are strictly preserved.
        """
        mock_images = [
            ("img_dangling", "<none>", "<none>"),
            ("img_paxel", "ghcr.io/yc-software/paxel-client", "latest"),
            ("img_postgres", "postgres", "15-alpine"),
        ]
        res, rmi_log = self._run_with_mock_docker(
            args=["--force"],
            images=mock_images,
            current_deploy="mediscanai-backend:prod",
        )
        assert res.returncode == 0
        assert "Preserved image (untagged/dangling image preserved): img_dangling" in res.stdout
        assert "Skipped image (ownership unverified; non-canonical repository 'ghcr.io/yc-software/paxel-client')" in res.stdout
        assert "img_dangling" not in rmi_log
        assert "img_paxel" not in rmi_log
        assert "img_postgres" not in rmi_log

    def test_arbitrary_ownership_label_without_provenance_rejected(self):
        """
        Verify that an image from a non-canonical repository cannot claim ownership
        via an arbitrary or spoofed label without established build provenance.
        """
        mock_images = [
            ("img_spoofed", "untrusted-registry/fake-service", "latest"),
        ]
        res, rmi_log = self._run_with_mock_docker(
            args=["--force"],
            images=mock_images,
            current_deploy="mediscanai-backend:prod",
        )
        assert res.returncode == 0
        assert "Skipped image (ownership unverified; non-canonical repository 'untrusted-registry/fake-service')" in res.stdout
        assert "img_spoofed" not in rmi_log

    def test_current_deployment_image_preserved(self):
        """
        Verify that the currently deployed image (recorded in .current_deployment)
        is permanently protected and never deleted.
        """
        mock_images = [
            ("img_active", "mediscanai-backend", "production_active"),
        ]
        res, rmi_log = self._run_with_mock_docker(
            args=["--force"],
            images=mock_images,
            current_deploy="mediscanai-backend:production_active",
        )
        assert res.returncode == 0
        assert "Protected [CURRENT]: mediscanai-backend:production_active" in res.stdout
        assert "Retained protected/in-use MediScanAI image: mediscanai-backend:production_active (img_active)" in res.stdout
        assert "img_active" not in rmi_log

    def test_both_rollback_images_preserved(self):
        """
        Verify that both previous known-good rollback images recorded in
        .deployment_history are identified and preserved against deletion.
        """
        history = [
            "2026-11-18 10:00:00 | DEPLOY | mediscanai-backend:rollback_1 | prev: old",
            "2026-11-19 10:00:00 | DEPLOY | ghcr.io/djcode0718/mediscanai-backend:rollback_2 | prev: rollback_1",
            "2026-11-20 10:00:00 | DEPLOY | mediscanai-backend:current | prev: rollback_2",
        ]
        mock_images = [
            ("img_curr", "mediscanai-backend", "current"),
            ("img_rb1", "mediscanai-backend", "rollback_1"),
            ("img_rb2", "ghcr.io/djcode0718/mediscanai-backend", "rollback_2"),
        ]
        res, rmi_log = self._run_with_mock_docker(
            args=["--force"],
            images=mock_images,
            current_deploy="mediscanai-backend:current",
            history_lines=history,
        )
        assert res.returncode == 0
        assert "Protected [HISTORY]: ghcr.io/djcode0718/mediscanai-backend:rollback_2" in res.stdout
        assert "Protected [HISTORY]: mediscanai-backend:rollback_1" in res.stdout
        assert "img_rb1" not in rmi_log
        assert "img_rb2" not in rmi_log
        assert "img_curr" not in rmi_log

    def test_running_and_stopped_container_images_preserved(self):
        """
        Verify that images referenced by active or stopped containers are
        dynamically detected and protected against removal.
        """
        mock_images = [
            ("img_stopped_ctr", "mediscanai-backend", "in_stopped_container"),
            ("img_obsolete", "mediscanai-backend", "really_obsolete"),
        ]
        res, rmi_log = self._run_with_mock_docker(
            args=["--force"],
            images=mock_images,
            container_images=["mediscanai-backend:in_stopped_container"],
            container_ids=["ctr_stopped_99"],
            current_deploy="mediscanai-backend:active",
        )
        assert res.returncode == 0
        assert "Protected [ACTIVE/STOPPED CONTAINER]: mediscanai-backend:in_stopped_container" in res.stdout
        assert "Retained protected/in-use MediScanAI image: mediscanai-backend:in_stopped_container" in res.stdout
        # Container image must NOT be removed
        assert "img_stopped_ctr" not in rmi_log
        # Truly obsolete image without container or rollback should be removed
        assert "img_obsolete" in rmi_log

    def test_immediate_preremoval_recheck_prevents_deletion(self):
        """
        Verify that if an image has a container ancestor reference detected
        during the immediate pre-removal recheck, removal is aborted.
        """
        mock_images = [
            ("img_racing", "mediscanai-backend", "racing_candidate"),
        ]
        # Simulate container ancestor match
        res, rmi_log = self._run_with_mock_docker(
            args=["--force"],
            images=mock_images,
            ancestor_in_use=["sha256:mock_sha_img_racing", "mediscanai-backend:racing_candidate"],
            current_deploy="mediscanai-backend:active",
        )
        assert res.returncode == 0
        assert "Retained protected/in-use MediScanAI image: mediscanai-backend:racing_candidate" in res.stdout
        assert "img_racing" not in rmi_log

    def test_force_mode_cannot_bypass_ownership_or_container_guards(self):
        """
        Verify that --force execution mode DOES NOT bypass:
        - Exact canonical repository match
        - Protected deployment image
        - Rollback history images
        - Running/stopped container references
        - Locked volume safeguards
        - Temporary file deletion prohibition
        """
        history = [
            "2026-11-19 12:00:00 | DEPLOY | mediscanai-backend:rb_image | prev: none",
        ]
        mock_images = [
            ("img_unrelated", "not-mediscanai-backend", "fake"),
            ("img_curr", "mediscanai-backend", "current_active"),
            ("img_rb", "mediscanai-backend", "rb_image"),
            ("img_ctr", "mediscanai-backend", "in_use"),
        ]
        res, rmi_log = self._run_with_mock_docker(
            args=["--force"],
            images=mock_images,
            container_images=["mediscanai-backend:in_use"],
            current_deploy="mediscanai-backend:current_active",
            history_lines=history,
        )
        assert res.returncode == 0
        assert "Operating in FORCE execution mode" in res.stdout
        assert "Automatic deletion of temporary files is DISABLED" in res.stdout
        assert "mediscanai_postgres_data' is LOCKED and exempt from pruning" in res.stdout
        assert "img_unrelated" not in rmi_log
        assert "img_curr" not in rmi_log
        assert "img_rb" not in rmi_log
        assert "img_ctr" not in rmi_log

    def test_malformed_deployment_history_triggers_safe_lock(self):
        """
        Verify that a malformed or corrupt deployment history triggers the
        METADATA_AMBIGUOUS safety lock, causing ALL candidate images to be preserved.
        """
        corrupted_history = [
            "CORRUPTED_LINE_WITHOUT_PIPES_OR_FIELDS",
            "malformed | line",
        ]
        mock_images = [
            ("img_candidate_1", "mediscanai-backend", "candidate_1"),
            ("img_candidate_2", "mediscanai-backend", "candidate_2"),
        ]
        res, rmi_log = self._run_with_mock_docker(
            args=["--force"],
            images=mock_images,
            current_deploy="mediscanai-backend:active",
            history_lines=corrupted_history,
        )
        assert res.returncode == 0
        assert "WARNING: Deployment history is malformed or corrupt" in res.stdout
        assert "CRITICAL SAFETY LOCK: Deployment metadata is missing, malformed, or ambiguous" in res.stdout
        assert "Preserved image (metadata ambiguous lock active)" in res.stdout
        # Zero images removed when history is corrupt
        assert "img_candidate_1" not in rmi_log
        assert "img_candidate_2" not in rmi_log

    def test_scheduled_maintenance_follows_all_safety_restrictions(self):
        """
        Verify that routine scheduled maintenance (invoked without --force)
        adheres to exact ownership matching and leaves unverified images untouched.
        """
        mock_images = [
            ("img_other", "other-project/backend", "1.0"),
            ("img_canon", "mediscanai-backend", "candidate_routine"),
        ]
        res, rmi_log = self._run_with_mock_docker(
            args=["--dry-run"],
            images=mock_images,
            current_deploy="mediscanai-backend:active",
        )
        assert res.returncode == 0
        assert "Operating in DRY-RUN mode. No files or images will be deleted" in res.stdout
        assert "Skipped image (ownership unverified; non-canonical repository 'other-project/backend')" in res.stdout
        assert rmi_log == ""

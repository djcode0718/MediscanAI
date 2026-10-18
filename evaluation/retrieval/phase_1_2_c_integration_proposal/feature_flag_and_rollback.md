# MediScanAI Emergency Guardrail Feature Flag & Rollback Specification

**Document Version:** 1.0.0  
**Phase:** Phase 1.2.c — Integration Proposal & Readiness Design  
**Date:** 2026-10-17  
**Status:** Operational Design (Zero Production Code Changes)

---

## 1. Feature Flag Design & Default Governance

To ensure zero unintended operational disruption and enforce strict clinical change-management, the emergency guardrail must be controlled by an explicit configuration flag:

```ini
# Production Environment Variable (.env)
EMERGENCY_GUARDRAIL_ENABLED=false
```

### 1.1 Invariant Governance Rules
1. **Default State: `false` (Disabled)**
   - In any fresh deployment, staging instance, or production container, `EMERGENCY_GUARDRAIL_ENABLED` defaults strictly to `false` until formal clinical sign-off and deployment owner approval are recorded.
2. **Explicit Authorization Required:**
   - Setting `EMERGENCY_GUARDRAIL_ENABLED=true` requires verified compliance with all 11 Acceptance Gates defined in `acceptance_gates.json`.
3. **No Dynamic Client Toggling:**
   - The flag is an immutable server-side environment variable. Clients (mobile app, web UI) cannot override or disable the guardrail via headers or query parameters.

---

## 2. Configuration Schema & Startup Validation

To prevent an incomplete or malformed configuration from silently bypassing emergency safeguards, the system implements a strict two-tier validation lifecycle.

### 2.1 Configuration Schema Requirements
The configuration must satisfy the following JSON schema:
- `version`: Semantic version string (e.g., `"1.0.0"`).
- `emergency_hotlines`: Dictionary containing at least `"india"` (`"112"`) and `"us"` (`"911"`).
- `rules`: Non-empty list of rule objects, each containing:
  - `rule_id`: Non-empty unique string (e.g. `"RULE-01-CARDIOVASCULAR-CHEST-PAIN"`).
  - `category`: Valid clinical category string.
  - `severity`: `"CRITICAL_EMERGENCY"` or `"HIGH_PRIORITY"`.
  - `triggers`: Non-empty list of valid regex pattern strings.
- `negation_patterns`: List of valid regex strings.
- `historical_and_family_patterns`: List of valid regex strings.
- `contextual_exceptions`: List of valid regex strings.

### 2.2 Startup Validation (`backend/main.py:startup_event`)
When the application starts:
1. If `EMERGENCY_GUARDRAIL_ENABLED=true`:
   - The configuration file is read and parsed.
   - All regex patterns are compiled during startup. Any invalid regex syntax raises a fatal `GuardrailConfigurationError`.
   - If the configuration file is missing, corrupt, or contains empty rules:
     - In **STRICT PRODUCTION MODE**, the server **refuses to start** (exits with code 1) to prevent running without verified safety logic.
     - In **FAIL-SAFE COMPATIBILITY MODE**, the system logs an alert and initializes with embedded, hardcoded fail-safe rules.
2. If `EMERGENCY_GUARDRAIL_ENABLED=false`:
   - The application logs: `[STARTUP] Emergency Guardrail is DISABLED via feature flag.`
   - No guardrail middleware is attached; original pipeline execution is preserved.

---

## 3. Runtime Behavior Matrix

```
                      [Request Received]
                              │
             Is EMERGENCY_GUARDRAIL_ENABLED == true?
                     ├── NO ──► Execute Legacy Pipeline
                     │          (100% historical baseline behavior)
                     │
                     └── YES ──► Execute Two-Stage Guardrail Pipeline:
                                 ├── Pre-Gen Detection / Fast-Path
                                 ├── Hybrid Retrieval & Generation
                                 └── Post-Gen Deterministic Enforcement
```

### Telemetry and Audit Event Invariants
When enabled, every request logs a structured audit event to the PostgreSQL database:
```json
{
  "event_type": "EMERGENCY_GUARDRAIL_EVALUATED",
  "enabled": true,
  "is_emergency": false,
  "action_taken": "PASS_THROUGH",
  "rule_id": null,
  "latency_ms": 0.012,
  "analysis_id": 1042
}
```
If an emergency triggers:
```json
{
  "event_type": "EMERGENCY_GUARDRAIL_EVALUATED",
  "enabled": true,
  "is_emergency": true,
  "action_taken": "POST_GENERATION_OVERRIDE",
  "rule_id": "RULE-01-CARDIOVASCULAR-CHEST-PAIN",
  "category": "cardiovascular",
  "severity": "CRITICAL_EMERGENCY",
  "latency_ms": 0.018,
  "analysis_id": 1043
}
```

---

## 4. Rapid Rollback Procedure

If unexpected behavior, false-positive alarms, or performance regressions are observed in staging or production, the guardrail can be rolled back immediately without deploying code.

### 4.1 Zero-Downtime Rollback Steps
1. **Update Environment Variable:**
   ```bash
   # On production server or container environment
   export EMERGENCY_GUARDRAIL_ENABLED=false
   ```
   Or update `.env` and trigger a rolling restart:
   ```bash
   sed -i 's/EMERGENCY_GUARDRAIL_ENABLED=true/EMERGENCY_GUARDRAIL_ENABLED=false/g' .env
   ```
2. **Reload Application Workers:**
   ```bash
   # Reload Uvicorn/Gunicorn workers with zero dropped requests
   kill -HUP $(pgrep -f "uvicorn backend.main:app")
   ```
3. **Verify Disablement via Health Probe:**
   Query the readiness probe:
   ```bash
   curl -s http://localhost:8000/api/health | jq .guardrail_status
   # Expected Output: {"enabled": false, "status": "disabled_by_flag"}
   ```

### 4.2 Restored Behavior Verification
To verify that disabling the feature restores 100% of the historical pipeline behavior:
1. Run the smoke test query:
   ```bash
   pytest tests/test_pipeline.py -v
   ```
2. Confirm that `MED-BENCH-038` generates the original un-guarded baseline response from Phase 1.2.a.
3. Verify that response times and database persistence matches pre-integration baseline.

---

## 5. Prevention of Silent Guardrail Bypass

A critical safety risk in feature-flagged systems is the **silent bypass**: a flag is marked `true`, but due to an error, requests bypass the guardrail undetected.

To prevent silent bypass:
1. **Response Integrity Marker:** When `EMERGENCY_GUARDRAIL_ENABLED=true`, every API response includes an internal telemetry header:
   `X-Guardrail-Evaluated: true`
   If an integration test or smoke probe receives `X-Guardrail-Evaluated: false` while the flag is set to true, an immediate alert is triggered.
2. **Periodic Safety Health Check:** A background liveness probe periodically sends a synthetic negative-control query and an emergency query to the internal evaluation interface. If the emergency query is not escalated, the health probe reports `UNHEALTHY: GUARDRAIL_BYPASS_DETECTED`.

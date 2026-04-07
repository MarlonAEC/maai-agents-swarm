---
phase: 01-infrastructure-foundation
plan: 02
subsystem: infra
tags: [bootstrap, docker, gpu-detection, litellm, ollama, security, shell]

# Dependency graph
requires:
  - 01-01 (docker-compose.yml, client.env, models.yaml, proxy_config.yaml)
provides:
  - bootstrap.sh first-run script with GPU detection, CPU model downgrade, config generation, model pull
  - LiteLLM security gate blocking backdoored versions 1.82.7/1.82.8
  - WEBUI_SECRET_KEY auto-generation (replaces CHANGE_ME_RUN_BOOTSTRAP placeholder)
  - proxy_config.yaml regenerated on each run with active profile model tags
affects:
  - Operators: single-command first-run setup via ./bootstrap.sh
  - All services: stack starts correctly after bootstrap completes

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "GPU detection: nvidia-smi check with OLLAMA_GPU_ENABLED override"
    - "CPU fallback: auto-downgrade reasoning 14b->7b, classifier 4b->1b"
    - "Security gate pattern: hard exit on known-bad dependency versions"
    - "Heredoc config generation: proxy_config.yaml written with variable substitution"
    - "Ollama readiness poll: wget with 120s timeout before model pulls"

key-files:
  created:
    - bootstrap.sh
  modified: []

key-decisions:
  - "sed -i compatibility: detect GNU vs BSD sed via sed --version for cross-platform support (Linux/macOS/Git Bash)"
  - "LiteLLM version check is best-effort: 'unknown' version warns but does not block (docker run may fail in restricted envs)"
  - "OLLAMA_GPU_ENABLED=false takes priority over nvidia-smi detection — explicit operator override respected"
  - "Ollama start: try named service up first, fall back to full up if service name resolution fails (start_period differences)"

# Metrics
duration: 1min
completed: 2026-04-07
---

# Phase 01 Plan 02: Bootstrap Script Summary

**bootstrap.sh first-run script with GPU detection, CPU auto-downgrade to qwen3:7b/gemma3:1b, LiteLLM security gate blocking 1.82.7/1.82.8, and full stack startup**

## Performance

- **Duration:** ~1 min
- **Started:** 2026-04-07T18:18:12Z
- **Completed:** 2026-04-07T18:19:22Z
- **Tasks:** 2 (Task 1 complete; Task 2 = checkpoint awaiting human verification)
- **Files modified:** 1

## Status

**PAUSED AT CHECKPOINT** — Task 2 is a `checkpoint:human-verify` gate requiring the user to run `./bootstrap.sh` and confirm the full stack works end-to-end.

Pre-flight automated checks completed successfully before checkpoint:
- `bash -n bootstrap.sh` — syntax valid
- `docker-compose.yml` — exists
- `clients/default/client.env` — exists
- `clients/default/models.yaml` — exists
- `config/litellm/proxy_config.yaml` — exists

## Accomplishments

- bootstrap.sh (230 lines) covering all 10 steps: prerequisite validation, env sourcing, secret generation, GPU detection, CPU model downgrade, proxy_config.yaml generation, LiteLLM security check, Ollama readiness wait, model pull, full stack start
- Hard security gate exits 1 on LiteLLM 1.82.7 or 1.82.8 (March 2026 supply chain attack); semver check ensures >=1.83.0
- CPU profile automatically selects qwen3:7b (vs 14b) and gemma3:1b (vs 4b) without user intervention
- proxy_config.yaml regenerated on every run — model tags always match the active profile

## Task Commits

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Create bootstrap.sh first-run script | 2a54acf | bootstrap.sh |
| 2 | Verify full stack end-to-end | — | (checkpoint — awaiting human) |

## Files Created/Modified

- `bootstrap.sh` — Complete 230-line first-run script:
  - Step 1: Validates Docker Compose V2, client.env, models.yaml existence
  - Step 2: Sources client.env vars
  - Step 3: Generates WEBUI_SECRET_KEY via openssl if placeholder detected, writes back to client.env
  - Step 4: `detect_profile()` — checks OLLAMA_GPU_ENABLED=false first, then nvidia-smi
  - Step 5: CPU downgrade — qwen3:7b, gemma3:1b (embedding unchanged)
  - Step 6: Generates config/litellm/proxy_config.yaml via heredoc with live variable substitution
  - Step 7: Pulls LiteLLM image, checks version, hard blocks 1.82.7/1.82.8 and anything <1.83.0
  - Step 8: Starts Ollama with profile, polls http://localhost:11434/api/tags with 120s timeout
  - Step 9: `docker exec ollama ollama pull` for each of REASONING, CLASSIFIER, EMBEDDING models
  - Step 10: Starts full stack, prints access URLs

## Decisions Made

- Cross-platform sed compatibility: detect GNU sed via `sed --version` then branch between `sed -i` (GNU) and `sed -i ''` (BSD/macOS/Git Bash)
- LiteLLM version "unknown" result warns but does not block — handles restricted Docker environments where `docker run` may fail
- OLLAMA_GPU_ENABLED takes precedence over nvidia-smi detection — allows operators to force CPU profile on a GPU machine
- Semver comparison logic accounts for the full range: <1.82, 1.82.x (all patches), ensuring nothing below 1.83.0 passes

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing critical functionality] Cross-platform sed compatibility**
- **Found during:** Task 1 — the plan specified `sed -i` which is GNU-only and fails on macOS/Git Bash
- **Fix:** Detect sed variant via `sed --version` and branch to appropriate syntax
- **Files modified:** bootstrap.sh
- **Commit:** 2a54acf

## Known Stubs

None — bootstrap.sh is complete. The proxy_config.yaml is regenerated on each bootstrap run, so the static file from Plan 01 is superseded by the generated version.

## Checkpoint — Awaiting Human Verification

**Task 2 is a blocking checkpoint.** The following verification steps are ready for the user:

1. Run bootstrap: `./bootstrap.sh` (or `bash bootstrap.sh` on Windows Git Bash)
   - Expected: GPU detected, gpu profile selected, models pulled (several minutes for first pull), stack started
2. Check containers: `docker compose --profile gpu ps`
   - Expected: ollama, litellm, open-webui all "Up" and "healthy"
3. Open browser: http://localhost:3000
   - Expected: Open WebUI login/registration page loads
4. Create account in Open WebUI and send a test message
   - Expected: Response from Qwen3 14B via LiteLLM routing
5. Verify LiteLLM routing: `curl http://localhost:4000/v1/models`
   - Expected: JSON listing reasoning-model, classifier-model, embedding-model
6. Run structural tests: `pytest tests/phase1/ -v`
   - Expected: 14 structural tests pass; live tests can now be unskipped and run

**Resume signal:** Type "approved" if stack works end-to-end, or describe any issues encountered.

## Next Phase Readiness

- bootstrap.sh is complete and syntax-valid
- All Plan 01 config files confirmed present
- Pending: human verification that the stack starts and chat works end-to-end
- Upon approval: Phase 01 is complete, Phase 02 (agent worker) can proceed

---
*Phase: 01-infrastructure-foundation*
*Completed: 2026-04-07 (checkpoint pending)*

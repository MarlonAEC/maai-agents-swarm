---
phase: 1
slug: infrastructure-foundation
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-07
---

# Phase 1 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | `pytest.ini` — Wave 0 installs |
| **Quick run command** | `pytest tests/phase1/ -x -q` |
| **Full suite command** | `pytest tests/phase1/ -v` |
| **Estimated runtime** | ~30 seconds (requires running Docker stack) |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/phase1/ -x -q --co` (collect-only, verify test structure)
- **After every plan wave:** Run `pytest tests/phase1/ -v` (requires running stack)
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 1-01-01 | 01 | 1 | INFRA-01 | smoke | `pytest tests/phase1/test_stack_startup.py -x` | ❌ W0 | ⬜ pending |
| 1-02-01 | 01 | 1 | INFRA-02 | smoke/manual | `pytest tests/phase1/test_local_only.py -x` | ❌ W0 | ⬜ pending |
| 1-03-01 | 01 | 1 | INFRA-03 | integration | `pytest tests/phase1/test_client_config.py -x` | ❌ W0 | ⬜ pending |
| 1-04-01 | 01 | 1 | INFRA-04 | smoke | `pytest tests/phase1/test_gpu_active.py -x` | ❌ W0 | ⬜ pending |
| 1-05-01 | 01 | 1 | INFRA-05 | integration | `pytest tests/phase1/test_litellm_routing.py -x` | ❌ W0 | ⬜ pending |
| 1-06-01 | 01 | 1 | INFRA-06 | integration | `pytest tests/phase1/test_networking.py -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/__init__.py` — package marker
- [ ] `tests/phase1/__init__.py` — package marker
- [ ] `tests/phase1/test_stack_startup.py` — stubs for INFRA-01
- [ ] `tests/phase1/test_local_only.py` — stubs for INFRA-02
- [ ] `tests/phase1/test_client_config.py` — stubs for INFRA-03
- [ ] `tests/phase1/test_gpu_active.py` — stubs for INFRA-04
- [ ] `tests/phase1/test_litellm_routing.py` — stubs for INFRA-05
- [ ] `tests/phase1/test_networking.py` — stubs for INFRA-06
- [ ] `tests/conftest.py` — shared fixtures (stack health wait, httpx client)
- [ ] `pytest.ini` — test runner config
- [ ] Framework install: `uv pip install pytest httpx`

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| GPU shows in Ollama logs | INFRA-04 | Requires physical GPU hardware | Run `docker compose --profile gpu up`, check `docker logs ollama` for GPU device line |
| Browser UI accessible | INFRA-01 | Visual browser check | Open `http://localhost:3000` and verify chat interface loads |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending

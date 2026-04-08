---
phase: 02
slug: core-api-and-end-to-end-chat
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-07
---

# Phase 02 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x + pytest-asyncio |
| **Config file** | pytest.ini (exists) |
| **Quick run command** | `docker compose exec core-api python -m pytest tests/ -x -q` |
| **Full suite command** | `python -m pytest tests/phase2/ -v` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `docker compose exec core-api python -m pytest tests/ -x -q`
- **After every plan wave:** Run `python -m pytest tests/phase2/ -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 02-01-01 | 01 | 1 | CHAT-01 | integration | `pytest tests/phase2/test_chat_endpoint.py` | ❌ W0 | ⬜ pending |
| 02-01-02 | 01 | 1 | CHAT-04, CHAT-05 | integration | `pytest tests/phase2/test_freeform_agent.py` | ❌ W0 | ⬜ pending |
| 02-01-03 | 01 | 1 | AGNT-07 | unit | `pytest tests/phase2/test_embedder_config.py` | ❌ W0 | ⬜ pending |
| 02-01-04 | 01 | 1 | AGNT-08 | unit | `pytest tests/phase2/test_non_streaming.py` | ❌ W0 | ⬜ pending |
| 02-01-05 | 01 | 1 | AGNT-09 | unit | `pytest tests/phase2/test_guardrails.py` | ❌ W0 | ⬜ pending |
| 02-02-01 | 02 | 1 | CHAT-03 | integration | `pytest tests/phase2/test_file_upload.py` | ❌ W0 | ⬜ pending |
| 02-02-02 | 02 | 1 | CHAT-06 | integration | `pytest tests/phase2/test_multiturn.py` | ❌ W0 | ⬜ pending |
| 02-02-03 | 02 | 2 | CHAT-02 | manual | See manual verifications | N/A | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/phase2/__init__.py` — test package init
- [ ] `tests/phase2/conftest.py` — shared fixtures (httpx test client, mock LiteLLM)
- [ ] `tests/phase2/test_chat_endpoint.py` — stub for CHAT-01
- [ ] `tests/phase2/test_freeform_agent.py` — stub for CHAT-04, CHAT-05
- [ ] `tests/phase2/test_embedder_config.py` — stub for AGNT-07
- [ ] `tests/phase2/test_non_streaming.py` — stub for AGNT-08
- [ ] `tests/phase2/test_guardrails.py` — stub for AGNT-09
- [ ] `tests/phase2/test_file_upload.py` — stub for CHAT-03
- [ ] `tests/phase2/test_multiturn.py` — stub for CHAT-06
- [ ] `pytest-asyncio` — install for async endpoint tests
- [ ] `httpx` — install for FastAPI TestClient

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Chat history persists across browser sessions | CHAT-02 | Requires browser state and Open WebUI's SQLite persistence | 1. Send a message in Open WebUI. 2. Close browser tab. 3. Reopen Open WebUI. 4. Verify previous conversation is visible. |
| Pipeline status messages visible in UI | CHAT-01 | UI rendering check — status events must display as indicators | 1. Send a message. 2. Observe "Processing..." status in chat. 3. Verify status clears when response arrives. |
| File upload acknowledgment displays correctly | CHAT-03 | File upload UX flow through Open WebUI | 1. Upload a PDF in chat. 2. Verify "File received: {name}" message appears. |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending

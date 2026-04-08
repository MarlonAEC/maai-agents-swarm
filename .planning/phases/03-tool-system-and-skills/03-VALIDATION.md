---
phase: 3
slug: tool-system-and-skills
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-08
---

# Phase 3 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x with pytest-asyncio |
| **Config file** | `pyproject.toml` and `pytest.ini` |
| **Quick run command** | `python -m pytest tests/phase3/ -x -q` |
| **Full suite command** | `python -m pytest tests/ -q` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest tests/phase3/ -x -q`
- **After every plan wave:** Run `python -m pytest tests/ -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 03-01-01 | 01 | 1 | AGNT-04 | unit | `pytest tests/phase3/test_tool_registry.py -x` | W0 | pending |
| 03-01-02 | 01 | 1 | AGNT-05 | unit | `pytest tests/phase3/test_tool_registry.py -x` | W0 | pending |
| 03-02-01 | 02 | 2 | AGNT-01 | unit | `pytest tests/phase3/test_skill_registry.py -x` | W0 | pending |
| 03-02-02 | 02 | 2 | AGNT-02 | unit | `pytest tests/phase3/test_skill_registry.py -x` | W0 | pending |
| 03-03-01 | 03 | 2 | AGNT-03 | unit | `pytest tests/phase3/test_matcher.py -x` | W0 | pending |
| 03-03-02 | 03 | 2 | AGNT-03 | integration | `pytest tests/phase3/test_matcher.py -x` | W0 | pending |
| 03-04-01 | 04 | 3 | AGNT-06 | unit | `pytest tests/phase3/test_matcher.py tests/phase3/test_chat_router.py -x` | W0 | pending |
| 03-04-02 | 04 | 3 | AGNT-02 | integration | `pytest tests/phase3/test_chat_router.py -x` | W0 | pending |

*Status: pending / green / red / flaky*

**Note on AGNT-06 (autonomy control):** Autonomy tests are consolidated across two test files rather than a standalone `test_autonomy.py`:
- `test_matcher.py` covers autonomy-aware routing (auto-execute -> AUTO_RUN, confirm-first -> CONFIRM_FIRST)
- `test_chat_router.py` covers the confirm-first chat flow (confirmation prompt, yes/no handling)

---

## Wave 0 Requirements

- [ ] `tests/phase3/conftest.py` -- shared fixtures (mock Ollama embed, skill YAML fixtures)
- [ ] `tests/phase3/test_tool_registry.py` -- stubs for AGNT-04, AGNT-05
- [ ] `tests/phase3/test_skill_registry.py` -- stubs for AGNT-01, AGNT-02
- [ ] `tests/phase3/test_matcher.py` -- stubs for AGNT-03, AGNT-06 (autonomy routing)
- [ ] `tests/phase3/test_executor.py` -- stubs for skill execution
- [ ] `tests/phase3/test_chat_router.py` -- integration stubs for routing flow, AGNT-06 (confirm-first flow)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Skill appears in Open WebUI chat response | AGNT-02 | Requires running Open WebUI + full Docker stack | Send "what can you do?" in chat, verify skill list response |
| Confirm-first prompt displays in chat UI | AGNT-06 | Requires browser interaction with Open WebUI | Trigger confirm-first skill, verify prompt appears |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending

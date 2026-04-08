---
phase: 4
slug: document-ingestion-and-rag
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-08
---

# Phase 4 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | `tests/conftest.py` or "none — Wave 0 installs" |
| **Quick run command** | `pytest tests/phase04/ -x -q` |
| **Full suite command** | `pytest tests/ -q` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/phase04/ -x -q`
- **After every plan wave:** Run `pytest tests/ -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 04-01-01 | 01 | 1 | DOCP-01 | unit | `pytest tests/phase04/test_docling_pipeline.py -x -q` | ❌ W0 | ⬜ pending |
| 04-01-02 | 01 | 1 | DOCP-02 | unit | `pytest tests/phase04/test_ocr_processing.py -x -q` | ❌ W0 | ⬜ pending |
| 04-02-01 | 02 | 1 | DOCP-03 | unit | `pytest tests/phase04/test_qdrant_indexing.py -x -q` | ❌ W0 | ⬜ pending |
| 04-02-02 | 02 | 1 | DOCP-04 | unit | `pytest tests/phase04/test_client_isolation.py -x -q` | ❌ W0 | ⬜ pending |
| 04-03-01 | 03 | 2 | DOCP-05 | integration | `pytest tests/phase04/test_rag_query.py -x -q` | ❌ W0 | ⬜ pending |
| 04-03-02 | 03 | 2 | DOCP-06 | integration | `pytest tests/phase04/test_chat_upload.py -x -q` | ❌ W0 | ⬜ pending |
| 04-04-01 | 04 | 2 | DOCP-07 | integration | `pytest tests/phase04/test_gpu_scheduling.py -x -q` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/phase04/conftest.py` — shared fixtures (mock Qdrant client, sample PDFs, test client IDs)
- [ ] `tests/phase04/test_docling_pipeline.py` — stubs for DOCP-01
- [ ] `tests/phase04/test_ocr_processing.py` — stubs for DOCP-02
- [ ] `tests/phase04/test_qdrant_indexing.py` — stubs for DOCP-03, DOCP-04
- [ ] `tests/phase04/test_client_isolation.py` — stubs for DOCP-04
- [ ] `tests/phase04/test_rag_query.py` — stubs for DOCP-05
- [ ] `tests/phase04/test_chat_upload.py` — stubs for DOCP-06
- [ ] `tests/phase04/test_gpu_scheduling.py` — stubs for DOCP-07

*If none: "Existing infrastructure covers all phase requirements."*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Scanned PDF OCR quality | DOCP-02 | Requires visual inspection of OCR output on real scanned documents | Upload a scanned PDF via Open WebUI, verify extracted text is readable and searchable |
| GPU VRAM starvation under load | DOCP-07 | Requires concurrent workload and nvidia-smi monitoring | Run simultaneous OCR + LLM inference, monitor VRAM with `nvidia-smi` |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending

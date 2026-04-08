---
status: partial
phase: 04-document-ingestion-and-rag
source: [04-VERIFICATION.md]
started: 2026-04-08T00:00:00Z
updated: 2026-04-08T00:00:00Z
---

## Current Test

[awaiting human testing]

## Tests

### 1. Upload-to-Index Pipeline
expected: Upload a PDF in Open WebUI chat — document_ingest skill queues ARQ job, returns job ID. Worker processes file through docproc and indexes chunks into Qdrant.
result: [pending]

### 2. RAG Query with Citations
expected: Ask "what does my document say about X?" — ask_documents skill triggers QdrantSearchTool, answer includes "Source: filename.pdf, page N" citations.
result: [pending]

### 3. GPU Lock Sequencing
expected: Start heavy LLM chat request, then upload a document simultaneously — ingest worker waits for GPU lock before running EasyOCR, no concurrent VRAM contention.
result: [pending]

## Summary

total: 3
passed: 0
issues: 0
pending: 3
skipped: 0
blocked: 0

## Gaps

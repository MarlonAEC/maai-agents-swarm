# Phase 3: Tool System and Skills - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md -- this log preserves the alternatives considered.

**Date:** 2026-04-08
**Phase:** 03-tool-system-and-skills
**Areas discussed:** Skill definition format, Skill matching strategy, Tool plugin architecture, Autonomy control UX

---

## Skill Definition Format

### Q1: How should skills relate to CrewAI's existing YAML config?

| Option | Description | Selected |
|--------|-------------|----------|
| Skills as wrappers | skills.yaml references agents.yaml/tasks.yaml entries | |
| Self-contained YAML | Each skill is a single file with everything inline | |
| Extend existing YAML | Add skill metadata to agents.yaml/tasks.yaml | |

**User's choice:** Initially rejected the question to clarify a concern about context window pollution -- didn't want all skills dumped into the LLM prompt. After explanation of two-stage routing (lightweight matcher index vs focused execution), user confirmed preference for easy add/remove format.

**Follow-up:** One file per skill in `clients/<client>/skills/`, auto-discovered at startup.

### Q2: Should the freeform agent become a skill file?

| Option | Description | Selected |
|--------|-------------|----------|
| Keep hardcoded | Freeform stays as built-in fallback in core_api | ✓ |
| Make it a skill file | Freeform becomes a special skill file with lowest priority | |

**User's choice:** Keep hardcoded
**Notes:** Prevents accidental deletion by clients.

---

## Skill Matching Strategy

### Q1: How should the Skill Matcher route user messages?

| Option | Description | Selected |
|--------|-------------|----------|
| Embedding similarity | Embed skills at startup, cosine similarity at runtime using nomic-embed-text | ✓ |
| LLM classifier | Send skill list + user message to Gemma 3 4B for classification | |
| Keyword + embedding hybrid | Exact trigger match first, embedding fallback | |

**User's choice:** Embedding similarity
**Notes:** Fast, no LLM call needed, uses already-available nomic-embed-text model.

### Q2: Should the system confirm ambiguous matches?

| Option | Description | Selected |
|--------|-------------|----------|
| No, trust the match | Above threshold runs, below goes freeform | |
| Confirm in ambiguous zone | Gray zone (0.5-0.7) asks user to confirm | ✓ |

**User's choice:** Confirm in ambiguous zone
**Notes:** Three-zone routing: auto-run >= 0.7, confirm 0.5-0.7, freeform < 0.5.

---

## Tool Plugin Architecture

### Q1: How should tools be organized and discovered?

| Option | Description | Selected |
|--------|-------------|----------|
| Convention directory | One .py file per tool in src/core_api/tools/, auto-scanned | ✓ |
| Plugin packages | Separate pip packages with entrypoints | |

**User's choice:** Convention directory
**Notes:** Simple drop-in pattern matching the skill file approach.

### Q2: How should per-client tool enable/disable work?

| Option | Description | Selected |
|--------|-------------|----------|
| Allowlist in client config | tools.yaml lists enabled tools; missing file = all enabled | ✓ |
| Blocklist in client config | tools.yaml lists disabled tools; everything else enabled | |
| Per-skill only | Tools only loaded if referenced by a present skill | |

**User's choice:** Allowlist in client config
**Notes:** Explicit control over what's available per client.

### Q3: Should users enable/disable skills from Open WebUI?

**User's question** (raised organically): "Will the user be able to enable/disable skills from the Open WebUI?"

| Option | Description | Selected |
|--------|-------------|----------|
| Chat command only | "list skills" / "what can you do?" returns skill index in chat | ✓ |
| You decide | Let Claude determine best approach | |
| Skip for now | No in-chat skill listing | |

**User's choice:** Chat command only (read-only list, no admin UI)
**Notes:** Enable/disable stays file-based. Admin UI deferred.

---

## Autonomy Control UX

### Q1: How should confirm-first skills present confirmation?

| Option | Description | Selected |
|--------|-------------|----------|
| Chat message confirmation | Agent describes action, asks yes/no in chat | ✓ |
| Summary + action plan | Detailed dry-run before confirmation | |
| You decide | Let Claude determine | |

**User's choice:** Chat message confirmation
**Notes:** Works within existing Open WebUI chat flow, no custom UI needed.

### Q2: Default autonomy for new skills?

| Option | Description | Selected |
|--------|-------------|----------|
| Confirm-first | Safer default, deployer opts into auto-execute | ✓ |
| Auto-execute | Skills run immediately unless marked confirm-first | |

**User's choice:** Confirm-first
**Notes:** Prevents unexpected actions from freshly added skills.

---

## Claude's Discretion

- Embedding index storage format
- Exact similarity thresholds (0.5/0.7 starting points)
- Tool registry implementation details
- Confirmation message phrasing
- CrewAI Crew assembly for dynamic skills
- "List skills" detection mechanism

## Deferred Ideas

- Admin UI for skill management in Open WebUI
- Dry-run / action plan confirmation for destructive skills

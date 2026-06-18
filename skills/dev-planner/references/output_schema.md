# dev-planner — Output Schema Reference

Full field specification for each layer of the development plan.

---

## LAYER 0 — Project Brief

| Field | Type | Description |
|:------|:-----|:------------|
| `PROJECT` | string | Short project name |
| `DOMAIN` | enum | `web_app` \| `ml_system` \| `neural_network` \| `algorithm` \| `data_pipeline` \| `embedded` \| `cli_tool` \| `research_prototype` \| `multi_domain` |
| `CONSTRAINTS` | list | Language, framework, hardware, dataset, deadline, team size |
| `ASSUMPTIONS` | list | Items tagged `[assumed]` — filled with defaults when input is underspecified |
| `SUCCESS` | string | Measurable definition of "done" |

---

## LAYER 1 — Final Objective

Single sentence. Required properties:
- **Measurable** — contains a metric, test, or observable behavior
- **Terminal** — end state, not process
- **Domain-complete** — accuracy % for ML, latency for systems, feature set for apps

---

## LAYER 2 — Build Objectives (Milestones)

| Field | Type | Description |
|:------|:-----|:------------|
| `id` | string | `BO-N` (e.g. `BO-1`) |
| `title` | string | Short milestone name |
| `goal` | string | What this BO produces |
| `criterion` | string | Pass/fail measurable condition |
| `blocks_on` | list\<string\> | Dependencies (e.g. `[BO-1, BO-2]` or `[]`) |

Rules:
- 3–8 BOs per plan (S=1, M=2–4, L=5–8 based on complexity score)
- BOs are ordered; each unlocks the next
- Every BO must be independently verifiable

---

## LAYER 3 — Task Graph

| Field | Type | Description |
|:------|:-----|:------------|
| `id` | string | `T-X.Y` (e.g. `T-1.2`) |
| `title` | string | Short task name |
| `type` | enum | `DESIGN` \| `IMPLEMENT` \| `TRAIN` \| `TUNE` \| `TEST` \| `INTEGRATE` \| `DOC` \| `REFACTOR` \| `EXPERIMENT` \| `ABLATION` \| `BASELINE` \| `PROFILE` \| `ANNOTATE` |
| `desc` | string | What to do |
| `input` | string | Artifact or state required |
| `output` | string | Artifact or state produced |
| `level` | enum | `LOW` (single function/module) \| `MID` (component/subsystem) |
| `verify` | string | Pointer to verification block (e.g. `V-1.2`) |

---

## LAYER 4 — Verification Blocks

| Field | Type | Description |
|:------|:-----|:------------|
| `id` | string | `V-X.Y` matching the task |
| `scope` | enum | `low` \| `mid` |
| `type` | enum | `unit` \| `integration` |
| `runtime` | string | Expected runtime (LOW < 30s, MID < 5min) |
| `assertions` | list | Conditions that must hold for pass |
| `correction_loop` | bool | Always `true` — wrap with `run_with_correction()` |

---

## LAYER 5 — Architectural Pseudocode

| Annotation | Meaning |
|:-----------|:--------|
| `# === BO-N: title ===` | Milestone boundary |
| `# → V-X.Y` | Verification pointer |
| `assert ...` | Inline invariant checkpoint |
| `TODO:` | Open design decision |
| `LOOP-UPDATE:` | Section likely to change after verification |
| `# Generated: <date> \| Iteration: N` | Version tracking |

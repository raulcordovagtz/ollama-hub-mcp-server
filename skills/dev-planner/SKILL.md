---
name: dev-planner
description: >
  Generate a complete, structured software development plan from any project proposal.
  Use this skill whenever a user presents a project idea, requirement document, or
  technical brief and wants it converted into an actionable plan with tasks, milestones,
  verification scripts, and architectural pseudocode. Trigger on: "plan this project",
  "break down this idea", "create a dev plan", "how should I build X", "architecture for
  X", "roadmap for X", "task breakdown", "what are the steps to build X", or any time a
  user describes a software project (app, neural network, algorithm, pipeline, system,
  library, tool) and wants a structured development guide. This skill covers ALL software
  development domains: web apps, ML/AI systems, neural networks, algorithm research,
  data pipelines, embedded systems, CLI tools, and research prototypes.
  Always use this skill instead of writing ad-hoc plans.
---

# dev-planner

Converts a raw project proposal into a **hierarchical, verifiable development plan**
following a hybrid architecture grounded in three proven paradigms:

| Paradigm | What it contributes |
|:---------|:--------------------|
| **MetaGPT SOP** | Standardized role-based outputs (Analyst → Architect → Planner) that reduce cascading errors |
| **HiPlan (ICLR 2025)** | Global milestone guides (coarse) + local stepwise hints (fine-grained) for long-horizon tasks |
| **Reflexion + ReAct** | Actor → Evaluator → Self-Reflection loops at block level; pseudocode updated per iteration |

The output is **not a static document** — it is a living plan with built-in correction
loops at low and mid level. Global correctness is the user's responsibility.

---

## Output Architecture (5 layers)

```
LAYER 0 │ PROJECT BRIEF          — distilled intent, constraints, success criteria
LAYER 1 │ FINAL OBJECTIVE        — single measurable end-state definition
LAYER 2 │ BUILD OBJECTIVES       — 3–8 milestones, each independently verifiable
LAYER 3 │ TASK GRAPH             — tasks per milestone, typed, with dependencies
LAYER 4 │ VERIFICATION BLOCKS    — assertion scripts (low-level) + integration checks (mid-level)
LAYER 5 │ ARCHITECTURAL PSEUDOCODE — living Python-style pseudocode, loop-updatable
```

Read `references/output_schema.md` for the full field spec of each layer.
Read `references/domain_patterns.md` for domain-specific guidance (ML, algorithms, systems).
Read `templates/verification_script.py` for the canonical verification script template.

---

## Step-by-Step Workflow

### STEP 0 — Parse the Proposal

Extract from the user's input:
- **Domain** — classify as one of: `web_app`, `ml_system`, `neural_network`, `algorithm`,
  `data_pipeline`, `embedded`, `cli_tool`, `research_prototype`, `multi_domain`
- **Known constraints** — language, framework, hardware, dataset, deadline, team size
- **Unknowns** — list what's missing; fill with reasonable defaults, flag them as `[assumed]`
- **Complexity score** — `S` (1 milestone), `M` (2–4), `L` (5–8) based on scope

For `neural_network` or `algorithm` domains, read `references/domain_patterns.md`
section "ML & Algorithm Projects" before proceeding.

---

### STEP 1 — Layer 0: Project Brief

Write a concise brief (≤150 words) covering:
```
PROJECT:     <name>
DOMAIN:      <domain>
CONSTRAINTS: <language, framework, hardware, data, etc.>
ASSUMPTIONS: <list of [assumed] items>
SUCCESS:     <what "done" means in measurable terms>
```

---

### STEP 2 — Layer 1: Final Objective

One sentence. Must be:
- **Measurable** — contains a metric, test, or observable behavior
- **Terminal** — describes the end state, not the process
- **Domain-complete** — valid for the domain (accuracy % for ML, latency for systems, etc.)

Example: *"A trained ResNet-variant that achieves ≥92% top-1 accuracy on CIFAR-10
with inference latency <10ms on a single A100 GPU."*

---

### STEP 3 — Layer 2: Build Objectives (Milestones)

Decompose the Final Objective into 3–8 **Build Objectives**. Rules:
- Each BO must be independently verifiable (has its own pass/fail criterion)
- BOs are ordered; each unlocks the next
- Label them `BO-1` through `BO-N`
- Include: `goal`, `criterion` (measurable), `blocks_on` (dependencies)

Format:
```
BO-1  <title>
  goal:      <what this BO produces>
  criterion: <how we know it passed — a test, metric, output file, etc.>
  blocks_on: [] or [BO-X, BO-Y]
```

---

### STEP 4 — Layer 3: Task Graph

For each Build Objective, list its tasks as a flat ordered graph:

```
BO-1 / T-1.1  <task title>
  type:   [DESIGN | IMPLEMENT | TRAIN | TUNE | TEST | INTEGRATE | DOC | REFACTOR]
  desc:   <what to do>
  input:  <artifact or state required>
  output: <artifact or state produced>
  level:  [LOW | MID]   ← LOW = single function/module; MID = component/subsystem
  verify: V-1.1         ← pointer to verification block
```

Task types for ML/Algorithm domains also include:
`EXPERIMENT`, `ABLATION`, `BASELINE`, `PROFILE`, `ANNOTATE`

---

### STEP 5 — Layer 4: Verification Blocks

For each task at level `LOW` or `MID`, generate a verification block.

**LOW-level block** — unit-scope, runs in <30s, deterministic:
```python
# V-1.1 — <task title>
# SCOPE: low | TYPE: unit
def verify_<id>():
    # setup
    ...
    # assert
    assert <condition>, "<failure message>"
    print("✓ V-1.1 passed")
```

**MID-level block** — component integration, may call subprocesses:
```python
# V-2.3 — <component title>
# SCOPE: mid | TYPE: integration
def verify_<id>():
    result = run_component(...)
    assert result.metric >= THRESHOLD, f"metric={result.metric} < {THRESHOLD}"
    assert result.shape == EXPECTED_SHAPE
    print("✓ V-2.3 passed")
```

**Correction loop** — every verification block includes a retry wrapper:
```python
def run_with_correction(verify_fn, max_retries=3):
    for attempt in range(max_retries):
        try:
            verify_fn()
            return True
        except AssertionError as e:
            print(f"  ✗ attempt {attempt+1}: {e}")
            # → surface to planner for pseudocode patch
    return False
```

See `templates/verification_script.py` for the full runnable template with
CLI runner, summary table, and correction-loop harness.

---

### STEP 6 — Layer 5: Architectural Pseudocode

Write Python-style pseudocode that captures the **full logical architecture**.
This is the living artifact — it gets patched when verification loops surface errors.

Rules for the pseudocode:
- Use Python syntax (valid enough to read, not necessarily runnable)
- Group by Build Objective using `# === BO-N: <title> ===` headers
- Annotate every major step with its verification ID: `# → V-1.1`
- Use `assert` statements as inline checkpoints for key invariants
- Use `TODO:` comments for design decisions still open
- Use `LOOP-UPDATE:` comments to mark sections likely to change after verification

```python
# === PROJECT: <name> ===
# Final Objective: <one-line>
# Generated: <date> | Iteration: 0

# === BO-1: <title> ===
def bo1_<slug>():
    data = load_data(path=CONFIG.data_path)          # → V-1.1
    assert data is not None, "Data load failed"

    processed = preprocess(data, **CONFIG.preprocess) # → V-1.2
    assert processed.shape[0] > 0

    # LOOP-UPDATE: normalization strategy may change after V-1.2
    return processed

# === BO-2: <title> ===
def bo2_<slug>(processed_data):
    model = build_model(CONFIG.architecture)          # → V-2.1
    # TODO: decide between Adam vs AdamW
    ...
```

---

## Correction Loop Protocol

When a verification block fails, follow this protocol before updating the pseudocode:

```
FAIL REPORT
  block:    V-X.Y
  task:     T-X.Y — <title>
  error:    <AssertionError or exception message>
  attempt:  N of 3

DIAGNOSIS  (one of)
  □ Logic error in implementation
  □ Wrong assumption in spec → update BO criterion
  □ Data/environment issue → not a code bug
  □ Threshold too tight → recalibrate criterion

ACTION
  □ Patch pseudocode section marked LOOP-UPDATE
  □ Update task description
  □ Update BO criterion
  □ Escalate to user (only if diagnosis = spec ambiguity)

PSEUDOCODE PATCH
  # LOOP-UPDATE [iteration N]: <what changed and why>
  <updated pseudocode block>
```

The correction loop runs **at block level only**. It does NOT trigger a full
re-plan. Global objective review remains the user's responsibility.

---

## Domain-Specific Guidance

See `references/domain_patterns.md` for:
- **ML/Neural Network projects** — data audit BO, baseline-first ordering,
  experiment tracking tasks, metric verification patterns
- **Algorithm/Research projects** — complexity proof tasks, asymptotic
  verification, ablation BO structure
- **Systems/Pipeline projects** — throughput benchmarks, fault-injection tests,
  contract verification patterns

---

## Quick Format Reference

Full output order:
1. `[BRIEF]` — Layer 0
2. `[OBJECTIVE]` — Layer 1
3. `[MILESTONES]` — Layer 2, all BOs
4. `[TASK GRAPH]` — Layer 3, grouped by BO
5. `[VERIFICATION BLOCKS]` — Layer 4, inline Python
6. `[PSEUDOCODE]` — Layer 5, full architecture
7. `[OPEN QUESTIONS]` — flagged [assumed] items needing user confirmation

Always present all 7 sections. Never skip verification blocks.
Never output global correctness guarantees — those belong to the user.
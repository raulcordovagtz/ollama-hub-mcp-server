# dev-planner — Domain Patterns Reference

Domain-specific guidance for the three major project categories.

---

## ML & Neural Network Projects

### Build Objective Ordering (mandatory)

Always follow this BO sequence for ML projects:

```
BO-1  Data Audit & Pipeline
BO-2  Baseline Model (simplest possible)
BO-3  Target Architecture Implementation
BO-4  Training & Tuning
BO-5  Evaluation & Ablations
BO-6  Inference Optimization (if required)
```

**Baseline-first rule:** Never skip BO-2. A working baseline is required before
implementing the target architecture. Baseline results become the floor criterion
for BO-3's pass condition.

### Data Audit BO (BO-1) — Required Tasks

```
T-1.1  ANNOTATE  — class distribution analysis
T-1.2  ANNOTATE  — missing values / corruption scan
T-1.3  IMPLEMENT — data loader with deterministic splits (train/val/test)
T-1.4  TEST      — data integrity assertions (shape, dtype, range, no leakage)
```

Criterion: `data_loader` returns correct splits with zero data leakage confirmed
by verification block V-1.4.

### Experiment Tracking Tasks

Include at least one `EXPERIMENT` task per training BO:
```
T-X.Y  EXPERIMENT  — log: lr, batch_size, seed, val_loss, val_acc per epoch
  output: experiment_log.csv + checkpoint.pt
```

### Metric Verification Patterns

```python
# ML metric assertions
assert val_accuracy >= THRESHOLD, f"val_acc={val_accuracy:.4f} < {THRESHOLD}"
assert val_loss < baseline_loss, f"no improvement over baseline"
assert not math.isnan(val_loss), "loss diverged (NaN)"
assert train_loss < val_loss * 1.5, "possible overfitting detected"
```

### Ablation BO Structure

```
BO-N  Ablation Study
  T-N.1  BASELINE  — record full-model metric
  T-N.2  ABLATION  — remove component A → measure delta
  T-N.3  ABLATION  — remove component B → measure delta
  T-N.4  PROFILE   — FLOPs, params, inference latency per variant
  criterion: delta table shows contribution of each component
```

---

## Algorithm & Research Projects

### Complexity Proof Tasks

Include a `DESIGN` task for theoretical analysis before any implementation:
```
T-1.1  DESIGN  — time complexity proof (Big-O)
  output: complexity_analysis.md with recurrence relation and solution
T-1.2  DESIGN  — space complexity analysis
T-1.3  DESIGN  — edge case enumeration (empty input, single element, overflow)
```

### Asymptotic Verification

```python
# Empirical complexity check
import time, random
sizes = [100, 1000, 10000]
times = []
for n in sizes:
    data = [random.randint(0, 10**6) for _ in range(n)]
    t0 = time.perf_counter()
    algorithm(data)
    times.append(time.perf_counter() - t0)

# For O(n log n): ratio should be ~constant * log(n2/n1)
ratio_1_2 = times[1] / times[0]
expected_ratio = (1000 * 10) / (100 * 7)  # n*log(n) ratio
assert 0.5 * expected_ratio <= ratio_1_2 <= 2.0 * expected_ratio, \
    f"complexity not O(n log n): ratio={ratio_1_2:.2f}, expected≈{expected_ratio:.2f}"
```

### Research Prototype BO Structure

```
BO-1  Literature baseline reimplementation
BO-2  Proposed modification / hypothesis
BO-3  Controlled experiment (same data, same seed, same hyperparams)
BO-4  Statistical significance test (t-test or Wilcoxon if non-normal)
BO-5  Write-up / reproducibility package
```

---

## Systems & Pipeline Projects

### Throughput Benchmark Tasks

```
T-X.Y  PROFILE  — throughput benchmark
  desc: measure requests/sec, p50/p95/p99 latency, error rate under load
  output: benchmark_report.json
  verify: V-X.Y
```

Verification pattern:
```python
assert throughput_rps >= TARGET_RPS, f"throughput={throughput_rps} < {TARGET_RPS}"
assert p99_latency_ms <= MAX_P99_MS, f"p99={p99_latency_ms}ms > {MAX_P99_MS}ms"
assert error_rate < 0.001, f"error_rate={error_rate:.4f} exceeds 0.1%"
```

### Fault Injection Tests

```
T-X.Y  TEST  — fault injection
  desc: simulate upstream failure, network partition, corrupted payload
  output: fault_report.md with recovery time per scenario
```

### Contract Verification Patterns

```python
# Input contract
assert isinstance(payload, dict), "payload must be dict"
assert "id" in payload and isinstance(payload["id"], str), "missing or invalid id"
assert 0 < len(payload.get("data", [])) <= MAX_BATCH, "batch size out of range"

# Output contract
assert result["status"] in ("ok", "partial", "error")
assert "timestamp" in result and isinstance(result["timestamp"], float)
```

---

## Quick Domain Classifier

| Keywords in proposal | Domain |
|:---------------------|:-------|
| train, model, dataset, accuracy, loss, epoch | `ml_system` or `neural_network` |
| sorting, search, graph, O(n), complexity, proof | `algorithm` |
| API, frontend, database, auth, deploy | `web_app` |
| pipeline, ETL, batch, streaming, Kafka, Spark | `data_pipeline` |
| firmware, GPIO, UART, embedded, RTOS | `embedded` |
| CLI, argparse, shell, stdin/stdout | `cli_tool` |
| hypothesis, experiment, reproduce, ablation | `research_prototype` |
| 2+ distinct domains above | `multi_domain` |

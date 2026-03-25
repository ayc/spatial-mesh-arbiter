# T4-01: Conformance Pass/Fail Criteria

> **Status:** REVIEW
> **Checklist Ref:** [GAPS_CHECKLIST.md](../GAPS_CHECKLIST.md)
> **Canonical Target:** `5-testing-and-conformance/01-mini-mesh-conformance.md`

## Audit Notes

Each scenario (A-T) has documented "Observation" subsections with semi-formal expectations. Missing: formalized assertions, metric collection, timing tolerances, and CI integration.

## Resolution

### 1. Assertion Framework

Each conformance scenario is converted into a set of **machine-checkable assertions** with timing windows. Assertions use a standard structure:

```rust
struct ConformanceAssertion {
    assertion_id:   String,          // e.g., "SCN-A-SPLIT-01"
    scenario_id:    String,          // e.g., "SCN-A"
    description:    String,
    metric_source:  MetricSource,    // How to observe the value
    predicate:      Predicate,       // What must be true
    timing_window:  TimingWindow,    // When it must be true
    severity:       Severity,        // MUST_PASS or SHOULD_PASS
}

enum TimingWindow {
    Within { seconds: f64 },         // Must become true within N seconds of trigger
    Sustained { seconds: f64 },      // Must remain true for N seconds
    Immediate,                       // Must be true on the next observable tick
}
```

### 2. Metric Collection

**Mechanism: Structured telemetry channel** (not log parsing).

Each Arbiter, Controller, and Edge Node exposes a structured telemetry stream:
- **Transport:** UDP to a local collector (lightweight, non-blocking)
- **Format:** Protobuf-encoded `TelemetryEvent` messages
- **Categories:** `topology_change`, `entity_count`, `tick_timing`, `proposal_outcome`, `dilation_factor`, `ghost_quality`, `adapter_hook_timing`

The conformance harness runs a telemetry collector that aggregates events and evaluates assertions against the stream.

```protobuf
message TelemetryEvent {
    uint64 tick = 1;
    string source_id = 2;           // arbiter_id or "controller"
    string category = 3;
    map<string, double> metrics = 4; // metric_name → value
    map<string, string> labels = 5;  // dimensional labels
}
```

### 3. Timing Tolerances

| Category | Default Tolerance | Notes |
|----------|------------------|-------|
| Topology operations (split/merge) | 5 seconds | Includes warm pool allocation + handoff |
| Intent terminal outcome | 1 tick (16.67ms) | Deterministic — should be exact |
| Metronome convergence | 5 seconds | Bounded slew rate |
| Dilation activation | 1 tick | Dilation formula is per-tick |
| Ghost correction | 3 seconds | Includes RUDP round-trip |
| Crash detection | `METRONOME_HEARTBEAT_STALE_TICKS` (3s default) | Configurable |

Tolerances are configurable per-assertion to account for CI environment variability (CI runners are slower than bare-metal).

### 4. CI Integration

**Harness binary:** `conformance-runner` — a standalone binary that:
1. Spins up a Docker Compose mesh (Controller + N Arbiters + Edge Nodes + swarm-tester bots)
2. Executes a scenario script (connect bots, trigger events, wait for conditions)
3. Collects telemetry
4. Evaluates assertions
5. Emits a JSON report with per-assertion pass/fail

**CI pipeline integration:**
```yaml
conformance:
  stage: test
  script:
    - cargo build --release -p conformance-runner
    - docker compose -f docker/conformance.yml up -d
    - ./target/release/conformance-runner --scenarios=all --report=json
    - docker compose -f docker/conformance.yml down
  artifacts:
    paths: [conformance-report.json]
  rules:
    - if: $CI_PIPELINE_SOURCE == "merge_request_event"  # PR gate
    - if: $CI_PIPELINE_SOURCE == "schedule"              # Nightly
```

**Gate policy:** All `MUST_PASS` assertions must pass. `SHOULD_PASS` failures emit warnings but don't block merge.

### 5. Example: Scenario A Assertions

Scenario A: "Automatic split when entity count exceeds threshold"

| Assertion ID | Predicate | Timing |
|-------------|-----------|--------|
| `SCN-A-SPLIT-01` | `arbiter_count >= 2` | Within 5s of 11th entity entering |
| `SCN-A-SPLIT-02` | `max(arbiter_entity_count) <= split_threshold + tolerance` | Sustained for 3s after split |
| `SCN-A-SPLIT-03` | `topology_epoch` incremented exactly once | Immediate after split |
| `SCN-A-SPLIT-04` | Zero `DUAL_WRITER` traces during split | Sustained during split window |

## References

- `docs/5-testing-and-conformance/01-mini-mesh-conformance.md` — 20 scenarios
- `docs-core/05-1-conformance-test-matrix.md` — Normative test matrix
- `docs-core/05-2-core-conformance-scenario-catalog.md` — Scenario catalog

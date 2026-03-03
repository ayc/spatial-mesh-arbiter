# T4-01: Conformance Pass/Fail Criteria

> **Status:** OPEN (narrowed after audit)
> **Checklist Ref:** [GAPS_CHECKLIST.md](../GAPS_CHECKLIST.md)
> **Canonical Target:** `5-testing-and-conformance/01-mini-mesh-conformance.md`

## Audit Notes

**Each scenario (A-T) does have documented expectations** in "Observation" subsections. Some include specific values:
- Scenario A: "As the 11th bot enters the bounding box, developers can observe the Mesh Controller instantly provision a secondary Arbiter"
- Scenario D: "Stale proposals are rejected with explicit `ActionFailed { reason: "Data Epoch Mismatch" }`"
- Scenario P: "pacing offset follows bounded slew (<=50us/frame) and absolute clamp (<=1000us), converging to abs(diff) <= 1 tick within 5 seconds"

These are semi-formal expectations, not just vague descriptions.

## Remaining Gap (Narrowed)

The observations describe *what should happen* but not *how to automatically verify it*:

### 1. Formalized Assertions
Convert observations into testable assertions with timing windows. E.g., Scenario A: "Within 5 seconds of the 11th entity entering, a second Arbiter MUST be provisioned AND entity count on original Arbiter MUST decrease."

### 2. Metric Collection
No spec for how to instrument Arbiters/Controller for test observation (Prometheus metrics? Log parsing? Custom telemetry channel?)

### 3. Timing Tolerances
Async operations need acceptable variance bands. E.g., "within 5 seconds" vs "within 100ms"

### 4. CI Integration
How to run conformance scenarios in CI (Docker Compose? Test harness binary?)

## Questions to Resolve

- [ ] Per-scenario assertion list with timing windows
- [ ] Metric/telemetry collection mechanism
- [ ] Acceptable timing tolerances
- [ ] CI pipeline integration strategy

## Proposed Resolution

_To be drafted._

## References

- `docs/5-testing-and-conformance/01-mini-mesh-conformance.md` — 20 scenarios with Observation subsections

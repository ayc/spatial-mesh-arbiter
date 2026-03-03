# T4-02: Swarm Tester Spec

> **Status:** OPEN
> **Checklist Ref:** [GAPS_CHECKLIST.md](../GAPS_CHECKLIST.md)
> **Canonical Target:** `5-testing-and-conformance/01-mini-mesh-conformance.md`

## Problem Statement

The swarm-tester crate is Phase 5 in the implementation plan and referenced by conformance testing, but its spec is thin:

1. Headless bot behavior model (Boids flocking mentioned but not specified)
2. WebSocket frame contract for bot ↔ Edge Node communication
3. Combat spam patterns (what abilities? What cadence? Random or scripted?)
4. Bot lifecycle (connect, authenticate, spawn, act, disconnect)
5. Metrics collection and reporting

## Questions to Resolve

- [ ] Boids algorithm parameters (separation, alignment, cohesion weights)
- [ ] Bot decision loop (per-tick? Lower frequency?)
- [ ] Combat action selection (random from ability pool? Prioritized? Scripted sequences?)
- [ ] Auth for bots (test tokens? Bypass? Dedicated test accounts?)
- [ ] Metric emission format
- [ ] Configurable bot count, spawn location, behavior profile

## Proposed Resolution

_To be drafted._

## References

- `docs/0-getting-started/02-implementation-phases.md` — Phase 5: swarm-tester
- `docs/5-testing-and-conformance/01-mini-mesh-conformance.md` — Swarm Tester references

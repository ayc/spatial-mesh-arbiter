# T4-03: Debug Canvas Spec

> **Status:** OPEN
> **Checklist Ref:** [GAPS_CHECKLIST.md](../GAPS_CHECKLIST.md)
> **Canonical Target:** `5-testing-and-conformance/01-mini-mesh-conformance.md`

## Problem Statement

A "2D Debug Canvas" for real-time R-Tree visualization is referenced but not specified:

1. What framework? (HTML Canvas? egui? Bevy debug renderer?)
2. What data is visualized? (Arbiter cell boundaries, entity positions, ghost zones, projectile paths?)
3. How does it receive data? (WebSocket from Controller? Direct Arbiter state read?)
4. Is it a separate service or embedded in an existing one?

## Questions to Resolve

- [ ] Rendering framework choice
- [ ] Data source and transport
- [ ] Visualization layers (topology, entities, ghosts, interest rings, dilation zones)
- [ ] Interaction (pan/zoom? Click entity for details? Time scrubbing?)
- [ ] Deployment: local dev only or also staging?

## Proposed Resolution

_To be drafted._

## References

- `docs/5-testing-and-conformance/01-mini-mesh-conformance.md` — Debug Canvas mention

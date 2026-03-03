# Internal Mesh Types: Architecture Summary

## 5. Summary of Architecture Rules

1.  **No Shared Memory:** Actors only communicate via message envelopes.
2.  **No Blocking Calls:** Spatial Actors must never perform Disk I/O or wait for Database locks within the 60Hz `tick()`.
3.  **Deterministic Time:** Every action is bound to a Shard Tick.
4.  **Spatial Jurisdiction:** Geography and R-Tree depth determine authoritative ownership.

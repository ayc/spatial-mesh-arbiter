# SK-96: Death Ghost

## Designer Intent

When my HP reaches 0, I do not truly die immediately. Instead, I enter a ghost phase for 8
seconds. During that phase I am fixed at the death position, cannot be targeted, cannot move,
cannot attack, and only get a small nearby healing bar. When the phase ends, I truly die, kill
credit is awarded, and the respawn flow begins with those 8 seconds already counted toward my dead
time.

## Primitive Composition

P-39 (On-Death Hook) → P-25 (Multi-Phase Vitals) → P-26 (Capability Bitmask) → P-27 (Targetability Overrides) → P-45 (Delay Timer) → P-66 (Status Effect Filter Mutation)

*See `ability-primitives/` for canonical definitions.*

## Inputs

- No input (triggered automatically on lethal HP)

## Observable Behavior

1. HP reaches 0 -> enter `GhostPhase` instead of committing terminal death
2. Ghost phase fixes the entity at the death position: no movement, no attacks, no items
3. Ghost phase is untargetable, ignored by AoE, ignored by skillshot collision, and does not block pathing
4. The ghost keeps ordinary vision updates from that fixed position
5. Existing buffs and debuffs are cleared on ghost entry because they applied to the corporeal body
6. The ability bar is replaced with a heal-only nearby support set
7. Ghost phase lasts exactly 8 seconds and cannot be ended early by enemies or ally effects
8. When the timer expires, terminal death is committed, kill credit is awarded, and `PlayerDied` is emitted
9. Meta subtracts the authored 8-second ghost credit from the resolved base respawn timer, so the ghost time counts toward dead time
10. Visual: translucent/spectral appearance, restricted healing-only ability bar

## Engine Primitives Required

### Ghost Phase Is A Normal Intermediate Lifecycle Phase

This mechanic is not a post-terminal shell. It is an ordinary `P-25` intermediate phase:

1. HP reaches 0
2. Stage 10 transitions the entity into `GhostPhase`
3. The entity remains locally active in the Arbiter for limited allied-beneficial casting
4. After 8 seconds, Stage 10 commits terminal death
5. Only then are kill credit and `PlayerDied` published

This keeps the mechanic inside the existing lifecycle contract instead of inventing a "dead but
still acting" state.

### Phase Restrictions And Observer Semantics

Ghost phase applies fixed capability and targeting rules:

- `CAN_MOVE = false`
- `CAN_ATTACK = false`
- `CAN_USE_ITEMS = false`
- `PASSIVES_ACTIVE = false`
- `CAN_CAST = true` only for the authored ghost ability whitelist
- hostile/allied/self targeting denied
- area effects denied
- skillshot collision denied
- pathing collision denied

Because the phase stays active rather than suspended, the ghost continues to emit normal
observer/vision updates from the fixed death position.

### Respawn Delay Credit On True Death

The 8-second ghost window counts toward dead time, but Meta timing does not start until terminal
death is real:

1. Ghost phase begins on lethal HP, but `PlayerDied` is NOT emitted yet
2. Ghost phase runs for 8 seconds
3. On expiry, terminal death commits and `PlayerDied` is emitted with `respawn_delay_credit_ticks = 8s`
4. Meta computes `effective_respawn_delay = max(base_respawn_delay - 8s, 0)`

This preserves the gameplay goal without requiring a terminally dead active shell.

### Body/Status Reset On Ghost Entry

On ghost entry, all active buffs and debuffs are removed in one batch:

- corporeal protections, DoTs, anti-heal, and ordinary CC are cleared
- the ghost starts from a clean state
- the ghost does not inherit passive offensive pressure from the dead body

This is a generated all-polarity cleanse on phase entry, not a separate cast.

### Limited Ability Usage During Ghost Phase

The ghost can cast only the authored heal/support whitelist:

1. `validate_intent` checks `lifecycle_phase == GhostPhase`
2. attempted abilities outside the ghost ability set are rejected
3. allowed abilities resolve normally, including ordinary allied-heal interactions
4. hostile abilities are not legal in the canonical profile

## Cross-Boundary Concerns

The ghost remains on the Arbiter where lethal HP occurred. Because movement is disabled, there is
no phase-handoff path to solve.

Healing casts from the ghost follow ordinary authority rules:

1. local allies are healed locally
2. neighboring Ghost allies use the same target-owner relay rules as any other beneficial cast

Because terminal death has not happened yet, Meta is not involved during the 8-second phase. The
only Meta-facing event is the final `PlayerDied` published on ghost expiry with the authored
respawn-delay credit.

If the Arbiter crashes during ghost phase, current crash-recovery semantics apply: the phase is not
resumed, and the player re-enters through the normal crash/spawn recovery path rather than
continuing the interrupted ghost.

## Compiler Requirements

Designer specifies:

- ghost duration
- allowed ghost ability IDs
- respawn-delay credit
- whether statuses are cleared on entry

Compiler emits:

- entity-level `ghost_phase` config
- Stage 10 lethal-HP interception that transitions into the authored intermediate phase
- generated capability restrictions and generated targetability/pathing-denial overlay
- optional generated all-polarity cleanse on phase entry
- terminal-death emission on phase expiry with `respawn_delay_credit_ticks`

Compiler validates:

- `ghost_duration_ticks > 0`
- `respawn_delay_credit_ticks` is in `[0, ghost_duration_ticks]`
- `ghost_ability_set` is non-empty
- every ghost-phase ability is allied-beneficial and/or self-beneficial only

## Resolved Notes

- Ghost healing is ordinary healing and therefore still participates in normal on-heal and anti-heal interactions on the target.
- `SK-91 Team-Agnostic Stasis` does not affect the ghost under the canonical profile because the phase denies area-effect admission entirely.
- The ghost does not block pathing.
- Passive offensive pressure does not persist because active statuses are cleared on entry and `PASSIVES_ACTIVE` is forced off during the phase.
- `SK-89 Respawn Anchor`, when present, evaluates only when ghost phase ends and terminal death is finally committed.
- `SK-93 Death Prevention` does not trigger at ghost expiry because expiry is a phase-completion death commit, not a new lethal-damage event.
- Vision continues to update from the ghost's fixed position for the full phase duration.
- Talented offensive variants are out of scope for the canonical profile; `ghost_phase` is intentionally limited to allied-beneficial/self-beneficial casting.

# SK-122: Counterspell

## Designer Intent

I see an enemy begin casting a powerful spell. Before it resolves, I use my reaction to COUNTER it — the spell is cancelled entirely. No damage, no effect, no projectile. The enemy's mana/resource is consumed but nothing happens. I've nullified their ability at the cost of my reaction cooldown.

## Primitive Composition

P-40 (On-Cast Intercept)

*See `ability-primitives/` for canonical definitions.*

## Inputs

- Caster entity (the counterspeller)
- Target entity (the enemy currently casting)
- Timing: must be used DURING the enemy's cast time (before resolution)

## Observable Behavior

1. Enemy begins casting an ability (cast bar visible)
2. During the cast time: I use Counterspell targeting the casting enemy
3. If successful: enemy's ability is CANCELLED — no damage, no projectile, no effect
4. The enemy's resource cost is still consumed (mana spent, slot used)
5. The enemy's ability goes on full cooldown (as if it was cast, but produced nothing)
6. My counterspell goes on cooldown
7. If the enemy's ability was instant (no cast time): cannot be countered (nothing to react to)
8. Visual: magical disruption effect on the enemy, fizzle animation, "Countered!" indicator

## Engine Primitives Required

Counterspell is already the canonical `P-40` mid-cast intercept path.

The runtime contract is:

1. Any admitted ability with `cast_time > 0` publishes visible cast state.
2. That cast-state record includes the public `ability_id`, scheduled completion tick, and
   `can_be_counterspelled`.
3. A successful `P-40` intercept marks the cast cancelled before completion effects fire.
4. The target's already-committed resource cost is preserved and the ability remains on full
   cooldown.
5. If the cancelled cast owns active channel outputs, Stage 11 teardown removes them in the same
   tick.

So the mechanic is not a bespoke "delete the spell" exception. It is the standard cast-state plus
intercept contract: cancel before completion, preserve committed cost, prevent root effects from
resolving.

Instant abilities have no cast-state window and therefore cannot be counterspelled. The reaction
resource question is orthogonal to the compiler contract; this sketch works as an ordinary ability
with its own cooldown.

## Cross-Boundary Concerns

Counterspell uses the same visible cast-state and relay model as the rest of the channel/cast
contract.

1. Same-Arbiter targets are checked locally against their current published cast-state entry.
2. Remote/Ghost targets are only counterable if the counterspell reaches the authoritative owner
   before the cast completes.
3. If the authoritative owner receives the intercept after completion, the counter fails cleanly
   because there is no longer an active cast to cancel.

So cross-boundary countering is not a separate capability. It is the ordinary timing race against
the authoritative cast completion tick.

## Compiler Requirements

Designer specifies:

- a targeted hostile interrupt ability
- normal cooldown/cost for the counterspell itself
- which abilities in the game are or are not `can_be_counterspelled`

Compiler emits:

- the counterspell ability definition
- per-ability `can_be_counterspelled` flags on target abilities
- the standard visible cast-state publication for non-zero cast times
- the `P-40` intercept path that cancels the cast before completion effects fire

Compiler validates:

1. only abilities with `cast_time > 0` produce a counter window
2. `can_be_counterspelled = false` cleanly opts a casted ability out of interception
3. cancelled casts preserve already-committed cost/cooldown rather than refunding them

## Resolved Interaction Notes

- Counterspell cancels channels too, because active cast-state and channel lifecycle are one shared
  contract; cancelling the cast/channel prevents future completion or tick outputs and tears down
  maintained outputs in Stage 11.
- Counterspell is a pure intercept effect. It does not need to deal damage to succeed.
- Any cast with `cast_time = 0` has no counter window and cannot be counterspelled.
- Whether a specific boss spell, empowerment, or special cast is counterable is controlled by the
  authored `can_be_counterspelled` flag, not by sketch-local exception logic.

# SK-11: On-Kill Cascade

## Designer Intent

When I kill an enemy, an explosion of dark energy erupts from the corpse dealing AoE damage to nearby enemies. I also gain a 10% damage buff for 5 seconds. If the explosion kills another enemy, it triggers again — chain reaction through tightly packed groups.

## Primitive Composition

P-39 (On-Death Hook) → P-09 (Shape Overlap Query)

*See `ability-primitives/` for canonical definitions.*

## Inputs

- Triggering kill event (on-kill proc)
- Killed entity's position
- Caster's offensive stats

## Observable Behavior

1. Enemy HP reaches zero from my damage — kill confirmed
2. AoE explosion at the corpse's position — all enemies within radius take X damage
3. Caster gains +10% damage buff (5s duration, refreshes on each kill)
4. If the explosion kills another enemy, repeat from step 2 at the new corpse's position
5. Each cascade uses the caster's current offensive stats (including accumulated damage buff)
6. Cascade continues until no more kills occur or proc_depth is reached
7. Visual: chain of explosions rippling through a group

## Engine Primitives Required

TODO: The on-kill trigger fires AFTER damage resolution (HP reaches zero). This is a different phase than on-hit or on-crit — it happens after the target's SoftState is mutated. The kill check needs to detect "this entity just died from damage dealt by this caster." The explosion is resolved as a new AoE. The damage buff stacks/refreshes during the cascade — does the second explosion benefit from the buff gained from the first kill?

## Cross-Boundary Concerns

TODO: The killed entity's position is on their owning Arbiter. The explosion is local to that Arbiter. But the caster (who receives the damage buff) may be on a different Arbiter. Each kill in the cascade triggers: (1) a local AoE on the victim's Arbiter, (2) a relay to the caster's Arbiter for the buff. If kills cascade across boundaries, the ordering of buff applications vs. damage calculations matters.

## Compiler Requirements

TODO: Designer specifies: trigger (on-kill), AoE radius, AoE damage, buff (10% damage, 5s, refreshing), recursive (cascade on AoE kills). Compiler produces: on-kill proc trigger + zone definition + buff application + recursive cascade tracking. How does the compiler reason about the cascade — is it just proc_depth, or does it need to model kill probability?

## Open Questions

- Does the damage buff apply before or after the first cascade explosion resolves?
- If the cascade kills enemies on multiple Arbiters simultaneously, is there a deterministic ordering for buff applications?
- Does the on-kill trigger fire on any kill (minions, summons from SK-06) or only player/hero kills?
- Can the cascade trigger other on-kill effects (item procs, quest credit)?
- What is the kill detection mechanism — who determines "this entity died from this caster's damage" when damage sources may be complex (DoTs, reflected damage)?
- If the caster dies during the cascade (e.g., thorns from an AoE target), does the cascade stop?

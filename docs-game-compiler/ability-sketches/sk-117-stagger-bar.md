# SK-117: Stagger Bar

## Designer Intent

Boss enemies have a secondary bar above their HP — the Stagger Bar. My abilities deal stagger damage alongside regular HP damage. When the team depletes the stagger bar, the boss is STAGGERED: stunned for a long duration and takes increased damage. If we don't deplete the bar fast enough, it regenerates and we miss the window. Coordinating stagger damage is a core raid mechanic.

## Primitive Composition

P-48 (Secondary Stagger Bar) → P-26 (Capability Bitmask) → P-16 (Stat Layering)

*See `ability-primitives/` for canonical definitions.*

## Inputs

- Multiple attacker entities (team effort)
- Target entity (boss/elite with a stagger bar)
- Each ability has a stagger value (alongside its normal damage value)

## Observable Behavior

1. Boss spawns with a full Stagger Bar (e.g., 1000 stagger HP)
2. Players use abilities — each ability deals normal HP damage AND stagger damage to the bar
3. High-stagger abilities (big slow swings) deal more stagger; fast abilities deal less
4. As the bar depletes, visual indicator shows progress (bar turning yellow → orange → red)
5. If stagger bar reaches 0: boss enters STAGGER STATE for 5 seconds (stunned + 20% damage vulnerability)
6. After stagger state ends: stagger bar resets to full
7. If players don't deplete the bar within a time window (e.g., 30 seconds): bar regenerates to full (failed check)
8. Some boss phases have MANDATORY stagger checks — failure triggers a wipe mechanic
9. Visual: visible stagger bar under HP bar, screen shake on stagger, boss collapse animation

## Engine Primitives Required

Stagger Bar is already the canonical `P-48` secondary-resource model.

The target entity opts in through `EntityDefinition.stagger_bar`, which supplies:

1. `max_stagger`
2. `regen_rate_per_tick`
3. `regen_delay_ticks`
4. `stagger_duration_ticks`
5. `vulnerability_bonus`

Abilities contribute through the already-canonical `AbilityDefinition.stagger_damage` field. That
means one hit may carry both ordinary HP damage and stagger damage in parallel. The target owner
applies the HP packet through ordinary damage resolution, then updates the stagger bar through
`P-48`.

When the bar depletes, the engine applies the mechanical stagger state from the target's
`StaggerBarDef`: fixed stagger duration plus the authored vulnerability bonus. This is NOT ordinary
`apply_cc`; it does not use tenacity, DR, or status-resistance scaling. The bar resets only after
the stagger window ends, and regeneration is controlled by the authored per-tick rate plus delay.

The team-wide contribution model is just the shared target owner mutating one authoritative bar.
No special team accumulator is needed beyond multiple attacks all landing on the same boss.

## Cross-Boundary Concerns

The stagger bar is authoritative on the target owner, exactly like HP. If an attacker is remote and
the boss is a Ghost, the origin owner relays the prepared hit as usual; the boss owner then applies
both the HP-side combat packet and the authored `stagger_damage` locally.

So the cross-boundary rule is simple: stagger contribution rides the same prepared-hit path as the
rest of combat. There is no separate raid-wide stagger coordinator.

## Compiler Requirements

Designer specifies:

- optional `stagger_bar` on bosses/elites
- per-ability `stagger_damage`
- the entity's stagger duration, regen delay/rate, and vulnerability bonus
- any encounter-specific failure consequence separately (for example a wipe mechanic triggered by
  not staggering during a scripted window)

Compiler emits:

- `EntityDefinition.stagger_bar` for entities that participate in the mechanic
- per-ability `stagger_damage` values
- the standard `P-48` state-update path that mutates the bar, checks depletion, and applies the
  compiled mechanical stagger state
- downstream bar/state data for observer payloads

Compiler validates:

1. `max_stagger > 0`
2. `regen_rate_per_tick >= 0`
3. `regen_delay_ticks >= 0`
4. `stagger_duration_ticks > 0`
5. `stagger_damage` defaults to `0` when omitted and otherwise participates as a parallel damage
   channel, not as a bespoke status effect

## Resolved Interaction Notes

- Mechanical stagger is not ordinary CC. Its duration and vulnerability bonus come from
  `StaggerBarDef`, not from `apply_cc`, and are not reduced by tenacity or DR.
- Stagger regeneration is part of the `P-48` resource model, not healing, so anti-heal semantics do
  not apply to the bar's refill behavior.
- Multiple players naturally contribute to the same bar because the boss owner applies every
  incoming `stagger_damage` packet to one shared target resource.
- Mandatory stagger checks are encounter scripting layered on top of the canonical bar mechanic,
  not a separate stagger implementation.

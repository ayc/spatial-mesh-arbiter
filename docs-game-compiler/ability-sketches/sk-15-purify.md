# SK-15: Purify

## Designer Intent

I target an ally and instantly remove all negative status effects (debuffs, DoTs, crowd control). The ally then gains 1.5 seconds of debuff immunity — new debuffs applied during this window are blocked.

## Primitive Composition

P-66 (Status Effect Filter Mutation)

*See `ability-primitives/` for canonical definitions.*

## Inputs

- Caster entity
- Target ally entity (must be in range)

## Observable Behavior

1. Cast on ally — all negative status effects are immediately removed
2. This includes: DoTs, slows, stuns, roots, silences, damage-over-time, movement debuffs
3. Target gains a "Purified" buff granting debuff immunity for 1.5 seconds
4. During immunity window: any incoming debuff application is blocked (not just delayed)
5. Purify itself has a long cooldown (e.g., 120 seconds)
6. Visual: cleansing light effect on the target, immunity glow during the window

## Engine Primitives Required

Purify resolves against the target's **authoritative active status registry** on the target's owning Arbiter.

The canonical rule is:

1. Each runtime status entry carries compiled metadata: `polarity`, `is_cleansable`, and optional `status_application_immunity`.
2. Purify emits a `cleanse` filter with `polarity = negative` and `require_cleansable = true`.
3. The target Arbiter evaluates `SoftState.active_status_effects` against that filter and removes all matching entries in one atomic mutation batch.
4. Crowd control entries participate automatically because `apply_cc` compiles to generated negative status entries in the same registry.
5. After the cleanse, the ability applies a positive `Purified` status with `status_application_immunity = negative` and duration `90` ticks (1.5 seconds at 60Hz).
6. While `Purified` is active, any new negative status application is rejected before insertion. Existing positive or neutral statuses are unaffected.

This gives Purify one canonical behavior for DoTs, CC, anti-heal, slows, and other harmful status entries without special-casing each mechanic.

## Cross-Boundary Concerns

If the target ally is a Ghost, the caster's Arbiter relays the cleanse action to the target's owning Arbiter. The owning Arbiter performs the actual registry mutation because it owns the target's `SoftState.active_status_effects`.

There is no shared-state race condition:

1. Each entity has exactly one authoritative Arbiter per tick.
2. The owning Arbiter executes the cleanse in its deterministic single-threaded stage order.
3. Effects already admitted before the cleanse executes are visible to the cleanse and can be removed if they match the filter.
4. Effects that attempt to apply after the cleanse executes in the same tick see the newly-added `Purified` immunity status and are rejected if they are negative.

The cleanse therefore behaves as an atomic target-side mutation, not as a best-effort message racing with independent debuff writers.

## Compiler Requirements

Designer specifies:

- On each status definition: `polarity`, `is_cleansable`, and optional `status_application_immunity`
- On the Purify ability: ally target, range, cooldown, `cleanse { polarity = negative, require_cleansable = true }`
- A follow-up positive status definition (`purified`) with duration `90` ticks and `status_application_immunity = negative`

Compiler emits:

- A P-66 `cleanse` instruction/filter targeting the ally
- A positive status definition for `purified`
- A follow-up status application for `purified` after the cleanse
- Generated negative runtime status entries for any `apply_cc` effects that Purify should be able to remove

Compiler validates:

1. `apply_buff` references only `positive` statuses.
2. `apply_debuff` references only `negative` statuses.
3. `apply_cc` declares whether its generated status is cleansable.
4. `cleanse` filters operate only on canonical status metadata (`polarity`, `is_cleansable`), not arbitrary string tags.
5. Statuses granting `status_application_immunity` use a valid polarity domain (`negative`, `positive`, `all`).

## Resolved Interaction Notes

- Debuffs can be marked uncleanseable. `is_cleansable = false` prevents removal by generic Purify-style cleanse.
- Cleansing a DoT removes the target-side negative status entry only. Independent caster-side buffs or stacks persist unless they are separately authored as removable statuses on the caster.
- Purify does not rewind or cancel already-committed kinematic mutations. If a displacement has already entered movement resolution, removing a related status does not retroactively reposition the entity.
- Purify does not remove the `Purified` immunity status because the cleanse filter targets `negative` statuses only and `Purified` is `positive`.
- The immunity window blocks **new** negative status admissions, including DoT reapplications. It does not retroactively touch uncleanseable negatives that survived the initial cleanse.
- Linked mechanics such as Tether depend on how they are authored. If a harmful link is represented as a negative cleansable status on the target, Purify removes it. If the mechanic is modeled as a neutral/system binding, generic Purify does not remove it.
- Bulk removal is a linear scan over the target's bounded active-status list on the authoritative Arbiter. This is acceptable for the expected active-effect counts and remains deterministic.

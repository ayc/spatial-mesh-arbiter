# SK-107: Corpse Possession

## Designer Intent

When an enemy champion dies near me, I can interact with their corpse to BECOME them temporarily. I take over their body — gaining their model, abilities, and items — for 10 seconds. My own body is stored. After the duration (or on reactivation), I revert to my original form at the corpse's position.

## Primitive Composition

P-47 (Spatial Corpse Registry) → P-31 (Identity/Loadout Swap) → P-45 (Delay Timer)

*See `ability-primitives/` for canonical definitions.*

## Inputs

- Caster entity
- Target: a recently dead enemy champion's corpse (must be in range)

## Observable Behavior

1. Enemy champion dies near me — their corpse is available for 8 seconds
2. I interact with the corpse — my body disappears, I become the dead enemy
3. I have their model, their abilities (Q/W/E — not ultimate), and their items/stats
4. My HP is set to the dead enemy's max HP (I start at full HP in their body)
5. I can move, attack, and use their abilities freely for 10 seconds
6. After 10 seconds (or reactivation): I revert to my original form at my current position
7. On revert: my original HP is restored (as it was before possession)
8. If I die during possession: I revert to my original form with a brief untargetable phase
9. Visual: take on the dead enemy's appearance, dark aura to distinguish from the real champion

## Engine Primitives Required

Corpse Possession is now a canonical local corpse-snapshot transformation. It does not require a new
"dead entity persistence phase" beyond the existing corpse profile.

### Canonical Corpse Requirements

The possessed target's entity type must already define:

- `corpse_profile.persist_ticks >= 480`
- `corpse_profile.retain_loadout_snapshot = true`
- `corpse_profile.retain_effective_stats = true`

That yields a local corpse-registry record containing:

- death position
- retained projected loadout / appearance snapshot
- retained effective-stat snapshot

The possession cast then uses:

- `swap_identity(target = caster, source = { corpse_snapshot: target }, duration_ticks = 600, hp_policy = set_to_new_max, cooldown_policy = reset_new_slots, excluded_abilities = [corpse_ultimate])`

This means the caster keeps the same `entity_id`, team allegiance, and authority ownership, but
temporarily adopts the corpse snapshot's loadout, appearance, and retained effective combat profile.

### Body Storage and Restoration

`swap_identity` already stores the caster's original form and restores it on expiry or explicit
break. For this sketch:

- expiry after 10 seconds restores the original form at the caster's current position
- same-key reactivation explicitly breaks the possession early and restores the original form at the
  current position
- lethal damage during possession is modeled as a possession-break path, not true death of the
  caster: the possession form ends, the caster reverts, and a brief positive untargetable status is
  applied on return

### Items, Stats, and Appearance

This sketch does not treat the corpse's items as transferred inventory objects. Instead, the
corpse's retained loadout / passive / effective-stat snapshots carry the gameplay consequences of
those items into the temporary possessed form. Everyone sees the caster as the possessed corpse
appearance while the swap is active, with any ally-only marker handled through ordinary observer
presentation if the game wants one.

## Cross-Boundary Concerns

Corpse Possession follows the current canonical corpse rule: corpse access is local to the corpse's
authoritative Arbiter.

1. The cast succeeds only when the targeted corpse record exists on the CURRENT Arbiter.
2. Remote or Ghost-backed corpse possession is not supported in the current profile; the cast fails
   cleanly rather than requesting remote corpse data.
3. Once possession begins, the caster is still one ordinary live entity. Crossing boundaries during
   possession is just normal entity handoff carrying the active identity-swap state.
4. Expiry or reactivation revert happens on the caster's current authoritative owner and restores the
   original form at the current position, not at the corpse's death position.

## Compiler Requirements

Designer specifies:

- enemy corpse target filter and range
- possession duration
- which corpse-bearing entity types retain loadout/effective-stat snapshots
- excluded corpse abilities such as the ultimate
- revert behavior on expiry, reactivation, and possession-break

Compiler emits:

- a corpse-targeted cast using ordinary corpse-registry admission
- one `swap_identity` using `source = { corpse_snapshot: target }`
- ordinary stored-form restore on expiry or explicit break
- an optional short untargetable positive status applied after possession-break revert

Compiler validates:

1. the target corpse's source entity type defines `corpse_profile.retain_loadout_snapshot = true`
2. retained effective-stat usage requires `corpse_profile.retain_effective_stats = true`
3. corpse possession targets only the CURRENT Arbiter's corpse registry
4. excluded corpse abilities are valid public abilities in the retained corpse loadout snapshot

## Resolved Notes

- The possessed form keeps the caster's team/allegiance. Only appearance, loadout, and effective
  stat profile change.
- The possessed form starts at the new form's max HP via `hp_policy = set_to_new_max`.
- Cooldowns for the temporary corpse-derived loadout are reset through `cooldown_policy = reset_new_slots`.
- Current corpse buffs/debuffs are not inherited unless they were explicitly baked into the retained
  snapshot surfaces. Ordinary live status state does not carry through corpse possession by default.
- Corpse access is first-come-first-served through the local corpse-registry claim/admission rules;
  a consumed or expired corpse cannot be possessed again.

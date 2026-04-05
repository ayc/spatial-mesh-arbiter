# SK-51: Unstoppable

## Designer Intent

I activate a short defensive window that strips active crowd control, grants a shield, and then
prevents new crowd control from landing while the window lasts. I am still targetable and still
take damage normally.

## Primitive Composition

P-66 (Status Effect Filter Mutation) → P-62 (Categorized CC Immunity) → P-18 (Absorption Barrier)

*See `ability-primitives/` for canonical definitions.*

## Inputs

- Caster entity
- Self-cast only

## Observable Behavior

1. Activate — immediately remove active CC from self, gain a shield, and gain `unstoppable` for 2
   seconds.
2. While `unstoppable` is active, incoming CC is rejected before admission.
3. Damage portions of mixed damage+CC abilities still apply normally; only the CC component is
   stripped.
4. The status does not grant invulnerability, untargetability, or stealth.
5. Friendly, hostile, and self-inflicted CC are all blocked equally in this reference because the
   immunity check is relation-agnostic.
6. Forced movement, pulls, taunts, blinds, silences, stuns, roots, charms, fears, berserk, mute,
   and other authored CC categories are all blocked during the window.
7. Visual: shield impact on cast plus a clear `Unstoppable` buff presentation while active.

## Engine Primitives Required

The canonical version is one positive status plus one category-scoped self-cleanse:

1. On activation, the ability emits `cleanse(target = caster, polarity = negative,
   require_cleansable = false, cc_categories = [displacement, hard_disable, soft_disable,
   forced_movement, target_override, mute])`.
2. After that cleanse batch, the ability applies a positive `unstoppable` status whose
   `cc_immunity_categories` list uses the same full category set.
3. The ability also applies an ordinary shield through `apply_shield`.
4. While `unstoppable` is active, incoming CC attempts whose compiled `cc_category` matches one of
   those categories are rejected before they enter the target's active status registry.

This keeps Unstoppable narrow:

- it removes active crowd control
- it blocks new crowd control
- it does not purge arbitrary non-CC negative statuses
- it does not interfere with ordinary damage resolution

## Cross-Boundary Concerns

Unstoppable is enforced entirely on the target's authoritative Arbiter:

1. If a cross-boundary prepared hit carries both damage and CC, the target owner still applies the
   damage portion normally.
2. The same target owner then evaluates the CC component against active `cc_immunity_categories`.
3. If the target is currently `unstoppable`, the CC component is rejected locally and never creates
   a new status entry.
4. Because the activation cleanse is also target-side `P-66`, there is no race with foreign writers
   beyond the normal deterministic stage order on the target owner.

The attacker's Arbiter never needs an out-of-band "target is unstoppable" hint.

## Compiler Requirements

Designer specifies:

- self-cast activation
- duration of the Unstoppable window
- shield amount / duration
- which CC categories the window blocks (all canonical categories in this reference)

Compiler emits:

- one category-scoped `cleanse` against self that removes active CC without broad negative purge
- one positive `unstoppable` status definition with the matching `cc_immunity_categories` set
- one shield application

Compiler validates:

1. the `cleanse.cc_categories` list uses only canonical CC category names and has no duplicates
2. the `unstoppable` status is `positive`, not `negative`
3. the `unstoppable` status does not silently widen into damage immunity or targetability changes
4. the shield uses ordinary shield validation and remains independent of the CC-immunity window

## Resolved Interaction Notes

- Because immunity is category-based, Unstoppable blocks friendly and self-inflicted CC as well as
  hostile CC in this reference.
- Existing non-CC negatives such as anti-heal or DoTs are not removed by the activation cleanse
  unless the game separately authors that broader behavior.
- Time spent Unstoppable does not advance DR tiers, because blocked CC never admits and therefore
  never records a DR application.
- Enemy buff-strip mechanics may remove the positive `unstoppable` status if the game authors them
  to remove positive statuses.
- Unstoppable can coexist with other positive defensive states such as shields or even Burrow-style
  untargetability/invulnerability if the game separately allows those statuses to overlap.
- Entering a Vortex, being targeted by Charge pinning, or being hit by Mind Control all fail at the
  CC admission step while Unstoppable is active, but any paired damage still resolves normally.

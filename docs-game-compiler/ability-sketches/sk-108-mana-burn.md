# SK-108: Mana Burn

## Designer Intent

My auto-attacks destroy the target's mana. For each point of mana destroyed, the target also takes bonus magical damage. This lets me shut down mana-reliant enemies by draining their resource pool while simultaneously dealing damage.

## Primitive Composition

P-35 (On-Hit Hook) → P-49 (Resource Destruction-to-Damage)

*See `ability-primitives/` for canonical definitions.*

## Inputs

- Attacker entity (passive on auto-attacks)
- Target enemy entity

## Observable Behavior

1. Auto-attack hits target
2. Destroy X mana from the target's mana pool (e.g., 28 mana per hit)
3. If target has less mana than X: destroy all remaining mana
4. Deal bonus damage equal to the mana actually destroyed (28 mana burned = 28 bonus damage)
5. Bonus damage is in addition to normal auto-attack damage
6. If target has 0 mana: no mana is burned, no bonus damage from the burn
7. Visual: mana drain effect, blue energy pulled from target

## Engine Primitives Required

### Resource-Targeting Combat

All existing combat targets HP. Mana Burn introduces **combat that targets a secondary resource (mana)**:

```
struct ManaBurnEffect {
    mana_per_hit: SimFixed,
    damage_per_mana: SimFixed,  // 1.0 = damage equals mana destroyed
}
```

On auto-attack hit:
1. Read target's current mana
2. `mana_destroyed = min(mana_per_hit, target.current_mana)`
3. `target.current_mana -= mana_destroyed`
4. `bonus_damage = mana_destroyed * damage_per_mana`
5. Apply `bonus_damage` as additional damage through normal Phase 2 resolution

### Mana as Attackable Resource

Currently, mana is a passive resource: spent by abilities, regenerated over time. Mana Burn makes mana a TARGETABLE resource — enemies can forcibly reduce it. The engine needs:
- Mana stored as part of entity state (SoftState): `current_mana: SimFixed, max_mana: SimFixed`
- Mana modification by external combat events (not just self-consumption from ability casts)
- Mana can't go below 0 (floor at 0)

### Mana Drain vs Mana Burn

Two variants of the mechanic:
- **Mana Burn** (Anti-Mage): destroy target's mana, deal damage. The mana is DESTROYED (gone).
- **Mana Drain** (Lion): steal target's mana, transfer it to yourself. The mana MOVES from target to caster.

Both require the engine to support external mana modification. Mana Drain additionally requires cross-entity resource transfer (like SK-70 Energy Shield's cross-entity resource credit).

### Interaction With Mana-Dependent Abilities

When a target's mana is burned:
- They can no longer cast abilities that cost more than their remaining mana
- SK-97 Escalating Cost's exponential costs become unaffordable faster
- Abilities with conditional effects based on mana (Mana Void: damage based on MISSING mana) scale with the burn

## Cross-Boundary Concerns

TODO: Mana burn happens during auto-attack damage resolution. If the target is a Ghost:
1. Auto-attack damage relays to target's Arbiter (standard)
2. The mana burn effect also relays: "burn X mana and deal bonus damage equal to mana destroyed"
3. The target's Arbiter resolves the mana burn locally (reads actual mana, calculates burn, applies damage)
4. The bonus damage amount depends on the target's current mana — the attacker's Arbiter can't know this for Ghosts

The mana burn resolution must happen on the TARGET's Arbiter (where mana is authoritative). The relay carries the burn parameters, not the result.

## Compiler Requirements

TODO: Designer specifies: passive on auto-attacks, mana destroyed per hit, bonus damage per mana destroyed. Compiler produces:
- ManaBurnEffect on-hit modifier
- Per-hit resolution: read target mana → calculate burn → modify mana → calculate bonus damage → apply damage
- Mana modification as external combat event

The compiler needs to support **resource-targeting effects** — combat that modifies resources other than HP.

## Open Questions

- Does mana burn apply before or after normal auto-attack damage?
- Can mana burn trigger on-hit procs (SK-09 Chain Lightning from the bonus damage)?
- Does SK-17 Sacrifice Shield block the bonus damage (shield absorbs the HP damage but mana is still burned)?
- Can mana burn be reflected by SK-22 Damage Reflection (reflect the bonus damage back)?
- Does SK-51 Unstoppable prevent mana burn (it's not CC — it's resource manipulation)?
- Can mana burn affect entities with no mana pool (some entities might use a different resource)?
- Does SK-92 Anti-Heal interact with mana burn (anti-heal reduces healing, not mana burn)?
- Can mana burn be applied by abilities (not just auto-attacks)?
- Does the target's Edge Node need to show the mana change immediately (client prediction of mana burn)?

# SK-82: Projectile Deflect

## Designer Intent

I activate a deflect stance for 1.25 seconds. During this time, I am Protected (invulnerable to damage). Any projectiles that would hit me are caught and returned to their source, dealing the original damage to the attacker. Non-projectile damage (melee, AoE zones) is blocked but not returned.

## Primitive Composition

P-61 (Projectile Ownership Hijacking) → P-03 (Trajectory Steering)

*See `ability-primitives/` for canonical definitions.*

## Inputs

- Caster entity
- No target (self-only defensive activation)

## Observable Behavior

1. Activate — enter deflect stance for 1.25 seconds
2. Protected: take no damage from any source
3. Projectile hits during deflect: projectile is caught and returned to the attacker
4. Returned projectile deals the original damage to the attacker (using attacker's own offensive stats)
5. Non-projectile damage: blocked (Protected) but not returned
6. Melee attacks: blocked, not returned
7. AoE zone damage: blocked, not returned
8. The deflect stance does not prevent CC (stun can interrupt the deflect)
9. Visual: swirling blade animation, caught projectiles visibly redirected

## Engine Primitives Required

### Projectile Interception and Return

This is fundamentally different from SK-22 Damage Reflection (percentage of damage returned as a new damage event). Projectile Deflect:
- Only affects PROJECTILE entities (not instant damage, not melee, not zones)
- CATCHES the projectile (removes it from flight)
- RETURNS it to the source (creates a new projectile traveling back)
- Uses the ORIGINAL attacker's damage (the CombatContext from the caught projectile)

The Arbiter must:
1. Detect "a projectile entity is about to hit this entity"
2. Check "does this entity have ProjectileDeflect active?"
3. If yes: instead of resolving the projectile's damage, REVERSE the projectile
4. The reversed projectile targets the original caster, carrying the original CombatContext
5. The original caster takes their own damage (through their own Phase 2 defenses)

### Projectile vs Non-Projectile Classification

The engine must distinguish between damage sources:
- **Projectile entity collision:** Deflectable (SK-02 Poison Shot, SK-43 Drag tongue, SK-80 Wall Bounce)
- **AoE zone pulse:** Not deflectable (SK-29 Blizzard, SK-08 Aura)
- **Melee attack:** Not deflectable (close-range, no projectile)
- **Instant targeted damage:** Not deflectable (no projectile entity in flight)
- **Beam damage:** Not deflectable? (SK-63 Steerable Beam — continuous line, not a projectile entity)

The classification must be clear: deflect only works on damage delivered via a ProjectileActor entity.

### Reversed Projectile Creation

When a projectile is deflected:
1. The original projectile is despawned (caught)
2. A new projectile is created at the deflector's position
3. The new projectile targets the original caster
4. The new projectile carries the original CombatContext (attacker's offensive stats)
5. The CombatContext's "source" is now ambiguous — the deflector didn't create the damage, but they redirected it

For kill credit: if the deflected projectile kills the original caster, who gets the kill? The deflector? The caster (killed by their own damage)?

## Cross-Boundary Concerns

TODO: A projectile from Arbiter A (attacker) flies toward the deflector on Arbiter B. The projectile was handed off to Arbiter B during flight. On deflection:

1. Arbiter B catches the projectile (despawns it)
2. Arbiter B creates a new projectile targeting the original caster (on Arbiter A)
3. The new projectile needs to be handed off BACK to Arbiter A
4. The original CombatContext (with attacker's offensive stats) is carried along

This is a projectile round-trip: A → B (original) → B catches → B → A (deflected). Two handoffs for one projectile interaction.

## Compiler Requirements

TODO: Designer specifies: duration (1.25s), Protected (invulnerable during), deflect projectiles (catch + return), non-projectile damage blocked but not returned, CC still affects, returns use original CombatContext. Compiler produces:
- Protected status effect (invulnerable) with projectile deflect modifier
- Projectile collision override: if deflect active → intercept + reverse instead of damage
- Reversed projectile creation with original CombatContext
- Damage source classification (projectile vs non-projectile)

The compiler needs to express "this invulnerability has a special interaction with projectile entities" — a conditional override on the projectile collision path.

## Open Questions

- Can deflect return SK-41 Detonation Arrow (catch it and the deflector controls when it detonates)?
- Can deflect catch SK-55 Growing Projectile (returns it at its current size)?
- Does the deflected projectile trigger on-hit procs for the deflector or the original caster?
- Can the deflected projectile be deflected AGAIN by the original caster (infinite deflect tennis)?
- Does deflect work against SK-62 Boomerang projectiles (catch them on return trip)?
- Does deflect catch SK-09 Chain Lightning bounces (is a chain bounce a "projectile")?
- Can deflect catch SK-71 Sticky Bomb mid-flight (before it attaches)?
- If multiple projectiles hit during deflect, are ALL of them returned?
- Does the deflect stance block SK-40 Mind Control (not a projectile — should still affect)?
- Can the deflected projectile be intercepted by body-blocking allies of the original caster?

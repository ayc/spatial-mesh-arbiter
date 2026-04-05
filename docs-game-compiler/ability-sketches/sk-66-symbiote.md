# SK-66: Symbiote

## Designer Intent

I attach to an allied hero from anywhere on the map. While attached, my abilities fire from their position — I can shoot spikes at nearby enemies, shield my host, and spawn a locust. My actual body stays where it was, vulnerable and immobile. I can detach at any time to return to controlling my body.

## Primitive Composition

P-34 (Persistent Linkage) → P-31 (Identity/Loadout Swap) → P-26 (Capability Bitmask)

*See `ability-primitives/` for canonical definitions.*

## Inputs

- Caster entity
- Target ally entity (global range — anywhere on the map)
- Detach input (same ability key to end symbiote)

## Observable Behavior

1. Cast on ally — caster attaches to the host (global range, no distance limit)
2. Caster's body becomes immobile and vulnerable at its current position
3. While attached: caster's ability bar changes to symbiote abilities (Spike Burst, Carapace, Stab)
4. All symbiote abilities fire FROM the host's position, not the caster's position
5. The host can act normally — the symbiote doesn't restrict them
6. The caster sees the host's surroundings (camera follows the host)
7. Detach: caster returns to controlling their body at its original position
8. If the host dies: caster is forcibly detached
9. If the caster's body is killed while symbioted: caster dies (body is vulnerable)
10. Visual: symbiote hat on the host, spike effects emanating from the host

## Engine Primitives Required

Symbiote is one link-bound remote-origin projection on the CASTER, not a second controlled body.

The canonical decomposition is:

1. `link(target = host, origin_override = source_uses_target_position, observer_anchor = true)`
   establishes the persistent attachment.
2. A `P-31` loadout/profile swap projects the symbiote ability bar onto the caster for the
   attachment window.
3. A self-applied lockout/root on the caster body suppresses movement while leaving the body in the
   world as a vulnerable target.

That means the host is not being mind-controlled and the caster body is not physically attached to
the host. The acting entity remains the caster; only ability-origin queries and observer payload
anchoring are borrowed from the linked host.

The body stays at its original position, remains targetable, and can die normally. If the body is
removed, the acting entity dies and the whole symbiote projection ends. If the host is removed, the
link breaks and the caster cleanly detaches with their original loadout restored.

## Cross-Boundary Concerns

Symbiote is now covered by the canonical `link.origin_override` + `observer_anchor` + `P-31`
loadout-projection model.

1. The caster remains the acting entity for inputs, stats, cooldowns, and resource costs.
2. The linked host supplies the CURRENT origin position for range checks, projectile spawn points,
   ground-target centers, and other origin-derived spatial queries.
3. If the host is remote, ordinary cross-boundary relay rules determine which Arbiter resolves that
   spatial query authoritatively; there is no sketch-local "always proxy through the host" rule.
4. `observer_anchor = true` moves the caster's downstream observer payloads to the host's vicinity
   so the camera/view follows the host while the body remains targetable at its real position.
5. If the host hands off, the link survives as ordinary SoftState and the remote origin/observer
   anchor automatically follow the host's new owner. If the host is removed, the link breaks and the
   symbiote projection ends cleanly.

## Compiler Requirements

Designer specifies:

- ally target
- attach duration or detach conditions
- the symbiote loadout/profile to project onto the caster while attached
- a self-lock/immobilizing status on the body while attached
- `link.origin_override` so the caster uses the host's position as the ability origin
- `observer_anchor = true` if the camera/view should follow the host
- break rules on host removal, caster removal, or manual detach

Compiler emits:

- one `link` from the caster to the host with `origin_override` enabled
- one projected symbiote loadout through `swap_identity` or equivalent `P-31` profile swap on the
  caster
- one self-applied immobilizing/lockout status on the caster body for the attached duration
- one detach path that removes the link and reverts the projected loadout, typically through the
  existing same-key reactivation/hidden-variant surface

Compiler validates:

1. the target is allied
2. the projected loadout/profile exists
3. the body lockout is expressed through ordinary status/capability policy rather than a bespoke
   "symbiote mode" flag
4. remote-origin casting is authored through `link.origin_override`, not by moving the caster body
   or transferring authority to the host

## Resolved Interaction Notes

- Symbiote abilities use the caster's own offensive stats, cooldowns, and proc state. Only the
  spatial origin is borrowed from the host.
- The caster's body remains a normal targetable body at its original location. `observer_anchor`
  changes downstream view anchoring only; it does not make the body untargetable or move it.
- Host death cleanly detaches the symbiote by breaking the link. Caster death ends the effect
  normally because the acting entity is removed.
- The detach/revert path is a canonical reactivation/loadout-revert problem, not a sketch-local
  special case.

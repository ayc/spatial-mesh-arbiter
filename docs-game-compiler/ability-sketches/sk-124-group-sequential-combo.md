# SK-124: Group Sequential Combo

## Designer Intent

During combat, a combo opportunity triggers for the group. A shared combo wheel appears showing a
sequence of required role-and-ability contributions in order: for example Fighter first, then
Scout, then Mage, then Priest. Each player contributes their step when it is their turn. If the
group completes the full sequence before the deadlines expire, a powerful group effect resolves.

## Primitive Composition

P-54 (Group Choice Aggregator) → P-42 (Stacking Counters w/ Decay)

*See `ability-primitives/` for canonical definitions.*

## Inputs

- An opening ability or combat event that starts the group combo
- Multiple participants in the same `party` or `raid_subgroup`
- One ordered sequence of required `group_role_id` plus `group_interaction_tags`

## Observable Behavior

1. A combo opportunity opens and all eligible group members see the shared combo UI
2. Step 1 requires a specific role and ability tag within a short time limit
3. On success, the session advances immediately to the next step
4. Each later step is resolved the same way until the sequence ends or a step times out
5. Completing the full sequence resolves the authored success effect for the group
6. If a step times out, the authored failure effect resolves if present; otherwise the combo ends
   with no further result
7. Different authored sequences can produce different success or failure outcomes
8. Combat continues while the session is active; contributors still use ordinary abilities

## Engine Primitives Required

Group Sequential Combo is now the canonical sequential `group_interaction` pattern.

### Group Session Definition

The opening ability authors one `group_interaction` block with:

1. `participant_scope = party` or `raid_subgroup`
2. `mode = sequential`
3. `timeout_ticks`
4. one `sequential.steps` list
5. one `success_result`
6. optional `failure_result`

Each `GroupSequenceStepDef` declares:

- `required_role_id`
- `required_ability_tag`
- `time_limit_ticks`

This is not a bespoke shared state machine invented per sketch. It is one bounded `P-54` session
opened only after the starting ability commits successfully.

### Advancement By Ordinary Ability Casts

Sequential contributions are ordinary admitted ability casts, not a new combo-input message type.

When any participant casts an ability:

1. Stage 2 admits or rejects the ordinary cast first
2. if the cast is admitted, the session owner checks the participant's `group_role_id`
3. it then checks whether the ability's `group_interaction_tags` match the current step
4. if both match before the deadline, the session advances immediately and records that
   contribution

So the actual sequential combo is "who cast which tagged ability at the right time," not "who
pressed a separate combo button."

### Success, Failure, And Result Application

If the final step completes in time, `success_result` resolves. If a step times out, `failure_result`
resolves if authored.

`GroupResultBlock.apply_to` determines whether the effects run:

- once per participant with implicit `participant` bindings, or
- once on the trigger owner

The resulting buffs, heals, and damage still resolve on each relevant entity's authoritative owner
through the ordinary relay rules.

## Cross-Boundary Concerns

This sketch uses the canonical cross-Arbiter `P-54` session-owner model.

1. When the opening ability commits, one Arbiter becomes the session owner.
2. If a participant on another Arbiter contributes a matching cast, that local owner admits the
   ordinary cast first and then relays the contribution tuple to the session owner.
3. Deadlines remain deterministic because every Arbiter shares the same authoritative tick.
4. When the session resolves, any participant-scoped reward still applies on each participant's
   authoritative owner through the normal relay path.

The sequential combo is therefore cross-Arbiter safe without a Controller-owned combo state machine
or a second client-input plane.

## Compiler Requirements

Designer specifies:

- the participant scope
- the session timeout
- the ordered step list
- the role required at each step
- the ability tag required at each step
- the success and optional failure results

Compiler emits:

- one `group_interaction(mode = sequential)` directive on the opening ability
- the ordered step definitions
- any required `group_interaction_tags` on contributor abilities
- one bounded session owner and relay contract using the existing `P-54` runtime

Compiler validates:

1. `timeout_ticks > 0`
2. `steps` is non-empty
3. every `time_limit_ticks > 0`
4. referenced tags and roles are authored explicitly rather than inferred from class names or UI
   text
5. result effects are expressible as ordinary `GroupResultBlock` payloads

## Resolved Notes

- The same participant may satisfy multiple different steps if later steps also match that
  participant's authored role and tagged ability choices.
- If multiple eligible participants race for the same step, the first admitted matching cast for
  that step wins. Later casts simply resolve as ordinary abilities after the step has already
  advanced.
- Combat does not pause during the session. Players can be interrupted, crowd-controlled, killed,
  or otherwise denied from contributing because the combo uses ordinary real-time ability casts.
- One admitted cast satisfies at most one sequential step. The runtime does not let one cast skip
  multiple steps.
- This sketch assumes one active Heroic Opportunity-style sequential session per opening trigger for
  the group. Sequence variants are just different authored `group_interaction` definitions.
- This sketch no longer requires new group-state machinery. The canonical `group_interaction`
  sequential contract already covers it.

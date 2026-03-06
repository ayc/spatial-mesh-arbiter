# Lua Subset Conformance Test Matrix v0.1

This document defines required compiler conformance tests for:

1. `01-1-lua-subset-profile.md`
2. `01-2-lua-whitelisted-api.md`

Keywords **MUST**, **MUST NOT**, **SHOULD**, and **MAY** are normative.

## 1. Scope

1. This matrix is normative for compiler certification of Lua profile support.
2. A compiler implementation is conformant only if all required tests pass.
3. Optional tests MAY be implemented, but MUST NOT substitute required tests.

## 2. Harness Requirements

Test harness MUST support:

1. compile success/failure assertions
2. normalized IR snapshot output
3. deterministic diagnostic code assertions
4. per-test profile-bound configuration input
5. golden artifact comparison across repeated runs

## 3. Pass Criteria

1. All `REQ` tests MUST pass.
2. No required negative test MAY compile successfully.
3. Diagnostics MUST match expected diagnostic class exactly.
4. IR snapshots for deterministic-equivalence tests MUST match byte-for-byte
   except for explicitly allowed metadata fields.

## 4. Required Test Groups

1. `PARSER`: syntax and grammar admission.
2. `PROFILE`: forbidden language features.
3. `API`: whitelist symbol and signature enforcement.
4. `CONTEXT`: `edge`/`arbiter`/`meta` policy enforcement.
5. `DETERMINISM`: nondeterminism rejection.
6. `BOUNDS`: boundedness and budget enforcement.
7. `IR_EQUIV`: canonicalization and output stability.
8. `DIAG`: deterministic diagnostic quality.

## 5. Required Test Cases

| Test ID | Group | Level | Scenario | Expected Result | Expected Diagnostic |
|---|---|---|---|---|---|
| `LUA-PARSER-001` | `PARSER` | `REQ` | minimal rule with context, trigger, outcome | compile succeeds | n/a |
| `LUA-PARSER-002` | `PARSER` | `REQ` | nested `if/elseif/else` in `validate` | compile succeeds | n/a |
| `LUA-PARSER-003` | `PARSER` | `REQ` | malformed block missing `end` | compile fails | `LUA_PROFILE_PARSE_ERROR` |
| `LUA-PROFILE-001` | `PROFILE` | `REQ` | `while` loop present | compile fails | `LUA_PROFILE_UNSUPPORTED_FEATURE` |
| `LUA-PROFILE-002` | `PROFILE` | `REQ` | `repeat ... until` present | compile fails | `LUA_PROFILE_UNSUPPORTED_FEATURE` |
| `LUA-PROFILE-003` | `PROFILE` | `REQ` | `goto` label present | compile fails | `LUA_PROFILE_UNSUPPORTED_FEATURE` |
| `LUA-PROFILE-004` | `PROFILE` | `REQ` | direct recursion in rule helper | compile fails | `LUA_PROFILE_UNSUPPORTED_FEATURE` |
| `LUA-PROFILE-005` | `PROFILE` | `REQ` | `require("x")` used | compile fails | `LUA_PROFILE_FORBIDDEN_API` |
| `LUA-API-001` | `API` | `REQ` | unknown helper symbol call | compile fails | `LUA_API_UNKNOWN_SYMBOL` |
| `LUA-API-002` | `API` | `REQ` | known helper with wrong arity | compile fails | `LUA_API_ARITY_MISMATCH` |
| `LUA-API-003` | `API` | `REQ` | known helper with wrong arg type | compile fails | `LUA_API_ARG_TYPE_MISMATCH` |
| `LUA-API-004` | `API` | `REQ` | numeric arg outside declared domain | compile fails | `LUA_API_ARG_DOMAIN_VIOLATION` |
| `LUA-API-005` | `API` | `REQ` | whitelisted helper correct signature | compile succeeds | n/a |
| `LUA-API-006` | `API` | `REQ` | `formula_eval` with registered formula id | compile succeeds | n/a |
| `LUA-API-007` | `API` | `REQ` | `formula_eval` with unknown formula id | compile fails | `LUA_API_FORMULA_UNKNOWN` |
| `LUA-API-008` | `API` | `REQ` | `mailbox_send` with valid payload and idempotency key | compile succeeds | n/a |
| `LUA-API-009` | `API` | `REQ` | `can_interact` with valid actor/object/action args | compile succeeds | n/a |
| `LUA-API-010` | `API` | `REQ` | `housing_place_item` with valid payload and idempotency key | compile succeeds | n/a |
| `LUA-API-011` | `API` | `REQ` | `ai_set_state` with valid npc id and state id | compile succeeds | n/a |
| `LUA-API-012` | `API` | `REQ` | `craft_execute` with valid recipe id and idempotency key | compile succeeds | n/a |
| `LUA-API-013` | `API` | `REQ` | `craft_execute` with unknown recipe id | compile fails | `LUA_API_CRAFTING_POLICY_VIOLATION` |
| `LUA-API-014` | `API` | `REQ` | `cast_spell` with valid spell id, target, and variant | compile succeeds | n/a |
| `LUA-API-015` | `API` | `REQ` | `cast_spell` with unknown spell id | compile fails | `LUA_API_SPELL_POLICY_VIOLATION` |
| `LUA-API-016` | `API` | `REQ` | `activate_skill` with unknown skill id | compile fails | `LUA_API_SKILL_POLICY_VIOLATION` |
| `LUA-API-017` | `API` | `REQ` | `talent_allocate` with valid talent id and idempotency key | compile succeeds | n/a |
| `LUA-API-018` | `API` | `REQ` | `talent_allocate` with unknown talent id | compile fails | `LUA_API_TALENT_POLICY_VIOLATION` |
| `LUA-API-019` | `API` | `REQ` | `party_create` with valid leader and idempotency key | compile succeeds | n/a |
| `LUA-API-020` | `API` | `REQ` | `party_invite` with unknown party id | compile fails | `LUA_API_PARTY_POLICY_VIOLATION` |
| `LUA-API-021` | `API` | `REQ` | `raid_assign_subgroup` with out-of-range subgroup | compile fails | `LUA_API_RAID_POLICY_VIOLATION` |
| `LUA-API-022` | `API` | `REQ` | `pvp_queue_join` with valid queue id and idempotency key | compile succeeds | n/a |
| `LUA-API-023` | `API` | `REQ` | `pvp_report_result` with unknown match id | compile fails | `LUA_API_PVP_POLICY_VIOLATION` |
| `LUA-CONTEXT-001` | `CONTEXT` | `REQ` | `spend_resource` in `edge` rule | compile fails | `LUA_API_CONTEXT_FORBIDDEN` |
| `LUA-CONTEXT-002` | `CONTEXT` | `REQ` | `emit_hard_event` in `arbiter` rule | compile fails | `LUA_API_CONTEXT_FORBIDDEN` |
| `LUA-CONTEXT-003` | `CONTEXT` | `REQ` | durable helper in `meta` rule with idempotency key | compile succeeds | n/a |
| `LUA-CONTEXT-004` | `CONTEXT` | `REQ` | non-continuous intent rule without terminal outcome | compile fails | `LUA_PROFILE_CONTEXT_POLICY_VIOLATION` |
| `LUA-CONTEXT-005` | `CONTEXT` | `REQ` | `mailbox_send` in `arbiter` rule | compile fails | `LUA_API_CONTEXT_FORBIDDEN` |
| `LUA-CONTEXT-006` | `CONTEXT` | `REQ` | `housing_place_item` in `arbiter` rule | compile fails | `LUA_API_CONTEXT_FORBIDDEN` |
| `LUA-CONTEXT-007` | `CONTEXT` | `REQ` | `interact_object` in `edge` rule | compile fails | `LUA_API_CONTEXT_FORBIDDEN` |
| `LUA-CONTEXT-008` | `CONTEXT` | `REQ` | `ai_set_state` in `meta` rule | compile fails | `LUA_API_CONTEXT_FORBIDDEN` |
| `LUA-CONTEXT-009` | `CONTEXT` | `REQ` | `craft_execute` in `arbiter` rule | compile fails | `LUA_API_CONTEXT_FORBIDDEN` |
| `LUA-CONTEXT-010` | `CONTEXT` | `REQ` | `cast_spell` in `meta` rule | compile fails | `LUA_API_CONTEXT_FORBIDDEN` |
| `LUA-CONTEXT-011` | `CONTEXT` | `REQ` | `activate_skill` in `edge` rule | compile fails | `LUA_API_CONTEXT_FORBIDDEN` |
| `LUA-CONTEXT-012` | `CONTEXT` | `REQ` | `talent_allocate` in `arbiter` rule | compile fails | `LUA_API_CONTEXT_FORBIDDEN` |
| `LUA-CONTEXT-013` | `CONTEXT` | `REQ` | `skill_grant_xp` in `arbiter` rule | compile fails | `LUA_API_CONTEXT_FORBIDDEN` |
| `LUA-CONTEXT-014` | `CONTEXT` | `REQ` | `party_join` in `arbiter` rule | compile fails | `LUA_API_CONTEXT_FORBIDDEN` |
| `LUA-CONTEXT-015` | `CONTEXT` | `REQ` | `raid_assign_subgroup` in `edge` rule | compile fails | `LUA_API_CONTEXT_FORBIDDEN` |
| `LUA-CONTEXT-016` | `CONTEXT` | `REQ` | `pvp_queue_join` in `arbiter` rule | compile fails | `LUA_API_CONTEXT_FORBIDDEN` |
| `LUA-CONTEXT-017` | `CONTEXT` | `REQ` | `pvp_report_result` in `arbiter` rule | compile fails | `LUA_API_CONTEXT_FORBIDDEN` |
| `LUA-DET-001` | `DETERMINISM` | `REQ` | `math.random` in `arbiter` path | compile fails | `LUA_PROFILE_DETERMINISM_VIOLATION` |
| `LUA-DET-002` | `DETERMINISM` | `REQ` | `os.time` in `arbiter` path | compile fails | `LUA_PROFILE_DETERMINISM_VIOLATION` |
| `LUA-DET-003` | `DETERMINISM` | `REQ` | unordered `pairs()` drives mutation order | compile fails | `LUA_PROFILE_DETERMINISM_VIOLATION` |
| `LUA-DET-004` | `DETERMINISM` | `REQ` | canonical sort helper used before deterministic iteration | compile succeeds | n/a |
| `LUA-DET-005` | `DETERMINISM` | `REQ` | formula definition uses nondeterministic op | compile fails | `LUA_PROFILE_DETERMINISM_VIOLATION` |
| `LUA-DET-006` | `DETERMINISM` | `REQ` | AI transition depends on unordered target iteration | compile fails | `LUA_PROFILE_DETERMINISM_VIOLATION` |
| `LUA-DET-007` | `DETERMINISM` | `REQ` | spell target list iterated via unordered `pairs()` before `cast_spell` effect fan-out | compile fails | `LUA_PROFILE_DETERMINISM_VIOLATION` |
| `LUA-DET-008` | `DETERMINISM` | `REQ` | raid subgroup list iterated via unordered `pairs()` before deterministic encounter scaling | compile fails | `LUA_PROFILE_DETERMINISM_VIOLATION` |
| `LUA-BOUNDS-001` | `BOUNDS` | `REQ` | selector helper missing `max_targets` literal | compile fails | `LUA_API_UNBOUNDED_SELECTOR` |
| `LUA-BOUNDS-002` | `BOUNDS` | `REQ` | selector `max_targets` exceeds profile cap | compile fails | `LUA_API_UNBOUNDED_SELECTOR` |
| `LUA-BOUNDS-003` | `BOUNDS` | `REQ` | mutations count exceeds `max_mutations_per_rule` | compile fails | `LUA_API_MUTATION_BUDGET_EXCEEDED` |
| `LUA-BOUNDS-004` | `BOUNDS` | `REQ` | emits count exceeds `max_internal_emits_per_rule` | compile fails | `LUA_API_EMIT_BUDGET_EXCEEDED` |
| `LUA-BOUNDS-005` | `BOUNDS` | `REQ` | required bounds profile key absent | compile fails | `LUA_PROFILE_UNBOUNDED_EXECUTION_RISK` |
| `LUA-BOUNDS-006` | `BOUNDS` | `REQ` | formula op count exceeds `max_formula_ops_per_eval` | compile fails | `LUA_API_FORMULA_UNBOUNDED` |
| `LUA-BOUNDS-007` | `BOUNDS` | `REQ` | stat modifier count exceeds `max_stat_modifiers_per_entity` | compile fails | `LUA_API_STAT_MODIFIER_BUDGET_EXCEEDED` |
| `LUA-BOUNDS-008` | `BOUNDS` | `REQ` | mailbox attachments exceed `max_mail_attachments_per_message` | compile fails | `LUA_API_MAILBOX_POLICY_VIOLATION` |
| `LUA-BOUNDS-009` | `BOUNDS` | `REQ` | terrain query count exceeds `max_terrain_queries_per_rule` | compile fails | `LUA_API_TERRAIN_QUERY_BUDGET_EXCEEDED` |
| `LUA-BOUNDS-010` | `BOUNDS` | `REQ` | interactions exceed `max_interactions_per_rule` | compile fails | `LUA_API_INTERACTION_POLICY_VIOLATION` |
| `LUA-BOUNDS-011` | `BOUNDS` | `REQ` | housing placements exceed `max_housing_items_per_plot` | compile fails | `LUA_API_HOUSING_POLICY_VIOLATION` |
| `LUA-BOUNDS-012` | `BOUNDS` | `REQ` | AI state transitions exceed `max_ai_state_transitions_per_rule` | compile fails | `LUA_API_AI_BUDGET_EXCEEDED` |
| `LUA-BOUNDS-013` | `BOUNDS` | `REQ` | recipe ingredient entries exceed `max_recipe_ingredient_entries` | compile fails | `LUA_API_CRAFTING_BUDGET_EXCEEDED` |
| `LUA-BOUNDS-014` | `BOUNDS` | `REQ` | craft queue ops exceed `max_craft_queue_ops_per_rule` | compile fails | `LUA_API_CRAFTING_BUDGET_EXCEEDED` |
| `LUA-BOUNDS-015` | `BOUNDS` | `REQ` | spell effect ops exceed `max_spell_effect_ops_per_cast` | compile fails | `LUA_API_SPELL_BUDGET_EXCEEDED` |
| `LUA-BOUNDS-016` | `BOUNDS` | `REQ` | skill activations exceed `max_skill_activations_per_rule` | compile fails | `LUA_API_SKILL_BUDGET_EXCEEDED` |
| `LUA-BOUNDS-017` | `BOUNDS` | `REQ` | talent mutations exceed `max_talent_mutations_per_rule` | compile fails | `LUA_API_TALENT_BUDGET_EXCEEDED` |
| `LUA-BOUNDS-018` | `BOUNDS` | `REQ` | skill xp grants exceed `max_skill_xp_grants_per_rule` | compile fails | `LUA_API_SKILL_BUDGET_EXCEEDED` |
| `LUA-BOUNDS-019` | `BOUNDS` | `REQ` | party mutations exceed `max_party_mutations_per_rule` | compile fails | `LUA_API_PARTY_BUDGET_EXCEEDED` |
| `LUA-BOUNDS-020` | `BOUNDS` | `REQ` | raid mutations exceed `max_raid_mutations_per_rule` | compile fails | `LUA_API_RAID_BUDGET_EXCEEDED` |
| `LUA-BOUNDS-021` | `BOUNDS` | `REQ` | pvp queue ops exceed `max_pvp_queue_ops_per_rule` | compile fails | `LUA_API_PVP_BUDGET_EXCEEDED` |
| `LUA-BOUNDS-022` | `BOUNDS` | `REQ` | pvp result reports exceed `max_pvp_result_reports_per_rule` | compile fails | `LUA_API_PVP_BUDGET_EXCEEDED` |
| `LUA-IR-001` | `IR_EQUIV` | `REQ` | same Lua source compiled twice | identical IR snapshot hash | n/a |
| `LUA-IR-002` | `IR_EQUIV` | `REQ` | semantically equivalent source with reordered declarations | identical normalized IR snapshot hash | n/a |
| `LUA-IR-003` | `IR_EQUIV` | `REQ` | equivalent Lua and YAML rule definitions | identical normalized IR snapshot hash | n/a |
| `LUA-IR-004` | `IR_EQUIV` | `REQ` | fixed literals in variant textual forms | identical normalized numeric IR values | n/a |
| `LUA-DIAG-001` | `DIAG` | `REQ` | single deterministic violation | one primary diagnostic with stable code | `LUA_PROFILE_DETERMINISM_VIOLATION` |
| `LUA-DIAG-002` | `DIAG` | `REQ` | multiple violations in one file | stable ordering of primary/secondary diagnostics | deterministic diagnostic set |
| `LUA-DIAG-003` | `DIAG` | `REQ` | failed compile | diagnostics include source span and symbol/rule id | deterministic diagnostic shape |

## 6. Cross-Run Stability Requirements

For every `REQ` success case:

1. compile artifact hash MUST match across at least two repeated runs
2. emitted IR field ordering MUST be canonical
3. numeric normalization output MUST be identical

For every `REQ` failure case:

1. primary diagnostic code MUST be stable
2. source span mapping MUST be stable for unchanged input
3. additional diagnostics MAY differ only if explicitly documented by compiler
   policy

## 7. Required Fixture Packs

Implementations MUST maintain at least:

1. `fixtures/lua/pass/` for required positive tests
2. `fixtures/lua/fail/` for required negative tests
3. `fixtures/lua/equivalence/` for IR-equivalence tests
4. `fixtures/lua/profile-bounds/` for budget/cap scenarios

Fixture naming SHOULD include test id prefixes (for example:
`LUA-API-003-wrong-arg-type.lua`).

## 8. Release Gating Policy

A compiler release that changes Lua profile behavior MUST:

1. run the full required matrix
2. publish pass/fail summary by test id
3. fail release gating if any `REQ` case regresses
4. include explicit migration notes if diagnostic classes or rule semantics
   changed

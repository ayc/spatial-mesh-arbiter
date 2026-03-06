# Designer Language v0.1 (Grammar Spec)

This document defines the first formal grammar and semantics contract for the
designer-facing game definition language.

Keywords **MUST**, **MUST NOT**, **SHOULD**, and **MAY** are normative.

## 1. Scope

This language is a declarative authoring surface for game semantics that
compile into runtime artifacts compatible with `docs-core/`.

It is not a general-purpose programming language.

## 2. Design Goals

1. Be readable by non-engineers.
2. Encode game rules without requiring engine internals knowledge.
3. Expose execution placement (`edge`, `arbiter`, `meta`) to avoid anti-patterns.
4. Compile deterministically and fail closed on unsafe constructs.

## 3. Source Model

### 3.1 File Format

1. Canonical contract format is semantic IR, not raw source text.
2. A Lua-subset authoring profile SHOULD be the primary designer-facing surface
   (`01-1-lua-subset-profile.md`).
3. YAML and JSON MAY be used as alternate authoring or interchange formats.
4. All accepted front-end syntaxes MUST canonicalize to equivalent semantic IR
   before compatibility checks and image emission.

### 3.2 Module Layout

A game definition consists of modules:

1. `entities`
2. `intents`
3. `rules`
4. `events`
5. `tables`
6. `states` (optional state machines for NPC/system flows)

## 4. Execution Context Semantics

Every rule MUST declare one execution context:

1. `edge`: pre-validation and non-authoritative screening.
2. `arbiter`: authoritative deterministic simulation.
3. `meta`: durable business workflow processing.

Context restrictions:

1. `arbiter` rules MUST satisfy strict determinism and boundedness.
2. `edge` rules MUST NOT emit durable commits directly.
3. `meta` rules MUST use explicit durable event semantics and idempotency keys.

## 5. Type System (v0.1)

Primitive types:

1. `bool`
2. `int`
3. `fixed`
4. `string`
5. `id`
6. `enum<T>`

Composite types:

1. `list<T>` (bounded max length required)
2. `map<K,V>` (bounded key domain required for authoritative paths)
3. `record` (named fields)

Numeric rules:

1. Authoritative numeric behavior MUST compile to `docs-core/01-spatial-runtime-kernel.md` numeric semantics.
2. Floating-point authoring literals MAY be accepted, but compiler MUST normalize to canonical fixed/int representation before emission.

## 6. Grammar (EBNF)

```ebnf
game_def         = header, { module } ;
header           = "game", ident, "version", semver ;

module           = entities_mod
                 | intents_mod
                 | rules_mod
                 | events_mod
                 | tables_mod
                 | states_mod ;

entities_mod     = "entities", "{", { entity_decl }, "}" ;
entity_decl      = "entity", ident, "{", { field_decl }, "}" ;
field_decl       = ident, ":", type_ref, [ "=" , literal ], ";" ;

intents_mod      = "intents", "{", { intent_decl }, "}" ;
intent_decl      = "intent", ident, "{",
                   "id", "=", int_lit, ";",
                   "lane", "=", lane_lit, ";",
                   "payload", "=", type_ref, ";",
                   "}", ;

rules_mod        = "rules", "{", { rule_decl }, "}" ;
rule_decl        = "rule", ident, "{",
                   "context", "=", context_lit, ";",
                   "on", trigger_decl, ";",
                   [ "validate", block ],
                   [ "apply", block ],
                   [ "emit", block ],
                   "outcome", outcome_decl, ";",
                   "}" ;

trigger_decl     = "intent" "(" ident ")"
                 | "event" "(" ident ")"
                 | "tick" "(" ident ")" ;

block            = "{", { stmt }, "}" ;
stmt             = assign_stmt | call_stmt | if_stmt | reject_stmt ;
assign_stmt      = path, "=", expr, ";" ;
call_stmt        = ident, "(", [ arg_list ], ")", ";" ;
if_stmt          = "if", "(", expr, ")", block, [ "else", block ] ;
reject_stmt      = "reject", "(", reject_code, ")", ";" ;

events_mod       = "events", "{", { event_decl }, "}" ;
event_decl       = "event", ident, "{", { field_decl }, "}" ;

tables_mod       = "tables", "{", { table_decl }, "}" ;
table_decl       = "table", ident, "{", schema_decl, rows_decl, "}" ;

states_mod       = "states", "{", { state_machine_decl }, "}" ;
state_machine_decl = "machine", ident, "{", { state_decl }, { transition_decl }, "}" ;
```

Note: this EBNF describes the canonical semantic model. Source syntax MAY be
Lua-subset, YAML, or JSON so long as canonicalized IR behavior is equivalent.

## 7. Statement Semantics

### 7.1 `validate` Block

1. Contains predicate expressions and safe helper calls.
2. Failure MUST produce deterministic reject path.

### 7.2 `apply` Block

1. Contains bounded mutation intents.
2. Mutations are declarative and compile to adapter-compatible `mutations` payloads.

### 7.3 `emit` Block

1. Produces internal events and/or durable events according to context policy.
2. `arbiter` emits MUST remain idempotent-safe across retries/replay.

### 7.4 `outcome`

1. Every non-continuous intent rule MUST define explicit terminal outcome behavior.
2. Terminal outcome semantics MUST align with `docs-core/02-spatial-messaging-plane.md`.

## 8. Forbidden Constructs (Compile Errors)

1. unbounded loops
2. recursion
3. wall-clock reads in authoritative paths
4. host randomness in authoritative paths
5. dynamic code evaluation
6. network/disk I/O in authoritative rule bodies
7. non-deterministic map/set iteration affecting mutation order

## 9. Compiler Diagnostics Contract

Compiler MUST classify language errors at least as:

1. `SCHEMA_ERROR`
2. `TYPE_ERROR`
3. `DETERMINISM_VIOLATION`
4. `UNBOUNDED_EXECUTION_RISK`
5. `CONTEXT_POLICY_VIOLATION`
6. `COMPATIBILITY_VIOLATION`

## 10. Minimal Authoring Example (YAML Form)

```yaml
game: "arpg-template"
version: "0.1.0"

intents:
  - name: "ability.cast_targeted"
    id: 0x0110
    lane: SIMULATION
    payload: CastTargetedPayload

rules:
  - name: "fireball.cast"
    context: arbiter
    on:
      intent: "ability.cast_targeted"
    validate:
      - cooldown_ready(caster, "fireball")
      - resource_at_least(caster, "mana", fixed("30.0"))
      - distance_leq(caster, target, fixed("40.0"))
    apply:
      - spend_resource(caster, "mana", fixed("30.0"))
      - spawn_projectile(projectile_id: "fireball_basic", speed: fixed("18.0"))
    outcome:
      accept: true
      reject_code: OUT_OF_RANGE
```

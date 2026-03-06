# Lua Subset Profile v0.1

This document defines an optional Lua-like authoring profile for the designer
language in `01-designer-language.md`.

Keywords **MUST**, **MUST NOT**, **SHOULD**, and **MAY** are normative.

## 1. Scope and Positioning

1. This profile is an authoring front-end only.
2. Lua source accepted under this profile MUST compile to the same canonical IR
   used by YAML/JSON inputs.
3. Engine runtime nodes MUST NOT execute arbitrary Lua source directly.

## 2. Design Goals

1. Preserve familiar Lua syntax for designers.
2. Enforce deterministic and bounded execution for authoritative paths.
3. Fail closed at compile time for unsupported or unsafe constructs.

## 3. Compilation Model

1. Source files are statically parsed and type-checked.
2. Compiler resolves symbols and context placement (`edge`, `arbiter`, `meta`)
   before code generation.
3. Output is IR/game image artifacts; no source interpretation in production.
4. Conformance tests for this profile are defined in
   `01-3-lua-conformance-test-matrix.md`.

## 4. Supported Lua Surface (v0.1)

### 4.1 Core Syntax

1. `local` declarations and assignments.
2. `if` / `elseif` / `else`.
3. function declarations with named parameters.
4. table literals for declarative data blocks.
5. `return` statements.

### 4.2 Rule Definition Shape

1. Rules MUST declare:
   1. stable rule id/name
   2. execution context
   3. trigger (`intent`, `event`, or `tick`)
2. Rules MAY include `validate`, `apply`, and `emit` functions.
3. Every terminal intent rule MUST declare explicit outcome/reject behavior.

### 4.3 Allowed Standard Helpers

1. Only symbols defined in `01-2-lua-whitelisted-api.md` MAY be called.
2. Helper calls MUST be context-valid (`edge`, `arbiter`, `meta`).
3. Unknown helper calls MUST fail compilation.

## 5. Forbidden Language Features (Compile Errors)

1. `while` loops.
2. `repeat ... until` loops.
3. `goto` and labels.
4. recursion (direct or indirect).
5. dynamic code loading (`load`, `loadfile`, `dofile`, `string.dump`).
6. module loading (`require`, `package.*`) in game rule source.
7. metatables (`setmetatable`, `getmetatable`, metamethod definitions).
8. coroutines.
9. arbitrary global writes.
10. non-whitelisted standard libraries.

## 6. Determinism and Boundedness Constraints

1. Authoritative (`arbiter`) rules MUST be deterministic across replays.
2. Host time and randomness APIs MUST NOT be used in authoritative paths.
3. Table iteration order MUST be explicit:
   1. unordered `pairs()` MUST NOT drive mutation order
   2. ordered iteration MUST use canonical sort helpers
4. Numeric values in authoritative paths MUST compile to fixed/int semantics.
5. Any per-invocation work MUST be bounded by compile-time or schema-visible
   limits.

## 7. Context Policy Rules

1. `edge`:
   1. MAY run screening/validation helpers
   2. MUST NOT emit durable commits directly
2. `arbiter`:
   1. MAY perform authoritative state transitions
   2. MUST satisfy deterministic and bounded execution constraints
3. `meta`:
   1. MAY perform durable business workflows
   2. MUST include idempotency semantics for durable actions

## 8. Minimal Profile Grammar (Informative)

```ebnf
rule_file       = { rule_decl } ;
rule_decl       = "rule", "(", string_lit, ")", block ;
block           = "do", { stmt }, "end" ;
stmt            = assign_stmt
                | if_stmt
                | fn_decl
                | call_stmt
                | return_stmt ;
fn_decl         = "function", ident, "(", [ param_list ], ")", block ;
if_stmt         = "if", expr, "then", block, { "elseif", expr, "then", block },
                  [ "else", block ], "end" ;
```

Note: this is a profile sketch. The parser contract is defined by compiler
implementation and conformance tests.

## 9. Diagnostics Contract

Compiler MUST classify profile errors at least as:

1. `LUA_PROFILE_PARSE_ERROR`
2. `LUA_PROFILE_UNSUPPORTED_FEATURE`
3. `LUA_PROFILE_FORBIDDEN_API`
4. `LUA_PROFILE_DETERMINISM_VIOLATION`
5. `LUA_PROFILE_UNBOUNDED_EXECUTION_RISK`
6. `LUA_PROFILE_CONTEXT_POLICY_VIOLATION`

## 10. Example (Allowed Shape)

```lua
rule("fireball.cast") do
  context("arbiter")
  on_intent("ability.cast_targeted")

  function validate(ctx)
    require_predicate(cooldown_ready(ctx.caster, "fireball"), "COOLDOWN")
    require_predicate(resource_at_least(ctx.caster, "mana", fixed("30.0")), "NO_MANA")
    require_predicate(distance_leq(ctx.caster, ctx.target, fixed("40.0")), "OUT_OF_RANGE")
  end

  function apply(ctx)
    spend_resource(ctx.caster, "mana", fixed("30.0"))
    spawn_projectile("fireball_basic", fixed("18.0"))
  end

  outcome_accept()
end
```

## 11. Example (Rejected)

```lua
rule("bad.rule") do
  context("arbiter")
  function apply(ctx)
    while true do
      local n = math.random()
      mutate(ctx, n)
    end
  end
end
```

Expected compile failures:

1. unbounded loop
2. forbidden randomness in authoritative path

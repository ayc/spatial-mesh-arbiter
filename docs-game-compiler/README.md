# Game Compiler Framework

This directory defines a designer-facing game definition model and compiler contract
that targets the engine contracts in `docs-core/`.

## Purpose

- Allow non-engineers to author game behavior in bounded data/DSL form.
- Compile authored content into deterministic runtime artifacts.
- Keep game business logic decoupled from engine runtime internals.

## Precedence

1. `docs-core/` is authoritative for engine/runtime contracts.
2. `docs-game-compiler/` is authoritative for game-definition/compiler contracts.
3. `docs/` is an implementation/reference layer (ARPG template today).

If this directory conflicts with `docs-core/`, `docs-core/` wins.

## Document Index

1. [00-scope-and-principles.md](00-scope-and-principles.md)
2. [01-designer-language.md](01-designer-language.md)
3. [01-1-lua-subset-profile.md](01-1-lua-subset-profile.md)
4. [01-2-lua-whitelisted-api.md](01-2-lua-whitelisted-api.md)
5. [01-3-lua-conformance-test-matrix.md](01-3-lua-conformance-test-matrix.md)
6. [02-schema-and-validation.md](02-schema-and-validation.md)
7. [03-compiler-pipeline.md](03-compiler-pipeline.md)
8. [04-game-image-format.md](04-game-image-format.md)
9. [05-runtime-loading-and-activation.md](05-runtime-loading-and-activation.md)
10. [06-version-line-cutover-and-rollback.md](06-version-line-cutover-and-rollback.md)
11. [07-tooling-workflow.md](07-tooling-workflow.md)
12. [08-sdk-catalog-wishlist.md](08-sdk-catalog-wishlist.md)
13. [09-sdk-surface-draft.md](09-sdk-surface-draft.md)

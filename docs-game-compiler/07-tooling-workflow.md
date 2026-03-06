# Tooling Workflow

## 1. Roles

1. Designers author gameplay content and rules.
2. Tools/Build systems compile content into game images.
3. Runtime operators stage and activate signed images.

## 2. Recommended Loop

1. author/edit content
2. run local validation and preview tests
3. compile image artifact
4. run conformance smoke checks
5. promote through PR, nightly, and release gates

## 3. Guardrails

1. Designers SHOULD not need to modify engine runtime code.
2. Runtime deploys SHOULD use immutable game images.
3. Emergency overrides MUST still respect version-line safety policy.

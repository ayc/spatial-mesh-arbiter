# Schema and Validation

Keywords **MUST**, **MUST NOT**, **SHOULD**, and **MAY** are normative.

## 1. Canonical Schema Rules

1. Every authorable type MUST have explicit schema versioning.
2. Required fields MUST be explicit and machine-validated.
3. Unknown required fields MUST fail validation.
4. Numeric fields that affect authoritative mutation MUST include scale semantics.

## 2. Validation Tiers

1. Structural validation: shape, types, required fields.
2. Semantic validation: references, constraints, enum domains.
3. Determinism validation: banned constructs, bounded execution, numeric normalization.
4. Compatibility validation: adapter API major and wire schema intersections.

## 3. Compile Gate

Compilation MUST fail if any required validation tier fails.

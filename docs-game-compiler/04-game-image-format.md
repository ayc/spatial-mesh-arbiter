# Game Image Format

Keywords **MUST**, **MUST NOT**, **SHOULD**, and **MAY** are normative.

## 1. Artifact Identity

Each emitted image MUST include:

1. `game_id`
2. `game_version`
3. `adapter_identity`
4. `adapter_api_major`
5. supported `wire_schema_versions`
6. content digest/checksum metadata

## 2. Image Sections

A game image MUST contain:

1. manifest section (identity and compatibility)
2. schema descriptors section
3. compiled gameplay data section
4. deterministic lookup/index section
5. optional diagnostics/debug metadata section

## 3. Integrity

1. Image integrity MUST be verifiable before activation.
2. Runtime MUST reject images with invalid digest/signature.

# Compiler Pipeline

Keywords **MUST**, **MUST NOT**, **SHOULD**, and **MAY** are normative.

## 1. Pipeline Stages

1. ingest authoring sources
2. parse and canonicalize inputs
3. run structural and semantic validation
4. run determinism and boundedness checks
5. normalize numeric/data representations
6. generate optimized runtime tables/indexes
7. emit signed game image artifact

## 2. Deterministic Build Requirements

1. Same inputs and toolchain version MUST produce byte-equivalent outputs.
2. Compiler MUST emit reproducible manifest metadata.
3. Non-deterministic build-time data (timestamps, host IDs) MUST be excluded from functional sections.

## 3. Outputs

1. game image package
2. build manifest and checksums
3. validation report and failure diagnostics

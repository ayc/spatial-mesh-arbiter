# Gemini — Project Instructions

> **Read `AGENTS.md` first.** It contains the full project context, architecture, engineering rules, and tracking guidelines that apply to all agents.

This file contains Gemini-specific additions only.

## Critical Rules for Gemini

1. **DO NOT SKIM OR HALLUCINATE ARCHITECTURE.** The high-level markdown files (e.g., `docs/README.md`) contain idealized summaries. The absolute source of truth is the Rust code and the internal contracts in `docs/2-contracts-and-interfaces/internal-mesh-types/`. If you do not read the structs, you will misunderstand the system.
2. **READ WHOLE FILES.** If you use a tool to read a file and it truncates, you MUST paginate through the rest of the file before drawing conclusions. Do not infer missing content.
3. **DO NOT INVENT STRUCT FIELDS OR ENUM VARIANTS.** If you are unsure whether a field exists, read the file. Never guess.

## Gemini-Specific Guidelines

- When proposing architectural changes, check `memory-bank/DECISIONS.md` for prior decisions and rationale before suggesting alternatives.
- When starting a session, read `memory-bank/SESSION_HANDOFF.md` for context from the previous session.

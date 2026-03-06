# Editorial Pipeline (Andrea → Marlin → Marek)

This pipeline is designed for the weekly cadence:

- Monday: Publish
- Tuesday: Research
- Wednesday: Publish
- Thursday: Research
- Friday: Publish
- Saturday: Research
- Sunday: Research

## Directories

- `research/` — handoff files prepared by **Andrea**
- `drafts/` — article drafts prepared by **Marlin**
- `final/` — final edited articles prepared by **Marek**
- `templates/` — markdown templates for each stage
- `state.json` — queue + status tracking

## File naming

Use consistent slug-based naming:

- Research: `YYYY-MM-DD-<slug>.research.md`
- Draft: `YYYY-MM-DD-<slug>.draft.md`
- Final: `YYYY-MM-DD-<slug>.final.md`

Example: `2026-03-10-zero-trust-for-ai-agents.research.md`

## Workflow

1. **Research day (Tue/Thu/Sat/Sun)**
   - Andrea picks the next queued topic from `state.json`.
   - Andrea writes research note using `templates/research-template.md`.
   - Andrea sets topic status to `researched` and writes `researchFile` path.

2. **Drafting**
   - Marlin picks a `researched` topic.
   - Marlin writes full draft using `templates/draft-template.md`.
   - Marlin sets status to `drafted` and writes `draftFile` path.

3. **Editing**
   - Marek picks a `drafted` topic.
   - Marek edits and finalizes with `templates/final-checklist.md`.
   - Marek sets status to `edited` and writes `finalFile` path.

4. **Publish day (Mon/Wed/Fri)**
   - Publish next `edited` topic into `_posts/YYYY-MM-DD-<slug>.md`.
   - Move/copy from `final/` to `_posts/`.
   - Set status to `published`.

## Status values

- `queued`
- `researched`
- `drafted`
- `edited`
- `published`
- `blocked`

## Coordination rule

Every stage must update `state.json` in the same commit as its content file.
This ensures Marlin can always pick up Andrea's latest research without ambiguity.

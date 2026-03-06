# Agents Playbook

This is the operational contract so everyone knows what to do without ad-hoc coordination.

## Roles

- **Andrea** = research owner
- **Marlin** = drafting owner
- **Marek** = editing owner

## Daily source of truth

1. `automation/pipeline/daily/YYYY-MM-DD.md`
2. `automation/pipeline/state.json`

If these conflict, update `state.json` first and regenerate daily task.

## Handoff contract

- Andrea outputs: `research/*.research.md`
- Marlin outputs: `drafts/*.draft.md`
- Marek outputs: `final/*.final.md`
- Publish output: `_posts/YYYY-MM-DD-slug.md`

Each stage must update `state.json` in the same commit.

## Minimum quality bar by role

### Andrea
- At least 3 credible sources
- Specific angle, not generic summary
- Practical security implications

### Marlin
- Full article draft from research handoff
- Concrete examples/checklists
- No invented references

### Marek
- Clarity, flow, consistency
- Tighten title + intro
- Final readiness checklist complete

## Status transitions

`queued -> researched -> drafted -> edited -> published`

Allowed exception:
- Any stage can set `blocked` with a short reason in commit message.

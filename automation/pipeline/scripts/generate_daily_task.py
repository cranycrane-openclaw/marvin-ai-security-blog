#!/usr/bin/env python3
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[3]
PIPELINE = ROOT / "automation" / "pipeline"
STATE_PATH = PIPELINE / "state.json"
DAILY_DIR = PIPELINE / "daily"
TIMEZONE = ZoneInfo("Europe/Prague")

CADENCE = {
    "monday": "publish",
    "tuesday": "research",
    "wednesday": "publish",
    "thursday": "research",
    "friday": "publish",
    "saturday": "research",
    "sunday": "research",
}

@dataclass
class Topic:
    id: str
    slug: str
    title: str
    status: str


def load_state() -> dict:
    with STATE_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)


def pick_next(topics: list[dict], statuses: tuple[str, ...]) -> Topic | None:
    for t in topics:
        if t.get("status") in statuses:
            return Topic(
                id=t.get("id", ""),
                slug=t.get("slug", ""),
                title=t.get("title", ""),
                status=t.get("status", ""),
            )
    return None


def render_research_task(date_str: str, topic: Topic | None) -> str:
    target = (
        f"- Topic: **{topic.title}** (`{topic.id}`, slug `{topic.slug}`)\n- Current status: `{topic.status}`"
        if topic
        else "- No queued topic found in `state.json` → Andrea should add 1-2 new queued topics first."
    )
    return f"""# Daily Editorial Task — {date_str}

Primary mode today: **RESEARCH** (Andrea lead)

## Main objective
Produce at least one complete research handoff in `automation/pipeline/research/`.

## Target topic
{target}

## Role responsibilities today

### Andrea (Research)
- Use `templates/research-template.md`
- Save as `research/YYYY-MM-DD-<slug>.research.md`
- Ensure at least 3 high-quality sources
- Update `state.json` (`status: researched`, `researchFile`, `updatedAt`)

### Marlin (Builder)
- Pick latest `researched` topic
- Start/continue draft in `drafts/YYYY-MM-DD-<slug>.draft.md`
- Update `state.json` if moving to `drafted`

### Marek (Editor)
- If any topic is `drafted`, run final polish using `templates/final-checklist.md`
- Move output to `final/YYYY-MM-DD-<slug>.final.md`
- Update `state.json` if moving to `edited`

## Definition of done
- [ ] New/updated research file exists
- [ ] `state.json` updated in same commit
- [ ] Pipeline remains consistent (no missing file paths)
"""


def render_publish_task(date_str: str, edited: Topic | None, drafted: Topic | None) -> str:
    if edited:
        target = f"- Ready to publish: **{edited.title}** (`{edited.id}`, slug `{edited.slug}`)"
    elif drafted:
        target = (
            f"- No `edited` topic available. Fast-track edit for: **{drafted.title}** "
            f"(`{drafted.id}`, slug `{drafted.slug}`)"
        )
    else:
        target = "- No `edited`/`drafted` topics available. Priority: create and edit one article from researched queue."

    return f"""# Daily Editorial Task — {date_str}

Primary mode today: **PUBLISH** (Marlin + Marek lead)

## Main objective
Publish one article to `_posts/YYYY-MM-DD-<slug>.md`.

## Target topic
{target}

## Role responsibilities today

### Marlin (Builder)
- If needed, finish draft from `drafts/`
- Ensure technical accuracy and practical recommendations
- Keep front matter compatible with Jekyll

### Marek (Editor)
- Final pass with `templates/final-checklist.md`
- Produce `final/YYYY-MM-DD-<slug>.final.md`
- Confirm readability + SEO/meta quality

### Andrea (Research)
- Refill queue if `queued` topics < 3
- Add at least one new topic proposal into `state.json` when backlog is thin

## Publish steps
- Copy finalized article into `_posts/YYYY-MM-DD-<slug>.md`
- Update `state.json` (`status: published`, `publishedPost`, `updatedAt`)
- Commit with clear message (e.g., `Publish: <title>`)

## Definition of done
- [ ] One new `_posts/` article committed
- [ ] `state.json` marked `published`
- [ ] Backlog health checked (next topics available)
"""


def main() -> None:
    DAILY_DIR.mkdir(parents=True, exist_ok=True)

    state = load_state()
    topics = state.get("topics", [])

    now = datetime.now(TIMEZONE)
    date_str = now.date().isoformat()
    weekday = now.strftime("%A").lower()
    mode = CADENCE.get(weekday, "research")

    queued = pick_next(topics, ("queued",))
    edited = pick_next(topics, ("edited",))
    drafted = pick_next(topics, ("drafted",))

    if mode == "research":
        content = render_research_task(date_str, queued)
    else:
        content = render_publish_task(date_str, edited, drafted)

    out_path = DAILY_DIR / f"{date_str}.md"
    out_path.write_text(content, encoding="utf-8")
    print(f"Generated {out_path}")


if __name__ == "__main__":
    main()

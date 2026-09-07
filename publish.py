#!/usr/bin/env python3
"""Render the AI brief archive from Victor's markdown.

Victor writes one file per briefing into his own workspace and never touches
this repo — same separation as the MCP servers being pure HTTP clients. This
script is the only thing that writes HTML.

    ./publish.py                 # render from the default source dir
    ./publish.py --source DIR    # render from somewhere else
    ./publish.py --check         # parse only, write nothing (CI / pre-commit)

Source format — one file per brief, `YYYY-MM-DD.md`:

    ---
    date: 2026-09-07
    time: 16:43 CEST
    title: Consolidation, scrutiny, and a warning from inside
    lead: One or two sentences under the headline.
    sources: X/Twitter home feed via profile=brahim, plus @karpathy.
    ---

    ## Nvidia confirms it is acquiring Hugging Face
    story: nvidia-hugging-face
    signal: the open-model hub is about to have one very large owner.
    source: https://blogs.nvidia.com/blog/nvidia-to-acquire-hugging-face

    Body prose. Blank-line separated paragraphs.

    ## Scrutiny catches up with the Astra launch
    story: gpt-6-astra
    angle: new
    signal: the pushback is now as much of the story as the demos.

    Body prose.

    # Worth watching
    - A short item.
    - Another.

    # Bottom line
    One or two sentences.

`story:` is what makes running stories work: two briefs carrying the same slug
become one story page with a timeline, and the brief links there instead of
re-explaining the story. `angle: new` marks the entry that carried something
genuinely new — everything else in a repeat story is a restatement.
"""

from __future__ import annotations

import argparse
import html
import re
import sys
from dataclasses import dataclass, field
from datetime import date as Date
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DEFAULT_SOURCE = Path.home() / "Server/agents/openclaw/victor/briefs"

FONTS = (
    '<link rel="preconnect" href="https://fonts.googleapis.com">\n'
    '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>\n'
    '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?'
    "family=Archivo:wght@700;800&family=Source+Serif+4:ital,wght@0,400;0,600;1,400"
    '&family=IBM+Plex+Mono:wght@400;500&display=swap">'
)

ITEM_KEYS = {"story", "signal", "source", "angle"}


class BriefError(ValueError):
    """A source file that cannot be rendered. Never guess past one."""


@dataclass
class Item:
    title: str
    body: list[str] = field(default_factory=list)
    story: str | None = None
    signal: str | None = None
    source: str | None = None
    angle: str | None = None

    @property
    def is_new_angle(self) -> bool:
        return (self.angle or "").strip().lower() == "new"


@dataclass
class Brief:
    date: Date
    title: str
    lead: str
    time: str = ""
    sources: str = ""
    items: list[Item] = field(default_factory=list)
    watching: list[str] = field(default_factory=list)
    bottom_line: str = ""

    @property
    def slug(self) -> str:
        return self.date.isoformat()

    @property
    def stamp(self) -> str:
        return self.date.strftime("%b %d %Y").upper()


# ---------------------------------------------------------------- parsing


def _split_front_matter(text: str, path: Path) -> tuple[dict[str, str], str]:
    if not text.startswith("---"):
        raise BriefError(f"{path.name}: missing --- front matter block")
    try:
        _, raw, body = text.split("---", 2)
    except ValueError as exc:
        raise BriefError(f"{path.name}: front matter is not closed by ---") from exc
    meta: dict[str, str] = {}
    for line in raw.strip().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" not in line:
            raise BriefError(f"{path.name}: front matter line is not key: value -> {line!r}")
        key, _, value = line.partition(":")
        meta[key.strip().lower()] = value.strip().strip('"')
    return meta, body


def parse_brief(path: Path) -> Brief:
    meta, body = _split_front_matter(path.read_text(encoding="utf-8"), path)

    for required in ("date", "title"):
        if not meta.get(required):
            raise BriefError(f"{path.name}: front matter needs a {required}:")
    try:
        when = Date.fromisoformat(meta["date"])
    except ValueError as exc:
        raise BriefError(f"{path.name}: date must be YYYY-MM-DD, got {meta['date']!r}") from exc

    brief = Brief(
        date=when,
        title=meta["title"],
        lead=meta.get("lead", ""),
        time=meta.get("time", ""),
        sources=meta.get("sources", ""),
    )

    section = None  # None | "watching" | "bottom"
    item: Item | None = None

    for line in body.splitlines():
        stripped = line.strip()

        if stripped.startswith("## "):
            item = Item(title=stripped[3:].strip())
            brief.items.append(item)
            section = None
            continue

        if stripped.startswith("# "):
            heading = stripped[2:].strip().lower()
            item = None
            if heading.startswith("worth"):
                section = "watching"
            elif heading.startswith("bottom"):
                section = "bottom"
            else:
                raise BriefError(
                    f"{path.name}: unknown section {stripped!r} "
                    "(expected '# Worth watching' or '# Bottom line')"
                )
            continue

        if section == "watching":
            if stripped.startswith("- "):
                brief.watching.append(stripped[2:].strip())
            continue

        if section == "bottom":
            if stripped:
                brief.bottom_line = (brief.bottom_line + " " + stripped).strip()
            continue

        if item is None:
            continue

        key_match = re.match(r"^([a-z]+):\s*(.*)$", stripped)
        if key_match and key_match.group(1) in ITEM_KEYS and not item.body:
            setattr(item, key_match.group(1), key_match.group(2).strip())
            continue

        if stripped:
            if item.body and item.body[-1]:
                item.body[-1] = item.body[-1] + " " + stripped
            else:
                item.body.append(stripped)
        elif item.body and item.body[-1]:
            item.body.append("")

    for entry in brief.items:
        entry.body = [p for p in entry.body if p]
        if entry.source and not entry.source.startswith("http"):
            raise BriefError(
                f"{path.name}: source for {entry.title!r} is not a URL -> {entry.source!r}"
            )

    if not brief.items:
        raise BriefError(f"{path.name}: no '## ' story items found")
    return brief


def load_briefs(source: Path) -> list[Brief]:
    if not source.is_dir():
        raise BriefError(f"source directory does not exist: {source}")
    briefs = [parse_brief(p) for p in sorted(source.glob("*.md"))]
    if not briefs:
        raise BriefError(f"no *.md briefs in {source}")
    briefs.sort(key=lambda b: b.date, reverse=True)
    return briefs


# ---------------------------------------------------------------- stories


@dataclass
class Appearance:
    brief: Brief
    item: Item
    rank: int  # 1 = led the brief


@dataclass
class Story:
    slug: str
    title: str
    appearances: list[Appearance] = field(default_factory=list)

    @property
    def days(self) -> int:
        return len(self.appearances)

    @property
    def is_running(self) -> bool:
        return self.days >= 2

    @property
    def latest(self) -> Appearance:
        return max(self.appearances, key=lambda a: a.brief.date)


def collect_stories(briefs: list[Brief]) -> dict[str, Story]:
    stories: dict[str, Story] = {}
    for brief in briefs:
        for rank, item in enumerate(brief.items, start=1):
            if not item.story:
                continue
            story = stories.setdefault(item.story, Story(slug=item.story, title=item.title))
            story.appearances.append(Appearance(brief=brief, item=item, rank=rank))
    for story in stories.values():
        story.appearances.sort(key=lambda a: a.brief.date)
        story.title = story.latest.item.title
    return stories


# ---------------------------------------------------------------- rendering

E = html.escape


def page(title: str, description: str, depth: int, body: str) -> str:
    up = "../" * depth
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{E(title)}</title>
<meta name="description" content="{E(description)}">
{FONTS}
<link rel="stylesheet" href="{up}css/main.css">
</head>
<body>
<a class="skip-link" href="#main">Skip to content</a>

<header class="masthead">
  <div class="container masthead__inner">
    <p class="masthead__name"><a href="{up}index.html">AI BRIEF</a></p>
    <span class="masthead__tag">Wire archive &middot; brahim bousnguar</span>
  </div>
</header>
<hr class="tape">

<main id="main">
{body}
  <p class="end-mark">-30-</p>
</main>

<footer class="site-footer">
  <div class="container">
    <p style="margin:0"><a href="{up}index.html">&larr; All briefs</a></p>
  </div>
</footer>
</body>
</html>
"""


def timeline_svg(story: Story) -> str:
    """One mark per briefing. State is carried by shape, never colour alone."""
    n = len(story.appearances)
    # The lane label sits ABOVE the line, not beside it: a long story title
    # placed to the left runs into the first mark at any truncation length.
    left, right = 50, 520
    step = 0 if n < 2 else (right - left) / (n - 1)
    xs = [left + step * i for i in range(n)] if n > 1 else [left]

    ticks, marks = [], []
    for x, app in zip(xs, story.appearances):
        ticks.append(
            f'<text x="{x:.0f}" y="34">{E(app.brief.date.strftime("%b %d").upper())}</text>'
        )
        if app.item.is_new_angle:
            marks.append(
                f'<path d="M{x:.0f} 83 L{x + 12:.0f} 95 L{x:.0f} 107 L{x - 12:.0f} 95 Z" '
                f'fill="var(--embargo)"/>'
            )
        elif app.rank == 1:
            marks.append(f'<circle cx="{x:.0f}" cy="95" r="11" fill="var(--stamp)"/>')
        else:
            marks.append(
                f'<circle cx="{x:.0f}" cy="95" r="9" fill="var(--paper)" '
                f'stroke="var(--ink)" stroke-width="2"/>'
            )

    label = E(story.title[:52] + ("…" if len(story.title) > 52 else ""))
    return f"""<svg viewBox="0 0 560 150" role="img" aria-labelledby="tl-t tl-d">
<title id="tl-t">{E(story.title)} across {n} briefing{"s" if n != 1 else ""}</title>
<desc id="tl-d">One mark per briefing. Filled circles mark a lead slot, open circles a
mention, and a diamond marks an entry that carried a genuinely new angle.</desc>
<line x1="{left}" y1="46" x2="{right}" y2="46" stroke="var(--ink)" stroke-width="2"/>
<g font-family="IBM Plex Mono, monospace" font-size="12" fill="var(--ink)" text-anchor="middle">
{chr(10).join(ticks)}
</g>
<text x="{left}" y="74" font-family="Archivo, sans-serif" font-weight="700" font-size="13" fill="var(--ink)">{label}</text>
<line x1="{left}" y1="95" x2="{right}" y2="95" stroke="var(--ink)" stroke-width="1" stroke-dasharray="3 4"/>
{chr(10).join(marks)}
<g font-family="IBM Plex Mono, monospace" font-size="11" fill="var(--ink)">
<circle cx="16" cy="134" r="7" fill="var(--stamp)"/><text x="30" y="138">LED THE BRIEF</text>
<circle cx="170" cy="134" r="6" fill="var(--paper)" stroke="var(--ink)" stroke-width="2"/><text x="184" y="138">MENTIONED</text>
<path d="M320 126 L329 134 L320 142 L311 134 Z" fill="var(--embargo)"/><text x="336" y="138">NEW ANGLE</text>
</g>
</svg>"""


def render_brief(brief: Brief, stories: dict[str, Story]) -> str:
    dateline = [f"<span>AI BRIEF</span>", f"<span>{E(brief.stamp)}</span>"]
    if brief.time:
        dateline.append(f"<span>{E(brief.time.upper())}</span>")
    bar = '<span class="dateline__sep">&middot;</span>'.join(dateline)

    out = [
        '  <div class="band">\n    <div class="container">',
        f'      <p class="dateline">{bar}</p>',
        f"      <h1>{E(brief.title)}</h1>",
    ]
    if brief.lead:
        out.append(f'      <p class="lead">{E(brief.lead)}</p>')
    out.append("    </div>\n  </div>\n")

    out.append('  <div class="band">\n    <div class="container">\n      <h2>Top signal</h2>')
    for rank, item in enumerate(brief.items, start=1):
        klass = "story story--lead" if rank == 1 else "story"
        out.append(f'      <article class="{klass}">')
        out.append(f'        <span class="story__num">{rank:02d}</span>')

        story = stories.get(item.story or "")
        if story and story.is_running:
            tag = "new angle" if item.is_new_angle else f"running story &middot; day {story.days}"
            out.append(
                f'        <a class="daycount" href="../stories/{E(story.slug)}.html">{tag}</a>'
            )
        out.append(f'        <h3 class="story__title">{E(item.title)}</h3>')
        for para in item.body:
            out.append(f"        <p>{E(para)}</p>")
        if item.signal:
            out.append(
                f'        <p class="story__signal"><strong>Signal:</strong> {E(item.signal)}</p>'
            )
        if item.source:
            out.append(f'        <p class="story__source">Source: {E(item.source)}</p>')
        out.append("      </article>")
    out.append("    </div>\n  </div>\n")

    if brief.watching:
        out.append('  <div class="band band--wire">\n    <div class="container">')
        out.append('      <span class="slug">Worth watching</span>\n      <ul class="watch">')
        out.extend(f"        <li>{E(w)}</li>" for w in brief.watching)
        out.append("      </ul>\n    </div>\n  </div>\n")

    if brief.bottom_line or brief.sources:
        out.append('  <div class="band band--sunk">\n    <div class="container">')
        out.append('      <div class="cols cols--2">')
        out.append('        <div class="block block--paper">')
        out.append('          <span class="slug">Bottom line</span>')
        out.append(f'          <p class="lead" style="margin:0">{E(brief.bottom_line)}</p>')
        out.append("        </div>")
        out.append('        <div class="block block--fill">')
        out.append('          <span class="slug">Sources scanned</span>')
        out.append(
            f'          <p class="story__source" style="margin:0">{E(brief.sources)}</p>'
        )
        out.append("        </div>\n      </div>\n    </div>\n  </div>\n")

    return "\n".join(out)


def render_story(story: Story) -> str:
    out = [
        '  <div class="band">\n    <div class="container">',
        f'      <p class="dateline"><span>RUNNING STORY</span>'
        f'<span class="dateline__sep">&middot;</span><span>DAY {story.days}</span></p>',
        f"      <h1>{E(story.title)}</h1>",
        "    </div>\n  </div>\n",
        '  <div class="band band--sunk">\n    <div class="container">',
        '      <figure class="figure">',
        f'        <div class="figure__frame">{timeline_svg(story)}</div>',
        f'        <figcaption class="caption">Appeared in {story.days} briefings. '
        "Only entries marked with a diamond carried something that had not already been "
        "reported.</figcaption>",
        "      </figure>\n    </div>\n  </div>\n",
        '  <div class="band">\n    <div class="container">\n      <h2>What changed, and when</h2>',
    ]
    for app in reversed(story.appearances):
        out.append('      <article class="story">')
        out.append(
            f'        <span class="story__num">{E(app.brief.stamp)}</span>'
        )
        out.append(f'        <h3 class="story__title">{E(app.item.title)}</h3>')
        for para in app.item.body:
            out.append(f"        <p>{E(para)}</p>")
        if app.item.source:
            out.append(f'        <p class="story__source">Source: {E(app.item.source)}</p>')
        out.append(
            f'        <p class="story__source">'
            f'<a href="../briefs/{E(app.brief.slug)}.html">Full brief, '
            f"{E(app.brief.stamp)}</a></p>"
        )
        out.append("      </article>")
    out.append("    </div>\n  </div>\n")
    return "\n".join(out)


def render_index(briefs: list[Brief], stories: dict[str, Story]) -> str:
    latest = briefs[0]
    dateline = [f"<span>LATEST</span>", f"<span>{E(latest.stamp)}</span>"]
    if latest.time:
        dateline.append(f"<span>{E(latest.time.upper())}</span>")
    bar = '<span class="dateline__sep">&middot;</span>'.join(dateline)

    out = [
        '  <div class="band">\n    <div class="container">',
        f'      <p class="dateline">{bar}</p>',
        f"      <h1>{E(latest.title)}</h1>",
        f'      <p class="lead">{E(latest.lead)}</p>',
        f'      <p><a class="btn" href="briefs/{E(latest.slug)}.html">Read the brief</a></p>',
        "    </div>\n  </div>\n",
        '  <div class="band band--ink">\n    <div class="container">',
        '      <span class="slug">What this is</span>',
        '      <p class="lead" style="max-width:62ch">The Telegram brief is triage &mdash; a handful '
        "of items, ninety seconds, read on a commute and discarded. This is the layer underneath it: "
        "running stories tracked across days rather than restated each morning, every source link "
        "kept, and nothing thrown away.</p>",
        "    </div>\n  </div>\n",
    ]

    running = sorted(
        (s for s in stories.values() if s.is_running),
        key=lambda s: (s.latest.brief.date, s.days),
        reverse=True,
    )
    if running:
        out.append('  <div class="band">\n    <div class="container">')
        out.append("      <h2>Running stories</h2>")
        out.append(
            '      <p class="caption" style="margin-bottom:1.5rem">A story gets its own page the '
            "second time it appears. The brief links here instead of re-explaining it.</p>"
        )
        out.append('      <div class="cols cols--2">')
        for i, story in enumerate(running[:4]):
            klass = "block block--stamp" if i == 0 else "block"
            tag = "new angle" if story.latest.item.is_new_angle else "still moving"
            out.append(f'        <div class="{klass}">')
            out.append(f'          <span class="slug">Day {story.days} &middot; {tag}</span>')
            out.append(
                f'          <h3 style="margin-top:0"><a href="stories/{E(story.slug)}.html">'
                f"{E(story.title)}</a></h3>"
            )
            body = story.latest.item.body[0] if story.latest.item.body else ""
            out.append(f'          <p style="margin-bottom:0">{E(body)}</p>')
            out.append("        </div>")
        out.append("      </div>\n    </div>\n  </div>\n")

    out.append('  <div class="band band--sunk">\n    <div class="container">')
    out.append("      <h2>Every brief</h2>\n      <ul class=\"archive\">")
    for brief in briefs:
        out.append(
            f'        <li><span>{E(brief.stamp)}</span>'
            f'<a href="briefs/{E(brief.slug)}.html">{E(brief.title)}</a></li>'
        )
    out.append("      </ul>\n    </div>\n  </div>\n")
    return "\n".join(out)


# ---------------------------------------------------------------- driver


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    ap.add_argument("--out", type=Path, default=ROOT)
    ap.add_argument("--check", action="store_true", help="parse only, write nothing")
    args = ap.parse_args()

    try:
        briefs = load_briefs(args.source)
    except BriefError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    stories = collect_stories(briefs)
    running = sum(1 for s in stories.values() if s.is_running)
    print(f"parsed {len(briefs)} brief(s), {len(stories)} stor(y/ies), {running} running")

    if args.check:
        return 0

    (args.out / "briefs").mkdir(parents=True, exist_ok=True)
    (args.out / "stories").mkdir(parents=True, exist_ok=True)

    for brief in briefs:
        (args.out / "briefs" / f"{brief.slug}.html").write_text(
            page(
                f"AI Brief — {brief.stamp.title()}",
                brief.lead or brief.title,
                1,
                render_brief(brief, stories),
            ),
            encoding="utf-8",
        )

    for story in stories.values():
        if not story.is_running:
            continue
        (args.out / "stories" / f"{story.slug}.html").write_text(
            page(
                f"{story.title} — running story",
                f"How the {story.title} story developed across {story.days} briefings.",
                1,
                render_story(story),
            ),
            encoding="utf-8",
        )

    (args.out / "index.html").write_text(
        page(
            "AI Brief — wire archive",
            "The durable layer behind a Telegram AI briefing: running stories tracked "
            "over time, full sources, and every brief kept.",
            0,
            render_index(briefs, stories),
        ),
        encoding="utf-8",
    )

    print(f"wrote {len(briefs)} brief page(s), {running} story page(s), index.html")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

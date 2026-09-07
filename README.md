# AI Brief — wire archive

The durable layer behind a Telegram AI briefing. The brief itself is triage —
a handful of items read on a commute and discarded. This is where the detail
lives: running stories tracked across days rather than restated each time, every
source link kept, and nothing thrown away.

## What it does

Victor (the OpenClaw AI-news agent) writes one markdown file per briefing into
his own workspace. `publish.py` turns those into a static site:

- **a page per brief** — the full item list with sources
- **a page per running story** — every appearance of a story on one timeline,
  so a repeat is shown as *what changed* rather than re-explained
- **an index** — latest brief, running stories, and the full archive

A story becomes a running story the second time it appears. That is the point of
the site: the Telegram brief links to the story page instead of restating the
same announcement each run.

## Why the agent does not publish

Victor writes markdown; **only `publish.py` writes HTML**, and only a person or a
scheduled job runs it. The agent never needs push access to this repo — the same
separation the house MCP servers use, where a server is a pure HTTP client of its
target app and never touches the database.

## Requirements

- Python 3.11+ (standard library only — no dependencies)
- Victor's brief directory at `~/Server/agents/openclaw/victor/briefs/`

## Run

```bash
./publish.py                  # render from the default source dir
./publish.py --source DIR     # render from somewhere else
./publish.py --check          # parse only, write nothing
./publish.py --out DIR        # write somewhere else
```

`--check` parses every brief and writes nothing. It exits non-zero on a malformed
file, so it works as a pre-commit or CI gate.

Then verify — never skip this, the palette hides failures that eyeballing misses:

```bash
bash ~/.claude/skills/brb-flat-poster-theme/scripts/verify.sh . \
  index.html briefs/*.html stories/*.html
```

Serve from the **site root** and pass subdirectory pages as arguments. If you
`cd` into a subdirectory the stylesheet 404s, and an unstyled page passes every
contrast check while being completely broken.

## Brief format

One file per briefing, named `YYYY-MM-DD.md`:

```markdown
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

# Bottom line
One or two sentences.
```

| Key | Where | Meaning |
|---|---|---|
| `date` | front matter | Required. `YYYY-MM-DD`, and the file name should match |
| `title` | front matter | Required. The headline |
| `lead` | front matter | Standfirst under the headline |
| `time` | front matter | Shown in the dateline bar |
| `sources` | front matter | What was actually swept — only what was really opened |
| `story` | item | Slug tying this item to a running story. **This is what enables cross-brief tracking** |
| `signal` | item | The one-line read on what it means |
| `source` | item | A real URL. Rejected at parse time if it is not one |
| `angle` | item | `new` marks the entry that carried something genuinely new |

Item order is meaningful: the first item is the lead slot, which the timeline
renders as a filled circle. Everything else is a mention (open circle), and
`angle: new` overrides both with a diamond.

Parsing is strict on purpose. A malformed brief fails loudly rather than
rendering a page with quietly missing content.

## Tech stack

Static HTML and CSS, no build step and no JavaScript. Rendered by a single
dependency-free Python script. Fonts come from Google Fonts; everything else is
local.

## Repository layout

```
publish.py          the only thing that writes HTML
css/main.css        the design system — see DESIGN.md
DESIGN.md           the spec; changes in the same commit as the CSS
index.html          generated
briefs/*.html       generated, one per briefing
stories/*.html      generated, one per running story
```

Generated pages are committed so GitHub Pages can serve them directly.

## Notes

- **The design spec is binding.** `DESIGN.md` lists every component; anything not
  on the list does not exist. Adding a component means adding it to the spec in
  the same commit.
- **Re-verify everything after a CSS change**, not just the page you were looking
  at. Every page is generated from shared components, so a change lands
  everywhere at once.
- `--telex` amber is **fill-only** — it carries ink as a fill and can never set
  type on paper. `--ink-quiet` and the default link colour are **paper-only** and
  must be restated on every coloured surface. Both rules have already caught real
  failures; see DESIGN.md §2.

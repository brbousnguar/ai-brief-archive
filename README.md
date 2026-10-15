# AI Brief — wire archive

The durable layer behind a Telegram AI briefing. The brief itself is triage —
a handful of items read on a commute and discarded. This is where the detail
lives: running stories tracked across days rather than restated each time, every
source link kept, and nothing thrown away.

Live at **<https://heybrahim.com/ai-brief-archive/>**. The old
`brbousnguar.github.io/ai-brief-archive/` address only 301s there, so never link
to it.

## What it does

Victor (the OpenClaw AI-news agent) writes one markdown file per briefing into
his own workspace. `publish.py` turns those into a static site:

- **a page per brief** — a main picture, an audio version, then the full item
  list with sources
- **a page per running story** — every appearance of a story on one timeline,
  so a repeat is shown as *what changed* rather than re-explained
- **an index** — latest brief, running stories, and the full archive

### The main picture

Each brief opens with one picture: the share image (`og:image`) of the first
story whose source page has one. Bare homepages are skipped, because their share
image is the site's logo card, not the story's, and so is any image whose path
says `logo` or `default`. The picture is **hotlinked from the publisher and
credited** with a link to that story's source — never rehosted, never generated.
It is also the page's own `og:image`, so a shared brief link previews with it.

Lookups are cached in `images.json`, one entry per brief date, so each brief is
fetched once and a re-render is offline. A brief with no usable picture is stored
as `null` and renders text-only. A source that refused or timed out (OpenAI and
VentureBeat often answer a script with 403/429) is *not* cached and is retried on
the next run, for up to seven days. To pin a picture by hand, add
`image: https://…` to the brief's front matter, or edit its `images.json` entry.

### The audio version

From 2026-10-14 on, each brief also has a recording, for listening on a walk or
the bus. Older briefs stay text-only. The player sits under the main picture.
It is a skin over the page's own `<audio>`, so it keeps playing with the screen
locked, and the phone's lock screen shows the headline with skip buttons. It has
back 15 s and forward 30 s, a speed control, and a mini-player docked at the
bottom once the card scrolls away. The position is kept, so a stop picks up
where it left off. Without JavaScript the browser's own audio control shows
instead.

`narrate.py` records it with **Kokoro-82M** (voice `af_heart`, through
mlx-audio), locally on the mini. It needs no API and costs nothing, takes about
30 seconds a brief, and the card says it is an AI voice. The script reads the
headline, lead, each story with its signal, worth watching and the bottom line.
It leaves out sources and URLs. `publish.speech()` builds that text, and it also
respells the few things Kokoro misreads (`~50%`, `$52M`, `1.7x`, `v0.22.0`).
Print it with `narrate.py --say DATE`.

Output is `audio/<date>.mp3` (mono, 40 kbps, -16 LUFS, about 2.5 MB for a
9-minute brief) and `audio/manifest.json`. Each manifest entry carries a hash of
the text it read, and `publish.py` shows a player only while that hash still
matches the brief. When a same-day re-run changes the brief, the old recording
disappears from the page until the hook records the new one, a minute later.

The voice needs its own venv, kept outside the repo because the hook commits
with `git add -A`:

```bash
tts/setup.sh                                          # once; pinned in tts/requirements.txt
~/.local/share/ai-brief-tts/venv/bin/python narrate.py              # record what is new or changed
~/.local/share/ai-brief-tts/venv/bin/python narrate.py --date 2026-10-14 --force
python3 narrate.py --say 2026-10-14                   # what would be read; no venv needed
```

A story becomes a running story the second time it appears. That is the point of
the site: the Telegram brief links to the story page instead of restating the
same announcement each run.

## Why the agent does not publish

Victor writes markdown; **only `publish.py` writes HTML**, and only a person or a
scheduled job runs it. The agent never needs push access to this repo — the same
separation the house MCP servers use, where a server is a pure HTTP client of its
target app and never touches the database.

## Requirements

- Python 3.11+ (standard library only — no dependencies) for `publish.py`
- Victor's brief directory at `~/Server/agents/openclaw/victor/briefs/`
- For the audio only: an Apple Silicon Mac, `ffmpeg` with libmp3lame, and the
  venv from `tts/setup.sh`

## Run

```bash
./publish.py                  # render from the default source dir
./publish.py --source DIR     # render from somewhere else
./publish.py --check          # parse only, write nothing
./publish.py --out DIR        # write somewhere else
./publish.py --no-fetch       # render without looking up pictures (cache only)
```

`--check` parses every brief and writes nothing. It exits non-zero on a malformed
file, so it works as a pre-commit or CI gate.

Then verify — never skip this, the palette hides failures that eyeballing misses:

```bash
bash ~/Server/.claude/skills/brb-flat-poster-theme/scripts/verify.sh . \
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
| `image` | front matter | Optional. An `https://` picture that overrides the automatic one |
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

Static HTML and CSS, no build step. The scripts are `js/listen.js`, the audio
player, which is only loaded on a page with a recording, and a short inline one
on `404.html` that waits for a brief still being published. Rendered by a single
dependency-free Python script. Fonts come from Google Fonts and each brief's main
picture from its publisher; everything else, the recordings included, is local. Served by GitHub Pages
under the heybrahim.com custom domain of the `brbousnguar.github.io` user site.

## Repository layout

```
publish.py          the only thing that writes HTML
narrate.py          the only thing that writes audio
css/main.css        the design system — see DESIGN.md
js/listen.js        the audio player, the site's only script
DESIGN.md           the spec; changes in the same commit as the CSS
publish-hook.sh     launchd entry point: pull, render, push; then record, push
tts/                setup.sh + pinned requirements for the voice venv
images.json         main-picture cache, one entry per brief (written by publish.py)
audio/              <date>.mp3 + manifest.json (written by narrate.py)
index.html          generated
404.html            generated; waits for a brief that is still being published
briefs/*.html       generated, one per briefing
stories/*.html      generated, one per running story
```

Generated pages and recordings are committed so GitHub Pages can serve them
directly. Recordings are the one thing that makes the repo grow, at about 2.5 MB
a brief, and a same-day re-run that changes the brief adds another. If it ever
nears GitHub's 1 GB guidance, move `audio/` to release assets or another host.

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

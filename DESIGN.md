# AI Brief — design spec

Wire-service flat-poster identity. This document describes `css/main.css` as it
actually is. **It changes in the same commit as the CSS.** A spec that drifts is
worse than none.

Built on the `brb-flat-poster-theme` system. The *system* is shared with
`northafricanorigins.com`; the *palette, type and ornament are not*, and must not
be copied back and forth. That site derives from the Amazigh flag; this one
derives from the wire brief.

---

## 1. Where the palette comes from

The artifact is a **briefing** — so the palette comes from the material history
of briefings: newsprint, press black, the red of a correction stamp, teletype
amber, the blue of a wire desk, and the green of "cleared for release".

Nothing here was chosen because it felt modern. That is the point: a palette the
subject already owns cannot look like a template, because it is not one.

## 2. Tokens, with measured contrast

Ground: `--paper #FBF7EF`, ink `--ink #14120E`. **Ink on paper = 17.51:1.**

| Token | Hex | White on it | Ink on it | As text on paper | Class |
|---|---|---|---|---|---|
| `--wire` | `#1B5E7A` | 7.17 | 2.61 | **6.71** | DUAL-ROLE |
| `--embargo` | `#2E6B3E` | 6.39 | 2.93 | **5.98** | DUAL-ROLE |
| `--stamp` | `#C81E1E` | 5.74 | 3.26 | **5.37** | DUAL-ROLE |
| `--telex` | `#B8860B` | 3.25 | **5.75** | 3.05 | **FILL-ONLY** |

Measured with `scripts/check-palette.py` from the theme skill. Re-run it before
adding or changing any hue.

### The dual-role rule

A DUAL-ROLE token may both fill a block and set type on paper — one token, both
jobs, no parallel "text-safe twin" shadowing every brand colour.

**`--telex` is FILL-ONLY.** It carries ink as a fill (5.75:1) and nothing else.
It is 3.05:1 as text on paper, so **never set a link, heading or body copy in
it.** It fills the dateline bar and the sources block, both carrying `--ink`.

### Paper-only ink

Two tokens are **paper-only** and fail on every colour ground:

- `--ink-quiet #55504A` — 7.30:1 on paper, used by `.slug` and `.caption`
- `--wire` as the default link colour — 6.71:1 on paper, 1.25:1 on `--stamp`

Any coloured surface — band *or* block — must restate both. This is a live rule,
not theory. It has now failed verification twice, and both times only on a
`.block--*`, because the original rule covered `.band--*` alone:

| Run | Failure | Ratio |
|---|---|---|
| Pilot | `.slug` in `.block--stamp` | 1.39:1 |
| Pilot | `.slug` in `.block--fill` | 2.45:1 |
| Generated | story link in `.block--stamp` | 1.25:1 |

**Adding a new `.block--*` variant means adding it to both selector lists.**
The generated pages made headings into links, which the hand-written pilot did
not have — a reminder that a component gains new inner elements over time and
the colour rules have to cover the surface, not the snapshot.

Never dim white on a colour ground. `rgba(255,255,255,0.85)` composites well
below AA on a mid hue. Use solid `--on-colour`.

## 3. Type

| Role | Family | Used for |
|---|---|---|
| Display | Archivo 700/800, `-0.03em` | Headings, masthead, buttons |
| Reading | Source Serif 4 | Body copy only |
| Technical | IBM Plex Mono | Datelines, slugs, timestamps, day counters, source URLs, archive dates |

A serif reading face is deliberate — it is what a briefing is set in, and it
separates this site from the sans-body heritage site.

**The mono role has a real job here**, which is unusual and worth protecting: it
carries the wire furniture. Do not use it decoratively.

Every family has a real fallback stack. Avoid Inter and Space Grotesk — together
they are the most recognisable machine-generated pairing.

## 4. Form language

1. **Flat.** No shadows, gradients, blurs or glass. A block is one solid colour.
2. **Hard-edged.** `border-radius: 0` everywhere. The only radius in the system
   is `--radius-dot` for legend dots.
3. **Unequal.** Blocks in a group differ in size, colour or weight. The running-
   stories row is `1.6fr / 1fr` with one block in `--stamp` and one in
   `--paper-sunk`. **A row of identical cards is the failure this system
   replaced** — if a grid reads as a table of equals, it is wrong.

Separation comes from a colour change and a rule, never a border on all four
sides of every box.

Grids use `minmax(0, 1fr)`. Bare `1fr` cannot shrink below min-content and pushes
the page sideways on a phone.

### The ornament

**Punched paper tape** (`.tape`) — a band of ink perforations on `--telex`.

Derived from the subject like the palette. Unlike the haik stripes of the
heritage site, this ornament is **regular on purpose**: perforation is a machine
artifact, and evenness is what makes it read as tape rather than decoration. Do
not randomise it.

## 5. Imagery

Authored inline SVG only, with **one exception: the main picture.** No generated
imagery, ever.

### The main picture (`.cover`)

Each brief, and the index's latest brief, opens with one photograph: the share
image of one of the brief's own stories (see README). It sits **above the
dateline**, because briefing headlines run to six or seven lines and push
anything placed under them off the first screen.

- **Borrowed, not ours.** Hotlinked from the publisher, never rehosted, and
  always credited — `.cover__credit` names the source domain and links to the
  story, plus `· story 0N` when the picture is not the lead's.
- **One fixed frame.** `aspect-ratio: 1.91 / 1` (the share-image standard), with
  `object-fit: cover` and `object-position: 50% 0`. The ratio reserves space, so
  the page does not jump when the image arrives. The crop is anchored to the top
  because charts and tables, the common shape on X, keep their headers there.
- **Flat like everything else.** Hard edges, the standard `--rule` border, and a
  `--paper-sunk` ground while the image loads. No overlays, gradients or text
  set on the picture.
- **Paper bands only.** The credit uses `--ink-quiet` and the default link
  colour, both paper-only.
- **Never lazy-loaded.** It is the first thing on the page.

### Diagrams

- **Inline**, never `<img src="*.svg">` — inline SVG inherits the custom
  properties, so diagrams restyle with the theme.
- `fill` and `stroke` take `var(--token)`. **No hex literals in SVG.**
- `role="img"` + `<title>` + `<desc>`, and a caption that states the **finding**.
- Colour is never the only cue. The running-story diagram distinguishes states by
  *shape* — filled circle, open circle, diamond — with a labelled legend.
- Diagrams scroll in their own frame (`.figure__frame`, `min-width: 560px`)
  rather than shrinking to illegibility.

The signature diagram is the **running-story timeline**: one lane per story, one
mark per briefing. It exists to make the site's central problem vivid — that the
same two announcements led five briefings running and only one entry carried
anything new. Look for that shape of diagram: the one that makes the honest
limitation impossible to miss.

## 6. Audio

A brief from 2026-10-14 on can be listened to: on a walk, on the bus, with the
phone in a pocket. `narrate.py` records it and README.md explains the recording.
This section covers what the reader sees and hears.

### The player (`.listen`)

- **The native `<audio>` is the player.** `js/listen.js` skins it and never
  replaces it. Playing the real element is what keeps playback going with the
  screen locked and puts the headline and skip buttons on the lock screen
  (Media Session, with the main picture as artwork). Never swap it for Web
  Audio or a custom decoder.
- **The site's only script, and only where it is needed.** It is loaded on a
  brief page that has a recording, nowhere else. An inline head script sets
  `html.js` before paint, so the card renders first and nothing shifts. If the
  script fails to load, the class is removed. Without script, a mono label sits
  over the browser's own control.
- **Under the picture, above the dateline.** A briefing headline runs to six
  lines on a phone, and play has to be on the first screen.
- **Always says it is an AI voice.** The no-script label and the card note
  both say so. Never drop it to save space: on a narrow screen the note
  shortens to "AI voice", it is never removed.
- **Flat, paper only.** A `--rule` border on paper. The play block is `--wire`
  carrying `--on-colour` (7.17:1) and turns `--ink` on hover. The track is a
  ruled bar with `--wire` for what has played and `--paper-sunk` for the rest,
  and a square `--ink` thumb. Times and the note use `--ink-quiet`, which is
  paper-only. No radius, no shadow.
- **Touch first.** Every control is at least 44px. Back 15 s and forward 30 s
  are the buttons a walker reaches for. Speed steps 1, 1.25, 1.5, 1.75, 2,
  0.75. The speed is remembered, and so is the position, per brief
  (`localStorage`), so a reload offers "Resume from 3:12".

### The mini-player (`.dock`)

It appears only once playback has started **and** the card has scrolled away,
and never on load. It is fixed to the bottom on paper with one top `--rule`, a
4px progress line in `--wire`, play/pause, the headline (ellipsed), the time,
and a close button that pauses. Without motion: it appears and disappears, it
does not slide. The page gains bottom padding while it shows, so it never
covers the last line.

### What is read

The page in reading order, minus what only works on screen: headline, lead,
each story with its signal, worth watching, bottom line. Story numbers, day
counters, URLs and the sources-scanned note are not read. Plain neutral voice,
no music, no intro, no sign-off.

## 7. Concision

Target **~900 words of running prose** per page. Tables, captions and source
lists count separately.

Cut by moving detail into a diagram, a story page or a disclosure. **Never** by
dropping a date, a hedge, a source or an attribution — on a site whose value is
being trustworthy, the qualifications are the product. Do not game the target by
tabulating things nobody would naturally tabulate.

## 8. Components

Anything not on this list does not exist. Adding a component means adding it here.

`.masthead` · `.tape` · `.dateline` · `.slug` · `.end-mark` · `.band` (+
`--sunk` `--wire` `--embargo` `--stamp` `--ink`) · `.cols` (+ `--2` `--3`) ·
`.block` (+ `--wire` `--embargo` `--stamp` `--fill` `--paper`) · `.story` (+
`--lead`, `.story__num` `.story__title` `.story__signal` `.story__source`) ·
`.daycount` (also as a link to a story page) · `.watch` · `.archive` · `.figure` (+ `.figure__frame` `.caption`) ·
`.cover` (+ `.cover__frame` `.cover__credit`) · `.listen` (+ `.listen__label`
`.listen__player` `.listen__play` `.listen__main` `.listen__head` `.listen__title`
`.listen__time` `.listen__seek` `.listen__row` `.listen__btn` `.listen__rate`
`.listen__note`) · `.dock` (+ `.dock__bar` `.dock__row` `.dock__play`
`.dock__title` `.dock__time` `.dock__close`) · `.lead` · `.kicker` · `.btn` (+
`--ghost`, used for the index's "Listen" link) · `.skip-link` · `.site-footer`

Script hooks, not components: `.listen__cur` `.listen__dur` `.listen__more`
`.listen__cast` `.listen__i-play` `.listen__i-pause` `.dock__dur`. State
classes: `html.js`, `html.has-dock`, and `.is-playing` `.is-loading` `.is-error`
on the player.

## 9. Verification

```bash
bash ~/Server/.claude/skills/brb-flat-poster-theme/scripts/verify.sh . index.html briefs/2026-09-07.html
```

Serve from the **site root** and pass subdirectory pages as arguments — never
`cd` into the subdirectory, or the stylesheet 404s and an unstyled page passes
every contrast check.

Then Lighthouse (mobile) via the chrome-devtools MCP against
`http://127.0.0.1:8799/<page>`.

**Current status — all five generated pages pass** contrast and 320px reflow
with zero failures. Lighthouse (mobile) spot-checks:

| Page | a11y | Best practices | SEO |
|---|---|---|---|
| `index.html` | 100 (39/0) | 100 | 100 |
| `briefs/2026-09-07.html` | 100 (48/0) | 100 | 100 |
| `stories/nvidia-hugging-face.html` | 100 (46/0) | 100 | 100 |
| `briefs/2026-10-14.html` (with `.cover`) | 100 (43/0) | 100 | 100 |
| `briefs/2026-10-14.html` (with `.cover` + `.listen`) | 100 (52/0) | 100 | 100 |
| `index.html` (with the Listen link) | 100 (43/0) | 100 | 100 |

The player was also driven in Chromium and WebKit at 320px and 390px. Play,
skip, speed, the dock, close and resume after a reload all work, with zero
console errors.

Note: headless Chrome clamps its viewport to 500px, so a `--window-size=320`
screenshot proves nothing. `verify.sh` measures true narrow reflow in a
fixed-width iframe.

## 10. Migration status

Pilot approved. Every page is now **generated** by `publish.py` from markdown in
Victor's workspace — see `README.md`. No page is hand-maintained, so a component
change lands everywhere at once and `verify.sh` must be re-run across all pages,
not just the one you were editing.

No legacy stylesheet exists, so the two-stylesheet coexistence rule never applied.

Live on GitHub Pages at <https://heybrahim.com/ai-brief-archive/>. The launchd
job `ai.openclaw.victor-publish` runs `publish-hook.sh` whenever Victor writes a
brief. The hook pushes the text first, then records the audio and pushes again.

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

The files are served from `fonts/` (#13), not Google Fonts: latin and latin-ext
woff2 subsets with the same `unicode-range` split Google uses, declared at the
top of `main.css`. Archivo and Source Serif 4 are variable and carry their
weight range in one file; Plex Mono is static, one file per weight. The two
faces the first screen is set in are preloaded. The service worker caches them,
so the installed app reads in its own faces offline, and no reader's IP goes to
Google for a font.

**Source links.** `Source:` on a story is a link, labelled with the host and
path (cut at 60 characters) and carrying the full URL. It was plain text until
#13, on a site whose promise is that every source link is kept.

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

### The mark (#11)

The logo is the same tape, cut to a square: a `--paper` strip across `--wire`,
three `--ink` holes, the last hole larger and `--stamp` red, for the story
that made the brief. It is chosen over a sheet-of-paper icon (generic) and a
timeline dot (thin at 16 px) because it stays readable in a browser tab.

`tools/make_icons.py` draws it from rectangles and circles in a 100-unit box,
so the SVG and every PNG share one geometry. No glyphs, no rounding: iOS
and Android round the corners themselves. The maskable icon pulls the holes in
to 72% so Android's circle crop keeps all four. In the masthead it is inlined
as `.masthead__mark`, 0.9em square, `aria-hidden` (the link text names it).

### The nav, the archive list and the share row (#15)

The masthead carries five mono links (`.masthead__nav`): Latest, Stories,
Archive, About, Follow, the same on every page. The current one sits on a 3px
`--stamp` rule, the only place that red is a line. From 720px the nav sits
right of the name; on a phone it takes its own row under it. Each link is a
44px tap target.

The archive (`.archive`) is no longer a mono wall. On the index it is grouped
by week under a slug heading on an ink rule (`.archive__week`); each row is
the day in mono (`.archive__date`), the headline in the reading face at body
size (`.archive__title`), and what the brief holds, stories and listening
time, in quiet mono (`.archive__meta`): three columns from 720px, the meta
under the headline on a phone. The stories index uses the same list, flat.

The share row (`.share`) closes a brief, above the pager and in the same
band. Its buttons (`.share__btn`) are the player's: 44px mono, hard-edged,
ink on paper, inverted on hover. The three that need an API (the share sheet,
copy link, copy as text) render `hidden` and `js/share.js` shows them; Email,
LinkedIn, X and the plain-text file are links and need nothing. The status
line (`.share__status`) keeps its height so a "Link copied" does not move the
pager.

### The cookie question (#25)

Google Analytics waits for a yes, so a first visit asks. The banner
(`.consent`) borrows the dock's frame: full width on the bottom edge, paper,
one ink rule on top, and above the dock when both show. It holds a `.slug`
("Cookies"), one sentence with a link to what is counted, and Refuse and
Accept as two `.consent__btn`, which are the share row's buttons: same size,
same weight, side by side, Refuse first. Nothing about either button leans:
no fill, no colour, no "recommended". On a phone the two buttons share the
width under the sentence. It is not modal and never takes focus on load; the
body pads by its measured height so the footer is never under it. A footer
button (`.site-footer__cookies`, set like the footer's links) reopens it, with
the current answer in a quiet mono line (`.consent__now`), so withdrawing is
as easy as agreeing.

### Counting (#19)

Numbers are wire furniture, so they are mono and quiet, except on the index
tally where they are the point. The facts line (`.facts`) under a brief's lead
says what it holds and how long it takes (stories, running, sources, minutes
to read at 230 words a minute, listening time). The tally (`.cols--tally`) is
five unequal blocks in `.cols`: the first on `--wire` and 1.6 times wider,
the last on `--telex`, one display-face number (`.tally__n`) over a slug each;
on a phone two columns with the first block across both. The sources table
(`.table`) has slug headings on an ink rule, ruled rows, and right-aligned
tabular mono numbers (`.num`). Story pages say the span in days and how many
entries carried a new angle in their existing caption.

## 5. Imagery

Authored inline SVG only, with **one exception: the main picture.** No generated
imagery, ever.

### The main picture (`.cover`)

Each brief, and the index's latest brief, opens with one photograph: the share
image of one of the brief's own stories (see README). On a phone it sits
**above the dateline**, because briefing headlines run to six or seven lines
and push anything placed under them off the first screen. From 900px it sits
**beside** the headline instead (`.hero`, below): at container width the frame
is 600px tall and the first screen of a brief was a borrowed picture and
nothing else (#13).

### The hero (#13)

`.hero` is the opening of a brief and of the index: `.hero__media` (the
picture, then the player when there is one) and `.hero__text` (dateline,
headline, lead, and the index's buttons). It is a plain stack on a phone and a
`2fr / 3fr` grid from 900px, unequal like every other grid here. A brief with
no picture gets no grid; its player sits above the dateline as before. A
picture whose hotlink has died hides itself and sets `.hero--text`, which
collapses the grid, so a dead CDN path never leaves a broken-image icon at the
top of an old brief.

The headline scale went with it: `--t-h1` tops out at 3.75rem, not 5rem, and
an h1 over 100 characters takes `.h1--long` (3rem). Headlines average 113
characters, and at poster size that was six lines on a desktop and ten on a
phone. Every "/" in a heading is followed by a `<wbr>`, because
"OpenAI/Anthropic" otherwise breaks inside a word at display size.

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
- **Only where it is needed.** It is loaded on a brief page that has a
  recording, nowhere else. (The only other script is the 404 page's wait,
  below.) An inline head script sets
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

### Read-along (#7)

- **The page follows the voice.** The blocks the voice reads carry `data-t`,
  the second each starts; the recorder knows them exactly because it reads one
  paragraph at a time. The block being read gets `.is-reading`: a `--paper-sunk`
  tint 8px beyond the text with a 3px `--wire` rule on its left edge, both
  box-shadows so nothing moves. On the wire band the tint is the band's blue
  deepened with a fifth of `--ink` (a `color-mix`, no new token; white type
  keeps more than its 7:1) and the rule is `--on-colour`. The signal keeps its
  embargo rule and only gains the tint. No radius, no shadow beyond those two.
- **It scrolls with the voice, not against the reader.** The block is brought
  into the band above the dock only when it is off screen, with the page's own
  scroll behaviour (plain under reduced motion). A wheel, a swipe or an arrow
  key stops the following; it resumes once the block being read is on screen
  again.
- **Step by paragraph.** The card's buttons become previous / next paragraph
  (a bar-and-triangle glyph with a ¶), and so do earbud and lock-screen
  previous / next. Back within two seconds of a start goes to the paragraph
  before. While playing, timed blocks show a pointer and a tap reads from
  there; links, the player and a text selection are left alone. Space pauses,
  R repeats the paragraph.
- **Falls back cleanly.** A brief without paragraph times keeps the 15 s / 30 s
  buttons and nothing is marked.

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

## 7. The 404 page

GitHub Pages serves `404.html` for any missing address in the archive. Its
default page is a dead end, and the usual way to reach it is a brief link
opened straight from Telegram: Victor sends the link the moment he writes the
file, about a minute before the page is live.

So for a brief dated within the last day or two, an inline script turns the
page into "This brief is on its way". The dateline reads `Publishing`, and the
script checks every 8 seconds (`HEAD`, no cache) and reloads once the page is
up, keeping `#listen`. It gives up after four minutes and says so. Any other
address gets "Not here, or not yet" and the button to all briefs. Without
script, the text covers both cases and asks for a reload.

Every link on it is absolute (`/…`), because it is served at
whatever depth the missing address had. It is `noindex` and carries no share
tags. It uses only existing components.

## 8. Concision

Target **~900 words of running prose** per page. Tables, captions and source
lists count separately.

Cut by moving detail into a diagram, a story page or a disclosure. **Never** by
dropping a date, a hedge, a source or an attribution — on a site whose value is
being trustworthy, the qualifications are the product. Do not game the target by
tabulating things nobody would naturally tabulate.

## 9. Components

Anything not on this list does not exist. Adding a component means adding it here.

`.masthead` (+ `.masthead__nav`) · `.tape` · `.dateline` · `.slug` · `.end-mark` · `.band` (+
`--sunk` `--wire` `--embargo` `--stamp` `--ink`) · `.cols` (+ `--2` `--3`) ·
`.block` (+ `--wire` `--embargo` `--stamp` `--fill` `--paper`) · `.story` (+
`--lead`, `.story__num` `.story__title` `.story__signal` `.story__source`) ·
`.daycount` (also as a link to a story page) · `.watch` · `.archive` (+
`.archive__week` `.archive__date` `.archive__title` `.archive__meta`) ·
`.figure` (+ `.figure__frame` `.caption`) ·
`.cover` (+ `.cover__frame` `.cover__credit`) · `.hero` (+ `.hero__media`
`.hero__text` `--text`) · `.h1--long` · `.pager` (+ `.pager__link` `--next`
`.pager__title`) · `.share` (+ `.share__row` `.share__btn` `.share__status`) ·
`.facts` · `.cols--tally` (+ `.tally__n`) · `.table` (+ `.num`) ·
`.listen` (+ `.listen__label`
`.listen__player` `.listen__play` `.listen__main` `.listen__head` `.listen__title`
`.listen__time` `.listen__seek` `.listen__row` `.listen__btn` `.listen__rate`
`.listen__note`) · `.dock` (+ `.dock__bar` `.dock__row` `.dock__play`
`.dock__title` `.dock__time` `.dock__close`) · `.consent` (+ `.consent__row`
`.consent__text` `.consent__choices` `.consent__btn` `.consent__now`) · `.lead` ·
`.kicker` · `.btn` (+ `--ghost`, used for the index's "Listen" link) ·
`.skip-link` · `.site-footer` (+ `.site-footer__cookies`)

Script hooks, not components: `.listen__cur` `.listen__dur` `.listen__more`
`.listen__cast` `.listen__i-play` `.listen__i-pause` `.dock__dur`. State
classes: `html.js`, `html.has-dock`, `html.has-consent`, and `.is-playing` `.is-loading` `.is-error`
on the player.

## 10. Verification

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

## 11. Migration status

Pilot approved. Every page is now **generated** by `publish.py` from markdown in
Victor's workspace — see `README.md`. No page is hand-maintained, so a component
change lands everywhere at once and `verify.sh` must be re-run across all pages,
not just the one you were editing.

No legacy stylesheet exists, so the two-stylesheet coexistence rule never applied.

Live on GitHub Pages at <https://ai.heybrahim.com/>. The launchd
job `ai.openclaw.victor-publish` runs `publish-hook.sh` whenever Victor writes a
brief. The hook pushes the text first, then records the audio and pushes again.

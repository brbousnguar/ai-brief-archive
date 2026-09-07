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

`--ink-quiet #55504A` is 7.30:1 on paper and **fails on every colour ground**.
Any coloured surface — band *or* block — must restate the colour of anything
using it. This is a live rule, not theory: the first verify run failed on
`.slug` inside `.block--stamp` at 1.39:1 and inside `.block--fill` at 2.45:1.
Both are now covered. Add a new `.block--*` variant and you must add it here too.

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

Authored inline SVG only. No photography, no generated imagery.

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

## 6. Concision

Target **~900 words of running prose** per page. Tables, captions and source
lists count separately.

Cut by moving detail into a diagram, a story page or a disclosure. **Never** by
dropping a date, a hedge, a source or an attribution — on a site whose value is
being trustworthy, the qualifications are the product. Do not game the target by
tabulating things nobody would naturally tabulate.

## 7. Components

Anything not on this list does not exist. Adding a component means adding it here.

`.masthead` · `.tape` · `.dateline` · `.slug` · `.end-mark` · `.band` (+
`--sunk` `--wire` `--embargo` `--stamp` `--ink`) · `.cols` (+ `--2` `--3`) ·
`.block` (+ `--wire` `--embargo` `--stamp` `--fill` `--paper`) · `.story` (+
`--lead`, `.story__num` `.story__title` `.story__signal` `.story__source`) ·
`.daycount` · `.watch` · `.archive` · `.figure` (+ `.figure__frame` `.caption`) ·
`.lead` · `.kicker` · `.btn` (+ `--ghost`) · `.skip-link` · `.site-footer`

## 8. Verification

```bash
bash ~/.claude/skills/brb-flat-poster-theme/scripts/verify.sh . index.html briefs/2026-09-07.html
```

Serve from the **site root** and pass subdirectory pages as arguments — never
`cd` into the subdirectory, or the stylesheet 404s and an unstyled page passes
every contrast check.

Then Lighthouse (mobile) via the chrome-devtools MCP against
`http://127.0.0.1:8799/<page>`.

**Current status — both pages:**

| Check | index.html | briefs/2026-09-07.html |
|---|---|---|
| Contrast | 0 failures | 0 failures |
| Reflow @320px | no overflow | no overflow |
| Lighthouse a11y | 100 (39 passed, 0 failed) | 100 (48 passed, 0 failed) |
| Best practices / SEO | 100 / 100 | 100 / 100 |

Note: headless Chrome clamps its viewport to 500px, so a `--window-size=320`
screenshot proves nothing. `verify.sh` measures true narrow reflow in a
fixed-width iframe.

## 9. Migration status

This is a **pilot**: the design system, a landing page and one real content page.
No legacy stylesheet exists, so the two-stylesheet coexistence rule does not
apply yet. Remaining pages and the publishing pipeline come after approval.

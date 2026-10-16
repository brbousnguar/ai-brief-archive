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

Each brief opens with a main picture, the share image of its first story whose
source page has one, cached in images.json. An optional `image:` front-matter
key pins one by hand. See "The main picture" in README.md.

Briefs that narrate.py has recorded get a player under the picture. The
recording is keyed to a hash of speech(brief), so a brief that changed since
it was recorded shows no player until it is recorded again. See "The audio
version" in README.md.

`story:` is what makes running stories work: two briefs carrying the same slug
become one story page with a timeline, and the brief links there instead of
re-explaining the story. `angle: new` marks the entry that carried something
genuinely new — everything else in a repeat story is a restatement.
"""

from __future__ import annotations

import argparse
import hashlib
import html
import http.client
import json
import re
import ssl
import sys
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass, field
from datetime import date as Date
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlparse

ROOT = Path(__file__).resolve().parent
DEFAULT_SOURCE = Path.home() / "Server/agents/openclaw/victor/briefs"

# The archive is its own site at ai.heybrahim.com (the CNAME file). The old
# heybrahim.com/ai-brief-archive/ links are forwarded here by the main site's
# 404.html, and brbousnguar.github.io/ai-brief-archive/ 301s here, so never link
# to either.
SITE_URL = "https://ai.heybrahim.com/"
HOME_URL = "https://heybrahim.com/"

FONTS = (
    '<link rel="preconnect" href="https://fonts.googleapis.com">\n'
    '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>\n'
    '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?'
    "family=Archivo:wght@700;800&family=Source+Serif+4:ital,wght@0,400;0,600;1,400"
    '&family=IBM+Plex+Mono:wght@400;500&display=swap">'
)

ITEM_KEYS = {"story", "signal", "source", "angle"}

USER_AGENT = f"Mozilla/5.0 (compatible; AIBriefArchive/1.0; +{SITE_URL})"
SHARE_IMAGE_KEYS = ("og:image:secure_url", "og:image", "twitter:image", "twitter:image:src")
# A share image that is really the publisher's logo card says nothing about the story.
GENERIC_IMAGE = re.compile(r"default|logo|favicon|placeholder", re.IGNORECASE)
# How long a brief keeps retrying a source that refused or timed out (403, 429…)
# before it settles for no picture.
RETRY_DAYS = 7

# Written by narrate.py: audio/<date>.mp3 plus a manifest keyed by brief date.
AUDIO_DIR = "audio"


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
    image: str = ""
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
        image=meta.get("image", ""),
    )
    if brief.image and not brief.image.startswith("https://"):
        raise BriefError(f"{path.name}: image must be an https:// URL -> {brief.image!r}")

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


# ---------------------------------------------------------------- cover pictures


@dataclass
class Cover:
    """A brief's main picture: the share image of one of its own stories.

    Hotlinked from the publisher and credited, never rehosted and never
    generated. `page` is the story source it came from, `rank` that story's slot.
    """

    image: str
    page: str
    story: str = ""
    rank: int = 1
    alt: str = ""

    @property
    def credit(self) -> str:
        return urlparse(self.page).netloc.removeprefix("www.")


class _MetaParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.meta: dict[str, str] = {}

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag != "meta":
            return
        found = dict(attrs)
        key = (found.get("property") or found.get("name") or "").lower()
        if key and found.get("content") and key not in self.meta:
            self.meta[key] = found["content"].strip()


def _ssl_context() -> ssl.SSLContext:
    context = ssl.create_default_context()
    # python.org builds ship without a CA bundle until someone runs "Install
    # Certificates"; macOS keeps a current one here.
    if Path("/etc/ssl/cert.pem").exists():
        context.load_verify_locations("/etc/ssl/cert.pem")
    return context


_SSL = _ssl_context()


def _open(url: str, accept: str):
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": accept})
    return urllib.request.urlopen(request, timeout=12, context=_SSL)


def share_image(url: str) -> tuple[str, str] | None:
    """Return (image URL, alt text) for a page's share image, or None if it has none.

    Raises OSError or HTTPException when the page could not be read at all, so
    the caller can tell "no picture" from "try again later".
    """
    try:
        with _open(url, "text/html") as response:
            final = response.geturl()
            charset = response.headers.get_content_charset() or "utf-8"
            raw = response.read(800_000)
    except urllib.error.HTTPError as exc:
        if exc.code in (404, 410):
            return None
        raise

    parser = _MetaParser()
    parser.feed(raw.decode(charset, "replace"))
    image = next((parser.meta[k] for k in SHARE_IMAGE_KEYS if parser.meta.get(k)), "")
    if not image:
        return None
    image = urljoin(final, image)
    if not image.startswith("https://") or GENERIC_IMAGE.search(urlparse(image).path):
        return None

    # Only "gone" disqualifies the image. Image CDNs often refuse a bot user
    # agent (401/403/429) that they serve to every reader's browser.
    try:
        with _open(image, "image/*") as response:
            if not response.headers.get_content_type().startswith("image/"):
                return None
    except urllib.error.HTTPError as exc:
        if exc.code in (404, 410):
            return None
    return image, parser.meta.get("og:image:alt", "")


def resolve_cover(brief: Brief, cache: dict, fetch: bool) -> Cover | None:
    """Pick the brief's main picture, from the cache when it has been looked up before.

    The first story whose source page has a real share image wins. Bare
    homepages are skipped: their share image is the site's, not the story's.
    """
    if brief.image:
        return Cover(image=brief.image, page=brief.image, story=brief.title)
    if brief.slug in cache:
        entry = cache[brief.slug]
        return Cover(**entry) if entry else None
    if not fetch:
        return None

    unreachable = False
    for rank, item in enumerate(brief.items, start=1):
        if not item.source or not urlparse(item.source).path.strip("/"):
            continue
        try:
            found = share_image(item.source)
        except (OSError, http.client.HTTPException, ValueError) as exc:
            print(f"  picture: {brief.slug} could not read {item.source} ({exc})")
            unreachable = True
            continue
        if found:
            cover = Cover(image=found[0], page=item.source, story=item.title, rank=rank, alt=found[1])
            cache[brief.slug] = asdict(cover)
            return cover

    # A refusal or a timeout may clear up, so only settle for "no picture" when
    # every source answered, or the brief is too old to keep asking about.
    if not unreachable or (Date.today() - brief.date).days > RETRY_DAYS:
        cache[brief.slug] = None
    return None


# ---------------------------------------------------------------- audio


_MAGNITUDE = {"K": "thousand", "M": "million", "B": "billion", "T": "trillion"}
# A bare figure like 24B or $52M, but not one inside a model name (LFM2.5-24B-A2B).
_FIGURE = re.compile(r"(?<![\w.-])(\$?)(\d+(?:\.\d+)?)([KMBT])(\+?)(?![\w.]\w)")


def _say_figure(m: re.Match) -> str:
    dollar, number, unit, plus = m.groups()
    return f"{'more than ' if plus else ''}{number} {_MAGNITUDE[unit]}{' dollars' if dollar else ''}"


def _spoken(text: str) -> str:
    """Page text as the voice should read it: no markup, no URLs, no slashes.

    Plus the few spellings Kokoro reads wrong, checked by transcribing a
    recording back with Whisper: "~50%" came out as "tilde", "$52M" as "52 M dollar".
    """
    text = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", text)  # a markdown link reads as its words
    text = re.sub(r"https?://\S+", "", text)
    text = re.sub(r"[*`]+", "", text)
    text = re.sub(r"(?<=[A-Za-z])/(?=[A-Za-z])", ", ", text)  # X/Twitter -> "X, Twitter"
    text = text.replace("&", " and ")
    text = re.sub(r"~\s?(?=\d)", "about ", text)
    text = _FIGURE.sub(_say_figure, text)
    text = re.sub(r"(?<![\w.])(\d+(?:\.\d+)?)x\b", r"\1 times", text)  # 1.7x faster
    text = re.sub(r"\bv(\d+(?:\.\d+)+)\b", r"version \1", text)  # v0.22.0
    return re.sub(r"\s+", " ", text).strip()


def _sentence(text: str) -> str:
    text = text.strip()
    return text if text[-1:] in ".?!" else text + "."


def _speech_plan(brief: Brief) -> list[list[tuple[tuple, str]]]:
    """Sections of (block key, spoken text), in page order.

    Headline and lead, each story with its signal, worth watching, bottom line.
    Leaves out what only works on screen: story numbers, day counters, source
    URLs and the sources-scanned note. The key names the page block that says
    the text, so a recording's paragraph times land on the right blocks (#7).
    """
    sections = [[(("title",), _sentence(brief.title)), (("lead",), brief.lead)]]
    for n, item in enumerate(brief.items):
        story = [(("item", n, "title"), _sentence(item.title))]
        story += [(("item", n, "body", j), para) for j, para in enumerate(item.body)]
        if item.signal:
            story.append((("item", n, "signal"), "Signal: " + _sentence(item.signal)))
        sections.append(story)
    if brief.watching:
        sections.append([(("watch", "head"), "Worth watching.")]
                        + [(("watch", k), w) for k, w in enumerate(brief.watching)])
    if brief.bottom_line:
        sections.append([(("bottom", "head"), "Bottom line."), (("bottom", "text"), brief.bottom_line)])
    spoken = [[(key, _spoken(text)) for key, text in section] for section in sections]
    return [[(key, text) for key, text in section if text] for section in spoken]


def speech(brief: Brief) -> list[list[str]]:
    """What the audio version says: sections of paragraphs, in page order."""
    return [[text for _, text in section] for section in _speech_plan(brief)]


def block_times(brief: Brief, audio: dict | None) -> dict[tuple, float]:
    """The second each page block starts in the recording, by block key (#7).

    The recorder reads one spoken paragraph at a time and notes where each
    starts, in the order of speech(); the keys come in the same order, so the
    two zip. Empty when the recording has no marks or they don't line up.
    """
    marks = (audio or {}).get("marks") or []
    keys = [key for section in _speech_plan(brief) for key, _ in section]
    if len(marks) != len(keys):
        return {}
    return dict(zip(keys, marks))


def speech_sha(brief: Brief) -> str:
    """The recording's key. Any change to what would be read changes it."""
    return hashlib.sha256(json.dumps(speech(brief)).encode()).hexdigest()[:16]


def load_audio(out: Path, briefs: list[Brief]) -> dict[str, dict]:
    """Recordings that still match their brief, by slug. Stale ones are dropped."""
    manifest_path = out / AUDIO_DIR / "manifest.json"
    if not manifest_path.exists():
        return {}
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    found = {}
    for brief in briefs:
        entry = manifest.get(brief.slug)
        if (
            entry
            and entry.get("sha") == speech_sha(brief)
            and (out / AUDIO_DIR / entry["file"]).exists()
        ):
            found[brief.slug] = entry
    return found


def _clock(seconds: float) -> str:
    seconds = round(seconds)
    return f"{seconds // 60}:{seconds % 60:02d}"


def _asset_version(path: Path) -> str:
    """A cache-buster that changes only when the file does."""
    return hashlib.sha256(path.read_bytes()).hexdigest()[:8] if path.exists() else "0"


# Square caps, like the timeline marks. The play triangle and pause bars are filled.
LISTEN_ICONS = {
    "play": '<svg class="listen__i-play" viewBox="0 0 24 24" width="28" height="28" aria-hidden="true"><path d="M7 4.5v15L19.5 12z"/></svg>',
    "pause": '<svg class="listen__i-pause" viewBox="0 0 24 24" width="28" height="28" aria-hidden="true"><path d="M6 4.5h4.5v15H6zM13.5 4.5H18v15h-4.5z"/></svg>',
    "back": '<svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true"><path d="M3 12a9 9 0 1 0 2.64-6.36"/><path d="M3 3v6h6"/></svg>',
    "forward": '<svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true"><path d="M21 12a9 9 0 1 1-2.64-6.36"/><path d="M21 3v6h-6"/></svg>',
    "cast": '<svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true"><path d="M7 17H3V4h18v13h-4"/><path d="M12 14l5 6H7z"/></svg>',
    "prev": '<svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true"><path d="M6 5v14"/><path d="M18 5l-9 7 9 7z"/></svg>',
    "next": '<svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true"><path d="M18 5v14"/><path d="M6 5l9 7-9 7z"/></svg>',
}


def listen_player(brief: Brief, audio: dict, paragraphs: int = 0) -> str:
    """The brief's audio player.

    The native <audio controls> is the no-script fallback. js/listen.js turns
    on the .listen__player card and drives that same element, which is what
    keeps lock-screen controls and background play working on a phone. With
    paragraph times on the page (#7) the skips become previous / next paragraph. html.js
    is set in the head, so nothing shifts when the script arrives.
    """
    src = f"../{AUDIO_DIR}/{audio['file']}"
    length, seconds = _clock(audio["seconds"]), audio["seconds"]
    i = LISTEN_ICONS
    if paragraphs >= 3:
        steps = (f'<button class="listen__btn" type="button" data-para="-1" aria-label="Previous paragraph">{i["prev"]}<span aria-hidden="true">&para;</span></button>\n'
                 f'              <button class="listen__btn" type="button" data-para="1" aria-label="Next paragraph"><span aria-hidden="true">&para;</span>{i["next"]}</button>')
    else:
        steps = (f'<button class="listen__btn" type="button" data-skip="-15" aria-label="Back 15 seconds">{i["back"]}<span>15</span></button>\n'
                 f'              <button class="listen__btn" type="button" data-skip="30" aria-label="Forward 30 seconds"><span>30</span>{i["forward"]}</button>')
    return f"""      <div class="listen" id="listen" data-title="{E(brief.title)}" data-date="{E(brief.stamp)}" data-slug="{E(brief.slug)}" data-duration="{seconds}">
        <p class="listen__label">Listen &middot; {length} &middot; read by an AI voice</p>
        <audio controls preload="none" src="{E(src)}">
          <a href="{E(src)}">Download the audio (MP3)</a>
        </audio>
        <div class="listen__player">
          <button class="listen__play" type="button" aria-label="Play the brief">{i["play"]}{i["pause"]}</button>
          <div class="listen__main">
            <p class="listen__head"><span class="listen__title">Listen<span class="listen__more"> to this brief</span></span><span class="listen__time"><span class="listen__cur">0:00</span> / <span class="listen__dur">{length}</span></span></p>
            <input class="listen__seek" type="range" min="0" max="{int(seconds)}" step="1" value="0" aria-label="Position in the audio">
            <div class="listen__row">
              {steps}
              <button class="listen__btn listen__rate" type="button" aria-label="Playback speed 1×">1×</button>
              <button class="listen__btn listen__cast" type="button" aria-label="Play on another device" hidden>{i["cast"]}</button>
              <p class="listen__note"><span class="listen__more">Read by an </span>AI voice &middot; <a href="{E(src)}" download aria-label="Download the MP3">MP3 <span aria-hidden="true">&darr;</span></a></p>
            </div>
          </div>
        </div>
      </div>"""


# ---------------------------------------------------------------- rendering

E = html.escape


def page(
    title: str,
    description: str,
    depth: int,
    body: str,
    path: str | None,
    cover: Cover | None = None,
    share_title: str | None = None,
    audio: bool = False,
    up: str | None = None,
) -> str:
    up = "../" * depth if up is None else up
    url = SITE_URL + (path or "")
    share = [
        f'<link rel="canonical" href="{E(url)}">',
        '<meta property="og:site_name" content="AI Brief">',
        f'<meta property="og:type" content="{"article" if depth else "website"}">',
        f'<meta property="og:title" content="{E(share_title or title)}">',
        f'<meta property="og:description" content="{E(description)}">',
        f'<meta property="og:url" content="{E(url)}">',
    ]
    if cover:
        share.append(f'<meta property="og:image" content="{E(cover.image)}">')
        share.append('<meta name="twitter:card" content="summary_large_image">')
    if path is None:
        # Not a page of its own (the 404): nothing to share or index.
        share = ['<meta name="robots" content="noindex">']
    if audio:
        # The site's only script. Set html.js before paint so the player card,
        # not the native control, is what renders first; undo it if the
        # script fails to load.
        share.append("<script>document.documentElement.classList.add('js')</script>")
        share.append(
            f'<script defer src="{up}js/listen.js?v={_asset_version(ROOT / "js/listen.js")}" '
            "onerror=\"document.documentElement.classList.remove('js')\"></script>"
        )
    head = "\n".join(share)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{E(title)}</title>
<meta name="description" content="{E(description)}">
{head}
{FONTS}
<link rel="stylesheet" href="{up}css/main.css?v={_asset_version(ROOT / "css/main.css")}">
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
    <p style="margin:0"><a href="{up}index.html">&larr; All briefs</a> &middot; <a href="{HOME_URL}">heybrahim.com</a></p>
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


def cover_figure(cover: Cover) -> str:
    """The main picture, credited to the page it came from.

    It opens the page, above the headline, so it is never lazy-loaded. The fixed frame ratio reserves
    the space before the image arrives, and `object-fit: cover` crops whatever
    shape the publisher chose into it.
    """
    which = "" if cover.rank == 1 else f" &middot; story {cover.rank:02d}"
    return (
        '      <figure class="cover">\n'
        '        <div class="cover__frame">'
        f'<img src="{E(cover.image)}" alt="{E(cover.alt)}" width="1200" height="630" '
        'fetchpriority="high" decoding="async" referrerpolicy="no-referrer"></div>\n'
        f'        <figcaption class="cover__credit">Picture: '
        f'<a href="{E(cover.page)}">{E(cover.credit)}</a>{which}</figcaption>\n'
        "      </figure>"
    )


def render_brief(
    brief: Brief, stories: dict[str, Story], cover: Cover | None, audio: dict | None
) -> str:
    dateline = [f"<span>AI BRIEF</span>", f"<span>{E(brief.stamp)}</span>"]
    if brief.time:
        dateline.append(f"<span>{E(brief.time.upper())}</span>")
    bar = '<span class="dateline__sep">&middot;</span>'.join(dateline)

    # Paragraph times (#7): the block being read is marked and the player steps
    # by paragraph. Each spoken paragraph knows its block, so this is a lookup.
    times = block_times(brief, audio)

    def at(*key) -> str:
        return f' data-t="{times[key]}"' if key in times else ""

    out = ['  <div class="band">\n    <div class="container">']
    if cover:
        out.append(cover_figure(cover))
    if audio:
        # Under the picture, above a headline that runs to six lines on a
        # phone: play is on the first screen.
        out.append(listen_player(brief, audio, paragraphs=len(times)))
    out.append(f'      <p class="dateline">{bar}</p>')
    out.append(f"      <h1{at('title')}>{E(brief.title)}</h1>")
    if brief.lead:
        out.append(f'      <p class="lead"{at("lead")}>{E(brief.lead)}</p>')
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
        n = rank - 1
        out.append(f'        <h3 class="story__title"{at("item", n, "title")}>{E(item.title)}</h3>')
        for j, para in enumerate(item.body):
            out.append(f'        <p{at("item", n, "body", j)}>{E(para)}</p>')
        if item.signal:
            out.append(
                f'        <p class="story__signal"{at("item", n, "signal")}><strong>Signal:</strong> {E(item.signal)}</p>'
            )
        if item.source:
            out.append(f'        <p class="story__source">Source: {E(item.source)}</p>')
        out.append("      </article>")
    out.append("    </div>\n  </div>\n")

    if brief.watching:
        out.append('  <div class="band band--wire">\n    <div class="container">')
        out.append(f'      <span class="slug"{at("watch", "head")}>Worth watching</span>\n      <ul class="watch">')
        out.extend(f'        <li{at("watch", k)}>{E(w)}</li>' for k, w in enumerate(brief.watching))
        out.append("      </ul>\n    </div>\n  </div>\n")

    if brief.bottom_line or brief.sources:
        out.append('  <div class="band band--sunk">\n    <div class="container">')
        out.append('      <div class="cols cols--2">')
        out.append('        <div class="block block--paper">')
        out.append(f'          <span class="slug"{at("bottom", "head")}>Bottom line</span>')
        out.append(f'          <p class="lead" style="margin:0"{at("bottom", "text")}>{E(brief.bottom_line)}</p>')
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


def render_index(
    briefs: list[Brief], stories: dict[str, Story], cover: Cover | None, audio: dict | None
) -> str:
    latest = briefs[0]
    dateline = [f"<span>LATEST</span>", f"<span>{E(latest.stamp)}</span>"]
    if latest.time:
        dateline.append(f"<span>{E(latest.time.upper())}</span>")
    bar = '<span class="dateline__sep">&middot;</span>'.join(dateline)

    out = [
        '  <div class="band">\n    <div class="container">',
        *([cover_figure(cover)] if cover else []),
        f'      <p class="dateline">{bar}</p>',
        f"      <h1>{E(latest.title)}</h1>",
        f'      <p class="lead">{E(latest.lead)}</p>',
        '      <p style="display:flex;flex-wrap:wrap;gap:0.75rem">'
        f'<a class="btn" href="briefs/{E(latest.slug)}.html">Read the brief</a>'
        + (
            f' <a class="btn btn--ghost" href="briefs/{E(latest.slug)}.html#listen">'
            f'Listen &middot; {_clock(audio["seconds"])}</a>'
            if audio
            else ""
        )
        + "</p>",
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


# The 404 page waits for a brief this young: Victor sends the link the moment he
# writes the file, about a minute before GitHub Pages has the page up.
WAIT_SCRIPT = """<script>
(function () {
  var m = location.pathname.match(/\\/briefs\\/(\\d{4}-\\d{2}-\\d{2})\\.html$/);
  var age = m ? (Date.now() - Date.parse(m[1] + 'T00:00:00Z')) / 864e5 : NaN;
  if (!(age > -1 && age < 2)) return;
  var status = document.getElementById('missing-status');
  document.getElementById('missing-slug').textContent = 'Publishing';
  document.getElementById('missing-title').textContent = 'This brief is on its way';
  document.getElementById('missing-lead').textContent =
    'It was filed a moment ago and goes live about a minute after the message is sent. ' +
    'This page opens it by itself as soon as it is up.';
  var tries = 0;
  function check() {
    tries++;
    fetch(location.pathname + '?live=' + Date.now(), { method: 'HEAD', cache: 'no-store' })
      .then(function (r) { if (r.ok) location.reload(); else later(); }, later);
  }
  function later() {
    if (tries >= 30) {
      status.textContent = 'Still not up after four minutes, so it may not have published. Every brief that did is in the archive.';
      return;
    }
    status.textContent = 'Checking every few seconds…';
    setTimeout(check, 8000);
  }
  check();
})();
</script>"""


def render_missing() -> str:
    """404.html. GitHub Pages serves it for any missing address in the archive.

    Its default 404 is a dead end, and the most common way here is a brief
    link opened from Telegram before the page is live. So for a recent brief
    this page says it is on its way and opens it when it is up (WAIT_SCRIPT).
    The text without script covers both cases.
    """
    return "\n".join([
        '  <div class="band">\n    <div class="container">',
        '      <p class="dateline"><span>AI BRIEF</span><span class="dateline__sep">&middot;</span>'
        '<span id="missing-slug">Not found</span></p>',
        '      <h1 id="missing-title">Not here, or not yet</h1>',
        '      <p class="lead" id="missing-lead">A brief goes live about a minute after its message is '
        "sent. If you followed a link from one just now, reload in a moment. Otherwise this address "
        "does not exist.</p>",
        '      <p class="caption" id="missing-status" role="status" style="margin-bottom:1.5rem"></p>',
        f'      <p><a class="btn" href="{E(urlparse(SITE_URL).path)}index.html">All briefs</a></p>',
        "    </div>\n  </div>\n",
        WAIT_SCRIPT,
    ])


# ---------------------------------------------------------------- driver


def render_sitemap(briefs: list[Brief], stories: dict[str, Story]) -> str:
    """sitemap.xml. The archive is a host of its own, so it lists its own pages."""
    entries = [(SITE_URL, briefs[0].slug)]
    entries += [(f"{SITE_URL}briefs/{b.slug}.html", b.slug) for b in briefs]
    entries += [(f"{SITE_URL}stories/{s.slug}.html", None) for s in stories.values() if s.is_running]
    rows = [
        f"  <url><loc>{E(loc)}</loc>" + (f"<lastmod>{day}</lastmod>" if day else "") + "</url>"
        for loc, day in entries
    ]
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "\n".join(rows)
        + "\n</urlset>\n"
    )


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    ap.add_argument("--out", type=Path, default=ROOT)
    ap.add_argument("--check", action="store_true", help="parse only, write nothing")
    ap.add_argument(
        "--no-fetch", action="store_true", help="never look up pictures; use images.json only"
    )
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

    # Each brief's picture is looked up once and kept here, so a re-render is
    # offline and gives the same page every time.
    cache_path = args.out / "images.json"
    cache = json.loads(cache_path.read_text(encoding="utf-8")) if cache_path.exists() else {}
    covers = {b.slug: resolve_cover(b, cache, fetch=not args.no_fetch) for b in briefs}
    cache_path.write_text(json.dumps(cache, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    recordings = load_audio(args.out, briefs)

    for brief in briefs:
        (args.out / "briefs" / f"{brief.slug}.html").write_text(
            page(
                f"AI Brief — {brief.stamp.title()}",
                brief.lead or brief.title,
                1,
                render_brief(brief, stories, covers[brief.slug], recordings.get(brief.slug)),
                f"briefs/{brief.slug}.html",
                cover=covers[brief.slug],
                share_title=brief.title,
                audio=brief.slug in recordings,
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
                f"stories/{story.slug}.html",
            ),
            encoding="utf-8",
        )

    (args.out / "index.html").write_text(
        page(
            "AI Brief — wire archive",
            "The durable layer behind a Telegram AI briefing: running stories tracked "
            "over time, full sources, and every brief kept.",
            0,
            render_index(briefs, stories, covers[briefs[0].slug], recordings.get(briefs[0].slug)),
            "",
            cover=covers[briefs[0].slug],
        ),
        encoding="utf-8",
    )

    # Served for missing addresses at any depth, so every link in it is absolute.
    (args.out / "404.html").write_text(
        page(
            "Not found — AI Brief",
            "This address is not in the AI brief archive, or not yet.",
            0,
            render_missing(),
            None,
            up=urlparse(SITE_URL).path,
        ),
        encoding="utf-8",
    )

    (args.out / "sitemap.xml").write_text(render_sitemap(briefs, stories), encoding="utf-8")
    (args.out / "robots.txt").write_text(
        f"User-agent: *\nAllow: /\n\nSitemap: {SITE_URL}sitemap.xml\n", encoding="utf-8"
    )

    pictured = sum(1 for c in covers.values() if c)
    print(f"wrote {len(briefs)} brief page(s), {running} story page(s), index.html")
    print(f"pictures on {pictured} of {len(briefs)} brief(s)")
    print(f"audio on {len(recordings)} of {len(briefs)} brief(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

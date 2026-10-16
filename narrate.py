#!/usr/bin/env python3
"""Record the audio version of each brief with a local voice.

Kokoro-82M (voice af_heart) through mlx-audio, on the mini: no API, no cost.
It needs its own venv, built by tts/setup.sh, so run it with that interpreter:

    VENV=~/.local/share/ai-brief-tts/venv/bin/python
    $VENV narrate.py                       # record whatever is new or changed
    $VENV narrate.py --date 2026-10-14     # one brief only
    $VENV narrate.py --force               # re-record even if up to date
    python3 narrate.py --say 2026-10-14    # print what would be read (no venv needed)

The words come from publish.speech(), so the page and the recording can never
disagree about what a brief says. Writes audio/<date>.mp3 and
audio/manifest.json. Each manifest entry carries the hash of the text it read;
publish.py shows a player only while that hash still matches the brief. It also
carries "marks" (#7): the second each spoken paragraph starts, known exactly
because the voice reads one paragraph at a time. publish.py puts them on the
page's blocks, and the player follows the brief paragraph by paragraph. A
recording without marks (made before #7) counts as out of date and is re-recorded.

Briefs before NARRATE_FROM stay text-only.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
import time
import wave
from datetime import date as Date
from pathlib import Path

import publish

NARRATE_FROM = Date(2026, 9, 5)

MODEL = "mlx-community/Kokoro-82M-bf16"
VOICE = "af_heart"
LANG = "a"  # American English
SPEED = 1.0  # the player has its own speed control

# Silence, in seconds. A story change needs to be audible with the phone in a
# pocket, so the gap between sections is about twice the one between paragraphs.
PARAGRAPH_GAP = 0.5
SECTION_GAP = 1.1

# Speech is mono at Kokoro's 24 kHz, so 40 kbps MP3 is plenty: about 300 KB a minute.
BITRATE = "40k"


def say(brief: publish.Brief) -> str:
    return "\n\n".join("\n".join(section) for section in publish.speech(brief))


def record(model, brief: publish.Brief, wav: Path) -> tuple[float, list[float]]:
    """Read the brief into a 16-bit mono WAV, paragraph by paragraph.

    Returns the seconds and the marks: where each spoken paragraph starts, in
    the order of publish.speech() (#7)."""
    import numpy as np

    rate = 24_000
    pieces, marks, samples = [], [], 0

    def add(piece):
        nonlocal samples
        pieces.append(piece)
        samples += len(piece)

    for s, section in enumerate(publish.speech(brief)):
        if s:
            add(np.zeros(int(SECTION_GAP * rate), dtype=np.float32))
        for p, paragraph in enumerate(section):
            if p:
                add(np.zeros(int(PARAGRAPH_GAP * rate), dtype=np.float32))
            marks.append(round(samples / rate, 2))
            for result in model.generate(text=paragraph, voice=VOICE, speed=SPEED, lang_code=LANG):
                rate = result.sample_rate
                add(np.asarray(result.audio, dtype=np.float32).reshape(-1))
    add(np.zeros(int(0.6 * rate), dtype=np.float32))

    audio = np.concatenate(pieces)
    pcm = (np.clip(audio, -1.0, 1.0) * 32767).astype("<i2")
    with wave.open(str(wav), "wb") as out:
        out.setnchannels(1)
        out.setsampwidth(2)
        out.setframerate(rate)
        out.writeframes(pcm.tobytes())
    return len(audio) / rate, marks


def encode(wav: Path, mp3: Path, brief: publish.Brief) -> None:
    """Loudness-normalise to -16 LUFS (the podcast norm) and encode, tagged."""
    subprocess.run(
        [
            "ffmpeg", "-v", "error", "-y", "-i", str(wav),
            "-af", "loudnorm=I=-16:TP=-1.5:LRA=11",
            "-ar", "24000", "-ac", "1", "-c:a", "libmp3lame", "-b:a", BITRATE,
            "-id3v2_version", "3",
            "-metadata", f"title={brief.title}",
            "-metadata", "artist=AI Brief",
            "-metadata", "album=heybrahim.com",
            "-metadata", f"date={brief.slug}",
            str(mp3),
        ],
        check=True,
    )


def duration(mp3: Path) -> float:
    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(mp3)],
        check=True, capture_output=True, text=True,
    )
    return round(float(probe.stdout.strip()), 2)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--source", type=Path, default=publish.DEFAULT_SOURCE)
    ap.add_argument("--out", type=Path, default=publish.ROOT)
    ap.add_argument("--date", help="only this brief (YYYY-MM-DD)")
    ap.add_argument("--force", action="store_true", help="re-record even if up to date")
    ap.add_argument("--say", metavar="DATE", help="print what the voice would read, then stop")
    args = ap.parse_args()

    try:
        briefs = publish.load_briefs(args.source)
    except publish.BriefError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    if args.say:
        brief = next((b for b in briefs if b.slug == args.say), None)
        if not brief:
            print(f"error: no brief for {args.say}", file=sys.stderr)
            return 1
        print(say(brief))
        return 0

    folder = args.out / publish.AUDIO_DIR
    manifest_path = folder / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else {}
    voice = f"kokoro/{VOICE}"

    todo = []
    for brief in briefs:
        if brief.date < NARRATE_FROM or (args.date and brief.slug != args.date):
            continue
        entry = manifest.get(brief.slug) or {}
        current = (
            entry.get("sha") == publish.speech_sha(brief)
            and entry.get("voice") == voice
            and entry.get("file")
            and entry.get("marks")
            and (folder / entry["file"]).exists()
        )
        if args.force or not current:
            todo.append(brief)
    if not todo:
        print("audio up to date")
        return 0

    from mlx_audio.tts.utils import load_model

    folder.mkdir(parents=True, exist_ok=True)
    model = load_model(MODEL)
    failed = 0
    for brief in sorted(todo, key=lambda b: b.date):
        started = time.monotonic()
        mp3 = folder / f"{brief.slug}.mp3"
        try:
            with tempfile.TemporaryDirectory() as tmp:
                wav, part = Path(tmp) / "speech.wav", Path(tmp) / "speech.mp3"
                _, marks = record(model, brief, wav)
                encode(wav, part, brief)
                os.replace(part, mp3)
        except Exception as exc:  # one bad brief must not stop the rest
            print(f"error: {brief.slug} not recorded ({exc})", file=sys.stderr)
            failed += 1
            continue
        manifest[brief.slug] = {
            "file": mp3.name,
            "sha": publish.speech_sha(brief),
            "voice": voice,
            "seconds": duration(mp3),
            "bytes": mp3.stat().st_size,
            "marks": marks,
        }
        manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        entry = manifest[brief.slug]
        print(
            f"recorded {brief.slug}: {publish._clock(entry['seconds'])}, "
            f"{entry['bytes'] / 1e6:.1f} MB, in {time.monotonic() - started:.0f}s"
        )
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())

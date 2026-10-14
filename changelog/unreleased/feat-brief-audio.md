### Added
- An audio version of each brief from 2026-10-14 on, read by a local voice (Kokoro, `af_heart`) and recorded on the mini by `narrate.py` (#3).
- A player under the main picture. It works with the screen locked and shows the headline on the lock screen. It has back 15 s / forward 30 s, speed, a docked mini-player and resume, and it says it is an AI voice. Without JavaScript the browser's own control shows. The index gets a "Listen" link.
- `tts/setup.sh` and pinned `tts/requirements.txt` for the voice venv, kept outside the repo.

### Changed
- `publish-hook.sh` pushes the text first, then records and pushes the audio, so a slow or failed recording never holds a brief back.
- The stylesheet and script URLs carry a content hash, so a deploy is never served with a stale cached stylesheet.

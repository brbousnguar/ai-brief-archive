### Added
- Each brief opens with a main picture: the share image of its first story that has one, hotlinked and credited, cached in `images.json` (#1).
- Canonical URLs and Open Graph tags on every page, so a shared brief previews with its picture.

### Changed
- Every link, log line and canonical URL now uses `https://heybrahim.com/ai-brief-archive/` instead of the github.io address.
- `publish-hook.sh` pulls before rendering and only publishes from `main`, so a merged PR no longer gets the next push rejected.

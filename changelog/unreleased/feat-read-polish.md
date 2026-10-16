### Changed
- Every source on brief and story pages is a link, labelled with its host and path (#13)
- On screens 900px and wider the picture and player sit beside the dateline, headline and lead, so the first screen carries the brief; the headline scale steps down and long headlines get a size of their own, with a break opportunity after every "/" (#13)
- `<title>` carries the headline; datelines are `<time>` elements; each brief has `article:published_time` and NewsArticle structured data (#13)
- "Sources scanned" reads "X/Twitter following feed, plus …" instead of the agent's profile name (#13)
- Fonts are served from `fonts/` instead of Google Fonts and cached by the service worker, so the installed app renders in its own faces offline (#13)

### Added
- Previous / next brief at the end of each brief (#13)
- A picture whose hotlink has died hides itself instead of showing a broken image (#13)

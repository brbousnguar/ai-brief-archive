### Added
- Every brief, story page, the index and the stories list say under the dateline that Victor, an AI agent, wrote the text from public sources and that it went out without human review; the plain-text copy and each feed entry carry the same line (EU AI Act art. 50(4), #33)
- Brief pages mark their text as AI-generated in their NewsArticle structured data (`digitalSourceType`, schema.org's member for IPTC's `trainedAlgorithmicMedia`), and new recordings carry an ID3 comment, "Synthetic voice; text written by an AI agent"; existing recordings are not retagged (#33)
- A `correction:` front-matter key, shown as a note at the end of the brief, its plain text and its feed entry (#33)
- The OFL licence text for Archivo, IBM Plex Mono and Source Serif 4 under `fonts/` (#33)

### Changed
- About: a brief can now be corrected, or a passage removed, when it is wrong or someone has a legal reason to ask, with the change noted at the bottom; corrections and removal requests go to a direct email address (#33)
- About: the privacy part says the cover picture is loaded from the publisher's server, which sees the reader's IP address and browser and may set a security cookie, and that the site keeps an offline copy of its pages in the browser; "Nothing else is collected" is gone (#33)
- The cover credit reads "Picture via <domain>" (#33)
- Google Analytics' cookie lasts 13 months from the first visit and is no longer extended by each visit (`cookie_update: false`) (#33)

### Fixed
- Agency photos (Getty, AFP, Reuters, AP, Shutterstock, Alamy, EPA, Bloomberg) are no longer used as a brief's picture; three briefs now render without one (#33)

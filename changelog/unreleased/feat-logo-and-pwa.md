### Added
- A logo: punched teletype tape on wire blue, the last hole stamped red, drawn by `tools/make_icons.py` into a favicon, an Apple touch icon, PWA icons and the masthead (#11).
- The archive installs as an app: `site.webmanifest`, iOS home-screen meta and a service worker. Pages load network-first so a new brief is never hidden behind a cached one, CSS/JS/icons are cached by hash, the last pages open offline, and audio is left alone (#11).

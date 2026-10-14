/* AI Brief audio player — the site's only script.

   Ported from the heybrahim.com notes player. The card and the docked
   mini-player are a skin over the brief's own <audio>, which stays in the page:
   without this script (or before it loads) the native control shows instead.
   Playing the real element is what keeps the lock-screen controls, background
   play and AirPlay working on a phone; Media Session adds the headline and the
   skip buttons there. The position is kept per brief in localStorage, best
   effort, so a walk can stop and pick up again. */
(function () {
  var root = document.querySelector('.listen');
  var ui = root && root.querySelector('.listen__player');
  if (!ui) return;
  var audio = root.querySelector('audio');
  var play = ui.querySelector('.listen__play');
  var seek = ui.querySelector('.listen__seek');
  var title = ui.querySelector('.listen__title');
  var cur = ui.querySelector('.listen__cur');
  var dur = ui.querySelector('.listen__dur');
  var rateBtn = ui.querySelector('.listen__rate');
  var cast = ui.querySelector('.listen__cast');
  var name = root.dataset.title;
  var titleHTML = title.innerHTML;
  var key = 'aibrief:listen:' + root.dataset.slug;
  var RATES = [1, 1.25, 1.5, 1.75, 2, 0.75];

  var total = +root.dataset.duration;
  var pending = null;      // a position chosen before the file's metadata arrived
  var dragging = false;
  var started = false;     // the dock only appears once something has played
  var dismissed = false;
  var cardVisible = true;
  var savedAt = 0;

  function store(k, v) {
    try { v === null ? localStorage.removeItem(k) : localStorage.setItem(k, String(v)); } catch (e) {}
  }
  function recall(k) {
    try { return localStorage.getItem(k); } catch (e) { return null; }
  }

  function clock(s) {
    s = Math.max(0, Math.floor(s || 0));
    var h = Math.floor(s / 3600), m = Math.floor(s / 60) % 60, r = ('0' + (s % 60)).slice(-2);
    return h ? h + ':' + ('0' + m).slice(-2) + ':' + r : m + ':' + r;
  }
  function spoken(s) {
    s = Math.max(0, Math.floor(s || 0));
    var m = Math.floor(s / 60), r = s % 60;
    return (m ? m + (m === 1 ? ' minute ' : ' minutes ') : '') + r + (r === 1 ? ' second' : ' seconds');
  }
  function now() {
    return audio.readyState ? audio.currentTime : (pending || 0);
  }

  // ── Docked mini-player ──────────────────────────────────────────────────
  var dock = document.createElement('div');
  dock.className = 'dock';
  dock.hidden = true;
  dock.setAttribute('role', 'region');
  dock.setAttribute('aria-label', 'Audio player');
  dock.innerHTML =
    '<div class="dock__bar" aria-hidden="true"><span></span></div>' +
    '<div class="container dock__row">' +
      play.outerHTML.replace('listen__play', 'listen__play dock__play') +
      '<a class="dock__title" href="#listen"></a>' +
      '<p class="dock__time"><span class="listen__cur">0:00</span><span class="dock__dur"> / ' + clock(total) + '</span></p>' +
      '<button class="dock__close" type="button" aria-label="Pause and close the mini-player">' +
        '<svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true"><path d="M6 6l12 12M18 6L6 18"/></svg>' +
      '</button>' +
    '</div>';
  dock.querySelector('.dock__title').textContent = name;
  document.body.appendChild(dock);
  var dockPlay = dock.querySelector('.listen__play');
  var dockCur = dock.querySelector('.listen__cur');
  var dockDur = dock.querySelector('.dock__dur');
  var dockBar = dock.querySelector('.dock__bar span');

  function placeDock() {
    var show = started && !dismissed && !cardVisible && !audio.ended;
    if (dock.hidden === !show) return;
    if (!show && dock.contains(document.activeElement)) play.focus({ preventScroll: true });
    dock.hidden = !show;
    document.documentElement.classList.toggle('has-dock', show);
  }

  // ── Rendering ───────────────────────────────────────────────────────────
  function render(t) {
    if (t === undefined) t = now();
    var p = total ? Math.min(100, (t / total) * 100) : 0;
    if (!dragging) seek.value = t;
    seek.style.setProperty('--p', p + '%');
    seek.setAttribute('aria-valuetext', spoken(t) + ' of ' + spoken(total));
    cur.textContent = dockCur.textContent = clock(t);
    dockBar.style.width = p + '%';
  }

  function setTotal(s) {
    if (!isFinite(s) || s <= 0) return;
    total = s;
    seek.max = Math.floor(s);
    dur.textContent = clock(s);
    dockDur.textContent = ' / ' + clock(s);
  }

  function playing(on) {
    root.classList.toggle('is-playing', on);
    dock.classList.toggle('is-playing', on);
    var label = on ? 'Pause' : (now() > 0 && !audio.ended ? 'Resume from ' + clock(now()) : 'Play the brief');
    play.setAttribute('aria-label', label);
    dockPlay.setAttribute('aria-label', on ? 'Pause' : 'Play');
    if ('mediaSession' in navigator) navigator.mediaSession.playbackState = on ? 'playing' : 'paused';
  }

  function save(t, force) {
    if (!force && Date.now() - savedAt < 4000) return;
    savedAt = Date.now();
    store(key, t > 5 && t < total - 10 ? Math.floor(t) : null);
  }

  // ── Actions ─────────────────────────────────────────────────────────────
  function goTo(t) {
    t = Math.max(0, Math.min(total || 0, t));
    if (audio.readyState) audio.currentTime = t;
    else pending = t;
    render(t);
    save(t, true);
    if (audio.paused) playing(false);
  }

  function start() {
    dismissed = false;
    var p = audio.play();
    if (p && p.catch) p.catch(function () {});
  }
  function toggle() {
    if (audio.paused || audio.ended) start();
    else audio.pause();
  }

  play.addEventListener('click', toggle);
  dockPlay.addEventListener('click', toggle);
  dock.querySelector('.dock__close').addEventListener('click', function () {
    audio.pause();
    dismissed = true;
    placeDock();
  });

  ui.querySelectorAll('[data-skip]').forEach(function (b) {
    b.addEventListener('click', function () { goTo(now() + +b.dataset.skip); });
  });

  seek.addEventListener('input', function () {
    dragging = true;
    render(+seek.value);
  });
  seek.addEventListener('change', function () {
    dragging = false;
    goTo(+seek.value);
  });
  seek.addEventListener('keydown', function (e) {
    var step = { ArrowLeft: -5, ArrowDown: -5, ArrowRight: 5, ArrowUp: 5, PageDown: -30, PageUp: 30 }[e.key];
    if (!step) return;
    e.preventDefault();
    goTo(now() + step);
  });

  function setRate(r) {
    audio.defaultPlaybackRate = audio.playbackRate = r;
    rateBtn.textContent = r + '×';
    rateBtn.setAttribute('aria-label', 'Playback speed ' + r + '×');
  }
  rateBtn.addEventListener('click', function () {
    var r = RATES[(RATES.indexOf(audio.playbackRate) + 1) % RATES.length] || 1;
    setRate(r);
    store('aibrief:listen:rate', r === 1 ? null : r);
  });

  // ── Media element events ────────────────────────────────────────────────
  audio.addEventListener('loadedmetadata', function () {
    setTotal(audio.duration);
    if (pending !== null) { audio.currentTime = pending; pending = null; }
  });
  audio.addEventListener('play', function () {
    started = true;
    if (!root.classList.contains('is-error')) title.innerHTML = titleHTML;
    playing(true);
    placeDock();
  });
  audio.addEventListener('pause', function () { playing(false); save(audio.currentTime, true); });
  audio.addEventListener('waiting', function () { root.classList.add('is-loading'); });
  audio.addEventListener('playing', function () { root.classList.remove('is-loading'); });
  audio.addEventListener('timeupdate', function () {
    if (pending !== null) return;
    render(audio.currentTime);
    save(audio.currentTime);
    if ('mediaSession' in navigator && navigator.mediaSession.setPositionState && isFinite(audio.duration)) {
      try {
        navigator.mediaSession.setPositionState({ duration: audio.duration, playbackRate: audio.playbackRate, position: audio.currentTime });
      } catch (e) {}
    }
  });
  audio.addEventListener('ended', function () {
    store(key, null);
    playing(false);
    placeDock();
  });
  audio.addEventListener('error', function () {
    root.classList.remove('is-loading');
    root.classList.add('is-error');
    title.textContent = 'Audio unavailable · try the MP3';
    playing(false);
  });

  // ── Dock visibility: only while the card is off screen ──────────────────
  if ('IntersectionObserver' in window) {
    new IntersectionObserver(function (entries) {
      cardVisible = entries[entries.length - 1].isIntersecting;
      placeDock();
    }).observe(root);
  }

  // ── Lock screen, headphones, car: Media Session ─────────────────────────
  if ('mediaSession' in navigator) {
    var ms = navigator.mediaSession;
    try {
      var art = [];
      var og = document.querySelector('meta[property="og:image"]');
      if (og) art.push({ src: og.content, sizes: '1200x630' });
      ms.metadata = new MediaMetadata({ title: name, artist: 'AI Brief · ' + root.dataset.date, album: 'heybrahim.com', artwork: art });
    } catch (e) {}
    [
      ['play', start],
      ['pause', function () { audio.pause(); }],
      ['seekbackward', function (d) { goTo(now() - (d.seekOffset || 15)); }],
      ['seekforward', function (d) { goTo(now() + (d.seekOffset || 30)); }],
      ['seekto', function (d) { goTo(d.seekTime); }]
    ].forEach(function (a) {
      try { ms.setActionHandler(a[0], a[1]); } catch (e) {}
    });
  }

  // ── Another device: AirPlay in Safari, Remote Playback elsewhere ────────
  if (window.WebKitPlaybackTargetAvailabilityEvent) {
    audio.addEventListener('webkitplaybacktargetavailabilitychanged', function (e) {
      cast.hidden = e.availability !== 'available';
    });
    cast.addEventListener('click', function () { audio.webkitShowPlaybackTargetPicker(); });
  } else if (audio.remote && audio.remote.watchAvailability) {
    audio.remote.watchAvailability(function (on) { cast.hidden = !on; }).catch(function () {});
    cast.addEventListener('click', function () { audio.remote.prompt().catch(function () {}); });
  }

  // ── Start: saved speed and position ─────────────────────────────────────
  var rate = +recall('aibrief:listen:rate');
  if (RATES.indexOf(rate) > 0) setRate(rate);
  var resume = +recall(key);
  if (resume > 5 && resume < total - 10) {
    pending = resume;
    title.textContent = 'Resume listening';
  }
  render();
  playing(false);
})();

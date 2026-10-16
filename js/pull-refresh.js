// Pull to refresh for the installed app. A browser tab has a reload button and its own
// pull-to-refresh; an app opened from the home screen has neither, so this runs only there.
// At the top of the page, drag down and let go past the mark: the page reloads. A short
// pull, a sideways swipe, a drag inside a scrolling panel or a form field, or an open
// dialog does nothing. No stylesheet and no inline style attribute: styles are set through
// the CSSOM and the spin is a Web Animation, so a strict style-src policy does not block it.
// Colours follow --ptr-bg / --ptr-fg, and the edge --ptr-shadow, when the page sets them.
(() => {
  const standalone =
    navigator.standalone === true || matchMedia("(display-mode: standalone), (display-mode: fullscreen)").matches;
  if (!standalone || !("ontouchstart" in window)) return;

  const ARM = 70; // indicator travel (px) that arms the reload; the finger moves twice that
  const MAX = 96;
  const still = matchMedia("(prefers-reduced-motion: reduce)").matches;
  // Android Chrome: no native pull-to-refresh fighting this one. iOS keeps its bounce.
  document.documentElement.style.overscrollBehaviorY = "contain";

  let el, arrow, x0, y0, state; // state: null | "maybe" | "pull" | "armed" | "busy"

  function build() {
    el = document.createElement("div");
    el.setAttribute("aria-hidden", "true");
    el.className = "ptr";
    Object.assign(el.style, {
      position: "fixed", top: "calc(env(safe-area-inset-top, 0px) + 8px)", left: "50%",
      width: "40px", height: "40px", margin: "0 0 0 -20px", borderRadius: "50%",
      display: "grid", placeItems: "center", zIndex: "2147483000", pointerEvents: "none",
      background: "var(--ptr-bg, Canvas)", color: "var(--ptr-fg, CanvasText)",
      boxShadow: "var(--ptr-shadow, 0 2px 10px rgba(0, 0, 0, .18))", opacity: "0", transform: "translateY(-64px)",
    });
    el.innerHTML =
      '<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round">' +
      '<path d="M20 12a8 8 0 1 1-2.34-5.66"/><path d="M20 4v5h-5"/></svg>';
    arrow = el.firstChild;
    document.body.appendChild(el);
  }

  function show(offset) {
    if (!el) build();
    const p = Math.min(offset / ARM, 1);
    el.style.transition = "none";
    el.style.opacity = String(p);
    el.style.transform = `translateY(${offset - 48}px)`;
    if (!still) arrow.style.transform = `rotate(${p * 270}deg)`;
    el.style.background = offset >= ARM ? "var(--ptr-fg, CanvasText)" : "var(--ptr-bg, Canvas)";
    el.style.color = offset >= ARM ? "var(--ptr-bg, Canvas)" : "var(--ptr-fg, CanvasText)";
  }

  function hide() {
    state = null;
    if (!el) return;
    el.style.transition = "transform .2s ease, opacity .2s ease";
    el.style.opacity = "0";
    el.style.transform = "translateY(-64px)";
  }

  // A touch that starts somewhere it means something else: fields, panels that scroll on
  // their own, dialogs, anything marked data-no-pull, or a page whose scroll is locked.
  function ignored(target) {
    const html = document.documentElement;
    if (getComputedStyle(document.body).overflowY === "hidden" || getComputedStyle(html).overflowY === "hidden") return true;
    if (document.querySelector("dialog[open]")) return true;
    for (let n = target; n && n !== document.body && n !== html; n = n.parentElement) {
      if (n.nodeType !== 1) continue;
      if (n.matches("input, textarea, select, [contenteditable=''], [contenteditable=true], [data-no-pull], [aria-modal=true]")) return true;
      const oy = getComputedStyle(n).overflowY;
      if ((oy === "auto" || oy === "scroll") && n.scrollHeight > n.clientHeight) return true;
    }
    return false;
  }

  const top = () => (document.scrollingElement || document.documentElement).scrollTop <= 0;

  addEventListener("touchstart", (e) => {
    if (state === "busy") return;
    state = null;
    if (e.touches.length !== 1 || !top() || ignored(e.target)) return;
    x0 = e.touches[0].clientX;
    y0 = e.touches[0].clientY;
    state = "maybe";
  }, { passive: true });

  addEventListener("touchmove", (e) => {
    if (!state || state === "busy") return;
    if (e.touches.length !== 1) return hide();
    const dx = e.touches[0].clientX - x0;
    const dy = e.touches[0].clientY - y0;
    if (state === "maybe") {
      if (Math.abs(dx) < 10 && Math.abs(dy) < 10) return;
      // Up, or more sideways than down: a scroll or a swipe, not a pull.
      if (dy <= 0 || Math.abs(dx) > dy) return (state = null);
      state = "pull";
    }
    if ((document.scrollingElement || document.documentElement).scrollTop > 2) return hide(); // the page scrolled after all
    const offset = Math.max(0, Math.min(MAX, dy / 2));
    state = offset >= ARM ? "armed" : "pull";
    show(offset);
  }, { passive: true });

  addEventListener("touchend", () => {
    if (state !== "armed") return hide();
    state = "busy";
    el.style.transition = "transform .15s ease";
    el.style.transform = `translateY(${ARM - 48}px)`;
    if (!still && arrow.animate) arrow.animate([{ transform: "rotate(0deg)" }, { transform: "rotate(360deg)" }], { duration: 700, iterations: Infinity });
    location.reload();
  }, { passive: true });

  addEventListener("touchcancel", () => { if (state !== "busy") hide(); }, { passive: true });
  // Back from the bfcache with a half-shown indicator: clear it.
  addEventListener("pageshow", () => { if (el) { state = null; hide(); } });
})();

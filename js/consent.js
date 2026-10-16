// AI Brief — ask before Google Analytics sets cookies (#25).
//
// Google's "basic" consent mode: nothing from Google loads until the reader
// says yes. The banner is in the page, `hidden`; this script shows it when
// there is no answer yet, or the answer is more than six months old (the
// CNIL's guidance). Yes loads gtag with ads storage, ad user data and ad
// personalisation denied, and host-only cookies that last 13 months. No, or
// withdrawing a yes from the footer's Cookies button, turns the tag off and
// deletes its cookies. The answer lives in localStorage; when that is
// blocked, nothing is stored and the reader is simply asked again.
//
// Cloudflare Web Analytics is a separate, cookieless beacon and is not
// affected.
(function () {
  var KEY = "ai-brief-consent";
  var MAX_AGE = 182 * 24 * 60 * 60 * 1000;   // about six months
  var COOKIE_SECONDS = 13 * 30 * 24 * 60 * 60; // 13 months
  var me = document.currentScript;
  var id = me && me.getAttribute("data-ga");
  var box = document.querySelector(".consent");
  if (!id || !box) return;
  var root = document.documentElement;
  var now = box.querySelector(".consent__now");
  var opener = document.querySelector("[data-consent-open]");
  var returnTo = null;  // focus goes back to the footer button only if it opened the banner
  var loaded = false;

  function read() {
    try {
      var saved = JSON.parse(localStorage.getItem(KEY));
      if (saved && (saved.v === "granted" || saved.v === "denied") && Date.now() - saved.t < MAX_AGE) {
        return saved;
      }
    } catch (e) {}
    return null;
  }

  function write(value) {
    try { localStorage.setItem(KEY, JSON.stringify({ v: value, t: Date.now() })); } catch (e) {}
  }

  function gtag() { window.dataLayer.push(arguments); }

  function load() {
    window["ga-disable-" + id] = false;
    if (loaded) {
      gtag("consent", "update", { analytics_storage: "granted" });
      return;
    }
    loaded = true;
    window.dataLayer = window.dataLayer || [];
    window.gtag = gtag;
    gtag("consent", "default", {
      analytics_storage: "granted",
      ad_storage: "denied",
      ad_user_data: "denied",
      ad_personalization: "denied"
    });
    gtag("js", new Date());
    gtag("config", id, {
      cookie_domain: "none",          // host-only: the cookie stays on this site
      cookie_expires: COOKIE_SECONDS,
      allow_google_signals: false,
      allow_ad_personalization_signals: false
    });
    var tag = document.createElement("script");
    tag.async = true;
    tag.src = "https://www.googletagmanager.com/gtag/js?id=" + encodeURIComponent(id);
    document.head.appendChild(tag);
  }

  function stop() {
    window["ga-disable-" + id] = true;
    if (loaded) gtag("consent", "update", { analytics_storage: "denied" });
    // Every Google Analytics cookie, host-only and on each parent domain:
    // the tag shipped in #23 set them on .heybrahim.com.
    var labels = location.hostname.split(".");
    document.cookie.split(";").forEach(function (pair) {
      var name = pair.split("=")[0].replace(/^\s+|\s+$/g, "");
      if (!/^(_ga|_ga_.+|_gid|_gat.*)$/.test(name)) return;
      document.cookie = name + "=; Max-Age=0; path=/";
      for (var i = 0; i < labels.length - 1; i++) {
        document.cookie = name + "=; Max-Age=0; path=/; domain=." + labels.slice(i).join(".");
      }
    });
  }

  function pad() {
    root.style.setProperty("--consent-h", box.offsetHeight + "px");
  }

  function show(saved) {
    if (now) {
      now.textContent = saved
        ? "Your answer: " + (saved.v === "granted" ? "accepted" : "refused") + " on " +
          new Date(saved.t).toLocaleDateString(undefined, { day: "numeric", month: "short", year: "numeric" }) + "."
        : "";
      now.hidden = !saved;
    }
    box.hidden = false;
    root.classList.add("has-consent");
    pad();
  }

  function hide() {
    box.hidden = true;
    root.classList.remove("has-consent");
  }

  function answer(value) {
    write(value);
    hide();
    if (value === "granted") load(); else stop();
    if (returnTo) returnTo.focus();
    returnTo = null;
  }

  Array.prototype.forEach.call(box.querySelectorAll("[data-consent]"), function (button) {
    button.addEventListener("click", function () { answer(button.getAttribute("data-consent")); });
  });
  window.addEventListener("resize", function () { if (!box.hidden) pad(); });

  if (opener) {
    var wrap = document.querySelector("[data-consent-wrap]");
    if (wrap) wrap.hidden = false;
    opener.addEventListener("click", function () {
      returnTo = opener;
      show(read());
      var first = box.querySelector("[data-consent]");
      if (first) first.focus();
    });
  }

  var saved = read();
  if (saved && saved.v === "granted") load();
  else if (!saved) show(null);
})();

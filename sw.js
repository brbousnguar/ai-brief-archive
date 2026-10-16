// AI Brief service worker (#11). Makes the archive installable and readable
// offline, without ever showing yesterday's brief when today's is out:
// - pages: network first, the cached copy only when the network fails;
// - CSS, JS, icons: cache first (their URLs carry a content hash), and the
//   fonts under /fonts/, whose files never change (#13);
// - audio, HEAD requests and other origins: not touched (range requests and
//   the 404 page's "is it up yet" checks go straight to the network).
const CACHE = "aibrief-v1";
const SHELL = ["/", "/site.webmanifest", "/icons/mark.svg", "/icons/icon-192.png"];

self.addEventListener("install", (event) => {
  event.waitUntil(caches.open(CACHE).then((c) => c.addAll(SHELL)));
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (event) => {
  const { request } = event;
  const url = new URL(request.url);
  if (request.method !== "GET" || url.origin !== self.location.origin) return;
  if (url.pathname.startsWith("/audio/")) return;

  if (request.mode === "navigate" || url.pathname.endsWith(".html") || url.pathname === "/") {
    event.respondWith(networkFirst(request));
  } else if (/^\/(css|js|icons|fonts)\//.test(url.pathname)) {
    event.respondWith(cacheFirst(request));
  }
});

async function networkFirst(request) {
  const cache = await caches.open(CACHE);
  try {
    const response = await fetch(request);
    if (response.ok) cache.put(request, response.clone());
    return response;
  } catch (err) {
    return (await cache.match(request, { ignoreSearch: true })) || (await cache.match("/")) || Response.error();
  }
}

async function cacheFirst(request) {
  const cache = await caches.open(CACHE);
  const hit = await cache.match(request);
  if (hit) return hit;
  const response = await fetch(request);
  if (response.ok) {
    // A new ?v= hash replaces the old copy instead of piling up beside it.
    const path = new URL(request.url).pathname;
    for (const old of await cache.keys()) {
      if (new URL(old.url).pathname === path) await cache.delete(old);
    }
    cache.put(request, response.clone());
  }
  return response;
}

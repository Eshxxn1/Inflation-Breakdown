(() => {
  // First-party, cookieless analytics: sends the pageview, which dashboard tabs are opened and time on page
  // to /api/collect on this same site. Skips local previews and visitors who ask not to be tracked.
  if (!/inflationbreakdown\.com$|\.workers\.dev$/.test(location.hostname) || navigator.webdriver) return;
  if (navigator.doNotTrack === "1" || window.doNotTrack === "1" || navigator.globalPrivacyControl === true) return;
  const send = (o) => {
    const body = JSON.stringify(o);
    try { if (navigator.sendBeacon && navigator.sendBeacon("/api/collect", new Blob([body], { type: "text/plain" }))) return; } catch (e) {}
    try { fetch("/api/collect", { method: "POST", body, keepalive: true, headers: { "content-type": "text/plain" } }); } catch (e) {}
  };
  const id = (crypto.randomUUID ? crypto.randomUUID() : Date.now().toString(36) + Math.random().toString(36).slice(2)).slice(0, 36);
  const utm = new URLSearchParams(location.search).get("utm_source") || new URLSearchParams(location.search).get("ref") || "";
  send({ t: "pv", id, p: location.pathname, r: document.referrer, u: utm });

  // tab views: the one opened on arrival, then each one clicked
  const seen = new Set();
  const tabView = (name) => { if (name && !seen.has(name)) { seen.add(name); send({ t: "tab", n: name }); } };
  const first = () => { const b = document.querySelector('#tabs button[aria-selected="true"]'); tabView(b ? b.dataset.tab : ""); };
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", () => setTimeout(first, 300)); else setTimeout(first, 300);
  document.addEventListener("click", (e) => { const b = e.target.closest && e.target.closest("#tabs button[data-tab]"); if (b) tabView(b.dataset.tab); });

  // engaged time: only counts while the page is visible
  let shown = document.visibilityState === "visible" ? Date.now() : 0, total = 0;
  const flush = () => { if (shown) { total += Date.now() - shown; shown = 0; } if (total > 1000) send({ t: "end", id, d: total / 1000 }); };
  document.addEventListener("visibilitychange", () => { if (document.visibilityState === "hidden") flush(); else shown = Date.now(); });
  window.addEventListener("pagehide", flush);
})();

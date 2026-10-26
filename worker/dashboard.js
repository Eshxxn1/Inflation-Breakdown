// The private analytics dashboard served at /stats. Plain HTML, CSS and JS, no external libraries.
export const DASHBOARD_HTML = String.raw`<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex, nofollow">
<title>Site Analytics · Inflation Breakdown</title>
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E%3Crect width='32' height='32' rx='7' fill='%2312284A'/%3E%3Crect x='6' y='19' width='4' height='7' rx='1' fill='%239CC3FF'/%3E%3Crect x='12' y='14' width='4' height='12' rx='1' fill='%239CC3FF'/%3E%3Crect x='18' y='10' width='4' height='16' rx='1' fill='%23FFFFFF'/%3E%3Crect x='24' y='6' width='4' height='20' rx='1' fill='%23FF8A7A'/%3E%3C/svg%3E">
<style>
:root{--bg:#F4F6F9;--panel:#FFFFFF;--fg:#172033;--muted:#566176;--line:#E1E6EE;--grid:#EDF0F4;--axis:#C5CDD8;
  --bar:#2F6FB3;--bar-soft:#D6E4F5;--good:#25734A;--bad:#B42D24;--navy:#12284A;--on-navy:#FFFFFF;--on-navy-muted:#B7C4D8;
  --shadow:0 4px 16px rgba(18,40,74,.14);color-scheme:light}
@media (prefers-color-scheme: dark){:root{--bg:#0C1525;--panel:#131F33;--fg:#E6EBF2;--muted:#9AA7BA;--line:#24324A;--grid:#1D2A40;--axis:#34445E;
  --bar:#6FA6E6;--bar-soft:#22385A;--good:#6CC08B;--bad:#F28B80;--navy:#16305A;--on-navy-muted:#B4C3DA;
  --shadow:0 4px 16px rgba(0,0,0,.5);color-scheme:dark}}
*{box-sizing:border-box}
html,body{margin:0;background:var(--bg);color:var(--fg);font:15px/1.5 system-ui,-apple-system,"Segoe UI",sans-serif;-webkit-font-smoothing:antialiased}
.wrap{max-width:1160px;margin:0 auto;padding:0 16px}
header{background:var(--navy);color:var(--on-navy)}
.top{display:flex;align-items:center;justify-content:space-between;gap:12px;padding:14px 0;flex-wrap:wrap}
.brand{display:flex;align-items:center;gap:10px;font-weight:600;font-size:16px;color:inherit;text-decoration:none}
.brand svg{width:28px;height:28px}
.top a.site{color:var(--on-navy-muted);font-size:14px}
.controls{display:flex;align-items:center;gap:12px;justify-content:space-between;flex-wrap:wrap;padding:20px 0 4px}
h1{font-size:24px;margin:0;font-weight:600}
.sub{color:var(--muted);font-size:13px;margin:2px 0 0}
.seg{display:inline-flex;border:1px solid var(--line);border-radius:999px;background:var(--panel);padding:3px}
.seg button{font:inherit;font-size:14px;border:0;background:transparent;color:var(--muted);padding:6px 14px;border-radius:999px;cursor:pointer;white-space:nowrap}
.seg button[aria-pressed=true]{background:var(--fg);color:var(--bg);font-weight:600}
.seg button:focus-visible,button:focus-visible,input:focus-visible{outline:2px solid var(--bar);outline-offset:2px}
.grid{display:grid;gap:16px;margin:16px 0}
.kpis{grid-template-columns:repeat(4,minmax(0,1fr))}
.card{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:16px 18px;min-width:0}
.card h2{font-size:14px;font-weight:600;margin:0 0 10px;color:var(--fg)}
.kpi .label{font-size:13px;color:var(--muted)}
.kpi .value{font-size:30px;font-weight:600;letter-spacing:-.01em;margin:2px 0;font-variant-numeric:tabular-nums}
.kpi .delta{font-size:13px;color:var(--muted)}
.delta .up{color:var(--good)} .delta .down{color:var(--bad)}
.live-dot{display:inline-block;width:8px;height:8px;border-radius:50%;background:var(--good);margin-right:6px;vertical-align:1px}
.two{grid-template-columns:2fr 1fr}
.three{grid-template-columns:repeat(3,minmax(0,1fr))}
#chart{position:relative}
#chart svg{display:block;width:100%;height:260px}
.legend{display:flex;gap:16px;font-size:13px;color:var(--muted);margin:0 0 6px}
.legend i{display:inline-block;width:12px;height:12px;border-radius:3px;margin-right:6px;vertical-align:-1px}
.tip{position:absolute;pointer-events:none;background:var(--panel);border:1px solid var(--line);box-shadow:var(--shadow);border-radius:8px;padding:8px 10px;font-size:13px;white-space:nowrap;transform:translate(-50%,-100%);margin-top:-8px;display:none;z-index:5}
.tip b{display:block;font-weight:600;margin-bottom:2px}
.earn .big{font-size:30px;font-weight:600;font-variant-numeric:tabular-nums;margin:2px 0}
.earn label{display:flex;align-items:center;gap:8px;font-size:14px;color:var(--muted);margin:12px 0 4px}
.earn input{font:inherit;width:90px;padding:6px 8px;border:1px solid var(--line);border-radius:8px;background:var(--bg);color:var(--fg)}
.earn .row{display:flex;justify-content:space-between;font-size:14px;padding:6px 0;border-top:1px solid var(--line)}
.earn .row span:last-child{font-variant-numeric:tabular-nums;font-weight:600}
.note{font-size:12.5px;color:var(--muted);margin:10px 0 0}
table{width:100%;border-collapse:collapse;font-size:14px}
th{text-align:left;font-weight:500;color:var(--muted);font-size:12.5px;padding:0 0 6px}
th.n,td.n{text-align:right;font-variant-numeric:tabular-nums;width:64px}
td{padding:5px 0;border-top:1px solid var(--line);position:relative}
td.k{padding-right:8px}
.barcell{position:relative;z-index:0;display:block;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;max-width:100%}
.barcell::before{content:"";position:absolute;z-index:-1;left:-4px;top:-2px;bottom:-2px;width:calc(var(--w) + 4px);background:var(--bar-soft);border-radius:0 4px 4px 0}
.empty{color:var(--muted);font-size:14px;padding:8px 0}
.gate{max-width:380px;margin:12vh auto;padding:28px}
.gate h1{margin-bottom:6px}
.gate p{color:var(--muted);margin:0 0 16px}
.gate input{font:inherit;width:100%;padding:10px 12px;border:1px solid var(--line);border-radius:8px;background:var(--bg);color:var(--fg)}
.gate button,.btn{font:inherit;font-weight:600;margin-top:12px;width:100%;padding:10px;border:0;border-radius:8px;background:var(--bar);color:#fff;cursor:pointer}
.err{color:var(--bad);font-size:14px;margin-top:10px;min-height:1.5em}
.foot{display:flex;justify-content:space-between;gap:12px;color:var(--muted);font-size:12.5px;padding:8px 0 40px;flex-wrap:wrap}
.foot button{font:inherit;background:none;border:0;color:var(--muted);text-decoration:underline;cursor:pointer;padding:0}
.sr{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0)}
@media (max-width:900px){.kpis{grid-template-columns:repeat(2,minmax(0,1fr))}.two,.three{grid-template-columns:1fr}}
@media (max-width:420px){.seg{width:100%;justify-content:space-between}.seg button{padding:6px 8px;font-size:13px}.kpi .value,.earn .big{font-size:24px}}
</style>
</head>
<body>
<header><div class="wrap top">
  <a class="brand" href="/stats"><svg viewBox="0 0 32 32" aria-hidden="true"><rect width="32" height="32" rx="7" fill="#1C3A66"/><rect x="6" y="19" width="4" height="7" rx="1" fill="#9CC3FF"/><rect x="12" y="14" width="4" height="12" rx="1" fill="#9CC3FF"/><rect x="18" y="10" width="4" height="16" rx="1" fill="#FFFFFF"/><rect x="24" y="6" width="4" height="20" rx="1" fill="#FF8A7A"/></svg><span>Site Analytics</span></a>
  <a class="site" href="/">inflationbreakdown.com ↗</a>
</div></header>

<main class="wrap" id="app">
  <form class="card gate" id="gate" hidden>
    <h1>Analytics</h1>
    <p>Enter the password you saved in Cloudflare as STATS_PASSWORD.</p>
    <label class="sr" for="pw">Password</label>
    <input id="pw" type="password" autocomplete="current-password" placeholder="Password" required>
    <button type="submit">Open dashboard</button>
    <div class="err" id="gate-err" role="alert"></div>
  </form>

  <section id="dash" hidden>
    <div class="controls">
      <div><h1>Traffic overview</h1><p class="sub" id="range-label"></p></div>
      <div class="seg" role="group" aria-label="Date range" id="ranges">
        <button type="button" data-d="1">Today</button><button type="button" data-d="7">7 days</button>
        <button type="button" data-d="30">30 days</button><button type="button" data-d="90">90 days</button><button type="button" data-d="365">12 months</button>
      </div>
    </div>

    <div class="grid kpis">
      <div class="card kpi"><div class="label">Pageviews</div><div class="value" id="k-pv">–</div><div class="delta" id="d-pv"></div></div>
      <div class="card kpi"><div class="label">Visitors</div><div class="value" id="k-v">–</div><div class="delta" id="d-v"></div></div>
      <div class="card kpi"><div class="label">Avg. time on page</div><div class="value" id="k-t">–</div><div class="delta" id="d-t"></div></div>
      <div class="card kpi"><div class="label"><span class="live-dot" aria-hidden="true"></span>Live now</div><div class="value" id="k-live">–</div><div class="delta">visitors in the last 30 min</div></div>
    </div>

    <div class="grid two">
      <div class="card">
        <h2>Pageviews and visitors per day</h2>
        <div class="legend"><span><i style="background:var(--bar)"></i>Pageviews</span><span><i style="background:var(--bar-soft);outline:1px solid var(--axis)"></i>Visitors</span></div>
        <div id="chart"><svg id="svg" role="img" aria-label="Daily pageviews and visitors"></svg><div class="tip" id="tip"></div></div>
      </div>
      <div class="card earn">
        <h2>Estimated AdSense earnings</h2>
        <div class="kpi"><div class="label">This period</div></div>
        <div class="big" id="e-period">–</div>
        <label for="rpm">Page RPM (US$ per 1,000 pageviews) <input id="rpm" type="number" min="0" max="200" step="0.5" value="5"></label>
        <div class="row"><span>Monthly pace (last 30 days)</span><span id="e-month">–</span></div>
        <div class="row"><span>Yearly pace</span><span id="e-year">–</span></div>
        <div class="row"><span>Range at half to double this RPM</span><span id="e-range">–</span></div>
        <p class="note">An estimate from pageviews × RPM. Ad blockers, unfilled ad slots and invalid-traffic deductions make real payouts differ; your AdSense account has the actual figure. Once it shows a Page RPM, enter it here.</p>
      </div>
    </div>

    <div class="grid three">
      <div class="card"><h2>Dashboard tabs viewed</h2><div id="t-tabs"></div></div>
      <div class="card"><h2>Traffic sources</h2><div id="t-sources"></div></div>
      <div class="card"><h2>Referring sites</h2><div id="t-referrers"></div></div>
      <div class="card"><h2>Countries</h2><div id="t-countries"></div></div>
      <div class="card"><h2>Devices</h2><div id="t-devices"></div></div>
      <div class="card"><h2>Pages</h2><div id="t-pages"></div></div>
      <div class="card"><h2>Browsers</h2><div id="t-browsers"></div></div>
      <div class="card"><h2>Operating systems</h2><div id="t-os"></div></div>
      <div class="card"><h2>About these numbers</h2><p class="note" style="margin:0">Visitors are counted without cookies: a visitor is an anonymous code made from the IP address and browser that changes every day, so a person who returns tomorrow counts again. Known bots are left out. Days follow <span id="tz"></span> time.</p></div>
    </div>

    <div class="foot"><span id="updated"></span><button type="button" id="logout">Sign out</button></div>
  </section>
</main>

<script>
(() => {
  const $ = (id) => document.getElementById(id);
  const store = {
    get(k) { try { return localStorage.getItem(k); } catch { return null; } },
    set(k, v) { try { localStorage.setItem(k, v); } catch {} },
    del(k) { try { localStorage.removeItem(k); } catch {} },
  };
  let pw = store.get("ib-stats-pw") || "";
  let days = parseInt(store.get("ib-stats-days") || "30", 10) || 30;
  let data = null;
  const nf = new Intl.NumberFormat("en-US");
  const money = (n) => n >= 100 ? "$" + nf.format(Math.round(n)) : "$" + n.toFixed(2);
  const regions = (() => { try { return new Intl.DisplayNames(["en"], { type: "region" }); } catch { return null; } })();
  const TABS = { overview: "Overview", drivers: "Drivers", components: "Components", momentum: "Momentum", regions: "Regions", method: "Methodology" };
  const flag = (cc) => cc && cc.length === 2 ? String.fromCodePoint(...[...cc.toUpperCase()].map((c) => 127397 + c.charCodeAt(0))) + " " : "";
  const dur = (s) => { if (!s) return "–"; s = Math.round(s); return s < 60 ? s + "s" : Math.floor(s / 60) + "m " + String(s % 60).padStart(2, "0") + "s"; };

  function showGate(msg) { $("dash").hidden = true; $("gate").hidden = false; $("gate-err").textContent = msg || ""; $("pw").focus(); }

  async function load() {
    if (!pw) return showGate();
    let res;
    try { res = await fetch("/api/stats?days=" + days, { headers: { authorization: "Bearer " + pw }, cache: "no-store" }); }
    catch { return showGate("Couldn't reach the server. Check your connection."); }
    if (res.status === 401) { store.del("ib-stats-pw"); pw = ""; return showGate("That password didn't match."); }
    const body = await res.json().catch(() => ({}));
    if (!res.ok) return showGate(body.message || "Something went wrong (" + res.status + ").");
    data = body; $("gate").hidden = true; $("dash").hidden = false; render();
  }

  function delta(el, now, prev, fmt) {
    if (!prev || !now) { el.textContent = prev ? "" : "no earlier data to compare"; return; }
    const pct = Math.round((now - prev) / prev * 100);
    const cls = pct > 0 ? "up" : pct < 0 ? "down" : "";
    el.innerHTML = '<span class="' + cls + '">' + (pct > 0 ? "▲ " : pct < 0 ? "▼ " : "") + Math.abs(pct) + "%</span> vs previous " + (days === 1 ? "day" : days + " days") + (fmt ? " (" + fmt(prev) + ")" : "");
  }

  function render() {
    const d = data, t = d.totals || {}, p = d.previous || {};
    document.querySelectorAll("#ranges button").forEach((b) => b.setAttribute("aria-pressed", String(+b.dataset.d === days)));
    const fmtDay = (s) => new Date(s + "T12:00:00").toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
    $("range-label").textContent = (days === 1 ? fmtDay(d.range.end) : fmtDay(d.range.start) + " – " + fmtDay(d.range.end)) + (d.firstDay ? "" : " · waiting for the first visit");
    $("k-pv").textContent = nf.format(t.pv || 0); delta($("d-pv"), t.pv, p.pv, nf.format);
    $("k-v").textContent = nf.format(t.v || 0); delta($("d-v"), t.v, p.v, nf.format);
    $("k-t").textContent = dur(t.t); delta($("d-t"), t.t, p.t, dur);
    $("k-live").textContent = nf.format(d.live || 0);
    $("tz").textContent = d.range.timezone.replace(/_/g, " ");
    $("updated").textContent = "Updated " + new Date().toLocaleTimeString([], { hour: "numeric", minute: "2-digit" });
    earnings(); chart();
    list("t-tabs", d.tabs, (k) => TABS[k] || k, "Opened");
    list("t-sources", d.sources, (k) => k);
    list("t-referrers", d.referrers, (k) => k);
    list("t-countries", d.countries, (k) => flag(k) + ((regions && regions.of(k)) || k));
    list("t-devices", d.devices, (k) => k);
    list("t-pages", d.pages, (k) => k === "/" ? "/ (dashboard)" : k);
    list("t-browsers", d.browsers, (k) => k);
    list("t-os", d.os, (k) => k);
  }

  function earnings() {
    if (!data) return;
    const rpm = Math.max(0, parseFloat($("rpm").value) || 0);
    store.set("ib-stats-rpm", String(rpm));
    const pv = (data.totals && data.totals.pv) || 0, m = data.last30pv || 0;
    $("e-period").textContent = money(pv * rpm / 1000);
    $("e-month").textContent = money(m * rpm / 1000);
    $("e-year").textContent = money(m * 12.17 * rpm / 1000);
    $("e-range").textContent = money(m * rpm / 2000) + " – " + money(m * rpm / 500) + " /mo";
  }

  function list(id, rows, label, head) {
    const el = $(id);
    if (!rows || !rows.length) { el.innerHTML = '<div class="empty">No data yet</div>'; return; }
    const max = Math.max(...rows.map((r) => r.pv));
    const esc = (s) => String(s == null || s === "" ? "Unknown" : s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
    el.innerHTML = '<table><thead><tr><th></th><th class="n">' + (head || "Views") + '</th><th class="n">Visitors</th></tr></thead><tbody>' +
      rows.map((r) => '<tr><td class="k"><span class="barcell" style="--w:' + (r.pv / max * 100).toFixed(1) + '%" title="' + esc(label(r.k)) + '">' + esc(label(r.k)) +
        '</span></td><td class="n">' + nf.format(r.pv) + '</td><td class="n">' + nf.format(r.v) + "</td></tr>").join("") + "</tbody></table>";
  }

  function chart() {
    const svg = $("svg"), tip = $("tip");
    const W = svg.clientWidth || 700, H = 260, m = { t: 12, r: 8, b: 26, l: 40 };
    svg.setAttribute("viewBox", "0 0 " + W + " " + H);
    // fill every day in the range, including days with no visits
    const byDay = Object.fromEntries((data.daily || []).map((r) => [r.day, r]));
    const pts = []; const s = new Date(data.range.start + "T12:00:00"), e = new Date(data.range.end + "T12:00:00");
    for (let x = new Date(s); x <= e; x.setDate(x.getDate() + 1)) {
      const k = x.getFullYear() + "-" + String(x.getMonth() + 1).padStart(2, "0") + "-" + String(x.getDate()).padStart(2, "0");
      pts.push({ day: k, pv: (byDay[k] || {}).pv || 0, v: (byDay[k] || {}).v || 0 });
    }
    const max = Math.max(4, ...pts.map((p) => p.pv));
    const step = Math.pow(10, Math.floor(Math.log10(max))); const nice = [1, 2, 2.5, 5, 10].map((f) => f * step).find((f) => max / f <= 5) || step * 10;
    const top = Math.ceil(max / nice) * nice;
    const iw = W - m.l - m.r, ih = H - m.t - m.b, n = pts.length, slot = iw / n;
    const bw = Math.max(1, Math.min(28, slot - 2)), y = (v) => m.t + ih - v / top * ih;
    const fmtShort = (k) => new Date(k + "T12:00:00").toLocaleDateString("en-US", { month: "short", day: "numeric" });
    let g = "";
    for (let v = 0; v <= top; v += nice) g += '<line x1="' + m.l + '" x2="' + (W - m.r) + '" y1="' + y(v) + '" y2="' + y(v) + '" stroke="var(' + (v ? "--grid" : "--axis") + ')"/>' +
      '<text x="' + (m.l - 6) + '" y="' + (y(v) + 4) + '" text-anchor="end" font-size="11" fill="var(--muted)">' + nf.format(v) + "</text>";
    const r = Math.min(4, bw / 2);
    const bar = (x, w, h, fill) => h <= 0 ? "" : '<path fill="' + fill + '" d="M' + x + "," + (m.t + ih) + "v" + -(h - r) + "q0," + -r + " " + r + "," + -r + "h" + (w - 2 * r) + "q" + r + ",0 " + r + "," + r + "v" + (h - r) + 'z"/>';
    pts.forEach((p, i) => {
      const x = m.l + i * slot + (slot - bw) / 2;
      g += bar(x, bw, ih - (y(p.pv) - m.t) , "var(--bar)");
      const vh = p.v / top * ih; if (vh > 0) g += bar(x + bw * 0.2, bw * 0.6, Math.min(vh, ih - (y(p.pv) - m.t)), "var(--bar-soft)");
    });
    const every = Math.ceil(n / Math.max(2, Math.floor(iw / 70)));
    pts.forEach((p, i) => { if (i % every === 0 || n === 1) g += '<text x="' + (m.l + i * slot + slot / 2) + '" y="' + (H - 8) + '" text-anchor="middle" font-size="11" fill="var(--muted)">' + fmtShort(p.day) + "</text>"; });
    g += '<rect id="hit" x="' + m.l + '" y="' + m.t + '" width="' + iw + '" height="' + ih + '" fill="transparent"/><line id="hair" y1="' + m.t + '" y2="' + (m.t + ih) + '" stroke="var(--axis)" stroke-dasharray="3 3" visibility="hidden"/>';
    svg.innerHTML = g;
    const hit = svg.querySelector("#hit"), hair = svg.querySelector("#hair");
    const move = (ev) => {
      const b = svg.getBoundingClientRect(), sx = (ev.clientX - b.left) * W / b.width;
      const i = Math.max(0, Math.min(n - 1, Math.floor((sx - m.l) / slot))), p = pts[i], cx = m.l + i * slot + slot / 2;
      hair.setAttribute("x1", cx); hair.setAttribute("x2", cx); hair.setAttribute("visibility", "visible");
      tip.style.display = "block"; tip.style.left = (cx * b.width / W) + "px"; tip.style.top = (y(p.pv) * b.height / H) + "px";
      tip.innerHTML = "<b>" + new Date(p.day + "T12:00:00").toLocaleDateString("en-US", { weekday: "short", month: "short", day: "numeric" }) + "</b>" + nf.format(p.pv) + " pageviews · " + nf.format(p.v) + " visitors";
    };
    hit.addEventListener("pointermove", move); hit.addEventListener("pointerdown", move);
    hit.addEventListener("pointerleave", () => { tip.style.display = "none"; hair.setAttribute("visibility", "hidden"); });
  }

  $("gate").addEventListener("submit", (e) => { e.preventDefault(); pw = $("pw").value; store.set("ib-stats-pw", pw); load(); });
  $("ranges").addEventListener("click", (e) => { const b = e.target.closest("button[data-d]"); if (!b) return; days = +b.dataset.d; store.set("ib-stats-days", String(days)); load(); });
  $("rpm").value = store.get("ib-stats-rpm") || "5";
  $("rpm").addEventListener("input", earnings);
  $("logout").addEventListener("click", () => { store.del("ib-stats-pw"); pw = ""; $("pw").value = ""; showGate(); });
  let rt; window.addEventListener("resize", () => { clearTimeout(rt); rt = setTimeout(() => data && chart(), 150); });
  setInterval(() => { if (pw && !document.hidden && data) load(); }, 60000);
  load();
})();
</script>
</body>
</html>`;

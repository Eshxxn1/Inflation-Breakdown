// Inflation Breakdown Worker.
// Serves the static site from site/ and adds a small first-party analytics system:
//   POST /api/collect  - the tracker on each page sends pageviews, tab views and time on page here
//   GET  /api/stats    - aggregated numbers for the dashboard (needs the STATS_PASSWORD secret)
//   GET  /stats        - the private analytics dashboard
// Data lives in a Cloudflare D1 (SQLite) database bound as DB. No cookies are set: a visitor is a
// daily-rotating hash of IP + browser, so the same person can't be followed from one day to the next.
import { DASHBOARD_HTML } from "./dashboard.js";

const BOT = /bot|crawl|spider|slurp|headless|lighthouse|pagespeed|preview|facebookexternalhit|embedly|monitor|uptime|curl|wget|python|axios|node-fetch|go-http|java\//i;
const TABS = new Set(["overview", "drivers", "components", "momentum", "regions", "method"]);
const SOURCES = [
  [/(^|\.)google\./, "Google"], [/(^|\.)bing\.com$/, "Bing"], [/duckduckgo\.com$/, "DuckDuckGo"],
  [/(^|\.)yahoo\./, "Yahoo"], [/(^|\.)(t\.co|twitter\.com|x\.com)$/, "X / Twitter"], [/reddit\.com$/, "Reddit"],
  [/(facebook\.com|fb\.me)$/, "Facebook"], [/linkedin\.com$|lnkd\.in$/, "LinkedIn"], [/news\.ycombinator\.com$/, "Hacker News"],
  [/chatgpt\.com$|openai\.com$/, "ChatGPT"], [/perplexity\.ai$/, "Perplexity"], [/claude\.ai$/, "Claude"],
  [/(^|\.)youtube\.com$/, "YouTube"], [/instagram\.com$/, "Instagram"], [/threads\.net$/, "Threads"], [/bsky\.app$/, "Bluesky"],
];

let schemaReady = false;
async function ensureSchema(db) {
  if (schemaReady) return;
  await db.batch([
    db.prepare(`CREATE TABLE IF NOT EXISTS pageviews (id TEXT PRIMARY KEY, ts INTEGER NOT NULL, day TEXT NOT NULL,
      path TEXT, visitor TEXT, source TEXT, referrer TEXT, country TEXT, device TEXT, browser TEXT, os TEXT,
      duration INTEGER NOT NULL DEFAULT 0)`),
    db.prepare("CREATE INDEX IF NOT EXISTS pageviews_day ON pageviews(day)"),
    db.prepare("CREATE INDEX IF NOT EXISTS pageviews_ts ON pageviews(ts)"),
    db.prepare("CREATE TABLE IF NOT EXISTS events (ts INTEGER NOT NULL, day TEXT NOT NULL, visitor TEXT, name TEXT, value TEXT)"),
    db.prepare("CREATE INDEX IF NOT EXISTS events_day ON events(day)"),
    db.prepare("CREATE TABLE IF NOT EXISTS salts (day TEXT PRIMARY KEY, salt TEXT NOT NULL)"),
  ]);
  schemaReady = true;
}

const json = (obj, status = 200, extra = {}) =>
  new Response(JSON.stringify(obj), { status, headers: { "content-type": "application/json", "cache-control": "no-store", ...extra } });
const clip = (s, n) => (typeof s === "string" ? s.slice(0, n) : "");

function localDay(ts, tz) {
  try { return new Intl.DateTimeFormat("en-CA", { timeZone: tz, year: "numeric", month: "2-digit", day: "2-digit" }).format(ts); }
  catch { return new Date(ts).toISOString().slice(0, 10); }
}

async function sha256(text) {
  const buf = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(text));
  return [...new Uint8Array(buf)].map((b) => b.toString(16).padStart(2, "0")).join("");
}

async function dailySalt(db, day) {
  const fresh = crypto.randomUUID();
  await db.prepare("INSERT OR IGNORE INTO salts (day, salt) VALUES (?, ?)").bind(day, fresh).run();
  const row = await db.prepare("SELECT salt FROM salts WHERE day = ?").bind(day).first();
  return row ? row.salt : fresh;
}

function parseUA(ua) {
  const device = /iPad|Tablet|PlayBook|Silk|(Android(?!.*Mobile))/i.test(ua) ? "Tablet" : /Mobi|iPhone|Android/i.test(ua) ? "Mobile" : "Desktop";
  const browser = /Edg\//.test(ua) ? "Edge" : /OPR\/|Opera/.test(ua) ? "Opera" : /SamsungBrowser/.test(ua) ? "Samsung Internet"
    : /Firefox|FxiOS/.test(ua) ? "Firefox" : /Chrome|CriOS/.test(ua) ? "Chrome" : /Safari/.test(ua) ? "Safari" : "Other";
  const os = /Windows/.test(ua) ? "Windows" : /iPhone|iPad|iPod/.test(ua) ? "iOS" : /Mac OS X|Macintosh/.test(ua) ? "macOS"
    : /Android/.test(ua) ? "Android" : /CrOS/.test(ua) ? "ChromeOS" : /Linux/.test(ua) ? "Linux" : "Other";
  return { device, browser, os };
}

function classifySource(ref, utm, host) {
  if (utm) return clip(utm, 60).toLowerCase().replace(/^\w/, (c) => c.toUpperCase());
  if (!ref) return { source: "Direct", referrer: "" };
  let h;
  try { h = new URL(ref).hostname.replace(/^www\./, ""); } catch { return { source: "Direct", referrer: "" }; }
  if (h === host.replace(/^www\./, "") || h.endsWith(".workers.dev")) return { source: "Direct", referrer: "" };
  for (const [re, name] of SOURCES) if (re.test(h)) return { source: name, referrer: h };
  return { source: h, referrer: h };
}

function sameSite(request, url) {
  const origin = request.headers.get("origin");
  if (!origin) return true; // sendBeacon from the same page may omit it in some browsers
  try { return new URL(origin).hostname.replace(/^www\./, "") === url.hostname.replace(/^www\./, ""); } catch { return false; }
}

async function collect(request, env, url) {
  if (!env.DB) return new Response(null, { status: 204 });
  const ua = request.headers.get("user-agent") || "";
  if (!ua || BOT.test(ua) || !sameSite(request, url)) return new Response(null, { status: 204 });
  let body;
  try { body = JSON.parse(await request.text()); } catch { return new Response(null, { status: 400 }); }
  if (!body || typeof body !== "object") return new Response(null, { status: 400 });

  await ensureSchema(env.DB);
  const now = Date.now();
  const day = localDay(now, env.TIMEZONE || "UTC");
  const ip = request.headers.get("cf-connecting-ip") || "";
  const visitor = (await sha256(`${await dailySalt(env.DB, day)}|${ip}|${ua}|${url.hostname.replace(/^www\./, "")}`)).slice(0, 16);

  if (body.t === "pv") {
    const id = clip(body.id, 40);
    if (!/^[\w-]{8,40}$/.test(id)) return new Response(null, { status: 400 });
    let path = clip(body.p, 200) || "/";
    path = path.replace(/\.html$/, "").replace(/\/index$/, "/") || "/";
    const src = classifySource(clip(body.r, 500), clip(body.u, 60), url.hostname);
    const { source, referrer } = typeof src === "string" ? { source: src, referrer: "" } : src;
    const { device, browser, os } = parseUA(ua);
    const country = (request.cf && request.cf.country) || "";
    await env.DB.prepare(`INSERT OR IGNORE INTO pageviews (id, ts, day, path, visitor, source, referrer, country, device, browser, os)
      VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`).bind(id, now, day, path, visitor, source, referrer, country, device, browser, os).run();
    if (Math.random() < 0.01) {
      const cutoff = now - 400 * 864e5; // keep about 13 months
      await env.DB.batch([env.DB.prepare("DELETE FROM pageviews WHERE ts < ?").bind(cutoff), env.DB.prepare("DELETE FROM events WHERE ts < ?").bind(cutoff),
        env.DB.prepare("DELETE FROM salts WHERE day < ?").bind(localDay(now - 3 * 864e5, env.TIMEZONE || "UTC"))]);
    }
  } else if (body.t === "tab") {
    const tab = clip(body.n, 30);
    if (!TABS.has(tab)) return new Response(null, { status: 400 });
    await env.DB.prepare("INSERT INTO events (ts, day, visitor, name, value) VALUES (?, ?, ?, 'tab', ?)").bind(now, day, visitor, tab).run();
  } else if (body.t === "end") {
    const id = clip(body.id, 40);
    const secs = Math.max(0, Math.min(1800, Math.round(Number(body.d) || 0)));
    if (/^[\w-]{8,40}$/.test(id) && secs > 0) {
      await env.DB.prepare("UPDATE pageviews SET duration = MAX(duration, ?) WHERE id = ? AND ts > ?").bind(secs, id, now - 864e5).run();
    }
  } else {
    return new Response(null, { status: 400 });
  }
  return new Response(null, { status: 204 });
}

async function authorized(request, env) {
  const given = (request.headers.get("authorization") || "").replace(/^Bearer\s+/i, "");
  if (!env.STATS_PASSWORD || !given) return false;
  const [a, b] = await Promise.all([given, env.STATS_PASSWORD].map((s) => crypto.subtle.digest("SHA-256", new TextEncoder().encode(s))));
  return crypto.subtle.timingSafeEqual(a, b);
}

async function stats(request, env, url) {
  if (!env.STATS_PASSWORD) return json({ error: "setup", message: "Add a secret named STATS_PASSWORD to the Worker in Cloudflare to open the dashboard." }, 503);
  if (!(await authorized(request, env))) return json({ error: "auth" }, 401);
  if (!env.DB) return json({ error: "db", message: "The DB database binding is missing." }, 503);
  await ensureSchema(env.DB);

  const tz = env.TIMEZONE || "UTC";
  const days = Math.max(1, Math.min(366, parseInt(url.searchParams.get("days") || "30", 10) || 30));
  const now = Date.now();
  const end = localDay(now, tz);
  const start = localDay(now - (days - 1) * 864e5, tz);
  const prevStart = localDay(now - (2 * days - 1) * 864e5, tz);
  const prevEnd = localDay(now - days * 864e5, tz);
  const db = env.DB;
  const top = (col, extra = "") => db.prepare(`SELECT ${col} AS k, COUNT(*) AS pv, COUNT(DISTINCT visitor || day) AS v FROM pageviews
    WHERE day BETWEEN ? AND ? ${extra} GROUP BY ${col} ORDER BY pv DESC LIMIT 12`).bind(start, end);
  const totals = (a, b) => db.prepare(`SELECT COUNT(*) AS pv, COUNT(DISTINCT visitor || day) AS v,
    AVG(CASE WHEN duration > 0 THEN duration END) AS t FROM pageviews WHERE day BETWEEN ? AND ?`).bind(a, b);

  const r = await db.batch([
    totals(start, end),
    totals(prevStart, prevEnd),
    db.prepare(`SELECT day, COUNT(*) AS pv, COUNT(DISTINCT visitor) AS v FROM pageviews WHERE day BETWEEN ? AND ? GROUP BY day ORDER BY day`).bind(start, end),
    top("path"),
    top("source"),
    top("referrer", "AND referrer <> ''"),
    top("country", "AND country <> ''"),
    top("device"),
    top("browser"),
    top("os"),
    db.prepare(`SELECT value AS k, COUNT(*) AS pv, COUNT(DISTINCT visitor || day) AS v FROM events WHERE name = 'tab' AND day BETWEEN ? AND ?
      GROUP BY value ORDER BY pv DESC`).bind(start, end),
    db.prepare("SELECT COUNT(DISTINCT visitor) AS v FROM pageviews WHERE ts > ?").bind(now - 30 * 60e3),
    db.prepare("SELECT COUNT(*) AS pv FROM pageviews WHERE ts > ?").bind(now - 30 * 864e5),
    db.prepare("SELECT MIN(day) AS first FROM pageviews"),
  ]);
  const rows = (i) => r[i].results || [];
  const one = (i) => rows(i)[0] || {};
  return json({
    range: { days, start, end, timezone: tz },
    totals: one(0), previous: one(1), daily: rows(2),
    pages: rows(3), sources: rows(4), referrers: rows(5), countries: rows(6),
    devices: rows(7), browsers: rows(8), os: rows(9), tabs: rows(10),
    live: one(11).v || 0, last30pv: one(12).pv || 0, firstDay: one(13).first || null,
  });
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    try {
      if (url.pathname === "/api/collect") {
        if (request.method !== "POST") return new Response(null, { status: 405, headers: { allow: "POST" } });
        return await collect(request, env, url);
      }
      if (url.pathname === "/api/stats") return await stats(request, env, url);
      if (url.pathname === "/stats" || url.pathname === "/stats/") {
        return new Response(DASHBOARD_HTML, { headers: { "content-type": "text/html; charset=utf-8", "cache-control": "no-store",
          "x-robots-tag": "noindex, nofollow", "referrer-policy": "no-referrer" } });
      }
    } catch (err) {
      console.error(err);
      if (url.pathname.startsWith("/api/")) return json({ error: "server", message: String(err && err.message || err) }, 500);
    }
    return env.ASSETS.fetch(request);
  },
};

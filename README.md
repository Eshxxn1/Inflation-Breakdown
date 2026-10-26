# Inflation Breakdown

A one-page website showing what's driving US inflation: every CPI component, its share of the
basket, its contribution to the headline rate, momentum, regional differences and how all of it
compares with the 2% target. Data from the U.S. Bureau of Labor Statistics (BLS) and FRED.

`site/index.html` is the whole website in one file. It opens offline and works on any static host.

## Where it lives

- **Website:** https://inflationbreakdown.com, a Cloudflare Worker that serves the `site` folder. Workers Builds runs
  `npx wrangler deploy` on every push to `main` (settings in `wrangler.jsonc`).
- **Updates:** `.github/workflows/update.yml` fetches new data, rebuilds `site/` and commits, which redeploys the site.
- **Analytics:** https://inflationbreakdown.com/stats (private, password protected). See below.

## Analytics

The site counts its own visits, with no cookies and no third-party service:

- `template/track.js` is built into every page. It sends the pageview, the dashboard tabs opened and the time spent
  on the page to `/api/collect`. Visitors with Do Not Track or Global Privacy Control turned on aren't counted.
- `worker/index.js` stores them in a Cloudflare D1 database named `inflation-analytics` (created automatically on
  the first deploy). A visitor is an anonymous hash of IP + browser that changes daily; the IP itself isn't stored.
  Rows older than about 13 months are deleted.
- `/stats` (`worker/dashboard.js`) shows pageviews, visitors, time on page, live visitors, tabs, sources, referrers,
  countries, devices, browsers and an AdSense earnings estimate from your Page RPM.

**One-time setup:** in Cloudflare, open **Workers & Pages → inflation-breakdown → Settings → Variables and Secrets →
Add**, choose type **Secret**, name it `STATS_PASSWORD`, and enter a password. That's the password for `/stats`.

## Make it yours

Edit `site.config.json`:

| Setting | What it does |
|---|---|
| `site_name` | Name shown at the top of the page and in link previews |
| `title`, `description` | Browser-tab title and the summary search engines and social sites show |
| `site_url` | The site's full address. Used for the link-preview image, sitemap and canonical link |
| `custom_domain` | Written to `site/CNAME` |
| `author` | Adds "Built by …" to the Disclaimer section |
| `about_html` | Optional extra HTML for the Disclaimer section: an about line, contact link and so on |
| `analytics_html` | Paste a privacy-friendly analytics snippet here (Plausible, GoatCounter, Cloudflare Web Analytics) |

Commit the change and the site rebuilds automatically.

## How updates work

`.github/workflows/update.yml` runs every day at 13:45 UTC. It:

1. runs `scripts/update_data.py`, which reads the BLS release tables (Tables A, 1, 2, 4, 6 and 7)
   and six FRED series, checks them, and rewrites `data/*.csv`;
2. runs `scripts/build_site.py`, which puts the page, the data and the chart library into
   `site/index.html`;
3. commits any changes; Cloudflare Pages then republishes the site.

On days without a new release nothing changes. If BLS has released but FRED hasn't caught up yet,
or anything fails a check (a missing row, contributions that don't add up to the published
headline), the update is skipped, the site keeps its current data, and the next day's run tries
again. You'll see a red step in the Actions tab when that happens.

Run it yourself: `pip install pandas lxml requests`, then `python scripts/update_data.py` and
`python scripts/build_site.py` from this folder.

**Untested against the live sites.** The updater was tested against copies of the BLS tables built from
this data, not against live bls.gov, which wasn't reachable when it was built. If the first run
fails, the Actions log names the table and row it couldn't read. BLS occasionally renames rows;
the name mappings are near the top of each section in `scripts/update_data.py`.

## What's in here

| Path | What it is |
|---|---|
| `site/index.html` | The published website (built) |
| `site/og-image.png` | Link-preview image |
| `template/page.html` | The dashboard page: layout, charts and calculations |
| `data/*.csv` | The data the page uses |
| `vendor/d3.min.js` | d3 v7.9.0, the chart library |
| `scripts/` | Updater and site builder |
| `worker/` | Cloudflare Worker: analytics collector, stats API and the `/stats` dashboard |
| `template/track.js` | The analytics snippet built into each page |

## Data and licence notes

BLS data are in the public domain. FRED data are provided by the Federal Reserve Bank of St. Louis;
cite FRED when you republish them. The footer and the Methodology tab do both. This is an
independent analysis, not an official BLS or Federal Reserve product.

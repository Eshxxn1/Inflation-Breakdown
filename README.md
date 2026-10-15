# Inflation Breakdown

A one-page website showing what's driving US inflation: every CPI component, its share of the
basket, its contribution to the headline rate, momentum, regional differences and how all of it
compares with the 2% target. Data from the U.S. Bureau of Labor Statistics (BLS) and FRED.

`site/index.html` is the whole website in one file. It opens offline and works on any static host.

## Where it lives

- **Website:** https://inflationbreakdown.com (GitHub Pages, deployed by `.github/workflows/update.yml`)
- **Domain:** inflationbreakdown.com, DNS at Cloudflare

### One-time setup (already done if the site is live)

1. **Settings → Pages → Source: GitHub Actions.**
2. **Settings → Secrets and variables → Actions → New repository secret:** `BLS_USER_AGENT`, value like
   `InflationBreakdown (you@example.com)`. BLS asks automated tools to identify themselves.
3. **Settings → Pages → Custom domain:** `inflationbreakdown.com`, Save.
4. **Cloudflare → inflationbreakdown.com → DNS → Records**, add (Proxy status: **DNS only**, grey cloud):

   | Type | Name | Content |
   |---|---|---|
   | A | `@` | `185.199.108.153` |
   | A | `@` | `185.199.109.153` |
   | A | `@` | `185.199.110.153` |
   | A | `@` | `185.199.111.153` |
   | AAAA | `@` | `2606:50c0:8000::153` |
   | AAAA | `@` | `2606:50c0:8001::153` |
   | AAAA | `@` | `2606:50c0:8002::153` |
   | AAAA | `@` | `2606:50c0:8003::153` |
   | CNAME | `www` | `eshxxn1.github.io` |

   Delete any other A, AAAA or CNAME records for `@` or `www` (Cloudflare adds parking records to new domains).
5. Wait for GitHub's DNS check to pass (minutes to a few hours), then tick **Enforce HTTPS** in Settings → Pages.

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
3. commits any changes and publishes the site.

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

## Data and licence notes

BLS data are in the public domain. FRED data are provided by the Federal Reserve Bank of St. Louis;
cite FRED when you republish them. The footer and the Methodology tab do both. This is an
independent analysis, not an official BLS or Federal Reserve product.

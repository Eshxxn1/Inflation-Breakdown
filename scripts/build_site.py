#!/usr/bin/env python3
"""Build the site: one self-contained page per country (dashboard page, its data and d3 in one file).

  site/index.html          United States (data/*.csv)
  site/canada/index.html   Canada (data/ca/*.csv)

Both pages come from template/page.html. Text that differs by country sits in <!--IF:us--> / <!--IF:ca-->
blocks and {{PLACEHOLDERS}} in the template, filled from COUNTRIES below; the page's scripts read
window.COUNTRY. Both pages also carry window.COMPARE, the data for the "US vs Canada" tab.
Run from the repository root:  python scripts/build_site.py
"""
import csv
import html
import json
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import site_shell  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATASETS = ["components", "components_monthly", "fred", "regions", "effects"]


MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]

# Canada's provinces and territories laid out roughly as on a map: [code, column, row, name, note]
CA_TILES = [
    ["YT", 0, 0, "Yukon", "Whitehorse"], ["NT", 1, 0, "Northwest Territories", "Yellowknife"], ["NU", 3, 0, "Nunavut", "Iqaluit"],
    ["NL", 7, 0, "Newfoundland and Labrador", ""],
    ["BC", 0, 1, "British Columbia", ""], ["AB", 1, 1, "Alberta", ""], ["SK", 2, 1, "Saskatchewan", ""], ["MB", 3, 1, "Manitoba", ""],
    ["ON", 4, 1, "Ontario", ""], ["QC", 5, 1, "Quebec", ""], ["PE", 7, 1, "Prince Edward Island", ""],
    ["NB", 6, 2, "New Brunswick", ""], ["NS", 7, 2, "Nova Scotia", ""],
]

COUNTRIES = {
    "us": {
        "dir": "data", "out": "index.html", "path": "/",
        "page": {
            "THIRD": "Supercore", "THIRD_LABEL": "Supercore*", "THIRD_NOTE": "Services excluding housing",
            "THIRD_SUB": "*Estimated from BLS and FRED data", "MOM_HEAD": "1-mo % SA",
            "MOM_TABLE_NOTE": "1-month changes are seasonally adjusted where BLS adjusts the series.",
            "ROC_NOTE": "*Supercore is estimated; Oct 2025 was never published, hence the gap.",
            "REGION_TITLE": "Regional map vs target", "MAP_ARIA": "Map of US states shaded by their census division's inflation",
            "METRO_TITLE": "Metro areas", "METRO_WORD": "metro area", "REGIONS_TAB": "Regions", "HIST_DS": "Index history (FRED)",
            "REGIONS_DS": "Regions and metros", "COUNTRY_ADJ": "US",
            "REGIONS_LEDE": "How inflation differs across the country, by census division and metro area.",
        },
        "js": {"code": "us"},
        "shell": {},
        "title_prefix": "",
    },
    "ca": {
        "dir": "data/ca", "out": "canada/index.html", "path": "/canada/",
        "page": {
            "THIRD": "CPI-trim", "THIRD_LABEL": "CPI-trim", "THIRD_NOTE": "The Bank of Canada's preferred core measure",
            "THIRD_SUB": "", "MOM_HEAD": "1-mo %",
            "MOM_TABLE_NOTE": "1-month changes aren't seasonally adjusted, as Statistics Canada reports them.",
            "ROC_NOTE": "CPI-trim is the Bank of Canada's preferred core measure. All series are seasonally adjusted.",
            "REGION_TITLE": "Provinces and territories vs target", "MAP_ARIA": "Map of Canada's provinces and territories shaded by their inflation",
            "METRO_TITLE": "Cities", "METRO_WORD": "city", "REGIONS_TAB": "Provinces", "HIST_DS": "Index history",
            "REGIONS_DS": "Provinces and cities", "COUNTRY_ADJ": "Canadian",
            "REGIONS_LEDE": "How inflation differs across Canada, by province, territory and city.",
        },
        "js": {
            "code": "ca", "third": "CPI-trim", "thirdLabel": "CPI-trim", "momUnit": "m/m", "agency": "Statistics Canada", "histNSA": True,
            "histNoteYoy": "Points each group added to 12-month inflation, estimated from Statistics Canada indexes and basket weights.",
            "histNoteMom": "Points each group added to each month’s change (not seasonally adjusted), estimated from Statistics Canada indexes and basket weights.",
            "regionNoteYoy": "12-month change to {latest}. Territories are shown through their capital cities. Local figures are noisier than the national one.",
            "regionNoteMom": "{prev}→{month} change, not seasonally adjusted. Territories are shown through their capital cities.",
            "metroNoteYoy": "12-month change to {latest}.", "metroNoteMom": "{prev}→{month} change, not seasonally adjusted.",
            "tiles": CA_TILES, "tileCols": 8, "tileRows": 3, "regionWord": "province",
        },
        "shell": {
            "people": "Canadian", "goal": "the Bank of Canada's 2% target",
            "about": "What's driving Canadian inflation, component by component.",
            "sources_html": '<a href="https://www.statcan.gc.ca/en/subjects-start/prices_and_price_indexes/consumer_price_indexes">Statistics Canada</a>, Consumer Price Index tables 18-10-0004, 0006, 0007 and 0256',
            "legal": "Independent analysis, not an official Statistics Canada or Bank of Canada product, and not financial advice. Source: Statistics Canada, under the Statistics Canada Open Licence.",
        },
        "title_prefix": "Canada · ",
    },
}


def load_csv(name, folder="data"):
    with open(ROOT / folder / f"{name}.csv", newline="", encoding="utf-8") as f:
        return [dict(r) for r in csv.DictReader(f)]


def fill_template(page, code, values):
    """Keep this country's <!--IF:..--> blocks, drop the other's, and fill the {{PLACEHOLDERS}}."""
    for other in COUNTRIES:
        if other == code:
            page = re.sub(r"<!--IF:%s-->|<!--/IF:%s-->" % (other, other), "", page)
        else:
            page = re.sub(r"<!--IF:%s-->.*?<!--/IF:%s-->" % (other, other), "", page, flags=re.S)
    for k, v in values.items():
        page = page.replace("{{" + k + "}}", html.escape(v, quote=True))
    left = re.findall(r"\{\{[A-Z_0-9]+\}\}", page)
    if left:
        sys.exit(f"template placeholders not filled for {code}: {sorted(set(left))}")
    return page


def compare_data(us, ca, ca_release):
    """Everything the US vs Canada tab draws, from both countries' data."""
    num = lambda v: None if v in ("", None) else float(v)
    cu = {r["item"]: r for r in us["components"]}
    cc = {r["item"]: r for r in ca["components"]}

    def yoy_series(rows, col):
        vals = {r["date"]: num(r.get(col)) for r in rows}
        out = {}
        for d, v in vals.items():
            prev = f"{int(d[:4]) - 1}{d[4:]}"
            if v is not None and vals.get(prev):
                out[d] = round((v / vals[prev] - 1) * 100, 2)
        return out

    us_nsa = any(num(r.get("headline_nsa")) for r in us["fred"])
    us_h = yoy_series(us["fred"], "headline_nsa" if us_nsa else "headline")
    us_c = yoy_series(us["fred"], "core_nsa" if us_nsa else "core")
    ca_h = yoy_series(ca["fred"], "headline_nsa")
    ca_c = yoy_series(ca["fred"], "core")  # Canada's core NSA isn't in the history file; SA 12-month is within a few hundredths
    # latest official 12-month figures override the computed ones for the latest month
    lu = max(r["date"] for r in us["fred"] if r["headline"])
    lc = max(r["date"] for r in ca["fred"] if r["headline"])
    us_h[lu], us_c[lu] = num(cu["All items"]["yoy"]), num(cu["All items less food and energy"]["yoy"])
    ca_h[lc], ca_c[lc] = num(cc["All items"]["yoy"]), num(cc["All items less food and energy"]["yoy"])
    dates = sorted(set(us_h) | set(ca_h))
    series = [{"date": d, "us_head": us_h.get(d), "ca_head": ca_h.get(d), "us_core": us_c.get(d), "ca_core": ca_c.get(d)}
              for d in dates if d >= "2020-01-01"]

    def sa_mom(rows):
        r = [x for x in rows if num(x["headline"])]
        return round((num(r[-1]["headline"]) / num(r[-2]["headline"]) - 1) * 100, 1)

    cm = (ca_release or {}).get("core_measures", {})
    kpis = [
        {"label": "All items, past 12 months", "us": num(cu["All items"]["yoy"]), "ca": num(cc["All items"]["yoy"])},
        {"label": "Core (excluding food and energy)", "us": num(cu["All items less food and energy"]["yoy"]), "ca": num(cc["All items less food and energy"]["yoy"]),
         "note": (f"Bank of Canada's CPI-trim: {cm['trim']:.1f}%, CPI-median: {cm['median']:.1f}%" if cm.get("trim") is not None and cm.get("median") is not None else None)},
        {"label": "Shelter, past 12 months", "us": num(cu["Shelter"]["yoy"]), "ca": num(cc["Shelter"]["yoy"])},
        {"label": "Latest month, seasonally adjusted", "us": sa_mom(us["fred"]), "ca": sa_mom(ca["fred"])},
    ]
    PAIRS = [  # (label shown, US item, Canada item, bold)
        ("All items", "All items", "All items", True), ("Core", "All items less food and energy", "All items less food and energy", True),
        ("Food", "Food", "Food", True), ("Groceries", "Food at home", "Food purchased from stores", False),
        ("Restaurants", "Food away from home", "Restaurants", False), ("Energy", "Energy", "Energy", True),
        ("Gasoline", "Gasoline (all types)", "Gasoline", False), ("Electricity", "Electricity", "Electricity", False),
        ("Natural gas", "Utility (piped) gas service", "Natural gas", False), ("Core goods", "Core goods", "Core goods", True),
        ("Clothing and footwear", "Apparel", "Clothing and footwear", False), ("Vehicles", "New vehicles", "Vehicle purchases", False),
        ("Core services", "Core services", "Core services", True), ("Shelter", "Shelter", "Shelter", False),
        ("Rent", "Rent of primary residence", "Rent", False), ("Vehicle insurance", "Motor vehicle insurance", "Vehicle insurance", False),
        ("Air travel", "Airline fares", "Air travel", False),
    ]
    pairs = []
    for label, ui, ci, agg in PAIRS:
        if ui in cu and ci in cc:
            pairs.append({"label": label, "us": num(cu[ui]["yoy"]), "ca": num(cc[ci]["yoy"]), "us_name": ui, "ca_name": ci, "agg": agg})

    def groups(effects):
        g = {}
        for r in effects:
            if r["view"] == "yoy" and r["level"] == "parent":
                g[r["group"]] = round(g.get(r["group"], 0) + float(r["contrib"]), 3)
        return g

    return {"kpis": kpis, "series": series, "pairs": pairs, "groups": {"us": groups(us["effects"]), "ca": groups(ca["effects"])},
            "heads": {"us": num(cu["All items"]["yoy"]), "ca": num(cc["All items"]["yoy"])},
            "gapNote": "" if us_nsa else "US months before the latest use seasonally adjusted indexes, within about 0.1 point of the official figures."}


def main():
    cfg = json.loads((ROOT / "site.config.json").read_text(encoding="utf-8"))
    d3 = (ROOT / "vendor" / "d3.min.js").read_text(encoding="utf-8")
    all_data = {}
    for code, cc in COUNTRIES.items():
        data = {name: load_csv(name, cc["dir"]) for name in DATASETS}
        for name, rows in data.items():
            if not rows:
                sys.exit(f"{cc['dir']}/{name}.csv is empty")
        all_data[code] = data
    ca_release = json.loads((ROOT / "data" / "ca" / "release.json").read_text(encoding="utf-8"))
    COUNTRIES["ca"]["js"]["weightRef"] = ca_release["link_month"] + "-01"
    cm = ca_release.get("core_measures", {})
    if cm.get("trim") is not None and cm.get("median") is not None:
        COUNTRIES["ca"]["shell"]["lede_extra"] = (f"The Bank of Canada's preferred core measures, CPI-trim and CPI-median, were "
                                                  f"{cm['trim']:.1f}% and {cm['median']:.1f}%. ")
        COUNTRIES["ca"]["page"]["THIRD_SUB"] = f"CPI-median: {cm['median']:.1f}% over 12 months"
    compare = compare_data(all_data["us"], all_data["ca"], ca_release)
    for code in COUNTRIES:
        build_page(cfg, d3, code, all_data[code], compare)


def build_page(cfg, d3, code, data, compare):
    cc = COUNTRIES[code]
    page = fill_template((ROOT / "template" / "page.html").read_text(encoding="utf-8"), code, cc["page"])
    latest_m = max(r["date"] for r in data["fred"] if r["headline"])
    y, m = int(latest_m[:4]), int(latest_m[5:7])
    prev = MONTHS[m - 2] if m > 1 else "December"
    page = page.replace('id="viewseg">', f'id="viewseg" data-yoy-title="{MONTHS[m - 1]} {y} compared with {MONTHS[m - 1]} {y - 1}" '
                        f'data-mom-title="{MONTHS[m - 1]} compared with {prev}">', 1)

    latest = latest_m
    about = cfg.get("about_html") or ""
    if cfg.get("author"):
        about = f"<p>Built by {html.escape(cfg['author'])}.</p>" + about
    page = page.replace("<!--ABOUT-->", about)

    site_url = (cfg.get("site_url") or "").rstrip("/")
    og = ""
    if site_url:
        og = (f'<meta property="og:image" content="{site_url}/og-image.png">\n'
              f'<meta property="og:url" content="{site_url}{cc["path"]}">\n'
              f'<link rel="canonical" href="{site_url}{cc["path"]}">\n'
              f'<link rel="alternate" hreflang="en-us" href="{site_url}/">\n'
              f'<link rel="alternate" hreflang="en-ca" href="{site_url}/canada/">\n'
              '<meta name="twitter:card" content="summary_large_image">\n')

    light, dark, sizes, favicon = site_shell.LIGHT, site_shell.DARK, site_shell.SIZES, site_shell.FAVICON
    rel_path = ROOT / cc["dir"] / "release.json"
    release = json.loads(rel_path.read_text(encoding="utf-8")) if rel_path.exists() else {}
    banner_html, month_name = site_shell.banner(data, release, cc["shell"])

    # minimal stand-in for the dashboard runtime: serves the embedded data, runs calculations, redraws on changes
    shim = (
        "window.__STANDALONE__=true;\n"
        "window.COUNTRY=" + json.dumps(cc["js"], separators=(",", ":")) + ";\n"
        "window.COMPARE=" + json.dumps(compare, separators=(",", ":")) + ";\n"
        "window.dash=(()=>{const D=" + json.dumps(data, separators=(",", ":")) + ";"
        "const calcs={},cache={};let params={tab:'overview',view:'yoy',roc_window:'3M',roc_range:'5Y',hist_range:'5Y',flow_measure:'contrib'};const cbs=[];"
        "const get=(id)=>{if(D[id])return{status:'ok',data:D[id],columns:Object.keys(D[id][0]),meta:[]};"
        "if(calcs[id]){if(!(id in cache)){try{cache[id]=calcs[id].fn(...calcs[id].inputs.map(i=>get(i).data))}catch(e){console.error('calc '+id,e);cache[id]=null}}"
        "return cache[id]==null?{status:'error',data:[]}:{status:'ok',data:cache[id]}}return{status:'missing',data:[]}};"
        "const run=()=>cbs.forEach(f=>{try{f()}catch(e){console.error(e)}});let rt;"
        "window.addEventListener('resize',()=>{clearTimeout(rt);rt=setTimeout(run,150)});"
        "return{calc:(id,o)=>{calcs[id]=o},data:get,onData:(f)=>{cbs.push(f);setTimeout(()=>{try{f()}catch(e){console.error(e)}},0)},"
        "params:()=>({...params}),setParams:(o)=>{Object.assign(params,o);run()},resetParams(){},"
        "colors:['#2F6FB3','#C47A2C','#3E9A6A','#7E5BB5','#C4536D','#2D9AA8','#8C8A3A','#566176'],refresh(){},"
        "setLink:(n)=>{try{history.replaceState(null,'','#'+n)}catch(e){}},loader(){}}})();"
    )

    ad_client = (cfg.get("adsense_client") or "").strip()
    if ad_client and not re.fullmatch(r"ca-pub-\d{10,20}", ad_client):
        sys.exit("adsense_client in site.config.json should look like ca-pub-1234567890123456")
    ads_head = (f'<script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client={ad_client}" crossorigin="anonymous"></script>\n'
                f'<meta name="google-adsense-account" content="{ad_client}">\n') if ad_client else ""

    # first-party, cookieless analytics (served by worker/index.js, viewed at /stats)
    tracker = "<script>" + (ROOT / "template" / "track.js").read_text(encoding="utf-8").strip() + "</script>\n"
    ads_head = ads_head + tracker

    if code == "us":
        title, desc = html.escape(cfg["title"]), html.escape(cfg["description"])
    else:
        title = html.escape(f"{cfg['site_name']}: what's driving Canadian CPI, component by component")
        desc = html.escape("What's driving Canadian inflation: every CPI component, its share of the basket, its contribution to the headline, "
                           "momentum and provincial differences against the Bank of Canada's 2% target. Updated after each Statistics Canada release.")
    out = f"""<!doctype html>
<html lang="{'en-CA' if code == 'ca' else 'en'}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
{site_shell.THEME_HEAD}
<title>{title}</title>
<meta name="description" content="{desc}">
<meta property="og:type" content="website">
<meta property="og:title" content="{title}">
<meta property="og:description" content="{desc}">
<meta property="og:site_name" content="{html.escape(cfg['site_name'])}">
{og}<link rel="icon" href="{favicon}">
<meta name="data-latest" content="{latest}">
{site_shell.FONTS}
<style>
{site_shell.theme_css()}
{site_shell.CSS}
</style>
<script>{d3}</script>
<script>{shim}</script>
{ads_head}{cfg.get('analytics_html') or ''}
</head>
<body class="standalone">
<a class="skip" href="#dash-root">Skip to the dashboard</a>
{site_shell.header(cfg, banner_html, code)}
<main class="wrap">
<div id="dash-root">
{page}
</div>
</main>
{site_shell.footer(cfg, month_name, country=cc["shell"])}
{site_shell.AFTER}
{site_shell.THEME_JS}
</body>
</html>
"""
    site = ROOT / "site"
    (site / cc["out"]).parent.mkdir(parents=True, exist_ok=True)
    (site / cc["out"]).write_text(out, encoding="utf-8")
    print(f"site/{cc['out']} written ({len(out) // 1024} KB, latest data {latest})")
    if code != "us":
        return
    domain = (cfg.get("custom_domain") or "").strip()
    if domain:
        (site / "CNAME").write_text(domain + "\n", encoding="utf-8")
    if site_url:
        (site / "robots.txt").write_text(f"User-agent: *\nAllow: /\nDisallow: /stats\nDisallow: /api/\nSitemap: {site_url}/sitemap.xml\n", encoding="utf-8")
        (site / "sitemap.xml").write_text(
            '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
            f"  <url><loc>{site_url}/</loc><lastmod>{latest[:7]}-15</lastmod><changefreq>monthly</changefreq></url>\n"
            f"  <url><loc>{site_url}/canada/</loc><lastmod>{latest[:7]}-20</lastmod><changefreq>monthly</changefreq></url>\n"
            f"  <url><loc>{site_url}/privacy</loc><changefreq>yearly</changefreq></url>\n</urlset>\n",
            encoding="utf-8")
    ads_txt = site / "ads.txt"
    if ad_client:
        ads_txt.write_text(f"google.com, {ad_client.replace('ca-', '')}, DIRECT, f08c47fec0942fa0\n", encoding="utf-8")
    elif ads_txt.exists():
        ads_txt.unlink()
    (site / "privacy.html").write_text(privacy_page(cfg, ads_head, light, dark, sizes, favicon, month_name), encoding="utf-8")


def privacy_page(cfg, ads_head, light, dark, sizes, favicon, month_name):
    name = html.escape(cfg["site_name"])
    email = (cfg.get("contact_email") or "").strip()
    contact = (f'<p>Questions about this policy: <a href="mailto:{html.escape(email)}">{html.escape(email)}</a>.</p>' if email else "")
    ads = "googlesyndication" in ads_head
    ad_section = """
<h2>Advertising</h2>
<p>This site shows ads served by Google AdSense. Google and its partners use cookies and similar technologies to show ads and to measure them. Those ads may be based on your previous visits to this and other websites.</p>
<p>Google’s use of advertising cookies lets it and its partners serve ads based on your visits here and elsewhere on the internet. You can turn off personalized advertising in <a href="https://adssettings.google.com">Google’s Ads Settings</a>, or opt out of some third-party vendors’ cookies at <a href="https://www.aboutads.info/choices/">aboutads.info</a>.</p>
<p>How Google uses data from sites that use its services: <a href="https://policies.google.com/technologies/partner-sites">policies.google.com/technologies/partner-sites</a>.</p>
<p>Visitors in the European Economic Area, the UK and Switzerland are asked for consent before personalized ads are shown, through Google’s consent message.</p>""" if ads else ""
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
{site_shell.THEME_HEAD}
<title>Privacy policy · {name}</title>
<meta name="description" content="How {name} handles visitor data, cookies and advertising.">
<link rel="icon" href="{favicon}">
{site_shell.FONTS}
<style>
{site_shell.theme_css()}
{site_shell.CSS}
.policy{{max-width:44rem;margin:0 auto;padding:40px 0 56px;font-size:16px;line-height:1.65;color:var(--color-fg)}}
.policy h1{{font-size:32px;margin:0 0 6px}}
.policy h2{{font-size:19px;margin:28px 0 8px}}
.policy p{{margin:0 0 12px}}
.policy .muted{{color:var(--color-fg-muted)}}
.policy a{{color:inherit}}
</style>
{ads_head}</head>
<body class="standalone">
<header class="masthead"><div class="wrap"><nav class="topbar" aria-label="Site"><a class="brand" href="/">{site_shell.LOGO}<span>{name}</span></a>
<div class="top-right"><nav class="country" aria-label="Country"><a href="/">United States</a><a href="/canada/">Canada</a></nav>{site_shell.THEME_BTN}</div></nav></div></header>
<main class="wrap"><article class="policy">
<h1>Privacy policy</h1>
<p class="muted">{name} · inflationbreakdown.com</p>
<h2>What this site collects</h2>
<p>There are no accounts, sign-ups or forms, and the site doesn’t ask for any personal information. The dashboard runs in your browser using public data from the U.S. Bureau of Labor Statistics, FRED and Statistics Canada.</p>
<p>To understand how the site is used, it counts visits itself: the page viewed, the dashboard tabs opened, time spent, the referring website, the country (worked out from the IP address, which is not stored), and the device and browser type. It uses no cookies for this. Each visitor is represented by an anonymous code built from the IP address and browser that changes every day, so visits can’t be linked across days or to a person. If your browser sends a Do Not Track or Global Privacy Control signal, nothing is counted. These records are kept for about 13 months.</p>
<p>The site is hosted on Cloudflare, which processes standard request information such as IP addresses to deliver and protect the site. See <a href="https://www.cloudflare.com/privacypolicy/">Cloudflare’s privacy policy</a>.</p>
{ad_section}
<h2>Changes</h2>
<p>If this policy changes, the updated version will be posted on this page.</p>
{contact}
</article></main>
{site_shell.footer(cfg, month_name, base="/")}
{site_shell.THEME_JS}
</body>
</html>
"""


if __name__ == "__main__":
    main()

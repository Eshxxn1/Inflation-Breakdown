#!/usr/bin/env python3
"""Build site/index.html: the dashboard page, its data and d3 in one self-contained file.

Reads template/page.html, data/*.csv, vendor/d3.min.js and site.config.json.
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


def load_csv(name):
    with open(ROOT / "data" / f"{name}.csv", newline="", encoding="utf-8") as f:
        return [dict(r) for r in csv.DictReader(f)]


def main():
    cfg = json.loads((ROOT / "site.config.json").read_text(encoding="utf-8"))
    page = (ROOT / "template" / "page.html").read_text(encoding="utf-8")
    d3 = (ROOT / "vendor" / "d3.min.js").read_text(encoding="utf-8")
    data = {name: load_csv(name) for name in DATASETS}
    for name, rows in data.items():
        if not rows:
            sys.exit(f"data/{name}.csv is empty")

    latest = max(r["date"] for r in data["fred"] if r["headline"])
    about = cfg.get("about_html") or ""
    if cfg.get("author"):
        about = f"<p>Built by {html.escape(cfg['author'])}.</p>" + about
    page = page.replace("<!--ABOUT-->", about)

    site_url = (cfg.get("site_url") or "").rstrip("/")
    og = ""
    if site_url:
        og = (f'<meta property="og:image" content="{site_url}/og-image.png">\n'
              f'<meta property="og:url" content="{site_url}/">\n'
              f'<link rel="canonical" href="{site_url}/">\n'
              '<meta name="twitter:card" content="summary_large_image">\n')

    light, dark, sizes, favicon = site_shell.LIGHT, site_shell.DARK, site_shell.SIZES, site_shell.FAVICON
    release = json.loads((ROOT / 'data' / 'release.json').read_text(encoding='utf-8')) if (ROOT / 'data' / 'release.json').exists() else {}
    banner_html, month_name = site_shell.banner(data, release)

    # minimal stand-in for the dashboard runtime: serves the embedded data, runs calculations, redraws on changes
    shim = (
        "window.__STANDALONE__=true;\n"
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

    title = html.escape(cfg["title"])
    desc = html.escape(cfg["description"])
    out = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
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
:root{{{light}{sizes}}}
@media (prefers-color-scheme: dark){{:root{{{dark}}}}}
{site_shell.CSS}
</style>
<script>{d3}</script>
<script>{shim}</script>
{ads_head}{cfg.get('analytics_html') or ''}
</head>
<body class="standalone">
<a class="skip" href="#dash-root">Skip to the dashboard</a>
{site_shell.header(cfg, banner_html)}
<main class="wrap">
{site_shell.viewbar(data)}
<div id="dash-root">
{page}
</div>
</main>
{site_shell.footer(cfg, month_name)}
{site_shell.AFTER}
</body>
</html>
"""
    site = ROOT / "site"
    site.mkdir(exist_ok=True)
    (site / "index.html").write_text(out, encoding="utf-8")
    domain = (cfg.get("custom_domain") or "").strip()
    if domain:
        (site / "CNAME").write_text(domain + "\n", encoding="utf-8")
    if site_url:
        (site / "robots.txt").write_text(f"User-agent: *\nAllow: /\nSitemap: {site_url}/sitemap.xml\n", encoding="utf-8")
        (site / "sitemap.xml").write_text(
            '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
            f"  <url><loc>{site_url}/</loc><lastmod>{latest[:7]}-15</lastmod><changefreq>monthly</changefreq></url>\n"
            f"  <url><loc>{site_url}/privacy</loc><changefreq>yearly</changefreq></url>\n</urlset>\n",
            encoding="utf-8")
    ads_txt = site / "ads.txt"
    if ad_client:
        ads_txt.write_text(f"google.com, {ad_client.replace('ca-', '')}, DIRECT, f08c47fec0942fa0\n", encoding="utf-8")
    elif ads_txt.exists():
        ads_txt.unlink()
    (site / "privacy.html").write_text(privacy_page(cfg, ads_head, light, dark, sizes, favicon, month_name), encoding="utf-8")
    print(f"site/index.html written ({len(out) // 1024} KB, latest data {latest})")


def privacy_page(cfg, ads_head, light, dark, sizes, favicon, month_name):
    name = html.escape(cfg["site_name"])
    email = (cfg.get("contact_email") or "").strip()
    contact = (f'<p>Questions about this policy: <a href="mailto:{html.escape(email)}">{html.escape(email)}</a>.</p>' if email else "")
    ads = bool(ads_head)
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
<title>Privacy policy · {name}</title>
<meta name="description" content="How {name} handles visitor data, cookies and advertising.">
<link rel="icon" href="{favicon}">
{site_shell.FONTS}
<style>
:root{{{light}{sizes}}}
@media (prefers-color-scheme: dark){{:root{{{dark}}}}}
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
<div class="toplinks"><a href="/">Back to the dashboard</a></div></nav></div></header>
<main class="wrap"><article class="policy">
<h1>Privacy policy</h1>
<p class="muted">{name} · inflationbreakdown.com</p>
<h2>What this site collects</h2>
<p>There are no accounts, sign-ups or forms, and the site doesn’t ask for any personal information. The dashboard runs in your browser using public data from the U.S. Bureau of Labor Statistics and FRED.</p>
<p>The site is hosted on Cloudflare, which processes standard request information such as IP addresses to deliver and protect the site. See <a href="https://www.cloudflare.com/privacypolicy/">Cloudflare’s privacy policy</a>.</p>
{ad_section}
<h2>Changes</h2>
<p>If this policy changes, the updated version will be posted on this page.</p>
{contact}
</article></main>
{site_shell.footer(cfg, month_name, base="/")}
</body>
</html>
"""


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Build site/index.html: the dashboard page, its data and d3 in one self-contained file.

Reads template/page.html, data/*.csv, vendor/d3.min.js and site.config.json.
Run from the repository root:  python scripts/build_site.py
"""
import csv
import html
import json
import pathlib
import sys

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

    favicon = ("data:image/svg+xml,"
               "%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E"
               "%3Crect width='32' height='32' rx='7' fill='%231f1e1d'/%3E"
               "%3Crect x='6' y='17' width='4' height='9' rx='1' fill='%233b6fb6'/%3E"
               "%3Crect x='12' y='12' width='4' height='14' rx='1' fill='%234f9a6b'/%3E"
               "%3Crect x='18' y='8' width='4' height='18' rx='1' fill='%23c27c2c'/%3E"
               "%3Crect x='24' y='5' width='4' height='21' rx='1' fill='%23d0453a'/%3E%3C/svg%3E")

    light = ("--color-fg:#1f1e1d;--color-fg-muted:#6b6a64;--color-bg:#ffffff;--color-panel:#faf9f5;--color-border-line:#e5e3dc;"
             "--color-ok:#2f7d4a;--color-warn:#a86b00;--color-bad:#b3261e;--cds-chart-status-critical:#d0453a;--cds-chart-muted:#b9b7ae;"
             "--cds-chart-grid:#ecebe6;--cds-chart-axis:#c9c7bf;--cds-chart-reference:#6b6a64;--cds-surface-popover:#ffffff;"
             "--cds-border:#dcdad3;--cds-shadow-popover:0 2px 10px rgba(0,0,0,.14);--cds-text-secondary:#6b6a64;")
    dark = ("--color-fg:#ecebe6;--color-fg-muted:#a3a19a;--color-bg:#1a1918;--color-panel:#232220;--color-border-line:#3a3936;"
            "--color-ok:#6cc08b;--color-warn:#e0a84a;--color-bad:#f07a70;--cds-chart-status-critical:#e25f53;--cds-chart-muted:#6e6c66;"
            "--cds-chart-grid:#2f2e2b;--cds-chart-axis:#4a4945;--cds-chart-reference:#a3a19a;--cds-surface-popover:#2b2a27;"
            "--cds-border:#45443f;--cds-shadow-popover:0 2px 10px rgba(0,0,0,.5);--cds-text-secondary:#a3a19a;")
    sizes = ("--cds-radius:8px;--cds-pad-xs:4px;--cds-pad-sm:8px;--cds-pad-md:12px;--cds-pad-lg:16px;--cds-gap-xs:4px;--cds-gap-sm:8px;"
             "--cds-gap-md:12px;--cds-gap-lg:20px;--cds-gap-xl:28px;--cds-font-size-caption:12px;--cds-font-size-body:14px;"
             "--cds-font-size-heading:16px;--cds-font-size-title:28px;--cds-font-weight-medium:500;"
             "--font-anthropic-sans:system-ui,-apple-system,'Segoe UI',Roboto,sans-serif;--font-anthropic-serif:Georgia,'Times New Roman',serif;"
             "--cds-dur-slow:.3s;--cds-ease-out:cubic-bezier(.2,.8,.2,1);")

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
        "colors:['#3b6fb6','#c27c2c','#4f9a6b','#8a5cb8','#c4536d','#2d9aa8','#8c8a3a','#6b6a64'],refresh(){},"
        "setLink:(n)=>{try{history.replaceState(null,'','#'+n)}catch(e){}},loader(){}}})();"
    )

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
<style>
:root{{{light}{sizes}}}
@media (prefers-color-scheme: dark){{:root{{{dark}}}}}
html,body{{margin:0;background:var(--color-bg);color:var(--color-fg)}}
#dash-root{{max-width:1240px;margin:0 auto;padding:24px 16px}}
.site-bar{{max-width:1240px;margin:0 auto;padding:14px 16px 0;font:600 13px/1 var(--font-anthropic-sans);letter-spacing:.02em;color:var(--color-fg-muted)}}
.site-foot{{max-width:1240px;margin:0 auto;padding:8px 16px 40px;font:12px/1.6 var(--font-anthropic-sans);color:var(--color-fg-muted)}}
.site-foot a{{color:inherit}}
</style>
<script>{d3}</script>
<script>{shim}</script>
{cfg.get('analytics_html') or ''}
</head>
<body class="standalone">
<div class="site-bar">{html.escape(cfg['site_name'])}</div>
<div id="dash-root">
{page}
</div>
<footer class="site-foot">
Data: <a href="https://www.bls.gov/cpi/">U.S. Bureau of Labor Statistics</a> and <a href="https://fred.stlouisfed.org/">FRED, Federal Reserve Bank of St. Louis</a>.
Independent analysis; not an official BLS or Federal Reserve product. Latest data: {latest[:7]}.
</footer>
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
            f"  <url><loc>{site_url}/</loc><lastmod>{latest[:7]}-15</lastmod><changefreq>monthly</changefreq></url>\n</urlset>\n",
            encoding="utf-8")
    print(f"site/index.html written ({len(out) // 1024} KB, latest data {latest})")


if __name__ == "__main__":
    main()

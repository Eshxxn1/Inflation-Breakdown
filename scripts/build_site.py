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
    banner_html, month_name = site_shell.banner(data)

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
{cfg.get('analytics_html') or ''}
</head>
<body class="standalone">
{site_shell.header(cfg, banner_html)}
<main class="wrap">
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
            f"  <url><loc>{site_url}/</loc><lastmod>{latest[:7]}-15</lastmod><changefreq>monthly</changefreq></url>\n</urlset>\n",
            encoding="utf-8")
    print(f"site/index.html written ({len(out) // 1024} KB, latest data {latest})")


if __name__ == "__main__":
    main()

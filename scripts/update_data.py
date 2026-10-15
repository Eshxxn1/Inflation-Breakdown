#!/usr/bin/env python3
"""Refresh data/*.csv from the latest BLS CPI release and FRED.

Sources (all public, no API keys):
  BLS CPI news release tables  https://www.bls.gov/news.release/cpi.t01.htm (and t02, t04, t06, t07, nr0)
  FRED series via fredgraph.csv https://fred.stlouisfed.org/graph/fredgraph.csv?id=...

BLS asks automated clients to identify themselves: set BLS_USER_AGENT to something like
  "cpi-breakdown (you@example.com)"
The script validates everything it parses and exits non-zero without writing anything if a
table looks wrong, so a bad run never publishes bad numbers.
Run from the repository root:  python scripts/update_data.py   (add --offline DIR to read saved HTML)
"""
import csv
import io
import math
import os
import pathlib
import re
import sys

import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
BLS = "https://www.bls.gov/news.release/"
FRED_IDS = {"headline": "CPIAUCSL", "core": "CPILFESL", "food": "CPIUFDSL", "energy": "CPIENGSL",
            "core_goods": "CUSR0000SACL1E", "shelter": "CUSR0000SAH1"}
OFFLINE = None
if "--offline" in sys.argv:
    OFFLINE = pathlib.Path(sys.argv[sys.argv.index("--offline") + 1])


class Bad(Exception):
    pass


def fetch(url):
    if OFFLINE:
        return (OFFLINE / url.rsplit("/", 1)[-1].split("?")[0]).read_text(encoding="utf-8")
    import requests
    ua = os.environ.get("BLS_USER_AGENT") or "cpi-breakdown-dashboard (set BLS_USER_AGENT with a contact email)"
    r = requests.get(url, headers={"User-Agent": ua, "Accept": "text/html,text/csv"}, timeout=90)
    r.raise_for_status()
    return r.text


def clean(label):
    s = re.sub(r"\(\d+\)", "", str(label))
    s = re.sub(r"\s+", " ", s).strip()
    return s


def val(x):
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return None
    s = str(x).strip().replace("–", "-").replace("−", "-")
    if s in ("", "-", "--"):
        return None
    try:
        return float(s)
    except ValueError:
        return None


def bls_table(page, must_have):
    """The table on a BLS page whose first column contains `must_have`, as {label: [cells...]}."""
    html = fetch(BLS + page)
    for df in pd.read_html(io.StringIO(html)):
        first = [clean(v) for v in df.iloc[:, 0].tolist()]
        if must_have in first:
            rows = {}
            for i, lab in enumerate(first):
                if lab and lab not in rows and not lab.lower().startswith("footnotes"):
                    rows[lab] = df.iloc[i, 1:].tolist()
            return rows, df, html
    raise Bad(f"{page}: no table containing '{must_have}'")


def need(rows, label, page):
    if label not in rows:
        raise Bad(f"{page}: row '{label}' not found")
    return rows[label]


def release_month(html):
    m = re.search(r"(January|February|March|April|May|June|July|August|September|October|November|December) (\d{4})", html)
    if not m:
        raise Bad("could not find the release month")
    months = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
    return f"{m.group(2)}-{months.index(m.group(1)) + 1:02d}"


def read_csv(name):
    with open(DATA / f"{name}.csv", newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def fmt(x, nd):
    return "" if x is None else f"{x:.{nd}f}"


# ------------------------------------------------------------------ Table 1 → components.csv
ALIAS_T1 = {"Nonalcoholic beverages": "Nonalcoholic beverages and beverage materials",
            "Core goods": "Commodities less food and energy commodities",
            "Core services": "Services less energy services",
            "Owners' equivalent rent": "Owners' equivalent rent of residences"}


def update_components():
    rows, _, html = bls_table("cpi.t01.htm", "All items")
    month = release_month(re.sub(r"<[^>]+>", " ", html))
    out = []
    for r in read_csv("components"):
        cells = need(rows, ALIAS_T1.get(r["item"], r["item"]), "Table 1")
        w, yoy, mom = val(cells[0]), val(cells[4]), val(cells[-1])
        if w is None or yoy is None or mom is None:
            raise Bad(f"Table 1: missing numbers for {r['item']}")
        out.append({**r, "weight": fmt(w, 3), "yoy": fmt(yoy, 1), "mom_sa": fmt(mom, 1)})
    allw = float(out[0]["weight"])
    if abs(allw - 100) > 0.01:
        raise Bad("Table 1: all-items relative importance is not 100")
    return month, out


# ------------------------------------------------------------------ Table A → components_monthly.csv
def update_monthly():
    rows, df, _ = bls_table("cpi.nr0.htm", "All items")
    labels = [" ".join(str(x) for x in (c if isinstance(c, tuple) else (c,))) for c in df.columns]
    months = []
    for lab in labels[1:8]:
        m = re.search(r"(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\.? (\d{4})", lab)
        if not m:
            raise Bad(f"Table A: can't read month header '{lab}'")
        months.append(f"{m.group(2)}-{['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'].index(m.group(1)) + 1:02d}")
    template = read_csv("components_monthly")
    items = []
    for r in template:
        if (r["item"], r["group"], r["depth"]) not in items:
            items.append((r["item"], r["group"], r["depth"]))
    out = []
    for item, group, depth in items:
        cells = need(rows, ALIAS_T1.get(item, item), "Table A")
        for i, mo in enumerate(months):
            v = val(cells[i])
            out.append({"item": item, "group": group, "depth": depth, "month": mo, "mom_sa": fmt(v, 1)})
    return out


# ------------------------------------------------------------------ Tables 2, 6, 7 → effects.csv
ALIAS_E = {"Owners' equivalent rent": "Owners' equivalent rent of residences",
           "Nonalcoholic beverages": "Nonalcoholic beverages and beverage materials",
           "Tuition, school fees and childcare": "Tuition, other school fees, and childcare",
           "Internet services": "Internet services and electronic information providers",
           "Telephone hardware and smartphones": "Telephone hardware, calculators, and other consumer information items",
           "Toys and other recreational goods": "Other recreational goods",
           "Water and sewer and trash collection": "Water and sewer and trash collection services",
           "Vehicles and parts": "Transportation commodities less motor fuel",
           "Recreation goods": "Recreation commodities",
           "Education and communication goods": "Education and communication commodities"}
SUM_PARENTS = {"Water, trash and household services", "Alcohol, tobacco and personal care goods"}


def update_effects(headline_yoy, headline_mom):
    t2, _, _ = bls_table("cpi.t02.htm", "All items")
    t6, _, _ = bls_table("cpi.t06.htm", "All items")
    t7, _, _ = bls_table("cpi.t07.htm", "All items")
    # leftover rows ("Rest of ..." and household operations) are recomputed below; real BLS items always have a weight
    template = [r for r in read_csv("effects") if r["view"] == "yoy" and r["weight"] != "" and r["item"] != "Other household operations"]
    out = []
    for view in ("yoy", "mom"):
        eff_t = t7 if view == "yoy" else t6
        parents, order = {}, []
        for r in template:
            p = r["parent"]
            if r["level"] == "parent":
                parents[p] = {"row": r, "subs": []}
                order.append(p)
            else:
                parents[p]["subs"].append(r)
        built = {}
        for p in order:
            prow = parents[p]["row"]
            subs = []
            for s in parents[p]["subs"]:
                lab = ALIAS_E.get(s["item"], s["item"])
                c2 = need(t2, lab, "Table 2")
                ce = need(eff_t, lab, "Table 7" if view == "yoy" else "Table 6")
                w, chg = val(c2[0]), val(c2[1] if view == "yoy" else c2[-1])
                eff = val(ce[2])
                if w is None or eff is None:
                    raise Bad(f"{view}: missing weight or effect for {s['item']}")
                subs.append({"item": s["item"], "weight": w, "change": chg, "contrib": eff})
            if p in SUM_PARENTS:
                w = sum(s["weight"] for s in subs)
                eff = sum(s["contrib"] for s in subs)
                chg = None
            else:
                lab = ALIAS_E.get(p, p)
                c2 = need(t2, lab, "Table 2")
                ce = need(eff_t, lab, "Table 7" if view == "yoy" else "Table 6")
                w, chg, eff = val(c2[0]), val(c2[1] if view == "yoy" else c2[-1]), val(ce[2])
                if w is None or eff is None:
                    raise Bad(f"{view}: missing weight or effect for {p}")
            built[p] = {"group": prow["group"], "weight": w, "change": chg, "contrib": eff, "subs": subs}
        # whatever of core services isn't in a listed component (household operations etc.)
        svc_w = val(need(t2, "Services less energy services", "Table 2")[0])
        svc_e = val(need(eff_t, "Services less energy services", "Table 7" if view == "yoy" else "Table 6")[2])
        listed = [b for b in built.values() if b["group"] == "Core services"]
        rest_w = svc_w - sum(b["weight"] for b in listed)
        rest_e = svc_e - sum(b["contrib"] for b in listed)
        hh = built["Water, trash and household services"]
        hh["subs"].append({"item": "Other household operations", "weight": rest_w, "change": None, "contrib": rest_e})
        hh["weight"] += rest_w
        hh["contrib"] += rest_e
        total = 0
        for p in order:
            b = built[p]
            total += b["contrib"]
            out.append({"view": view, "parent": p, "item": p, "group": b["group"], "level": "parent", "weight": fmt(b["weight"], 3),
                        "change": fmt(b["change"], 1), "contrib": fmt(b["contrib"], 3), "basis": "official"})
            for s in b["subs"]:
                out.append({"view": view, "parent": p, "item": s["item"], "group": b["group"], "level": "sub", "weight": fmt(s["weight"], 3),
                            "change": fmt(s["change"], 1), "contrib": fmt(s["contrib"], 3), "basis": "official"})
            resid = b["contrib"] - sum(s["contrib"] for s in b["subs"])
            if abs(resid) >= 0.005:
                out.append({"view": view, "parent": p, "item": "Rest of " + p.lower(), "group": b["group"], "level": "sub", "weight": "",
                            "change": "", "contrib": fmt(resid, 3), "basis": "official"})
        target = headline_yoy if view == "yoy" else headline_mom
        if abs(total - target) > (0.15 if view == "yoy" else 0.1):
            raise Bad(f"{view}: contributions add to {total:.3f}, published headline is {target}")
        print(f"  {view}: contributions add to {total:.3f} (published {target})")
    return out


# ------------------------------------------------------------------ Table 4 → regions.csv
AREAS = {"Chicago": "Chicago-Naperville-Elgin, IL-IN-WI", "Los Angeles": "Los Angeles-Long Beach-Anaheim, CA",
         "New York": "New York-Newark-Jersey City, NY-NJ-PA", "Atlanta": "Atlanta-Sandy Springs-Roswell, GA",
         "Baltimore": "Baltimore-Columbia-Towson, MD", "Detroit": "Detroit-Warren-Dearborn, MI",
         "Houston": "Houston-The Woodlands-Sugar Land, TX", "Miami": "Miami-Fort Lauderdale-West Palm Beach, FL",
         "Philadelphia": "Philadelphia-Camden-Wilmington, PA-NJ-DE-MD", "Phoenix": "Phoenix-Mesa-Scottsdale, AZ",
         "San Francisco": "San Francisco-Oakland-Hayward, CA", "Seattle": "Seattle-Tacoma-Bellevue, WA",
         "St. Louis": "St. Louis, MO-IL", "Boston": "Boston-Cambridge-Newton, MA-NH", "Dallas-Fort Worth": "Dallas-Fort Worth-Arlington, TX",
         "Denver": "Denver-Aurora-Lakewood, CO", "Minneapolis-St. Paul": "Minneapolis-St.Paul-Bloomington, MN-WI",
         "Riverside": "Riverside-San Bernardino-Ontario, CA", "San Diego": "San Diego-Carlsbad, CA",
         "Tampa": "Tampa-St. Petersburg-Clearwater, FL", "Washington DC": "Washington-Arlington-Alexandria, DC-VA-MD-WV"}


def update_regions(month):
    rows, _, _ = bls_table("cpi.t04.htm", "U.S. city average")
    y, m = int(month[:4]), int(month[5:])
    names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    latest = f"{names[m - 1]} {y}"
    prev = f"{names[m - 2]} {y if m > 1 else y - 1}"
    out = []
    for r in read_csv("regions"):
        cells = need(rows, AREAS.get(r["area"], r["area"]), "Table 4")
        sched = str(cells[0]).strip()
        yoy_now, mom_now, yoy_prev = val(cells[1]), val(cells[3]), val(cells[4])
        if yoy_now is not None:
            out.append({**r, "yoy": fmt(yoy_now, 1), "mom": fmt(mom_now, 1) if sched == "M" else "", "period": latest})
        elif yoy_prev is not None:
            out.append({**r, "yoy": fmt(yoy_prev, 1), "mom": "", "period": prev})
        else:
            raise Bad(f"Table 4: no 12-month change for {r['area']}")
    return out


# ------------------------------------------------------------------ FRED → fred.csv
def update_fred():
    url = "https://fred.stlouisfed.org/graph/fredgraph.csv?id=" + ",".join(FRED_IDS.values()) + "&cosd=2019-01-01"
    df = pd.read_csv(io.StringIO(fetch(url)), na_values=["."])
    df = df.rename(columns={df.columns[0]: "date"})
    for v in FRED_IDS.values():
        if v not in df.columns:
            raise Bad(f"FRED: series {v} missing")
    out = []
    for _, r in df.iterrows():
        row = {"date": str(r["date"])[:10]}
        for k, v in FRED_IDS.items():
            row[k] = fmt(None if pd.isna(r[v]) else float(r[v]), 3)
        out.append(row)
    return out


def write(name, rows):
    with open(DATA / f"{name}.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()), lineterminator="\n")
        w.writeheader()
        w.writerows(rows)


def main():
    try:
        month, comps = update_components()
        print(f"BLS release month: {month}")
        fred = update_fred()
        fred_latest = max(r["date"] for r in fred if r["headline"])[:7]
        if fred_latest != month:
            raise Bad(f"FRED's latest month is {fred_latest} but BLS has released {month}; try again later")
        head = next(r for r in comps if r["item"] == "All items")
        monthly = update_monthly()
        effects = update_effects(float(head["yoy"]), float(head["mom_sa"]))
        regions = update_regions(month)
        # cross-check: FRED headline 12-month change vs BLS (SA vs NSA differ a little)
        f = {r["date"][:7]: float(r["headline"]) for r in fred if r["headline"]}
        y, m = int(month[:4]), int(month[5:])
        sa12 = (f[month] / f[f"{y - 1}-{m:02d}"] - 1) * 100
        if abs(sa12 - float(head["yoy"])) > 0.4:
            raise Bad(f"FRED 12-month {sa12:.2f} is far from BLS {head['yoy']}")
    except Bad as e:
        report("warning", f"Not updating: {e}")
        sys.exit(1)
    except Exception as e:  # network errors, unexpected page layouts
        report("error", f"Update failed: {type(e).__name__}: {e}")
        sys.exit(1)
    write("components", comps)
    write("components_monthly", monthly)
    write("effects", effects)
    write("regions", regions)
    write("fred", fred)
    report("notice", f"Data updated to {month} (contributions add to the published headline within tolerance)")


def report(level, msg):
    """Print a message; inside GitHub Actions it also shows as an annotation on the run's summary page."""
    msg = str(msg).replace("\n", " ")[:900]
    print(msg, file=sys.stderr if level != "notice" else sys.stdout)
    if os.environ.get("GITHUB_ACTIONS"):
        print(f"::{level} title=CPI data update::{msg}")


if __name__ == "__main__":
    main()

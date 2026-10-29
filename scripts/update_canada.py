#!/usr/bin/env python3
"""Fetch Canada's CPI from Statistics Canada and write data/ca/*.csv in the same layout as the US files.

Tables (all public, no key needed):
  18-10-0004-01  CPI, monthly, not seasonally adjusted (all products, Canada, provinces and cities)
  18-10-0006-01  CPI, monthly, seasonally adjusted (all-items, the eight major components, ex food and energy)
  18-10-0007-01  Basket weights
  18-10-0256-01  Bank of Canada core measures (CPI-trim, CPI-median, CPI-common)

Statistics Canada doesn't publish contributions for each item, so they're estimated here from the basket
weights (see contributions()). Food, energy and core goods use Statistics Canada's own aggregates; core
services is the remainder, so the four groups add exactly to the published all-items change.

Run from the repository root:  python scripts/update_canada.py
For testing with downloaded tables: python scripts/update_canada.py --offline DIR  (DIR holds <table>.csv
or <table>_recent.csv files).
"""
import csv
import io
import json
import pathlib
import sys
import zipfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "ca"
START = "2018-01"           # earliest month kept (history charts start in 2019; 12 extra months for changes)
UA = {"User-Agent": "inflationbreakdown.com data updater (https://github.com/Eshxxn1/Inflation-Breakdown)"}


class Bad(Exception):
    pass


def report(level, msg):
    print(f"::{level} title=Canada CPI update::{msg}")


# ---------------------------------------------------------------- loading
def load(pid, offline):
    if offline:
        for name in (f"{pid}.csv", f"{pid}_recent.csv"):
            p = pathlib.Path(offline) / name
            if p.exists():
                return [r for r in csv.DictReader(open(p, encoding="utf-8-sig")) if r["REF_DATE"][:7] >= START[:4] or len(r["REF_DATE"]) == 4]
        raise Bad(f"no file for table {pid} in {offline}")
    import requests
    url = f"https://www150.statcan.gc.ca/n1/tbl/csv/{pid}-eng.zip"
    r = requests.get(url, headers=UA, timeout=300)
    if r.status_code != 200:
        raise Bad(f"Statistics Canada table {pid}: HTTP {r.status_code}")
    z = zipfile.ZipFile(io.BytesIO(r.content))
    name = next(n for n in z.namelist() if n.endswith(".csv") and "MetaData" not in n)
    rows = []
    for row in csv.DictReader(io.TextIOWrapper(z.open(name), encoding="utf-8-sig")):
        d = row["REF_DATE"]
        if len(d) == 4 or d >= START:
            rows.append(row)
    return rows


def series(rows, geo="Canada", dim="Products and product groups", extra=None):
    """{product: {month: value}} for one geography."""
    out = {}
    for r in rows:
        if r["GEO"] != geo or r["VALUE"] in ("", None):
            continue
        if extra and any(r.get(k) != v for k, v in extra.items()):
            continue
        out.setdefault(r[dim], {})[r["REF_DATE"]] = float(r["VALUE"])
    return out


# ---------------------------------------------------------------- what the site shows
# Contribution tree: group -> parents -> subs, as (label shown, Statistics Canada product)
TREE = {
    "Food": [
        ("Food from stores", "Food purchased from stores", [
            ("Meat", "Meat"), ("Fish and seafood", "Fish, seafood and other marine products"),
            ("Dairy products and eggs", "Dairy products and eggs"), ("Bakery and cereal products", "Bakery and cereal products (excluding baby food)"),
            ("Fruit and nuts", "Fruit, fruit preparations and nuts"), ("Vegetables", "Vegetables and vegetable preparations"),
            ("Other food and non-alcoholic drinks", "Other food products and non-alcoholic beverages")]),
        ("Restaurants", "Food purchased from restaurants", [
            ("Table-service restaurants", "Food purchased from table-service restaurants"),
            ("Fast food and take-out", "Food purchased from fast food and take-out restaurants"),
            ("Cafeterias and other restaurants", "Food purchased from cafeterias and other restaurants")]),
    ],
    "Energy": [
        ("Energy", "Energy", [
            ("Gasoline", "Gasoline"), ("Electricity", "Electricity"), ("Natural gas", "Natural gas"),
            ("Fuel oil and other fuels", "Fuel oil and other fuels")]),
    ],
    "Core goods": [
        ("Vehicle purchases", "Purchase of passenger vehicles", []),
        ("Clothing and footwear", None, [
            ("Clothing", "Clothing"), ("Footwear", "Footwear"), ("Accessories, watches and jewellery", "Clothing accessories, watches and jewellery")]),
        ("Furniture and household equipment", None, [
            ("Furniture and household textiles", "Furniture and household textiles"), ("Household equipment", "Household equipment")]),
        ("Vehicle parts and supplies", "Passenger vehicle parts, accessories and supplies", []),
        ("Health and personal care goods", None, [
            ("Health care goods", "Health care goods"), ("Personal care supplies", "Personal care supplies and equipment")]),
        ("Alcohol and tobacco from stores", None, [
            ("Alcohol from stores", "Alcoholic beverages purchased from stores"), ("Tobacco", "Tobacco products and smokers' supplies")]),
        ("Recreation goods", None, [
            ("Recreational vehicles", "Purchase of recreational vehicles and outboard motors"),
            ("Toys, games and hobby supplies", "Toys, games (excluding video games) and hobby supplies"),
            ("Sporting and exercise equipment", "Sporting and exercise equipment"),
            ("Computers and devices", "Digital computing equipment and devices")]),
        ("Household supplies", None, [
            ("Cleaning products", "Household cleaning products"), ("Paper, plastic and foil", "Paper, plastic and aluminum foil supplies"),
            ("Pet food and supplies", "Pet food and supplies"), ("Plants and flowers", "Seeds, plants and cut flowers")]),
    ],
    "Core services": [
        ("Rented accommodation", "Rented accommodation", [
            ("Rent", "Rent"), ("Tenants' insurance", "Tenants' insurance premiums"),
            ("Tenants' repairs and other costs", "Tenants' maintenance, repairs and other expenses")]),
        ("Owned accommodation", "Owned accommodation", [
            ("Mortgage interest cost", "Mortgage interest cost"), ("Homeowners' replacement cost", "Homeowners' replacement cost"),
            ("Property taxes", "Property taxes and other special charges"), ("Home and mortgage insurance", "Homeowners' home and mortgage insurance"),
            ("Homeowners' maintenance and repairs", "Homeowners' maintenance and repairs"), ("Other homeowner costs", "Other owned accommodation expenses")]),
        ("Transportation services", None, [
            ("Vehicle insurance", "Passenger vehicle insurance premiums"), ("Vehicle maintenance and repair", "Passenger vehicle maintenance and repair services"),
            ("Air travel", "Air transportation"), ("Rail, bus and other inter-city travel", "Rail, highway bus and other inter-city transportation"),
            ("Local transit and taxis", "Local and commuter transportation"), ("Vehicle leasing", "Leasing of passenger vehicles"),
            ("Vehicle rental", "Rental of passenger vehicles"), ("Parking", "Parking fees"),
            ("Vehicle registration", "Passenger vehicle registration fees"), ("Driver's licences", "Drivers' licences")]),
        ("Communication services", None, [
            ("Phone services", "Telephone services"), ("Postal and other communication services", "Postal and other communications services")]),
        ("Travel and recreation services", None, [
            ("Travel tours", "Travel tours"), ("Hotels and other lodging", "Traveller accommodation"),
            ("Recreation facilities", "Use of recreational facilities and services"),
            ("Streaming subscriptions", "Video and audio subscription services"),
            ("Live entertainment", "Spectator entertainment (excluding video and audio subscription services)")]),
        ("Education", None, [
            ("Tuition fees", "Tuition fees"), ("Other lessons and courses", "Other lessons, courses and education services")]),
        ("Health and personal care services", None, [
            ("Health care services", "Health care services"), ("Personal care services", "Personal care services")]),
        ("Household services", None, [
            ("Child care", "Child care services"), ("Housekeeping", "Housekeeping services"),
            ("Other household services", "Other household services"),
            ("Furniture and appliance services", "Services related to household furnishings and equipment")]),
        ("Drinks at bars and restaurants", "Alcoholic beverages served in licensed establishments", []),
        ("Water", "Water", []),
    ],
}
GROUP_PRODUCT = {"Food": "Food", "Energy": "Energy", "Core goods": "Goods excluding food purchased from stores and energy"}

# Component table, heat map and target bars: (shown name, product, group, level, depth)
COMPONENTS = [
    ("All items", "All-items", "Headline", "total", 0),
    ("Food", "Food", "Food", "aggregate", 1),
    ("Food purchased from stores", "Food purchased from stores", "Food", "aggregate", 2),
    ("Meat", "Meat", "Food", "leaf", 3),
    ("Fish and seafood", "Fish, seafood and other marine products", "Food", "leaf", 3),
    ("Dairy products and eggs", "Dairy products and eggs", "Food", "leaf", 3),
    ("Bakery and cereal products", "Bakery and cereal products (excluding baby food)", "Food", "leaf", 3),
    ("Fruit and nuts", "Fruit, fruit preparations and nuts", "Food", "leaf", 3),
    ("Vegetables", "Vegetables and vegetable preparations", "Food", "leaf", 3),
    ("Other food and drinks", "Other food products and non-alcoholic beverages", "Food", "leaf", 3),
    ("Restaurants", "Food purchased from restaurants", "Food", "leaf", 2),
    ("Energy", "Energy", "Energy", "aggregate", 1),
    ("Gasoline", "Gasoline", "Energy", "leaf", 2),
    ("Electricity", "Electricity", "Energy", "leaf", 2),
    ("Natural gas", "Natural gas", "Energy", "leaf", 2),
    ("Fuel oil and other fuels", "Fuel oil and other fuels", "Energy", "leaf", 2),
    ("All items less food and energy", "All-items excluding food and energy", "Core", "aggregate", 1),
    ("Core goods", "Goods excluding food purchased from stores and energy", "Core goods", "aggregate", 2),
    ("Clothing and footwear", "Clothing and footwear", "Core goods", "leaf", 3),
    ("Vehicle purchases", "Purchase of passenger vehicles", "Core goods", "leaf", 3),
    ("Furniture and household equipment", "Household furnishings and equipment", "Core goods", "leaf", 3),
    ("Vehicle parts and supplies", "Passenger vehicle parts, accessories and supplies", "Core goods", "leaf", 3),
    ("Health care goods", "Health care goods", "Core goods", "leaf", 3),
    ("Personal care supplies", "Personal care supplies and equipment", "Core goods", "leaf", 3),
    ("Alcohol from stores", "Alcoholic beverages purchased from stores", "Core goods", "leaf", 3),
    ("Tobacco", "Tobacco products and smokers' supplies", "Core goods", "leaf", 3),
    ("Computers and devices", "Digital computing equipment and devices", "Core goods", "leaf", 3),
    ("Core services", None, "Core services", "aggregate", 2),
    ("Shelter", "Shelter", "Core services", "aggregate", 3),
    ("Rent", "Rent", "Core services", "leaf", 4),
    ("Mortgage interest cost", "Mortgage interest cost", "Core services", "leaf", 4),
    ("Homeowners' replacement cost", "Homeowners' replacement cost", "Core services", "leaf", 4),
    ("Property taxes", "Property taxes and other special charges", "Core services", "leaf", 4),
    ("Home and mortgage insurance", "Homeowners' home and mortgage insurance", "Core services", "leaf", 4),
    ("Homeowners' maintenance and repairs", "Homeowners' maintenance and repairs", "Core services", "leaf", 4),
    ("Vehicle insurance", "Passenger vehicle insurance premiums", "Core services", "leaf", 3),
    ("Vehicle maintenance and repair", "Passenger vehicle maintenance and repair services", "Core services", "leaf", 3),
    ("Air travel", "Air transportation", "Core services", "leaf", 3),
    ("Phone services", "Telephone services", "Core services", "leaf", 3),
    ("Travel tours", "Travel tours", "Core services", "leaf", 3),
    ("Tuition fees", "Tuition fees", "Core services", "leaf", 3),
    ("Child care", "Child care services", "Core services", "leaf", 3),
    ("Health care services", "Health care services", "Core services", "leaf", 3),
    ("Personal care services", "Personal care services", "Core services", "leaf", 3),
]

# Momentum grid: seasonally adjusted series (table 18-10-0006)
SA_ITEMS = [
    ("All items", "All-items", "Headline", 0),
    ("Food", "Food", "Food", 1),
    ("All items less food and energy", "All-items excluding food and energy", "Core", 1),
    ("Shelter", "Shelter", "Core services", 2),
    ("Transportation", "Transportation", "Core", 2),
    ("Household and furnishings", "Household operations, furnishings and equipment", "Core", 2),
    ("Clothing and footwear", "Clothing and footwear", "Core goods", 2),
    ("Health and personal care", "Health and personal care", "Core", 2),
    ("Recreation and education", "Recreation, education and reading", "Core", 2),
    ("Alcohol, tobacco and cannabis", "Alcoholic beverages, tobacco products and recreational cannabis", "Core", 2),
]

PROVINCES = [  # (area shown, StatCan geography, region)
    ("Newfoundland and Labrador", "Newfoundland and Labrador", "Atlantic"), ("Prince Edward Island", "Prince Edward Island", "Atlantic"),
    ("Nova Scotia", "Nova Scotia", "Atlantic"), ("New Brunswick", "New Brunswick", "Atlantic"),
    ("Quebec", "Quebec", "Central"), ("Ontario", "Ontario", "Central"),
    ("Manitoba", "Manitoba", "Prairies"), ("Saskatchewan", "Saskatchewan", "Prairies"), ("Alberta", "Alberta", "Prairies"),
    ("British Columbia", "British Columbia", "West Coast"),
    ("Yukon", "Whitehorse, Yukon", "North"), ("Northwest Territories", "Yellowknife, Northwest Territories", "North"),
    ("Nunavut", "Iqaluit, Nunavut", "North"),
]
CITIES = [
    ("St. John's", "St. John's, Newfoundland and Labrador"), ("Charlottetown", "Charlottetown and Summerside, Prince Edward Island"),
    ("Halifax", "Halifax, Nova Scotia"), ("Saint John", "Saint John, New Brunswick"), ("Québec City", "Québec, Quebec"),
    ("Montréal", "Montréal, Quebec"), ("Ottawa–Gatineau", "Ottawa-Gatineau, Ontario part, Ontario/Quebec"),
    ("Toronto", "Toronto, Ontario"), ("Thunder Bay", "Thunder Bay, Ontario"), ("Winnipeg", "Winnipeg, Manitoba"),
    ("Regina", "Regina, Saskatchewan"), ("Saskatoon", "Saskatoon, Saskatchewan"), ("Edmonton", "Edmonton, Alberta"),
    ("Calgary", "Calgary, Alberta"), ("Vancouver", "Vancouver, British Columbia"), ("Victoria", "Victoria, British Columbia"),
    ("Whitehorse", "Whitehorse, Yukon"), ("Yellowknife", "Yellowknife, Northwest Territories"), ("Iqaluit", "Iqaluit, Nunavut"),
]


def prev_month(m, k=1):
    y, mo = int(m[:4]), int(m[5:7]) - k
    while mo <= 0:
        mo += 12
        y -= 1
    return f"{y:04d}-{mo:02d}"


def pct(a, b):
    return None if a is None or b is None else (a / b - 1) * 100


def rnd(x, n=1):
    if x is None:
        return ""
    t = f"{x:.{n}f}"
    return f"{0:.{n}f}" if float(t) == 0 else t


def main(offline=None):
    t04, t06, t07, t256 = (load(p, offline) for p in ("18100004", "18100006", "18100007", "18100256"))
    I = series(t04)
    SA = series(t06)
    ALT = series(t256, dim="Alternative measures")
    latest = max(I["All-items"])
    if latest not in SA.get("All-items", {}):
        raise Bad(f"seasonally adjusted table doesn't have {latest} yet")

    # basket weights: the newest basket, at link-month prices, distributed to Canada
    wrows = [r for r in t07 if r["GEO"] == "Canada" and r["Price period of weight"] == "Weight at basket link month prices"
             and r["Geographic distribution of weight"] == "Distribution to selected geographies" and r["VALUE"]]
    basket = max(r["REF_DATE"] for r in wrows)
    W = {r["Products and product groups"]: float(r["VALUE"]) for r in wrows if r["REF_DATE"] == basket}
    # A basket built from year-Y spending starts with the May (Y+1) index, so its link month is April (Y+1).
    link = f"{int(basket) + 1}-04"
    if link > latest:  # not in use yet: fall back to the previous basket
        basket = str(int(basket) - 1)
        W = {r["Products and product groups"]: float(r["VALUE"]) for r in wrows if r["REF_DATE"] == basket}
        link = f"{int(basket) + 1}-04"

    def idx(p, m):
        return I.get(p, {}).get(m)

    def ri(p, m):
        """Relative importance of product p in month m: its link-month weight moved by its price relative to all-items."""
        w, a, b = W.get(p), idx(p, m), idx(p, link)
        if w is None or a is None or b is None:
            return None
        return w * (a / b) / (idx("All-items", m) / idx("All-items", link))

    def contrib(p, m, k):
        base = prev_month(m, k)
        r_, ch = ri(p, base), pct(idx(p, m), idx(p, base))
        return None if r_ is None or ch is None else r_ * ch / 100

    # ---- effects (contributions), 12-month and 1-month views
    effects = []
    for view, k in (("yoy", 12), ("mom", 1)):
        base = prev_month(latest, k)
        head = pct(idx("All-items", latest), idx("All-items", base))
        head_pub = round(head, 1)
        group_c = {g: contrib(p, latest, k) for g, p in GROUP_PRODUCT.items()}
        group_w = {g: W[p] for g, p in GROUP_PRODUCT.items()}
        group_c["Core services"] = head - sum(group_c.values())
        group_w["Core services"] = 100 - sum(group_w.values())
        for group, parents in TREE.items():
            rows = []
            for label, product, subs in parents:
                srows = []
                for sl, sp in subs:
                    if sp is None or W.get(sp) is None:
                        continue
                    c = contrib(sp, latest, k)
                    if c is None:
                        continue
                    srows.append({"view": view, "parent": label, "item": sl, "group": group, "level": "sub", "weight": W[sp],
                                  "change": pct(idx(sp, latest), idx(sp, base)), "contrib": c})
                if product:
                    pc, pw = contrib(product, latest, k), W.get(product)
                    pch = pct(idx(product, latest), idx(product, base))
                else:
                    pc, pw = sum(s["contrib"] for s in srows), sum(s["weight"] for s in srows)
                    r0 = sum(ri(sp, base) or 0 for _, sp in subs if sp and ri(sp, base) is not None)
                    pch = pc / r0 * 100 if r0 else None
                if pc is None or pw is None:
                    report("warning", f"{product or label}: no index or weight, left out")
                    continue
                rest_c = pc - sum(s["contrib"] for s in srows)
                if srows and product and abs(rest_c) >= 0.005:
                    srows.append({"view": view, "parent": label, "item": "Rest of " + label[0].lower() + label[1:], "group": group, "level": "sub",
                                  "weight": None, "change": None, "contrib": rest_c})
                rows.append({"view": view, "parent": label, "item": label, "group": group, "level": "parent", "weight": pw, "change": pch, "contrib": pc})
                rows.extend(srows)
            # the group's remainder: what the listed components don't cover
            pc_sum = sum(r["contrib"] for r in rows if r["level"] == "parent")
            pw_sum = sum(r["weight"] for r in rows if r["level"] == "parent")
            rest_c, rest_w = group_c[group] - pc_sum, group_w[group] - pw_sum
            if rest_w >= 0.1:
                name = "Other " + group[0].lower() + group[1:]
                rows.append({"view": view, "parent": name, "item": name, "group": group, "level": "parent", "weight": rest_w,
                             "change": None, "contrib": rest_c})
            elif rows:  # a rounding-sized remainder: fold it into the largest component so the group still adds up
                max((r for r in rows if r["level"] == "parent"), key=lambda r: r["weight"])["contrib"] += rest_c
            effects.extend(rows)
        total = sum(r["contrib"] for r in effects if r["view"] == view and r["level"] == "parent")
        if abs(total - head) > 1e-6:
            raise Bad(f"{view} contributions add to {total:.3f}, not {head:.3f}")
        print(f"{view}: headline {head_pub} ({head:.3f}); groups " + ", ".join(f"{g} {v:+.2f}" for g, v in group_c.items()))

    # ---- components table
    comps = []
    for name, product, group, level, depth in COMPONENTS:
        if product is None:  # core services: derived from the groups
            w = 100 - sum(W[p] for p in GROUP_PRODUCT.values())
            yo = next(r for r in effects if r["view"] == "yoy" and r["level"] == "parent" and r["group"] == "Core services")
            ys = [r for r in effects if r["view"] == "yoy" and r["group"] == "Core services" and r["level"] == "parent"]
            ms = [r for r in effects if r["view"] == "mom" and r["group"] == "Core services" and r["level"] == "parent"]
            ri12 = sum(ri(p, prev_month(latest, 12)) or 0 for p in ("All-items",)) - sum(ri(p, prev_month(latest, 12)) for p in GROUP_PRODUCT.values())
            ri1 = 100 - sum(ri(p, prev_month(latest, 1)) for p in GROUP_PRODUCT.values())
            comps.append((name, group, level, depth, w, sum(r["contrib"] for r in ys) / ri12 * 100, sum(r["contrib"] for r in ms) / ri1 * 100))
            continue
        if W.get(product) is None or idx(product, latest) is None:
            report("warning", f"component {product} missing, left out")
            continue
        comps.append((name, group, level, depth, W[product], pct(idx(product, latest), idx(product, prev_month(latest, 12))),
                      pct(idx(product, latest), idx(product, prev_month(latest, 1)))))

    # ---- momentum grid (seasonally adjusted, last seven months) with 12-month changes for the table beside it
    months = sorted(SA["All-items"])[-7:]
    monthly = []
    for name, product, group, depth in SA_ITEMS:
        for m in months:
            v = pct(SA[product].get(m), SA[product].get(prev_month(m)))
            monthly.append((name, group, depth, m, v, pct(idx(product, latest), idx(product, prev_month(latest, 12)))))

    # ---- index history: SA headline, core, food, shelter; NSA groups for the contribution history; CPI-trim and CPI-median
    trim_name = next(k for k in ALT if k.startswith("Measure of core inflation based on a trimmed mean approach, CPI-trim (index"))
    med_name = next(k for k in ALT if k.startswith("Measure of core inflation based on a weighted median approach, CPI-median (index"))
    hist = []
    for m in sorted(I["All-items"]):
        if m < "2019-01" and m < prev_month(latest, 93):
            continue
        hist.append({"date": m + "-01",
                     "headline": SA["All-items"].get(m), "core": SA["All-items excluding food and energy"].get(m),
                     "food": SA["Food"].get(m), "energy": idx("Energy", m), "core_goods": idx(GROUP_PRODUCT["Core goods"], m),
                     "shelter": SA["Shelter"].get(m), "third": ALT[trim_name].get(m), "fourth": ALT[med_name].get(m),
                     "headline_nsa": idx("All-items", m), "food_nsa": idx("Food", m), "energy_nsa": idx("Energy", m),
                     "core_goods_nsa": idx(GROUP_PRODUCT["Core goods"], m)})
    hist = [h for h in hist if h["date"] >= "2019-01-01"]

    # ---- provinces, territories (through their capitals) and cities
    regions = []
    for area, geo, region in PROVINCES:
        g = series(t04, geo=geo).get("All-items", {})
        regions.append((area, "division", region, pct(g.get(latest), g.get(prev_month(latest, 12))), pct(g.get(latest), g.get(prev_month(latest))), latest))
    for area, geo in CITIES:
        g = series(t04, geo=geo).get("All-items", {})
        regions.append((area, "metro", "", pct(g.get(latest), g.get(prev_month(latest, 12))), pct(g.get(latest), g.get(prev_month(latest))), latest))

    # ---- checks before writing anything
    head12 = pct(idx("All-items", latest), idx("All-items", prev_month(latest, 12)))
    if not (-5 < head12 < 20):
        raise Bad(f"implausible 12-month change {head12:.1f}%")
    if len(effects) < 40 or len(comps) < 30:
        raise Bad("too few components found; Statistics Canada may have renamed products")

    OUT.mkdir(parents=True, exist_ok=True)
    mo = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    period = f"{mo[int(latest[5:7]) - 1]} {latest[:4]}"

    def write(name, header, rows):
        with open(OUT / name, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f, lineterminator="\n")
            w.writerow(header)
            w.writerows(rows)

    write("components.csv", ["item", "group", "level", "depth", "weight", "yoy", "mom_sa"],
          [(n, g, l, d, f"{w:.3f}", rnd(y), rnd(m)) for n, g, l, d, w, y, m in comps])
    write("components_monthly.csv", ["item", "group", "depth", "month", "mom_sa", "yoy"],
          [(n, g, d, m, rnd(v), rnd(y)) for n, g, d, m, v, y in monthly])
    write("effects.csv", ["view", "parent", "item", "group", "level", "weight", "change", "contrib", "basis"],
          [(r["view"], r["parent"], r["item"], r["group"], r["level"], "" if r["weight"] is None else f"{r['weight']:.3f}",
            rnd(r["change"]), f"{r['contrib']:.3f}", "estimated") for r in effects])
    cols = ["date", "headline", "core", "food", "energy", "core_goods", "shelter", "third", "fourth", "headline_nsa", "food_nsa", "energy_nsa", "core_goods_nsa"]
    write("fred.csv", cols, [[h["date"]] + ["" if h[c] is None else f"{h[c]:.1f}" for c in cols[1:]] for h in hist])
    write("regions.csv", ["area", "type", "region", "yoy", "mom", "period"],
          [(a, t, r, rnd(y), rnd(m), period) for a, t, r, y, m, _ in regions])
    alt12 = lambda name: ALT.get(name, {}).get(latest)
    core_measures = {k: alt12(n) for k, n in (
        ("trim", "Measure of core inflation based on a trimmed mean approach, CPI-trim (year-over-year percent change)"),
        ("median", "Measure of core inflation based on a weighted median approach, CPI-median (year-over-year percent change)"),
        ("common", "Measure of core inflation based on a factor model, CPI-common (year-over-year percent change)"))}
    (OUT / "release.json").write_text(json.dumps({"month": latest, "basket": basket, "link_month": link, "core_measures": core_measures}) + "\n", encoding="utf-8")
    report("notice", f"Canada data updated to {latest} (12-month {head12:.1f}%, basket {basket}, link month {link})")


if __name__ == "__main__":
    off = sys.argv[sys.argv.index("--offline") + 1] if "--offline" in sys.argv else None
    try:
        main(off)
    except Bad as e:
        report("error", f"Canada data not updated: {e}")
        sys.exit(1)

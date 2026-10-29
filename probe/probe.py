"""One-off: download StatCan CPI tables and Bank of Canada core measures, write a compact inventory."""
import io, json, zipfile, csv, collections, pathlib, requests
OUT = pathlib.Path("probe/out"); OUT.mkdir(parents=True, exist_ok=True)
H = {"User-Agent": "inflationbreakdown.com data updater (github.com/Eshxxn1/Inflation-Breakdown)"}
log = []
def table(pid):
    url = f"https://www150.statcan.gc.ca/n1/tbl/csv/{pid}-eng.zip"
    r = requests.get(url, headers=H, timeout=180); r.raise_for_status()
    z = zipfile.ZipFile(io.BytesIO(r.content))
    name = [n for n in z.namelist() if n.endswith('.csv') and 'MetaData' not in n][0]
    log.append(f"{pid}: {len(r.content)//1024} KB zip, {name}")
    return list(csv.DictReader(io.TextIOWrapper(z.open(name), encoding='utf-8-sig')))
for pid in ["18100004", "18100006", "18100007", "18100256"]:
    try:
        rows = table(pid)
    except Exception as e:
        log.append(f"{pid}: FAILED {e!r}"); continue
    cols = list(rows[0].keys())
    prodcol = [c for c in cols if c not in ('REF_DATE','GEO','DGUID','UOM','UOM_ID','SCALAR_FACTOR','SCALAR_ID','VECTOR','COORDINATE','VALUE','STATUS','SYMBOL','TERMINATED','DECIMALS')]
    dates = sorted({r['REF_DATE'] for r in rows})
    geos = collections.Counter(r['GEO'] for r in rows)
    inv = {"columns": cols, "dim_cols": prodcol, "dates": [dates[0], dates[-1]], "n": len(rows), "geos": sorted(geos)}
    for c in prodcol:
        inv[c] = sorted({r[c] for r in rows})
    # keep recent rows for Canada + provinces so the real data can be inspected
    keep = [r for r in rows if r['REF_DATE'] >= '2019-01']
    json.dump(inv, open(OUT / f"{pid}_inventory.json", "w"), indent=1)
    with open(OUT / f"{pid}_recent.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=['REF_DATE','GEO'] + prodcol + ['UOM','VECTOR','VALUE','STATUS'], extrasaction='ignore'); w.writeheader(); w.writerows(keep)
    log.append(f"{pid}: {len(rows)} rows, dates {dates[0]}..{dates[-1]}, dims {prodcol}, recent rows {len(keep)}")
for g in ["CPI_MONTHLY", "CPI_COMPONENTS"]:
    try:
        r = requests.get(f"https://www.bankofcanada.ca/valet/observations/group/{g}/json?start_date=2018-01-01", headers=H, timeout=60)
        log.append(f"BoC {g}: HTTP {r.status_code}")
        if r.ok: open(OUT / f"boc_{g}.json", "w").write(r.text)
    except Exception as e:
        log.append(f"BoC {g}: FAILED {e!r}")
open(OUT / "log.txt", "w").write("\n".join(log) + "\n")
print("\n".join(log))

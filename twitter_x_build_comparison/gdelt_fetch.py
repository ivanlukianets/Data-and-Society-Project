# %% [markdown]
# GDELT fetcher — "one shot per theme, no retries" strategy.
#
# WHY NO RETRIES: GDELT's rate limiter appears to count *rejected* requests too,
# so hammering a blocked theme keeps the window open forever. Instead we try each
# theme ONCE per pass, skip it on 429, and move on. Rerun the script to fill gaps.
#
# Uses timelinevol (percentage of daily coverage) — lighter than timelinevolraw
# and perfectly adequate, since we normalize anyway for correlation.
#
# Output (appended incrementally): gdelt_daily.csv (theme, date, share)
#
# HOW TO USE:
#   1. Run it. Some themes succeed, some get 429'd.
#   2. Wait 15-20 min doing NOTHING (no requests at all — that's what resets the window).
#   3. Run it again. It skips what's done and retries only what's missing.
#   4. Repeat until all 21 are in. Usually takes 3-4 passes.

# %%
import requests, time, json, csv, os
import pandas as pd

TAXONOMY = "topic_gdelt_taxonomy_v2.csv"
OUT = "gdelt_daily.csv"
BASE = "https://api.gdeltproject.org/api/v2/doc/doc"
START, END = "20240101000000", "20241231235959"
SLEEP_BETWEEN = 800      # seconds between themes. Raise to 120 if still hitting walls.

SESSION = requests.Session()
SESSION.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})


def fetch_theme(query):
    """ONE attempt. Raises on 429 — caller skips to next theme."""
    params = {
        "query": f"{query} sourcecountry:US sourcelang:English",
        "mode": "timelinevol",          # lighter than volraw; returns % of daily coverage
        "format": "json",
        "startdatetime": START,
        "enddatetime": END,
    }
    r = SESSION.get(BASE, params=params, timeout=180)
    if r.status_code == 429:
        raise RuntimeError("RATE_LIMITED")
    r.raise_for_status()
    try:
        payload = r.json()
    except json.JSONDecodeError:
        raise RuntimeError(f"non-JSON: {r.text[:120]}")

    series = next((s["data"] for s in payload.get("timeline", [])
                   if isinstance(s, dict) and s.get("data")), None)
    if series is None:
        raise RuntimeError(f"no timeline: {list(payload.keys())}")

    rows = []
    for pt in series:
        d = str(pt.get("date", ""))[:8]
        if len(d) == 8:
            rows.append({"date": f"{d[:4]}-{d[4:6]}-{d[6:]}",
                         "share": pt.get("value", 0)})   # already a percentage
    df = pd.DataFrame(rows)
    if df.empty:
        raise RuntimeError("empty timeline")
    return df


# %%
themes = []
with open(TAXONOMY, encoding="utf-8") as f:
    for row in csv.DictReader(f):
        if row["decision"].startswith(("INCLUDE", "MERGE")) and row["gdelt_query"].strip():
            themes.append((row["theme"], row["gdelt_query"].strip()))

done = set()
if os.path.exists(OUT):
    done = set(pd.read_csv(OUT)["theme"].unique())

todo = [(t, q) for t, q in themes if t not in done]
print(f"{len(done)}/{len(themes)} already saved. Fetching {len(todo)} this pass.\n")

if not todo:
    print("Everything already fetched.")
else:
    limited, failed = [], []
    for i, (theme, q) in enumerate(todo, 1):
        print(f"[{i}/{len(todo)}] {theme}", flush=True)
        try:
            df = fetch_theme(q)
            df["theme"] = theme
            df[["theme", "date", "share"]].to_csv(
                OUT, mode="a", header=not os.path.exists(OUT), index=False)
            print(f"    OK — {len(df)} days [saved]\n", flush=True)
        except RuntimeError as e:
            if "RATE_LIMITED" in str(e):
                limited.append(theme)
                print("    429 — skipping (will retry next pass)\n", flush=True)
            else:
                failed.append((theme, str(e)))
                print(f"    ERROR: {e}\n", flush=True)
        except Exception as e:
            failed.append((theme, str(e)))
            print(f"    ERROR: {e}\n", flush=True)
        time.sleep(SLEEP_BETWEEN)

    print("=" * 55)
    if limited:
        print(f"{len(limited)} rate-limited. WAIT 15-20 MIN (no requests!), then rerun:")
        for t in limited:
            print(f"  - {t}")
    if failed:
        print(f"\n{len(failed)} real errors (bad query? fix in taxonomy):")
        for t, e in failed:
            print(f"  - {t}: {e[:80]}")

if os.path.exists(OUT):
    fin = pd.read_csv(OUT)
    print(f"\n{OUT}: {fin['theme'].nunique()}/{len(themes)} themes, {len(fin):,} rows")
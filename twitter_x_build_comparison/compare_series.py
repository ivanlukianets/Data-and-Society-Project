# %% [markdown]
# Twitter vs GDELT: lead/lag comparison per theme.
#
# CRITICAL FIX vs v1: the Twitter corpus is essentially empty Jan-Apr 2024
# (72-188 conversations/month vs 48k-135k from May onward) and has no December.
# On a day with 3 total conversations, one conversation in a theme = 33% "share" —
# a phantom spike larger than the real July assassination peak. Those days
# destroyed every correlation. We now keep only days with a real corpus volume.
#
# We report TWO correlation estimates per theme:
#   corr_share = theme's share of that day's classified conversations (main)
#   corr_raw   = theme's raw daily conversation count (robustness check)
# Pearson r is scale-invariant, so raw counts are a legitimate cross-check.
# If the two disagree wildly, treat the theme as unreliable.
#
# Lag convention: POSITIVE = Twitter leads (news follows N days later)
#                 NEGATIVE = News leads (Twitter follows)

# %%
import pandas as pd, numpy as np

TW, GD = "twitter_daily.csv", "gdelt_daily.csv"
MIN_DAILY_TOTAL = 500    # drop days where the corpus is too thin to form a share
MAX_LAG = 14
N_PERM = 2000
rng = np.random.default_rng(42)

def load(path):
    df = pd.read_csv(path)
    for c in ("date", "day"):
        if c in df.columns:
            df = df.rename(columns={c: "date"}); break
    else:
        raise ValueError(f"{path}: no date/day column: {list(df.columns)}")
    df["date"] = pd.to_datetime(df["date"])
    return df

tw, gd = load(TW), load(GD)

# --- day filter: keep only days with real corpus volume ---
day_tot = tw.groupby("date")["n"].sum()
good_days = day_tot[day_tot >= MIN_DAILY_TOTAL].index.sort_values()
print(f"Twitter days total          : {len(day_tot)}")
print(f"Days with >= {MIN_DAILY_TOTAL} convos    : {len(good_days)}"
      f"  ({good_days.min().date()} .. {good_days.max().date()})")
print(f"Dropped (too thin)          : {len(day_tot) - len(good_days)}\n")

tw = tw[tw.date.isin(good_days)].copy()
tw["tw_share"] = tw["n"] / tw["date"].map(day_tot)

idx = pd.DatetimeIndex(good_days)

def lagged(a, b, L):
    """corr(a_t, b_{t+L}). L>0 => a (Twitter) leads."""
    if L < 0:   a2, b2 = a[-L:], b[:L]
    elif L > 0: a2, b2 = a[:-L], b[L:]
    else:       a2, b2 = a, b
    m = ~(np.isnan(a2) | np.isnan(b2))
    if m.sum() < 60: return np.nan
    if np.nanstd(a2[m]) == 0 or np.nanstd(b2[m]) == 0: return np.nan
    return np.corrcoef(a2[m], b2[m])[0, 1]

lags = list(range(-MAX_LAG, MAX_LAG + 1))
rows = []

for theme in sorted(set(tw.theme) & set(gd.theme)):
    b = gd[gd.theme == theme].set_index("date")["share"].reindex(idx).to_numpy(float)
    sub = tw[tw.theme == theme].set_index("date")

    for label, series in (("share", "tw_share"), ("raw", "n")):
        a = sub[series].reindex(idx).fillna(0.0).to_numpy(float)
        cs = {L: lagged(a, b, L) for L in lags}
        ok = {L: c for L, c in cs.items() if not np.isnan(c)}
        if not ok:
            continue
        bl = max(ok, key=lambda L: ok[L]); bc = ok[bl]

        if label == "share":
            # permutation null: max |corr| over the same lag grid, so picking the
            # best lag can't inflate significance
            perm = np.empty(N_PERM)
            for i in range(N_PERM):
                sh = rng.integers(30, len(a) - 30)
                a_sh = np.roll(a, sh)
                perm[i] = np.nanmax(np.abs([lagged(a_sh, b, L) for L in lags]))
            p = float((perm >= abs(bc)).mean())
            row = {"theme": theme, "best_lag": bl, "corr_share": round(bc, 3),
                   "p": round(p, 3), "corr_lag0": round(cs.get(0, np.nan), 3)}
        else:
            row["corr_raw"] = round(bc, 3)
            row["raw_lag"] = bl
            rows.append(row)

res = pd.DataFrame(rows)
res["direction"] = np.where(res.best_lag > 0, "Twitter leads",
                     np.where(res.best_lag < 0, "News leads", "same-day"))
res["agree"] = np.where(np.sign(res.best_lag) == np.sign(res.raw_lag), "yes", "NO")
res = res[["theme", "corr_share", "corr_raw", "best_lag", "raw_lag",
           "direction", "p", "agree", "corr_lag0"]]
res = res.sort_values("corr_share", ascending=False)
res.to_csv(f"lag_results_{MIN_DAILY_TOTAL}.csv", index=False)

pd.set_option("display.width", 200)
print(res.to_string(index=False))
print("\nSIGNIFICANT (p < 0.05):")
sig = res[res.p < 0.05]
print(sig.to_string(index=False) if len(sig) else "  none")
print("\nwrote lag_results.csv")
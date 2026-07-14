
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

OUT_PNG = "chart_2_event_sync.png"
START, END = "2024-05-01", "2024-11-30"

tw = pd.read_csv(f"D:\\Applied Statistics\\Нова папка\\Data-and-Society-Project\\twitter_x_build_comparison\\twitter_daily.csv")
tw["day"] = pd.to_datetime(tw["day"])
gd = pd.read_csv(f"D:\\Applied Statistics\\Нова папка\\Data-and-Society-Project\\twitter_x_build_comparison\\gdelt_daily.csv")
gd["date"] = pd.to_datetime(gd["date"])

# Twitter "share" = each theme's daily conversation count / total daily conversations
# across the 33 matched themes (twitter_daily.csv does not include a pre-computed share column)
daily_total = tw.groupby("day")["n"].sum().rename("total")
tw = tw.merge(daily_total, on="day")
tw["share"] = tw["n"] / tw["total"]

idx = pd.date_range(START, END, freq="D")


def indexed_series(theme):
    t = tw[tw.theme == theme].set_index("day")["share"].reindex(idx).fillna(0)
    g = gd[gd.theme == theme].set_index("date")["share"].reindex(idx).fillna(0)
    # 3-day centered rolling mean smooths a handful of data-collection gap days
    t = t.rolling(3, center=True, min_periods=1).mean()
    g = g.rolling(3, center=True, min_periods=1).mean()
    t_idx = (t / t.max() * 100) if t.max() > 0 else t
    g_idx = (g / g.max() * 100) if g.max() > 0 else g
    return t_idx, g_idx


themes = [
    ("Trump Assassination Attempt(s)", "r = 0.69, lag 0 days - synchronized"),
    ("Trump & Trump Family (core)", "r = 0.13, lag 9 days - decoupled"),
]

fig, axes = plt.subplots(2, 1, figsize=(10, 8), sharex=True)

for ax, (theme, subtitle) in zip(axes, themes):
    t_idx, g_idx = indexed_series(theme)
    ax.plot(idx, t_idx, color="#2a78d6", linewidth=2, label="Twitter (share of conversations)")
    ax.plot(idx, g_idx, color="#e34948", linewidth=2, linestyle="--", label="GDELT news (share of coverage)")
    ax.set_title(f"{theme}\n{subtitle}", fontsize=12, loc="left")
    ax.set_ylabel("Index (own peak = 100)")
    ax.set_ylim(0, 105)
    ax.spines[["top", "right"]].set_visible(False)
    ax.yaxis.grid(True, color="#e1e0d9", linewidth=0.8)
    ax.set_axisbelow(True)
    ax.legend(loc="upper left", fontsize=9, frameon=False)

axes[-1].xaxis.set_major_locator(mdates.MonthLocator())
axes[-1].xaxis.set_major_formatter(mdates.DateFormatter("%b"))

plt.tight_layout()
plt.savefig(OUT_PNG, dpi=200)
print(f"Saved {OUT_PNG}")

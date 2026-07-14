import pandas as pd
import matplotlib.pyplot as plt

OUT_PNG = "chart_3_correlation_summary.png"
EDGE_ARTIFACT_THEMES = {"Congress, Senate & Lawmakers",
                         "Government Officials & Cabinet (RFK, DeSantis, Newsom, etc.)"}

df = pd.read_csv(f"D:\\Applied Statistics\\Нова папка\\Data-and-Society-Project\\twitter_x_build_comparison\\lag_results_500.csv")
df = df.sort_values("corr_share")  # ascending, so largest ends up on top in barh

labels = [t + (" *" if t in EDGE_ARTIFACT_THEMES else "") for t in df["theme"]]
colors = ["#1baf7a" if (p < 0.05 and t not in EDGE_ARTIFACT_THEMES) else "#b4b2a9"
          for p, t in zip(df["p"], df["theme"])]

fig, ax = plt.subplots(figsize=(10, 8))
bars = ax.barh(labels, df["corr_share"], color=colors, height=0.6)

for bar, val in zip(bars, df["corr_share"]):
    ax.text(bar.get_width() + 0.01, bar.get_y() + bar.get_height() / 2,
            f"{val:.2f}", va="center", fontsize=9, color="#333")

ax.set_xlabel("Cross-correlation of daily attention share, Twitter vs GDELT (threshold = 500 tweets)")
ax.set_title("Twitter and news synchronize on shock events, not on political narratives", fontsize=13)
ax.set_xlim(0, 0.78)
ax.spines[["top", "right"]].set_visible(False)
ax.xaxis.grid(True, color="#e1e0d9", linewidth=0.8)
ax.set_axisbelow(True)

# Legend
from matplotlib.patches import Patch
legend_elems = [
    Patch(facecolor="#1baf7a", label="Significant (p<0.05), lag \u2248 0"),
    Patch(facecolor="#b4b2a9", label="Not significant"),
]
ax.legend(handles=legend_elems, loc="lower right", frameon=False, fontsize=9)
fig.text(0.01, 0.01, "* p<0.05 but best lag sits at the +/-14 day window edge - likely an artifact, not real signal",
          fontsize=8, color="#888780")

plt.tight_layout(rect=[0, 0.03, 1, 1])
plt.savefig(OUT_PNG, dpi=200)
print(f"Saved {OUT_PNG}")

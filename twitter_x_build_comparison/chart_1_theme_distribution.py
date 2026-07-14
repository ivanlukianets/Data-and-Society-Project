import pandas as pd
import matplotlib.pyplot as plt

DATA_DIR = "D://Applied Statistics//Нова папка//Data-and-Society-Project"  # change to the folder holding the CSVs
OUT_PNG = "chart_1_theme_distribution.png"

df = pd.read_csv(f"D:\Applied Statistics\Нова папка\Data-and-Society-Project\\twitter_x_build_comparison\\topic_info_fin_merged_themes.csv")

# Exclude the BERTopic noise cluster - it isn't a real theme, just unclustered content
df = df[~df["theme"].str.contains("Unclustered")]

total_all = pd.read_csv(f"D:\Applied Statistics\Нова папка\Data-and-Society-Project\\twitter_x_build_comparison\\topic_info_fin_merged_themes.csv")["conversation_count"].sum()

top15 = df.sort_values("conversation_count", ascending=False).head(15).copy()
top15["share_pct"] = 100 * top15["conversation_count"] / total_all
top15 = top15.sort_values("share_pct")  # ascending for horizontal barh (largest on top)

fig, ax = plt.subplots(figsize=(9, 7))
bars = ax.barh(top15["theme"], top15["share_pct"], color="#2a78d6", height=0.6)

for bar, pct in zip(bars, top15["share_pct"]):
    ax.text(bar.get_width() + 0.15, bar.get_y() + bar.get_height() / 2,
            f"{pct:.1f}%", va="center", fontsize=9, color="#333")

ax.set_xlabel("% of all 2,000,000 conversations")
ax.set_title("Top-15 themes by share of the Twitter/X corpus\n(BERTopic noise cluster excluded)", fontsize=13)
ax.spines[["top", "right"]].set_visible(False)
ax.xaxis.grid(True, color="#e1e0d9", linewidth=0.8)
ax.set_axisbelow(True)

plt.tight_layout()
plt.savefig(OUT_PNG, dpi=200)
print(f"Saved {OUT_PNG}")

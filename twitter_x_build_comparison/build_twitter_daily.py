# %% [markdown]
# build_twitter_daily.py — FINAL
#
# THE PROBLEM: conversation_id in the BERTopic CSV went through pandas float64,
# so the last ~3 digits are gone (1.821550781452944e+18). They can't be recovered.
#
# THE FIX (safe, provable): apply the SAME float64 rounding to the parquet side,
# then join in that "lossy" space. Both sides get identical values -> the join works.
#
# WHY IT'S SAFE for a date-level join:
#   - near 1.8e18, adjacent float64 values are 256 apart, so only IDs differing
#     by < 256 can collide;
#   - Twitter snowflake IDs put the millisecond timestamp above bit 22, so two IDs
#     within 256 of each other are necessarily from the SAME millisecond;
#   - same millisecond => same date. A collision therefore cannot produce a wrong date.
#   (IDs from different days differ by >> 256 and never collide.)
#
# Output: twitter_daily.csv  (theme, day, n)

# %%
import duckdb

PARQUET_FILE = "usc_x_24_us_election_english_threaded.parquet"   # <-- your tweet-level parquet
CONV_TOPICS  = "conversation_topics_fin.csv"                     # conversation_id, topic
TOPIC_THEME  = "topic_to_theme.csv"                              # topic_id, theme
OUT          = "twitter_daily.csv"

con = duckdb.connect()
con.execute("SET memory_limit='4GB';")

# ---- 1. topic -> theme
con.execute(f"""
CREATE TABLE topic_theme AS
SELECT CAST(topic_id AS INT) AS topic_id, theme
FROM read_csv_auto('{TOPIC_THEME}', header=true)
""")

# ---- 2. conversation -> topic. Key = the float64 value (deliberately lossy).
con.execute(f"""
CREATE TABLE conv_topic AS
SELECT CAST(conversation_id AS DOUBLE) AS cid,
       CAST(topic AS INT)              AS topic_id
FROM read_csv_auto('{CONV_TOPICS}', header=true)
WHERE conversation_id IS NOT NULL
""")
n_ct = con.sql("SELECT COUNT(*) FROM conv_topic").fetchone()[0]

# ---- 3. conversation -> date. Cast the TRUE id through DOUBLE so it lands in the
#         same lossy space. Take MIN(date) per conversation.
con.execute(f"""
CREATE TABLE conv_date AS
SELECT CAST("conversationId" AS DOUBLE) AS cid,
       MIN(TRY_CAST(date AS DATE))      AS day
FROM read_parquet('{PARQUET_FILE}')
WHERE TRY_CAST(date AS DATE) BETWEEN DATE '2024-01-01' AND DATE '2024-12-31'
GROUP BY 1
""")
n_cd = con.sql("SELECT COUNT(*) FROM conv_date").fetchone()[0]

# ---- 4. JOIN CHECK — this is the number that matters
matched = con.sql("""
SELECT COUNT(*) FROM conv_topic ct JOIN conv_date cd ON ct.cid = cd.cid
""").fetchone()[0]
print(f"conv_topic rows : {n_ct:,}")
print(f"conv_date  rows : {n_cd:,}")
print(f">>> MATCHED     : {matched:,}  ({100*matched/n_ct:.1f}% of conversations got a date)")
if matched < 0.5 * n_ct:
    print(">>> STILL LOW — the two ID sets may come from different corpora. Check samples:")
    print(con.sql("SELECT cid FROM conv_topic LIMIT 3").df().to_string(index=False))
    print(con.sql("SELECT cid FROM conv_date  LIMIT 3").df().to_string(index=False))

# ---- 5. daily counts per theme (drop noise buckets)
con.execute(f"""
CREATE TABLE daily AS
SELECT tt.theme, cd.day, COUNT(*) AS n
FROM conv_topic ct
JOIN conv_date   cd ON ct.cid     = cd.cid
JOIN topic_theme tt ON ct.topic_id = tt.topic_id
WHERE tt.theme NOT ILIKE '%Unclustered%'
  AND tt.theme NOT ILIKE '%Low-Signal%'
  AND tt.theme NOT ILIKE '%Casual%'
GROUP BY 1, 2
ORDER BY 1, 2
""")
con.execute(f"COPY daily TO '{OUT}' (HEADER)")

s = con.sql("""SELECT COUNT(*) AS n_rows, COUNT(DISTINCT theme) AS n_themes,
                      COUNT(DISTINCT day) AS n_days, SUM(n) AS n_total
               FROM daily""").df().iloc[0]
print(f"\nwrote {OUT}")
print(f"  rows={int(s['n_rows']):,}  themes={int(s['n_themes'])}  "
      f"days={int(s['n_days'])} (want ~366)  conversations={int(s['n_total']):,}")

print("\ncoverage per theme:")
print(con.sql("""SELECT theme, COUNT(DISTINCT day) AS n_days, SUM(n) AS n_total
                 FROM daily GROUP BY 1 ORDER BY n_total DESC""").df().to_string(index=False))
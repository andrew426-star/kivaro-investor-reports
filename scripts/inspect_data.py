"""Inspect and clean the ES data."""
import pandas as pd
import databento as db
from pathlib import Path

RAW_PATH = Path("data/raw/glbx-mdp3-20231027-20261026.ohlcv-1s.dbn.zst")

print("Loading...")
store = db.DBNStore.from_file(str(RAW_PATH))
df = store.to_df().reset_index()
print(f"Shape: {df.shape}")

# Check symbols
print("\nSymbols:")
print(df["symbol"].value_counts())

print("\nInstrument IDs:")
print(df["instrument_id"].value_counts().head(20))

# Check price distribution per symbol
for sym in df["symbol"].unique()[:5]:
    sub = df[df["symbol"] == sym]
    print(f"\n{sym}: rows={len(sub)}, close min={sub['close'].min()}, max={sub['close'].max()}")

# Check for bad prices (close < 100 or close > 20000)
bad = df[(df["close"] < 100) | (df["close"] > 20000)]
print(f"\nBad price rows: {len(bad)} / {len(df)}")
if len(bad) > 0:
    print(bad[["ts_event", "symbol", "close", "volume"]].head(20))

# Check for zero/negative prices
bad2 = df[df["close"] <= 0]
print(f"\nZero/negative price rows: {len(bad2)}")

# Check for volume anomalies
print(f"\nVolume stats:")
print(df["volume"].describe())

# Check for zero volume rows (no trading)
zero_vol = df[df["volume"] == 0]
print(f"\nZero volume rows: {len(zero_vol)} / {len(df)}")

# Check date range per symbol
print("\nDate ranges per symbol:")
for sym in df["symbol"].unique():
    sub = df[df["symbol"] == sym]
    print(f"  {sym}: {sub['ts_event'].min()} to {sub['ts_event'].max()}, rows={len(sub)}")
"""Inspect cleaned ES data from parquet."""
import pandas as pd
from pathlib import Path

df = pd.read_parquet("data/es_1m_ohlcv.parquet")
print(f"Shape: {df.shape}")
print(f"Columns: {list(df.columns)}")

# Check symbols
print("\nSymbols:")
print(df["symbol"].value_counts())

# Check instrument IDs
print("\nInstrument IDs:")
print(df["instrument_id"].value_counts().head(20))

# Check price distribution per symbol
for sym in df["symbol"].unique()[:10]:
    sub = df[df["symbol"] == sym]
    print(f"\n{sym}: rows={len(sub)}, close min={sub['close'].min()}, max={sub['close'].max()}")

# Check for bad prices
bad = df[(df["close"] < 100) | (df["close"] > 20000)]
print(f"\nBad price rows: {len(bad)} / {len(df)}")
if len(bad) > 0:
    print(bad[["timestamp", "symbol", "close", "volume"]].head(20))

# Check for zero/negative prices
bad2 = df[df["close"] <= 0]
print(f"\nZero/negative price rows: {len(bad2)}")

# Check for zero volume rows (no trading)
zero_vol = df[df["volume"] == 0]
print(f"\nZero volume rows: {len(zero_vol)} / {len(df)}")

# Check date range per symbol
print("\nDate ranges per symbol:")
for sym in df["symbol"].unique():
    sub = df[df["symbol"] == sym]
    print(f"  {sym}: {sub['timestamp'].min()} to {sub['timestamp'].max()}, rows={len(sub)}")

# Check for duplicate timestamps
dups = df[df.duplicated(subset=["timestamp", "symbol"], keep=False)]
print(f"\nDuplicate timestamp+symbol rows: {len(dups)}")

# Check for missing minutes (gaps)
print("\nChecking for missing minutes in ES.FUT...")
es = df[df["symbol"] == "ES.FUT"].sort_values("timestamp") if "ES.FUT" in df["symbol"].values else df.sort_values("timestamp")
if "ES.FUT" not in df["symbol"].values:
    # Use the most common symbol
    es = df[df["symbol"] == df["symbol"].value_counts().index[0]].sort_values("timestamp")
    
print(f"ES rows: {len(es)}")
print(f"Date range: {es['timestamp'].min()} to {es['timestamp'].max()}")

# Check time gaps
es = es.copy()
es["ts_diff"] = es["timestamp"].diff().dt.total_seconds()
gaps = es[es["ts_diff"] > 120]  # gaps > 2 minutes
print(f"Gaps > 2 minutes: {len(gaps)}")
if len(gaps) > 0:
    print(gaps[["timestamp", "ts_diff", "close"]].head(20))
"""Sample-based inspection of ES data."""
import pandas as pd

df = pd.read_parquet("data/es_1m_ohlcv.parquet")
print(f"Shape: {df.shape}")
print(f"Columns: {list(df.columns)}")

# Symbols
print("\nSymbols:")
print(df["symbol"].value_counts())

# Instrument IDs
print("\nInstrument IDs (top 20):")
print(df["instrument_id"].value_counts().head(20))

# Sample price stats per symbol
print("\nPrice stats per symbol (sample):")
for sym in df["symbol"].unique():
    sub = df[df["symbol"] == sym]
    sample = sub["close"].dropna().sample(min(1000, len(sub)), random_state=42)
    print(f"  {sym}: rows={len(sub)}, close min={sub['close'].min()}, max={sub['close'].max()}, sample mean={sample.mean():.1f}")

# Bad prices
bad = df[(df["close"] < 100) | (df["close"] > 20000)]
print(f"\nBad price rows (<100 or >20000): {len(bad)} / {len(df)}")
if len(bad) > 0:
    print(bad[["timestamp", "symbol", "close", "volume"]].head(20))

# Zero/negative prices
bad2 = df[df["close"] <= 0]
print(f"\nZero/negative price rows: {len(bad2)}")

# Zero volume
zero_vol = df[df["volume"] == 0]
print(f"\nZero volume rows: {len(zero_vol)} / {len(df)}")

# Date range per symbol
print("\nDate ranges per symbol:")
for sym in df["symbol"].unique():
    sub = df[df["symbol"] == sym]
    print(f"  {sym}: {sub['timestamp'].min()} to {sub['timestamp'].max()}, rows={len(sub)}")

# Duplicate timestamps
dups = df[df.duplicated(subset=["timestamp", "symbol"], keep=False)]
print(f"\nDuplicate timestamp+symbol rows: {len(dups)}")
"""Convert raw Databento DBN file to clean 1-minute ES OHLCV parquet."""
import sys
from pathlib import Path

import pandas as pd
import databento as db

RAW_PATH = Path("data/raw/glbx-mdp3-20231027-20261026.ohlcv-1s.dbn.zst")
OUT_PATH = Path("data/es_1m_ohlcv.parquet")


def main():
    print("Loading DBN store...")
    store = db.DBNStore.from_file(str(RAW_PATH))

    print("Decoding to pandas...")
    df = store.to_df()

    print(f"Raw shape: {df.shape}")
    print(f"Columns: {list(df.columns)}")
    print(f"Index name: {df.index.name}")
    print(f"Index dtype: {df.index.dtype}")

    # Inspect first rows
    print("\nFirst 5 rows:")
    print(df.head())

    # Check for missing symbols / instruments
    if "instrument_id" in df.columns:
        print("\nInstrument IDs:", df["instrument_id"].unique()[:10])

    # Reset index to get timestamp as a column
    df = df.reset_index()

    # Find the timestamp column
    ts_col = None
    for c in df.columns:
        if "ts" in c.lower() or "time" in c.lower():
            ts_col = c
            break
    print(f"\nTimestamp column: {ts_col}")

    # Rename to a standard schema
    rename = {}
    if ts_col:
        rename[ts_col] = "timestamp"
    for c in ["open", "high", "low", "close", "volume"]:
        if c in df.columns:
            rename[c] = c
    if "instrument_id" in df.columns:
        rename["instrument_id"] = "instrument_id"
    df = df.rename(columns=rename)

    # Ensure timestamp is datetime
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)

    # Sort
    df = df.sort_values("timestamp").reset_index(drop=True)

    # Drop rows with NaN close (non-trading)
    df = df.dropna(subset=["close"])

    # Filter to continuous trading hours (ES: 18:00 - 17:00 next day ET)
    # We keep all data; the agent will trade during the day session.
    # For a realistic day-trader, we focus on 09:30-16:00 ET but keep full data
    # so the agent can also react to overnight moves.

    # Convert to ET for session filtering
    df["ts_et"] = df["timestamp"].dt.tz_convert("America/New_York")
    df["date"] = df["ts_et"].dt.date
    df["hour"] = df["ts_et"].dt.hour
    df["minute"] = df["ts_et"].dt.minute

    # Day session mask: 09:30 - 16:00 ET (regular trading hours)
    # ES also trades 18:00-17:00 (nearly 24h), but a day trader is active 9:30-16:00
    day_mask = (df["hour"] > 9) | ((df["hour"] == 9) & (df["minute"] >= 30))
    day_mask = day_mask & (df["hour"] < 16)

    print(f"\nRows in day session: {day_mask.sum()} / {len(df)}")
    print(f"Date range: {df['timestamp'].min()} to {df['timestamp'].max()}")
    print(f"Unique dates: {df['date'].nunique()}")

    # Save full data + day mask
    df["is_day_session"] = day_mask
    df.to_parquet(OUT_PATH, index=False)
    print(f"\nSaved to {OUT_PATH}")
    print(f"Final shape: {df.shape}")

    # Summary stats
    print("\nPrice stats:")
    print(df["close"].describe())


if __name__ == "__main__":
    main()
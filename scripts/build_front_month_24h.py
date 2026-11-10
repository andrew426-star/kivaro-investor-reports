"""Build 24-hour front-month ES series (memory efficient, chunked)."""
import pandas as pd
import numpy as np
import pyarrow.parquet as pq
import pyarrow as pa
from pathlib import Path

CONTRACT_MONTHS = {'H': 3, 'M': 6, 'U': 9, 'Z': 12}
CONTRACT_NAME_MAP = {3: 'Mar', 6: 'Jun', 9: 'Sep', 12: 'Dec'}

def compute_roll(y, m):
    if m == 1:
        return pd.Timestamp(year=y - 1, month=12, day=15)
    return pd.Timestamp(year=y, month=m - 1, day=15)

def main():
    print("Loading ES clean data (all hours)...")
    t = pq.read_table(
        'data/es_clean.parquet',
        columns=['symbol', 'timestamp', 'open', 'high', 'low', 'close', 'volume']
    )
    df = t.to_pandas()
    print(f"Input shape: {df.shape}")

    # Parse contract
    sym = df['symbol'].astype(str)
    df['contract_year'] = 2020 + sym.str[3:5].astype(int)
    df['contract_month'] = sym.str[2].map(CONTRACT_MONTHS)
    df = df.dropna(subset=['contract_month'])
    print(f"After parsing: {df.shape}")

    df['contract_expiry'] = [compute_roll(int(y), int(m)) for y, m in zip(df['contract_year'], df['contract_month'])]

    # Sort and pick front month per timestamp
    df = df.sort_values(['timestamp', 'contract_expiry']).reset_index(drop=True)
    front = df.drop_duplicates(subset=['timestamp'], keep='first').copy()
    print(f"Front month shape: {front.shape}")

    front['contract_name'] = front['contract_year'].astype(int).astype(str) + '-' + \
                             front['contract_month'].astype(int).map(CONTRACT_NAME_MAP)

    keep_cols = ['timestamp', 'open', 'high', 'low', 'close', 'volume', 'contract_name']
    front = front[keep_cols].copy()
    front = front.sort_values('timestamp').reset_index(drop=True)

    out = Path('data/es_front_month_24h.parquet')
    front.to_parquet(out, index=False)
    print(f"Saved to {out}")
    print(f"Final shape: {front.shape}")
    print(f"Date range: {front['timestamp'].min()} to {front['timestamp'].max()}")
    print(f"Price stats: min={front['close'].min()}, max={front['close'].max()}, mean={front['close'].mean():.2f}")

if __name__ == '__main__':
    main()
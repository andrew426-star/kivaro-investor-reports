"""Clean ES data: build continuous front-month contract, remove bad ticks."""
import pandas as pd
import pyarrow.parquet as pq
import pyarrow as pa
from pathlib import Path

# Read only needed columns
t = pq.read_table(
    'data/es_1m_ohlcv.parquet',
    columns=['symbol','instrument_id','timestamp','open','high','low','close','volume']
)
df = t.to_pandas()
print(f'Raw shape: {df.shape}')

# Filter to ES futures only (exclude spreads like ESZ4-ESH5)
df = df[~df['symbol'].str.contains('-', na=False)]
print(f'After removing spreads: {df.shape}')

# Filter to ES only (exclude MNQ, MES, etc.)
df = df[df['symbol'].str.startswith('ES')]
print(f'After ES-only filter: {df.shape}')

# Drop bad prices (close < 100 or close > 20000)
df = df[(df['close'] >= 100) & (df['close'] <= 20000)]
print(f'After price filter: {df.shape}')

# Drop rows with NaN close
df = df.dropna(subset=['close'])
print(f'After NaN drop: {df.shape}')

# Convert timestamp to ET
df['ts_et'] = df['timestamp'].dt.tz_convert('America/New_York')
df['date'] = df['ts_et'].dt.date
df['hour'] = df['ts_et'].dt.hour
df['minute'] = df['ts_et'].dt.minute

# Day session mask: 09:30-16:00 ET
day_mask = ((df['hour'] > 9) | ((df['hour'] == 9) & (df['minute'] >= 30))) & (df['hour'] < 16)
df['is_day_session'] = day_mask

# Sort
df = df.sort_values(['symbol', 'timestamp']).reset_index(drop=True)

# Save cleaned data
out = Path('data/es_clean.parquet')
df.to_parquet(out, index=False)
print(f'Saved to {out}')
print(f'Final shape: {df.shape}')
print(f'Date range: {df["timestamp"].min()} to {df["timestamp"].max()}')
print(f'Unique dates: {df["date"].nunique()}')
print(f'Symbols: {df["symbol"].value_counts().to_dict()}')
print(f'Price stats:')
print(df['close'].describe())

# Check day session stats
day_df = df[df['is_day_session']]
print(f'\nDay session rows: {len(day_df)} / {len(df)}')
print(f'Day session date range: {day_df["timestamp"].min()} to {day_df["timestamp"].max()}')
print(f'Day session unique dates: {day_df["date"].nunique()}')
"""Build continuous front-month ES price series - efficient version."""
import pandas as pd
import pyarrow.parquet as pq
from pathlib import Path

CONTRACT_MONTHS = {'H': 3, 'M': 6, 'U': 9, 'Z': 12}
CONTRACT_NAME_MAP = {3: 'Mar', 6: 'Jun', 9: 'Sep', 12: 'Dec'}

def main():
    t = pq.read_table(
        'data/es_clean.parquet',
        columns=['symbol', 'timestamp', 'open', 'high', 'low', 'close', 'volume', 'is_day_session', 'date']
    )
    df = t.to_pandas()
    print(f'Input shape: {df.shape}')
    
    # Day session only
    df = df[df['is_day_session'] == True].copy()
    print(f'After day session filter: {df.shape}')
    
    # Parse contract from symbol
    # ES futures codes: last digit = year (e.g., ESZ3 = Dec 2023)
    # In our data range (2023-2026), digit maps: 3→2023, 4→2024, 5→2025, 6→2026, 7→2027
    sym = df['symbol'].astype(str)
    year_digit = sym.str[3:5].astype(int)
    df['contract_year'] = 2020 + year_digit
    df['contract_month'] = sym.str[2].map(CONTRACT_MONTHS)
    df = df.dropna(subset=['contract_month'])
    print(f'After parsing: {df.shape}')
    
    # Compute roll date (15th of month before expiry)
    def compute_roll(y, m):
        if m == 1:
            return pd.Timestamp(year=y - 1, month=12, day=15)
        return pd.Timestamp(year=y, month=m - 1, day=15)
    
    df['contract_expiry'] = [compute_roll(y, m) for y, m in zip(df['contract_year'], df['contract_month'])]
    
    # Sort by timestamp ascending, then contract_expiry ascending
    df = df.sort_values(['timestamp', 'contract_expiry']).reset_index(drop=True)
    
    # Drop duplicates on timestamp, keeping the first (earliest expiry = front month)
    front = df.drop_duplicates(subset=['timestamp'], keep='first').copy()
    print(f'\nFront month shape: {front.shape}')
    print(f'Unique timestamps: {front["timestamp"].nunique()}')
    
    # Check duplicates
    dups = front[front.duplicated('timestamp', keep=False)]
    print(f'Duplicate timestamps: {len(dups)}')
    
    # Add contract name
    front['contract_name'] = front['contract_year'].astype(str) + '-' + \
                             front['contract_month'].astype(int).map(CONTRACT_NAME_MAP)
    
    print(f'\nContracts used: {front["contract_name"].value_counts().to_dict()}')
    print(f'Date range: {front["timestamp"].min()} to {front["timestamp"].max()}')
    
    # Check gaps
    front = front.sort_values('timestamp').reset_index(drop=True)
    front['ts_diff'] = front['timestamp'].diff().dt.total_seconds()
    gaps = front[front['ts_diff'] > 65]
    print(f'\nGaps > 65s: {len(gaps)}')
    if len(gaps) > 0:
        print(gaps[['timestamp', 'ts_diff', 'close']].head(10))
    
    # Keep needed columns
    keep_cols = ['timestamp', 'open', 'high', 'low', 'close', 'volume', 'contract_name', 'date']
    front = front[keep_cols].copy()
    
    out = Path('data/es_front_month.parquet')
    front.to_parquet(out, index=False)
    print(f'\nSaved to {out}')
    print(f'Final shape: {front.shape}')
    print(f'Price stats:')
    print(front['close'].describe())

if __name__ == '__main__':
    main()
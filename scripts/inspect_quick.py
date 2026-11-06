"""Quick inspect parquet with pyarrow."""
import pyarrow.parquet as pq

t = pq.read_table('data/es_1m_ohlcv.parquet', columns=['symbol','instrument_id','close','volume','timestamp'])
df = t.to_pandas()
print(f'Shape: {df.shape}')
print(f'Symbols: {df["symbol"].value_counts().to_dict()}')
print(f'Instrument IDs (top 10): {df["instrument_id"].value_counts().head(10).to_dict()}')
print(f'Close min: {df["close"].min()}, max: {df["close"].max()}')
print(f'Bad prices (<100 or >20000): {((df["close"]<100)|(df["close"]>20000)).sum()}')
print(f'Zero volume: {(df["volume"]==0).sum()}')
print(f'Date range: {df["timestamp"].min()} to {df["timestamp"].max()}')
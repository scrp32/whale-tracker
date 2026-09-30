import pandas as pd

def detect_dark_accumulation(df_daily_quotes, volume_threshold_multiplier=3.0, max_price_change_pct=1.5):
    """
    Identifies 'Dark Accumulation' days (high volume, tight price range).
    """
    if df_daily_quotes.empty:
        return pd.DataFrame()

    df = df_daily_quotes.copy()
    df['avg_vol_20'] = df.groupby('symbol')['volume'].transform(lambda x: x.rolling(20).mean())
    df['vol_spike'] = df['volume'] / df['avg_vol_20']
    df['price_spread_pct'] = ((df['high'] - df['low']) / df['low']) * 100.0
    df['close_change_pct'] = abs((df['close'] - df['open']) / df['open']) * 100.0
    
    dark_mask = (
        (df['vol_spike'] >= volume_threshold_multiplier) & 
        (df['close_change_pct'] <= max_price_change_pct) &
        (df['price_spread_pct'] <= (max_price_change_pct * 2.0))
    )
    
    dark_df = df[dark_mask].copy()
    dark_df['signal'] = "👁️ DARK ACCUMULATION DETECTED"
    
    return dark_df[['date', 'symbol', 'close', 'vol_spike', 'close_change_pct', 'signal']]

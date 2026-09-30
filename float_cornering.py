import pandas as pd

def calculate_float_cornering(accumulation_df, shareholding_meta_df):
    """
    Calculates the Float Cornering Index (FCI):
    FCI = (Net Shares Bought by Whales / Total Free Float Shares) * 100
    """
    if accumulation_df.empty or shareholding_meta_df.empty:
        return pd.DataFrame()

    merged = pd.merge(accumulation_df, shareholding_meta_df, on='symbol', how='inner')
    merged['free_float_shares'] = (merged['total_shares'] * (merged['free_float_pct'] / 100.0))
    merged['fci_pct'] = (merged['net_quantity'] / merged['free_float_shares']) * 100.0
    merged['absorption_days'] = merged['net_quantity'] / merged['avg_daily_volume']
    
    def evaluate_squeeze_potential(row):
        if row['fci_pct'] >= 5.0 and row['absorption_days'] >= 10:
            return "🔥 EXTREME FLOAT CORNER"
        elif row['fci_pct'] >= 2.0 and row['absorption_days'] >= 5:
            return "⚡ HIGH FLOAT CORNER"
        elif row['fci_pct'] >= 0.5:
            return "MODERATE ACCUMULATION"
        return "LOW IMPACT"

    merged['squeeze_signal'] = merged.apply(evaluate_squeeze_potential, axis=1)
    return merged.sort_values(by='fci_pct', ascending=False)

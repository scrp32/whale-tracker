import pandas as pd
from float_cornering import calculate_float_cornering
from dark_accumulation import detect_dark_accumulation
from whale_options import fetch_nse_participant_oi

class InstitutionalTracker:
    def __init__(self):
        self.super_investors_tier1 = [
            "NALANDA INDIA EQUITY FUND",
            "RADHAKISHAN DAMANI",
            "ASHISH KACHOLIA",
            "MUKUL AGRAWAL",
            "VIJAY KEDIA",
            "WESTBRIDGE CROSBY"
        ]

    def process_cash_and_float_signals(self, accumulation_df, shareholding_meta_df):
        """
        Runs the Float Cornering Index calculation across cash holdings.
        """
        if accumulation_df.empty or shareholding_meta_df.empty:
            return pd.DataFrame()
        return calculate_float_cornering(accumulation_df, shareholding_meta_df)

    def scan_dark_accumulation(self, df_daily_quotes):
        """
        Runs the stealth volume absorption scanner on daily OHLCV data.
        """
        if df_daily_quotes.empty:
            return pd.DataFrame()
        return detect_dark_accumulation(df_daily_quotes)

    def get_options_overlay(self, date_str: str = None):
        """
        Retrieves institutional & prop desk derivatives positioning.
        """
        return fetch_nse_participant_oi(date_str)

    def filter_super_investors(self, deals_df):
        """
        Filters deal feeds for Tier-1 Super Investor entries.
        """
        if deals_df.empty or 'investor_name' not in deals_df.columns:
            return pd.DataFrame()
        
        pattern = '|'.join(self.super_investors_tier1)
        filtered = deals_df[deals_df['investor_name'].str.upper().str.contains(pattern, na=False)].copy()
        filtered['tier_weight'] = 3.0
        return filtered

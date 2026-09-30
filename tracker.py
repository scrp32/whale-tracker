import pandas as pd

# Safe dynamic imports
try:
    from float_cornering import calculate_float_cornering
except ImportError:

    def calculate_float_cornering(accumulation_df, shareholding_meta_df):
        return pd.DataFrame()


try:
    from dark_accumulation import detect_dark_accumulation
except ImportError:

    def detect_dark_accumulation(df_daily_quotes):
        return pd.DataFrame()


try:
    from whale_options import fetch_nse_participant_oi
except ImportError:

    def fetch_nse_participant_oi(date_str=None):
        return pd.DataFrame()


class InstitutionalTracker:

    def __init__(self):
        self.super_investors_tier1 = [
            "NALANDA INDIA EQUITY FUND",
            "RADHAKISHAN DAMANI",
            "ASHISH KACHOLIA",
            "MUKUL AGRAWAL",
            "VIJAY KEDIA",
            "WESTBRIDGE CROSBY",
        ]

    def process_cash_and_float_signals(
        self, accumulation_df, shareholding_meta_df
    ):
        if accumulation_df.empty or shareholding_meta_df.empty:
            return pd.DataFrame()
        return calculate_float_cornering(accumulation_df, shareholding_meta_df)

    def scan_dark_accumulation(self, df_daily_quotes):
        if df_daily_quotes.empty:
            return pd.DataFrame()
        return detect_dark_accumulation(df_daily_quotes)

    def get_options_overlay(self, date_str: str = None):
        return fetch_nse_participant_oi(date_str)

    def filter_super_investors(self, deals_df):
        if deals_df.empty or "investor_name" not in deals_df.columns:
            return pd.DataFrame()

        pattern = "|".join(self.super_investors_tier1)
        filtered = deals_df[
            deals_df["investor_name"]
            .str.upper()
            .str.contains(pattern, na=False)
        ].copy()
        filtered["tier_weight"] = 3.0
        return filtered

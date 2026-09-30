import datetime
import io
import pandas as pd
import requests

def fetch_nse_participant_oi(date_str: str = None) -> pd.DataFrame:
    """
    Fetches participant-wise derivatives open interest (FII, DII, Pro, Client) from NSE archives.
    Date format: 'DDMMYYYY' (e.g., '29092026'). If None, defaults to previous day.
    """
    if not date_str:
        # Default to previous calendar day
        yesterday = datetime.date.today() - datetime.timedelta(days=1)
        date_str = yesterday.strftime("%d%m%Y")

    url = f"https://archives.nseindia.com/content/nsccl/fao_participant_oi_{date_str}.csv"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36'
    }

    try:
        res = requests.get(url, headers=headers, timeout=10)
        if res.status_code == 200:
            # First line of NSE CSV contains report title metadata
            df = pd.read_csv(io.StringIO(res.text), skiprows=1)
            return process_whale_options_data(df)
        else:
            print(f"Failed to fetch NSE OI data for {date_str}. HTTP Status: {res.status_code}")
            return pd.DataFrame()
    except Exception as e:
        print(f"Error executing NSE options retrieval: {e}")
        return pd.DataFrame()


def process_whale_options_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculates Net Option Delta Bias and Put-Call Ratio (PCR) for Whales (FII & Pro).
    """
    # Clean column headers
    df.columns = [c.strip() for c in df.columns]

    # Cast numerical columns
    numeric_cols = [c for c in df.columns if c != 'Client Type']
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

    # Calculate Net Positions (Longs - Shorts)
    df['Net Index Call'] = df['Option Index Call Long'] - df['Option Index Call Short']
    df['Net Index Put'] = df['Option Index Put Long'] - df['Option Index Put Short']

    # Calculate Put-Call Ratio (PCR) on Long Positions
    df['Index Option PCR'] = (df['Option Index Put Long'] / df['Option Index Call Long'].replace(0, 1)).round(2)

    # Compute Net Delta Score
    # Net Delta = (Call Longs + Put Shorts) - (Call Shorts + Put Longs)
    df['Net Delta Score'] = (
        (df['Option Index Call Long'] + df['Option Index Put Short']) - 
        (df['Option Index Call Short'] + df['Option Index Put Long'])
    )

    # Filter exclusively for Institutional and Prop Whales
    whale_df = df[df['Client Type'].isin(['FII', 'Pro'])].copy()

    # Re-order key signal columns
    return whale_df[[
        'Client Type', 
        'Net Index Call', 
        'Net Index Put', 
        'Index Option PCR', 
        'Net Delta Score', 
        'Future Index Long', 
        'Future Index Short'
    ]]

if __name__ == "__main__":
    df_options = fetch_nse_participant_oi()
    print("--- Institutional & Prop Whale Option Positioning ---")
    print(df_options.to_string(index=False))

import datetime
import io
import pandas as pd
import requests


def fetch_nse_participant_oi(date_str: str = None) -> pd.DataFrame:
    """Fetches participant-wise derivatives open interest from NSE archives."""
    if not date_str:
        yesterday = datetime.date.today() - datetime.timedelta(days=1)
        date_str = yesterday.strftime("%d%m%Y")

    url = f"https://archives.nseindia.com/content/nsccl/fao_participant_oi_{date_str}.csv"
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/115.0.0.0 Safari/537.36"
        )
    }

    try:
        res = requests.get(url, headers=headers, timeout=10)
        if res.status_code == 200:
            df = pd.read_csv(io.StringIO(res.text), skiprows=1)
            return process_whale_options_data(df)
        else:
            return pd.DataFrame()
    except Exception:
        return pd.DataFrame()


def process_whale_options_data(df: pd.DataFrame) -> pd.DataFrame:
    """Calculates Net Option Delta Bias and Put-Call Ratio for Whales."""
    df.columns = [c.strip() for c in df.columns]

    numeric_cols = [c for c in df.columns if c != "Client Type"]
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    # Calculate Net Positions
    df["Net Index Call"] = (
        df["Option Index Call Long"] - df["Option Index Call Short"]
    )
    df["Net Index Put"] = (
        df["Option Index Put Long"] - df["Option Index Put Short"]
    )

    # Put-Call Ratio (PCR)
    df["Index Option PCR"] = (
        df["Option Index Put Long"] / df["Option Index Call Long"].replace(0, 1)
    ).round(2)

    # Net Delta Score
    df["Net Delta Score"] = (
        df["Option Index Call Long"] + df["Option Index Put Short"]
    ) - (df["Option Index Call Short"] + df["Option Index Put Long"])

    # Ensure Net Delta Score is explicitly integer for display formatting
    df["Net Delta Score"] = df["Net Delta Score"].astype(int)

    whale_df = df[df["Client Type"].isin(["FII", "Pro"])].copy()

    return whale_df[
        [
            "Client Type",
            "Net Index Call",
            "Net Index Put",
            "Index Option PCR",
            "Net Delta Score",
            "Future Index Long",
            "Future Index Short",
        ]
    ]

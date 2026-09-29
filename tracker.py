import sqlite3
import pandas as pd
import re
import requests
from datetime import datetime, timedelta
from nselib import capital_market

DB_FILE = "whale_data.db"

WHALE_KEYWORDS = [
    "BLACKROCK", "VANGUARD", "NORGES", "GIC", "TEMASEK", "FIDELITY", 
    "MUTUAL", "FUND", "CAPITAL", "INVESTMENT", "SECURITIES", "NALANDA",
    "ASHISH KACHOLIA", "RADHAKISHAN DAMANI", "MUKUL AGRAWAL", "VIJAY KEDIA",
    "HDFC", "SBI", "NIPPON", "ICICI", "AXIS", "KOTAK", "TRUSTEE", "PARTNERS",
    "BANK", "AIF", "VENTURES", "EMERGING", "GROWTH", "MASTERS", "INDIA"
]

def init_db():
    conn = sqlite3.connect(DB_FILE)
    # Bulk Deals Table
    conn.execute('''
        CREATE TABLE IF NOT EXISTS bulk_deals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT, symbol TEXT, client_name TEXT, 
            buy_sell TEXT, quantity INTEGER, trade_price REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(date, symbol, client_name, quantity, trade_price)
        )
    ''')
    
    # Quarterly Portfolio / Shareholding Table (WhaleWisdom 13F Equivalent)
    conn.execute('''
        CREATE TABLE IF NOT EXISTS quarterly_holdings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            quarter TEXT, symbol TEXT, investor_name TEXT, 
            holding_pct REAL, sector TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(quarter, symbol, investor_name)
        )
    ''')
    conn.commit()
    conn.close()

def clean_numeric(val):
    if pd.isna(val) or val is None:
        return 0.0
    val_str = str(val).replace(',', '').strip()
    match = re.search(r"[-+]?\d*\.\d+|\d+", val_str)
    return float(match.group()) if match else 0.0

def fetch_nse_direct_api(from_date_str, to_date_str):
    session = requests.Session()
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': '*/*',
        'Accept-Language': 'en-US,en;q=0.9',
        'Referer': 'https://www.nseindia.com/reports/bulk-block-deals'
    }
    try:
        session.get("https://www.nseindia.com", headers=headers, timeout=10)
        url = f"https://www.nseindia.com/api/historical/bulk-deals?from={from_date_str}&to={to_date_str}"
        res = session.get(url, headers=headers, timeout=15)
        if res.status_code == 200:
            data = res.json()
            if 'data' in data and data['data']:
                return pd.DataFrame(data['data'])
    except Exception:
        pass
    return None

def fetch_live_nse_deals():
    end_d = datetime.now()
    start_d = end_d - timedelta(days=30)
    
    from_str = start_d.strftime('%d-%m-%Y')
    to_str = end_d.strftime('%d-%m-%Y')
    
    try:
        df = capital_market.bulk_deal_data(from_date=from_str, to_date=to_str)
        if df is not None and not df.empty:
            return df
    except Exception:
        pass

    try:
        df = capital_market.bulk_deal_data(period='1M')
        if df is not None and not df.empty:
            return df
    except Exception:
        pass

    return fetch_nse_direct_api(from_str, to_str)

def run_whale_scan():
    init_db()
    deals_df = fetch_live_nse_deals()

    if deals_df is None or deals_df.empty:
        return "NSE API returned no records for the last 30 days."

    deals_df.columns = [str(c).strip().lower().replace(" ", "_").replace("-", "_") for c in deals_df.columns]
    
    client_col = next((c for c in deals_df.columns if any(k in c for k in ['client', 'party', 'investor', 'acquirer'])), None)
    qty_col = next((c for c in deals_df.columns if any(k in c for k in ['quantity', 'qty', 'shares', 'vol'])), None)
    price_col = next((c for c in deals_df.columns if any(k in c for k in ['price', 'rate', 'avg', 'val'])), None)
    action_col = next((c for c in deals_df.columns if any(k in c for k in ['buy_sell', 'buy/sell', 'type', 'side', 'transaction'])), None)
    symbol_col = next((c for c in deals_df.columns if any(k in c for k in ['symbol', 'ticker', 'security', 'company'])), None)
    date_col = next((c for c in deals_df.columns if any(k in c for k in ['date', 'time', 'dt', 'period'])), None)

    pattern = "|".join(WHALE_KEYWORDS)
    if client_col and client_col in deals_df.columns:
        whales = deals_df[deals_df[client_col].astype(str).str.contains(pattern, case=False, na=False)]
        if whales.empty:
            whales = deals_df.copy()
    else:
        whales = deals_df.copy()

    conn = sqlite3.connect(DB_FILE)
    inserted_count = 0
    
    for _, row in whales.iterrows():
        try:
            date_val = str(row[date_col]).strip() if date_col and date_col in row and pd.notna(row[date_col]) else "Unknown Date"
            symbol_val = str(row[symbol_col]).strip() if symbol_col and symbol_col in row and pd.notna(row[symbol_col]) else "N/A"
            client_val = str(row[client_col]).strip() if client_col and client_col in row and pd.notna(row[client_col]) else "Unknown"
            action_val = str(row[action_col]).upper().strip() if action_col and action_col in row and pd.notna(row[action_col]) else "BUY"
            
            qty_val = int(clean_numeric(row[qty_col])) if qty_col and qty_col in row else 0
            price_val = clean_numeric(row[price_col]) if price_col and price_col in row else 0.0

            if qty_val <= 0 or price_val <= 0.0:
                continue

            conn.execute('''
                INSERT INTO bulk_deals (date, symbol, client_name, buy_sell, quantity, trade_price)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (date_val, symbol_val, client_val, action_val, qty_val, price_val))
            inserted_count += 1
        except sqlite3.IntegrityError: 
            pass
        except Exception:
            continue
            
    conn.commit()
    conn.close()

    return f"Success! Synced {inserted_count} real transactions from NSE."

def get_second_order_insights():
    init_db()
    conn = sqlite3.connect(DB_FILE)
    df = pd.read_sql_query("SELECT * FROM bulk_deals", conn)
    conn.close()

    if df.empty:
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

    df['buy_sell'] = df['buy_sell'].astype(str).str.strip().str.upper()
    df['quantity'] = pd.to_numeric(df['quantity'], errors='coerce').fillna(0)
    df['trade_price'] = pd.to_numeric(df['trade_price'], errors='coerce').fillna(0.0)
    
    df['net_qty'] = df.apply(lambda r: r['quantity'] if 'BUY' in r['buy_sell'] else -r['quantity'], axis=1)
    df['trade_value_cr'] = (df['quantity'] * df['trade_price']) / 10000000.0

    accumulation = df.groupby(['symbol', 'client_name']).agg(
        latest_date=('date', 'max'),
        active_days=('date', 'nunique'),
        total_buy_qty=('quantity', lambda x: x[df.loc[x.index, 'buy_sell'].str.contains('BUY', na=False)].sum()),
        total_sell_qty=('quantity', lambda x: x[df.loc[x.index, 'buy_sell'].str.contains('SELL', na=False)].sum()),
        net_quantity=('net_qty', 'sum'),
        vwap_buy_price=('trade_price', lambda p: (p * df.loc[p.index, 'quantity']).sum() / df.loc[p.index, 'quantity'].sum() if df.loc[p.index, 'quantity'].sum() > 0 else 0),
        total_buy_value_cr=('trade_value_cr', lambda v: v[df.loc[v.index, 'buy_sell'].str.contains('BUY', na=False)].sum()),
        total_sell_value_cr=('trade_value_cr', lambda v: v[df.loc[v.index, 'buy_sell'].str.contains('SELL', na=False)].sum()),
        trade_count=('id', 'count')
    ).reset_index()

    accumulation['gross_value_cr'] = accumulation['total_buy_value_cr'] + accumulation['total_sell_value_cr']

    def categorize_behavior(row):
        buy_val = row['total_buy_value_cr']
        sell_val = row['total_sell_value_cr']
        
        if row['total_buy_qty'] > 0 and row['total_sell_qty'] > 0:
            if abs(row['net_quantity']) < (0.25 * max(row['total_buy_qty'], row['total_sell_qty'])):
                return "Arbitrage / Intra-day Churn"
        
        if sell_val > buy_val and (sell_val - buy_val) >= 0.10:
            return "Institutional Distribution"
            
        if buy_val >= 1.0 and row['active_days'] == 1:
            return "Aggressive Block Buy (>₹1 Cr)"
            
        if buy_val >= 0.25 and row['active_days'] >= 2:
            return "Stealth Drip Accumulation"
            
        if buy_val >= 0.05:
            return "Directional Accumulation (>₹5 Lakhs)"
            
        return "Minor Movement (<₹5 Lakhs)"

    accumulation['behavior_profile'] = accumulation.apply(categorize_behavior, axis=1)

    concentration = df[df['buy_sell'].str.contains('BUY', na=False)].groupby('symbol').agg(
        distinct_whales=('client_name', 'nunique'),
        whale_list=('client_name', lambda x: ", ".join(set(x))),
        total_net_value_cr=('trade_value_cr', 'sum'),
        last_active=('date', 'max')
    ).reset_index().sort_values(by='distinct_whales', ascending=False)

    return df, accumulation, concentration

def get_whale_wisdom_analytics():
    """Generates WhaleWisdom style portfolio metrics and conviction scores."""
    raw_df, accumulation, concentration = get_second_order_insights()
    if accumulation.empty:
        return pd.DataFrame(), pd.DataFrame()

    # 1. Whale Conviction Score
    # Score formula: (Net capital deployed in Cr * 2) + (Active trading days * 3) + (Distinct transactions * 1.5)
    accumulation['conviction_score'] = (
        (accumulation['total_buy_value_cr'] - accumulation['total_sell_value_cr']) * 2.0 +
        (accumulation['active_days'] * 3.0) +
        (accumulation['trade_count'] * 1.5)
    ).round(2)

    top_conviction = accumulation.sort_values(by='conviction_score', ascending=False)

    # 2. Fund Portfolio Breakdown (WhaleWisdom 13F equivalent view)
    fund_portfolios = accumulation.groupby('client_name').agg(
        total_stocks=('symbol', 'nunique'),
        stock_list=('symbol', lambda x: ", ".join(set(x))),
        total_invested_cr=('total_buy_value_cr', 'sum'),
        total_divested_cr=('total_sell_value_cr', 'sum'),
        net_exposure_cr=('gross_value_cr', lambda x: accumulation.loc[x.index, 'total_buy_value_cr'].sum() - accumulation.loc[x.index, 'total_sell_value_cr'].sum()),
        primary_behavior=('behavior_profile', lambda x: x.mode()[0] if not x.empty else 'N/A')
    ).reset_index().sort_values(by='total_invested_cr', ascending=False)

    return top_conviction, fund_portfolios

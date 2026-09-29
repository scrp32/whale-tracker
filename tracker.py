import sqlite3
import pandas as pd
import re
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
    conn.execute('''
        CREATE TABLE IF NOT EXISTS bulk_deals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT, symbol TEXT, client_name TEXT, 
            buy_sell TEXT, quantity INTEGER, trade_price REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(date, symbol, client_name, quantity, trade_price)
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

def fetch_live_nse_deals():
    """Attempts multiple fetch strategies from NSE via nselib."""
    deals_df = None
    
    # Strategy 1: Period '1M'
    try:
        deals_df = capital_market.bulk_deal_data(period='1M')
    except Exception:
        pass

    # Strategy 2: Explicit Rolling 30-Day Date Range
    if deals_df is None or deals_df.empty:
        try:
            end_d = datetime.now()
            start_d = end_d - timedelta(days=30)
            deals_df = capital_market.bulk_deal_data(
                from_date=start_d.strftime('%d-%m-%Y'),
                to_date=end_d.strftime('%d-%m-%Y')
            )
        except Exception:
            pass

    # Strategy 3: Current Month Date Range
    if deals_df is None or deals_df.empty:
        try:
            end_d = datetime.now()
            start_d = end_d.replace(day=1)
            deals_df = capital_market.bulk_deal_data(
                from_date=start_d.strftime('%d-%m-%Y'),
                to_date=end_d.strftime('%d-%m-%Y')
            )
        except Exception:
            pass

    return deals_df

def run_whale_scan():
    init_db()
    
    deals_df = fetch_live_nse_deals()

    if deals_df is None or deals_df.empty:
        return "NSE API returned no bulk deal records for the selected period. Please try again during or after market hours."

    # Standardize column headers
    deals_df.columns = [str(c).strip().lower().replace(" ", "_").replace("-", "_") for c in deals_df.columns]
    
    # Column detection
    client_col = next((c for c in ['client_name', 'client', 'clientname', 'investor_name', 'party_name'] if c in deals_df.columns), deals_df.columns[2])
    qty_col = next((c for c in ['quantity_traded', 'quantity', 'qty', 'shares_traded', 'vol'] if c in deals_df.columns), None)
    price_col = next((c for c in ['trade_price', 'price', 'avg_price', 'rate', 'wtd_avg_price'] if c in deals_df.columns), None)
    action_col = next((c for c in ['buy_sell', 'buy/sell', 'type', 'side'] if c in deals_df.columns), None)
    symbol_col = next((c for c in ['symbol', 'security_name', 'ticker'] if c in deals_df.columns), None)
    date_col = next((c for c in ['date', 'transaction_date', 'deal_date'] if c in deals_df.columns), None)

    # Filter whales; if keywords return empty, ingest all available deals
    pattern = "|".join(WHALE_KEYWORDS)
    whales = deals_df[deals_df[client_col].astype(str).str.contains(pattern, case=False, na=False)]
    
    if whales.empty:
        whales = deals_df.copy()

    conn = sqlite3.connect(DB_FILE)
    inserted_count = 0
    
    for _, row in whales.iterrows():
        try:
            date_val = str(row[date_col]) if date_col and pd.notna(row[date_col]) else "Recent"
            symbol_val = str(row[symbol_col]) if symbol_col and pd.notna(row[symbol_col]) else "N/A"
            client_val = str(row[client_col]) if pd.notna(row[client_col]) else "Unknown"
            action_val = str(row[action_col]).upper() if action_col and pd.notna(row[action_col]) else "BUY"
            
            qty_val = int(clean_numeric(row[qty_col])) if qty_col else 0
            price_val = clean_numeric(row[price_col]) if price_col else 0.0

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

    if inserted_count == 0:
        return f"Fetched {len(deals_df)} raw records from NSE, but no new/valid trade rows could be added."

    return f"Success! Synced and saved {inserted_count} real transactions from NSE."

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
        total_buy_qty=('quantity', lambda x: x[df.loc[x.index, 'buy_sell'].str.contains('BUY', na=False)].sum()),
        total_sell_qty=('quantity', lambda x: x[df.loc[x.index, 'buy_sell'].str.contains('SELL', na=False)].sum()),
        net_quantity=('net_qty', 'sum'),
        vwap_buy_price=('trade_price', lambda p: (p * df.loc[p.index, 'quantity']).sum() / df.loc[p.index, 'quantity'].sum() if df.loc[p.index, 'quantity'].sum() > 0 else 0),
        total_buy_value_cr=('trade_value_cr', lambda v: v[df.loc[v.index, 'buy_sell'].str.contains('BUY', na=False)].sum()),
        total_sell_value_cr=('trade_value_cr', lambda v: v[df.loc[v.index, 'buy_sell'].str.contains('SELL', na=False)].sum()),
        trade_count=('id', 'count'),
        active_days=('date', 'nunique')
    ).reset_index()

    accumulation['gross_value_cr'] = accumulation['total_buy_value_cr'] + accumulation['total_sell_value_cr']

    def categorize_behavior(row):
        buy_val = row['total_buy_value_cr']
        sell_val = row['total_sell_value_cr']
        
        # Arbitrage / Churn
        if row['total_buy_qty'] > 0 and row['total_sell_qty'] > 0:
            if abs(row['net_quantity']) < (0.25 * max(row['total_buy_qty'], row['total_sell_qty'])):
                return "Arbitrage / Intra-day Churn"
        
        # Distribution
        if sell_val > buy_val and (sell_val - buy_val) >= 0.10:
            return "Institutional Distribution"
            
        # Block Buy
        if buy_val >= 1.0 and row['active_days'] == 1:
            return "Aggressive Block Buy (>₹1 Cr)"
            
        # Stealth Drip
        if buy_val >= 0.25 and row['active_days'] >= 2:
            return "Stealth Drip Accumulation"
            
        # Directional Accumulation
        if buy_val >= 0.05:
            return "Directional Accumulation (>₹5 Lakhs)"
            
        return "Minor Movement (<₹5 Lakhs)"

    accumulation['behavior_profile'] = accumulation.apply(categorize_behavior, axis=1)

    concentration = df[df['buy_sell'].str.contains('BUY', na=False)].groupby('symbol').agg(
        distinct_whales=('client_name', 'nunique'),
        whale_list=('client_name', lambda x: ", ".join(set(x))),
        total_net_value_cr=('trade_value_cr', 'sum')
    ).reset_index().sort_values(by='distinct_whales', ascending=False)

    return df, accumulation, concentration

import sqlite3
import pandas as pd
from nselib import capital_market

DB_FILE = "whale_data.db"

# Broadened keyword list to catch DIIs, MFs, Global Funds, and Marquee Indian Investors
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

def run_whale_scan():
    init_db()
    try:
        deals_df = capital_market.bulk_deal_data(period='1M')
        
        if deals_df is None or deals_df.empty: 
            return "No bulk deal records returned from NSE."
        
        deals_df.columns = [str(c).strip().lower().replace(" ", "_").replace("-", "_") for c in deals_df.columns]
        
        client_col = None
        for col in ['client_name', 'client', 'clientname', 'investor_name', 'client_name_']:
            if col in deals_df.columns:
                client_col = col
                break
                
        if not client_col:
            possible_cols = [c for c in deals_df.columns if 'client' in c or 'name' in c]
            if possible_cols:
                client_col = possible_cols[0]
            else:
                return f"Error: Could not identify Client column. Available columns: {list(deals_df.columns)}"
        
        pattern = "|".join(WHALE_KEYWORDS)
        whales = deals_df[deals_df[client_col].astype(str).str.contains(pattern, case=False, na=False)]
        
        # Fallback: if keywords are too restrictive, import all deals
        if whales.empty:
            whales = deals_df.copy()
            
        conn = sqlite3.connect(DB_FILE)
        inserted_count = 0
        
        for _, row in whales.iterrows():
            try:
                def get_val(keys, default="N/A"):
                    for k in keys:
                        if k in row and pd.notna(row[k]):
                            return str(row[k])
                    return default

                date_val = get_val(['date', 'transaction_date', 'deal_date'], 'Recent')
                symbol_val = get_val(['symbol', 'security_name', 'ticker'], 'N/A')
                client_val = str(row[client_col])
                action_val = get_val(['buy_sell', 'buy/sell', 'type', 'tx_type'], 'BUY').upper()
                
                raw_qty = get_val(['quantity_traded', 'quantity', 'qty', 'shares'], '0')
                raw_price = get_val(['trade_price', 'price', 'avg_price', 'rate'], '0')

                qty_val = int(float(str(raw_qty).replace(',', '')))
                price_val = float(str(raw_price).replace(',', ''))
                
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
        return f"Success! Sync completed. Added {inserted_count} transactions."
        
    except Exception as e:
        return f"Error connecting to NSE: {str(e)}"

def get_second_order_insights():
    conn = sqlite3.connect(DB_FILE)
    df = pd.read_sql_query("SELECT * FROM bulk_deals", conn)
    conn.close()

    if df.empty:
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

    df['buy_sell'] = df['buy_sell'].str.strip().str.upper()
    df['net_qty'] = df.apply(lambda r: r['quantity'] if 'BUY' in r['buy_sell'] else -r['quantity'], axis=1)
    df['trade_value_cr'] = (df['quantity'] * df['trade_price']) / 10000000

    # Aggregating metrics per symbol and client
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

    # Dynamic Behavior Classification Engine with Lowered Thresholds
    def categorize_behavior(row):
        buy_val = row['total_buy_value_cr']
        sell_val = row['total_sell_value_cr']
        net_val = buy_val - sell_val
        
        # 1. Arbitrage or Day-Trading Churn
        if row['total_buy_qty'] > 0 and row['total_sell_qty'] > 0:
            if abs(row['net_quantity']) < (0.20 * max(row['total_buy_qty'], row['total_sell_qty'])):
                return "Arbitrage / Intra-day Churn"
        
        # 2. Institutional Distribution
        if sell_val > buy_val and abs(net_val) >= 0.25:
            return "Institutional Distribution"
            
        # 3. Aggressive Block Buy
        if buy_val >= 2.0 and row['active_days'] == 1:
            return "Aggressive Block Buy (>₹2 Cr)"
            
        # 4. Stealth Drip Accumulation
        if buy_val >= 0.5 and row['active_days'] >= 2:
            return "Stealth Drip Accumulation"
            
        # 5. Directional Accumulation
        if buy_val >= 0.1:
            return "Directional Accumulation"
            
        return "Minor Movement (<₹10 Lakhs)"

    accumulation['behavior_profile'] = accumulation.apply(categorize_behavior, axis=1)

    # Multi-Whale Concentration
    concentration = df[df['buy_sell'].str.contains('BUY', na=False)].groupby('symbol').agg(
        distinct_whales=('client_name', 'nunique'),
        whale_list=('client_name', lambda x: ", ".join(set(x))),
        total_net_value_cr=('trade_value_cr', 'sum')
    ).reset_index().sort_values(by='distinct_whales', ascending=False)

    return df, accumulation, concentration

import sqlite3
import pandas as pd
from nselib import capital_market

DB_FILE = "whale_data.db"
WHALE_KEYWORDS = [
    "BLACKROCK", "VANGUARD", "NORGES", "GIC", "TEMASEK", "FIDELITY", 
    "MUTUAL", "FUND", "CAPITAL", "INVESTMENT", "SECURITIES"
]

def init_db():
    conn = sqlite3.connect(DB_FILE)
    conn.execute('''
        CREATE TABLE IF NOT EXISTS bulk_deals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT, symbol TEXT, client_name TEXT, 
            buy_sell TEXT, quantity INTEGER, trade_price REAL,
            UNIQUE(date, symbol, client_name, quantity, trade_price)
        )
    ''')
    conn.commit()
    conn.close()

def run_whale_scan():
    init_db()
    try:
        # Fetch 1 month of bulk deal data
        deals_df = capital_market.bulk_deal_data(period='1M')
        
        if deals_df is None or deals_df.empty: 
            return "No bulk deal records returned from NSE."
        
        # Clean and normalize column names
        deals_df.columns = [str(c).strip().lower().replace(" ", "_").replace("-", "_") for c in deals_df.columns]
        
        # Safely detect client name column across various NSE response schemas
        client_col = None
        for col in ['client_name', 'client', 'clientname', 'investor_name', 'client_name_']:
            if col in deals_df.columns:
                client_col = col
                break
                
        if not client_col:
            # Fallback: look for any column containing 'client' or 'name'
            possible_cols = [c for c in deals_df.columns if 'client' in c or 'name' in c]
            if possible_cols:
                client_col = possible_cols[0]
            else:
                return f"Error: Could not identify Client column. Available columns: {list(deals_df.columns)}"
        
        # Filter for whale keywords safely
        pattern = "|".join(WHALE_KEYWORDS)
        whales = deals_df[deals_df[client_col].astype(str).str.contains(pattern, case=False, na=False)]
        
        if whales.empty:
            return f"Fetched {len(deals_df)} NSE records, but 0 matched tracked whale keywords."
            
        conn = sqlite3.connect(DB_FILE)
        inserted_count = 0
        
        for _, row in whales.iterrows():
            try:
                # Helper function to get value across multiple potential column names
                def get_val(keys, default="N/A"):
                    for k in keys:
                        if k in row and pd.notna(row[k]):
                            return str(row[k])
                    return default

                date_val = get_val(['date', 'transaction_date', 'deal_date'], 'Recent')
                symbol_val = get_val(['symbol', 'security_name', 'ticker'], 'N/A')
                client_val = str(row[client_col])
                action_val = get_val(['buy_sell', 'buy/sell', 'type', 'tx_type'], 'N/A')
                
                raw_qty = get_val(['quantity_traded', 'quantity', 'qty', 'shares'], '0')
                raw_price = get_val(['trade_price', 'price', 'avg_price', 'rate'], '0')

                qty_val = int(float(raw_qty.replace(',', '')))
                price_val = float(raw_price.replace(',', ''))
                
                conn.execute('''
                    INSERT INTO bulk_deals (date, symbol, client_name, buy_sell, quantity, trade_price)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (date_val, symbol_val, client_val, action_val, qty_val, price_val))
                inserted_count += 1
            except sqlite3.IntegrityError: 
                pass  # Ignore duplicate records
            except Exception as row_err:
                continue
                
        conn.commit()
        conn.close()
        return f"Success! Added {inserted_count} new whale deal records to local database."
        
    except Exception as e:
        return f"Error connecting to NSE: {str(e)}"

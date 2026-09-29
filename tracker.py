import sqlite3
import pandas as pd
from nselib import capital_market

DB_FILE = "whale_data.db"
WHALE_KEYWORDS = ["BLACKROCK", "VANGUARD", "NORGES", "GIC", "TEMASEK", "FIDELITY", "MUTUAL", "FUND", "CAPITAL", "INVESTMENT"]

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
        # Pass period='1M' to retrieve recent data reliably
        deals_df = capital_market.bulk_deal_data(period='1M')
        
        if deals_df is None or deals_df.empty: 
            return "No bulk deal records returned from NSE."
        
        # Clean column names
        deals_df.columns = [c.strip().lower().replace(" ", "_") for c in deals_df.columns]
        
        client_col = 'client_name' if 'client_name' in deals_df.columns else 'client'
        
        # Case-insensitive filtering
        pattern = "|".join(WHALE_KEYWORDS)
        whales = deals_df[deals_df[client_col].astype(str).str.contains(pattern, case=False, na=False)]
        
        if whales.empty:
            return "Fetched NSE data successfully, but no transactions matched the specified whale keywords."
            
        conn = sqlite3.connect(DB_FILE)
        inserted_count = 0
        
        for _, row in whales.iterrows():
            try:
                date_val = row.get('date', row.get('transaction_date', 'Recent'))
                symbol_val = row.get('symbol', 'N/A')
                client_val = row.get(client_col, 'Unknown')
                action_val = row.get('buy/sell', row.get('type', 'N/A'))
                qty_val = int(str(row.get('quantity_traded', row.get('quantity', 0))).replace(',', ''))
                price_val = float(str(row.get('trade_price', row.get('price', 0))).replace(',', ''))
                
                conn.execute('''
                    INSERT INTO bulk_deals (date, symbol, client_name, buy_sell, quantity, trade_price)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (date_val, symbol_val, client_val, action_val, qty_val, price_val))
                inserted_count += 1
            except sqlite3.IntegrityError: 
                pass  # Skip duplicate entries
                
        conn.commit()
        conn.close()
        return f"Success! Inserted {inserted_count} new whale deal records."
        
    except Exception as e:
        return f"Error connecting to NSE: {str(e)}"

import sqlite3
import pandas as pd
from nselib import capital_market

DB_FILE = "whale_data.db"
WHALE_KEYWORDS = ["BLACKROCK", "VANGUARD", "NORGES", "GIC", "TEMASEK", "FIDELITY"]

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
        deals_df = capital_market.bulk_deal_data()
        if deals_df is None or deals_df.empty: 
            return
        
        deals_df.columns = [c.strip().lower().replace(" ", "_") for c in deals_df.columns]
        pattern = "|".join(WHALE_KEYWORDS)
        
        whales = deals_df[deals_df['client_name'].astype(str).str.contains(pattern, case=False, na=False)]
        
        conn = sqlite3.connect(DB_FILE)
        for _, row in whales.iterrows():
            try:
                conn.execute('''
                    INSERT INTO bulk_deals (date, symbol, client_name, buy_sell, quantity, trade_price)
                    VALUES (DATE('now'), ?, ?, ?, ?, ?)
                ''', (
                    row['symbol'], 
                    row['client_name'], 
                    row.get('buy/sell', 'N/A'), 
                    row.get('quantity_traded', 0), 
                    row.get('trade_price', 0)
                ))
            except sqlite3.IntegrityError: 
                pass
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error scanning: {e}")
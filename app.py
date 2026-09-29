import sqlite3
import pandas as pd
import streamlit as st
from tracker import run_whale_scan, DB_FILE

st.set_page_config(page_title="India Whale Tracker", layout="wide")
st.title("🐋 India Institutional Whale Tracker")

if st.button("⚡ Fetch Deals"):
    with st.spinner("Fetching latest data from NSE..."):
        status_message = run_whale_scan()
    st.info(status_message)

conn = sqlite3.connect(DB_FILE)
try:
    df = pd.read_sql_query("SELECT * FROM bulk_deals ORDER BY id DESC", conn)
except Exception:
    df = pd.DataFrame()
conn.close()

if not df.empty:
    df['value_cr'] = (df['quantity'] * df['trade_price']) / 10000000
    
    col1, col2 = st.columns(2)
    col1.metric("Total Tracked Deals", len(df))
    col2.metric("Total Whale Volume", f"₹{df['value_cr'].sum():.2f} Cr")
    
    st.markdown("---")
    st.dataframe(
        df[['date', 'symbol', 'client_name', 'buy_sell', 'quantity', 'trade_price', 'value_cr']], 
        use_container_width=True
    )
else:
    st.warning("No data stored yet. Click 'Fetch Deals' above to pull recent data.")

import sqlite3
import pandas as pd
import streamlit as st
from tracker import run_whale_scan, DB_FILE

st.set_page_config(page_title="India Whale Tracker", layout="wide")
st.title("🐋 India Institutional Whale Tracker")

if st.button("⚡ Fetch Today's Deals"):
    with st.spinner("Fetching NSE Data..."):
        run_whale_scan()
    st.rerun()

conn = sqlite3.connect(DB_FILE)
try:
    df = pd.read_sql_query("SELECT * FROM bulk_deals ORDER BY id DESC", conn)
except Exception:
    df = pd.DataFrame()
conn.close()

if not df.empty:
    df['value_cr'] = (df['quantity'] * df['trade_price']) / 10000000
    st.metric("Total Whale Volume", f"₹{df['value_cr'].sum():.2f} Cr")
    st.dataframe(
        df[['date', 'symbol', 'client_name', 'buy_sell', 'quantity', 'trade_price', 'value_cr']], 
        use_container_width=True
    )
else:
    st.info("No data yet. Click 'Fetch Today's Deals' above.")
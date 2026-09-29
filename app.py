import os
import sqlite3
import pandas as pd
import streamlit as st
from tracker import run_whale_scan, get_second_order_insights, DB_FILE

st.set_page_config(page_title="India Whale Intelligence", layout="wide")
st.title("🐋 Institutional Whale Intelligence (Behavioral Analysis)")

with st.sidebar:
    st.header("Data Control")
    if st.button("⚡ Sync Live Deals from NSE", use_container_width=True):
        with st.spinner("Connecting to NSE API & parsing bulk deals..."):
            status_message = run_whale_scan()
        st.sidebar.info(status_message)
        st.rerun()

    if st.button("🗑️ Clear Local Database", use_container_width=True):
        if os.path.exists(DB_FILE):
            os.remove(DB_FILE)
            st.sidebar.success("Database cleared.")
            st.rerun()

raw_df, accumulation_df, concentration_df = get_second_order_insights()

if raw_df.empty:
    st.warning("No data currently stored. Click '⚡ Sync Live Deals from NSE' in the sidebar to fetch real market data.")
else:
    st.sidebar.markdown("---")
    st.sidebar.header("🔍 Behavior Filters")
    
    all_behaviors = sorted(list(accumulation_df['behavior_profile'].unique()))
    
    selected_behaviors = st.sidebar.multiselect(
        "Filter by Market Behavior Profile",
        options=all_behaviors,
        default=all_behaviors
    )

    col1, col2, col3, col4 = st.columns(4)
    total_val = raw_df['trade_value_cr'].sum()
    stealth_count = len(accumulation_df[accumulation_df['behavior_profile'] == "Stealth Drip Accumulation"])
    block_count = len(accumulation_df[accumulation_df['behavior_profile'].str.contains("Block Buy", na=False)])
    directional_count = len(accumulation_df[accumulation_df['behavior_profile'].str.contains("Directional", na=False)])

    col1.metric("Gross Whale Volume", f"₹{total_val:.2f} Cr")
    col2.metric("Stealth Accumulations", stealth_count)
    col3.metric("Aggressive Block Buys", block_count)
    col4.metric("Directional Bets", directional_count)

    st.markdown("---")

    tab1, tab2, tab3 = st.tabs([
        "🧠 Behavioral Matrix", 
        "🎯 Multi-Whale Clusters", 
        "📜 Raw Deals Feed"
    ])

    with tab1:
        st.subheader("Whale Behavioral Analysis")

        if selected_behaviors:
            filtered_df = accumulation_df[
                accumulation_df['behavior_profile'].isin(selected_behaviors)
            ].sort_values(by='gross_value_cr', ascending=False)
        else:
            filtered_df = accumulation_df.copy()

        if not filtered_df.empty:
            st.dataframe(
                filtered_df[[
                    'symbol', 'client_name', 'behavior_profile', 'total_buy_value_cr', 
                    'total_sell_value_cr', 'gross_value_cr', 'vwap_buy_price', 'active_days'
                ]],
                column_config={
                    "behavior_profile": st.column_config.TextColumn("Market Behavior Profile"),
                    "total_buy_value_cr": st.column_config.NumberColumn("Bought (₹ Cr)", format="₹%.4f Cr"),
                    "total_sell_value_cr": st.column_config.NumberColumn("Sold (₹ Cr)", format="₹%.4f Cr"),
                    "gross_value_cr": st.column_config.NumberColumn("Total Trade Val (₹ Cr)", format="₹%.4f Cr"),
                    "vwap_buy_price": st.column_config.NumberColumn("Buy VWAP (₹)", format="₹%.2f"),
                    "active_days": "Active Days"
                },
                use_container_width=True
            )
        else:
            st.info("No records match the selected filter options.")

    with tab2:
        st.subheader("Multi-Whale Cluster Detection")
        if not concentration_df.empty:
            st.dataframe(
                concentration_df,
                column_config={
                    "distinct_whales": "Whale Count",
                    "whale_list": "Funds Involved",
                    "total_net_value_cr": st.column_config.NumberColumn("Combined Capital (₹ Cr)", format="₹%.2f Cr")
                },
                use_container_width=True
            )

    with tab3:
        st.subheader("Raw Bulk Deals Log")
        st.dataframe(
            raw_df[['date', 'symbol', 'client_name', 'buy_sell', 'quantity', 'trade_price', 'trade_value_cr']], 
            use_container_width=True
        )

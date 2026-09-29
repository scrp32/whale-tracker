import sqlite3
import pandas as pd
import streamlit as st
from tracker import run_whale_scan, get_second_order_insights, DB_FILE

st.set_page_config(page_title="India Whale Intelligence", layout="wide")
st.title("🐋 Institutional Whale Intelligence (Behavioral Insights)")

with st.sidebar:
    st.header("Data Control")
    if st.button("⚡ Fetch Latest Deals from NSE", use_container_width=True):
        with st.spinner("Fetching and processing bulk deal logs..."):
            status_message = run_whale_scan()
        st.info(status_message)

raw_df, accumulation_df, concentration_df = get_second_order_insights()

if raw_df.empty:
    st.warning("No data stored yet. Click 'Fetch Latest Deals from NSE' in the sidebar.")
else:
    # Sidebar Filters for Behavioral Analysis
    st.sidebar.markdown("---")
    st.sidebar.header("🔍 Behavior Filters")
    
    all_behaviors = list(accumulation_df['behavior_profile'].unique())
    selected_behaviors = st.sidebar.multiselect(
        "Filter by Market Behavior",
        options=all_behaviors,
        default=[b for b in all_behaviors if b != "Arbitrage / Intra-day Churn"]
    )
    
    min_deal_value = st.sidebar.slider(
        "Min Deal Size (₹ Cr)", 
        min_value=0.0, 
        max_value=float(max(accumulation_df['total_buy_value_cr'].max(), 5.0)), 
        value=0.5, 
        step=0.5
    )

    # Metrics
    col1, col2, col3 = st.columns(3)
    total_val = raw_df['trade_value_cr'].sum()
    stealth_count = len(accumulation_df[accumulation_df['behavior_profile'] == "Stealth Drip Accumulation"])
    block_count = len(accumulation_df[accumulation_df['behavior_profile'] == "Aggressive Block Buy (>₹10 Cr)"])

    col1.metric("Gross Whale Volume", f"₹{total_val:.2f} Cr")
    col2.metric("Stealth Accumulation Signals", stealth_count)
    col3.metric("Aggressive Block Buys", block_count)

    st.markdown("---")

    tab1, tab2, tab3, tab4 = st.tabs([
        "🧠 Whale Behavior Matrix", 
        "🎯 Multi-Whale Clusters", 
        "🏷️ Institutional VWAP Floors", 
        "📜 Raw Deals Feed"
    ])

    with tab1:
        st.subheader("Whale Behavioral Analysis")
        st.caption("Classifies transactions based on execution speed, position size, and multi-day patterns.")

        # Apply Filters
        filtered_df = accumulation_df[
            (accumulation_df['behavior_profile'].isin(selected_behaviors)) &
            ((accumulation_df['total_buy_value_cr'] >= min_deal_value) | (accumulation_df['total_sell_value_cr'] >= min_deal_value))
        ].sort_values(by='total_buy_value_cr', ascending=False)

        st.dataframe(
            filtered_df[[
                'symbol', 'client_name', 'behavior_profile', 'total_buy_value_cr', 
                'total_sell_value_cr', 'net_quantity', 'vwap_buy_price', 'active_days'
            ]],
            column_config={
                "behavior_profile": st.column_config.TextColumn("Market Behavior"),
                "total_buy_value_cr": st.column_config.NumberColumn("Bought (₹ Cr)", format="₹%.2f Cr"),
                "total_sell_value_cr": st.column_config.NumberColumn("Sold (₹ Cr)", format="₹%.2f Cr"),
                "vwap_buy_price": st.column_config.NumberColumn("Buy VWAP (₹)", format="₹%.2f"),
                "net_quantity": st.column_config.NumberColumn("Net Shares", format="%d"),
                "active_days": "Active Days"
            },
            use_container_width=True
        )

    with tab2:
        st.subheader("Multi-Whale Cluster Detection")
        multi_whale_only = concentration_df[concentration_df['distinct_whales'] > 1]
        
        if not multi_whale_only.empty:
            st.dataframe(
                multi_whale_only,
                column_config={
                    "distinct_whales": "Whale Count",
                    "whale_list": "Funds Involved",
                    "total_net_value_cr": st.column_config.NumberColumn("Combined Capital (₹ Cr)", format="₹%.2f Cr")
                },
                use_container_width=True
            )
        else:
            st.info("No multi-whale cluster signals detected in the current dataset.")

    with tab3:
        st.subheader("Institutional Entry Benchmark (VWAP)")
        vwap_summary = accumulation_df[accumulation_df['net_quantity'] > 0].groupby('symbol').agg(
            weighted_avg_price=('vwap_buy_price', 'mean'),
            total_net_value=('total_buy_value_cr', 'sum'),
            whales=('client_name', lambda x: ", ".join(set(x)))
        ).reset_index().sort_values(by='total_net_value', ascending=False)
        
        st.dataframe(
            vwap_summary,
            column_config={
                "weighted_avg_price": st.column_config.NumberColumn("Institutional Benchmark VWAP", format="₹%.2f"),
                "total_net_value": st.column_config.NumberColumn("Total Investment (₹ Cr)", format="₹%.2f Cr")
            },
            use_container_width=True
        )

    with tab4:
        st.subheader("Raw Bulk Deals Dataset")
        st.dataframe(
            raw_df[['date', 'symbol', 'client_name', 'buy_sell', 'quantity', 'trade_price', 'trade_value_cr']], 
            use_container_width=True
        )

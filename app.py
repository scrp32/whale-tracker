import os
import sqlite3
import pandas as pd
import streamlit as st
from tracker import run_whale_scan, get_second_order_insights, get_whale_wisdom_analytics, DB_FILE

st.set_page_config(page_title="WhaleWisdom India | Institutional Intelligence", layout="wide")

st.title("🐋 WhaleWisdom India: Institutional Intelligence")
st.caption("Real-time position tracking, fund portfolio composition, and conviction analytics for Indian Equity Markets.")

with st.sidebar:
    st.header("⚡ Live Data Control")
    if st.button("Sync Live Deals from NSE", use_container_width=True):
        with st.spinner("Fetching latest bulk/block transactions from NSE..."):
            status_message = run_whale_scan()
        st.sidebar.info(status_message)
        st.rerun()

    if st.button("🗑️ Reset Local Database", use_container_width=True):
        if os.path.exists(DB_FILE):
            os.remove(DB_FILE)
            st.sidebar.success("Database purged.")
            st.rerun()

raw_df, accumulation_df, concentration_df = get_second_order_insights()
conviction_df, fund_portfolios_df = get_whale_wisdom_analytics()

if raw_df.empty:
    st.warning("No market data in local database. Click **Sync Live Deals from NSE** in the sidebar to populate real institutional transactions.")
else:
    # Top KPI Bar
    col1, col2, col3, col4, col5 = st.columns(5)
    total_val = raw_df['trade_value_cr'].sum()
    unique_funds = raw_df['client_name'].nunique()
    unique_tickers = raw_df['symbol'].nunique()
    multi_whale_tickers = len(concentration_df[concentration_df['distinct_whales'] > 1])
    stealth_acc = len(accumulation_df[accumulation_df['behavior_profile'] == "Stealth Drip Accumulation"])

    col1.metric("Gross Capital Flow", f"₹{total_val:.2f} Cr")
    col2.metric("Tracked Whales", unique_funds)
    col3.metric("Target Companies", unique_tickers)
    col4.metric("Consensus Clusters", multi_whale_tickers)
    col5.metric("Stealth Accumulations", stealth_acc)

    st.markdown("---")

    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "🏆 High-Conviction Bets",
        "🏢 Fund Portfolios (13F View)",
        "🧠 Behavioral Matrix", 
        "🎯 Consensus Clusters", 
        "📜 Raw Deals Feed"
    ])

    # Tab 1: WhaleWisdom Conviction Index
    with tab1:
        st.subheader("High-Conviction Institutional Buys")
        st.markdown("Positions ranked by **Whale Conviction Score** (calculated using capital size, multi-day persistence, and net position bias).")
        
        if not conviction_df.empty:
            st.dataframe(
                conviction_df[[
                    'latest_date', 'symbol', 'client_name', 'conviction_score', 
                    'behavior_profile', 'total_buy_value_cr', 'vwap_buy_price', 'active_days'
                ]],
                column_config={
                    "latest_date": "Date",
                    "symbol": "Ticker",
                    "client_name": "Institutional Whale",
                    "conviction_score": st.column_config.NumberColumn("Conviction Score", format="%.2f 🔥"),
                    "behavior_profile": "Behavior Pattern",
                    "total_buy_value_cr": st.column_config.NumberColumn("Capital (₹ Cr)", format="₹%.2f Cr"),
                    "vwap_buy_price": st.column_config.NumberColumn("Est. VWAP Entry", format="₹%.2f"),
                    "active_days": "Active Days"
                },
                use_container_width=True
            )

    # Tab 2: Fund Portfolios (WhaleWisdom Style 13F Breakdown)
    with tab2:
        st.subheader("Institutional Fund Composition")
        st.markdown("Inspect total exposure and stock selection per individual fund or Super Investor.")

        if not fund_portfolios_df.empty:
            selected_fund = st.selectbox("Select a Fund / Investor to inspect:", options=fund_portfolios_df['client_name'].unique())
            
            fund_data = fund_portfolios_df[fund_portfolios_df['client_name'] == selected_fund].iloc[0]
            fund_holdings = accumulation_df[accumulation_df['client_name'] == selected_fund]

            f_col1, f_col2, f_col3 = st.columns(3)
            f_col1.metric("Total Capital Deployed", f"₹{fund_data['total_invested_cr']:.2f} Cr")
            f_col2.metric("Total Capital Divested", f"₹{fund_data['total_divested_cr']:.2f} Cr")
            f_col3.metric("Stocks Targeted", fund_data['total_stocks'])

            st.write(f"### Current Active Positions for **{selected_fund}**")
            st.dataframe(
                fund_holdings[[
                    'latest_date', 'symbol', 'behavior_profile', 'total_buy_value_cr', 
                    'total_sell_value_cr', 'vwap_buy_price', 'active_days'
                ]],
                column_config={
                    "latest_date": "Latest Deal Date",
                    "symbol": "Ticker",
                    "behavior_profile": "Strategy",
                    "total_buy_value_cr": st.column_config.NumberColumn("Buy Exposure", format="₹%.2f Cr"),
                    "total_sell_value_cr": st.column_config.NumberColumn("Sell Exposure", format="₹%.2f Cr"),
                    "vwap_buy_price": st.column_config.NumberColumn("Avg Entry Price", format="₹%.2f"),
                    "active_days": "Days Active"
                },
                use_container_width=True
            )

    # Tab 3: Behavioral Matrix
    with tab3:
        st.subheader("Whale Behavioral Analysis")
        all_behaviors = sorted(list(accumulation_df['behavior_profile'].unique()))
        selected_behaviors = st.multiselect("Filter Profile:", options=all_behaviors, default=all_behaviors)

        filtered_df = accumulation_df[accumulation_df['behavior_profile'].isin(selected_behaviors)].sort_values(by='gross_value_cr', ascending=False) if selected_behaviors else accumulation_df.copy()

        st.dataframe(
            filtered_df[[
                'latest_date', 'symbol', 'client_name', 'behavior_profile', 'total_buy_value_cr', 
                'total_sell_value_cr', 'gross_value_cr', 'vwap_buy_price', 'active_days'
            ]],
            column_config={
                "latest_date": "Deal Date",
                "behavior_profile": "Profile",
                "total_buy_value_cr": st.column_config.NumberColumn("Bought (₹ Cr)", format="₹%.4f Cr"),
                "total_sell_value_cr": st.column_config.NumberColumn("Sold (₹ Cr)", format="₹%.4f Cr"),
                "gross_value_cr": st.column_config.NumberColumn("Gross Volume (₹ Cr)", format="₹%.4f Cr"),
                "vwap_buy_price": st.column_config.NumberColumn("Buy VWAP (₹)", format="₹%.2f"),
                "active_days": "Active Days"
            },
            use_container_width=True
        )

    # Tab 4: Multi-Whale Clusters
    with tab4:
        st.subheader("Consensus & Overlap Detection")
        st.write("Companies being bought simultaneously by **multiple distinct institutional whales**.")
        if not concentration_df.empty:
            st.dataframe(
                concentration_df,
                column_config={
                    "distinct_whales": "Whale Count",
                    "whale_list": "Funds Involved",
                    "total_net_value_cr": st.column_config.NumberColumn("Combined Value", format="₹%.2f Cr"),
                    "last_active": "Latest Date"
                },
                use_container_width=True
            )

    # Tab 5: Raw Deals Feed
    with tab5:
        st.subheader("Complete Bulk Deals Log")
        st.dataframe(
            raw_df[['date', 'symbol', 'client_name', 'buy_sell', 'quantity', 'trade_price', 'trade_value_cr']], 
            column_config={
                "date": "Transaction Date",
                "trade_value_cr": st.column_config.NumberColumn("Value (₹ Cr)", format="₹%.4f Cr")
            },
            use_container_width=True
        )

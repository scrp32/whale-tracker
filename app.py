import os
import sys

# Append root directory to sys.path so Streamlit Cloud detects custom modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import pandas as pd
import streamlit as st
from tracker import InstitutionalTracker

st.set_page_config(page_title="Institutional Alpha Tracker", layout="wide")

st.title("⚡ Institutional Alpha Signal Engine")

# Initialize Tracker Engine
tracker = InstitutionalTracker()

# Sidebar Navigation
st.sidebar.header("Navigation & Settings")
selected_view = st.sidebar.radio(
    "Select View", 
    ["Overview", "Options & Derivatives Overlay", "Dark Accumulation Scanner"]
)

# -------------------------------------------------------------
# VIEW 1: OVERVIEW & CASH MARKET SIGNALS
# -------------------------------------------------------------
if selected_view == "Overview":
    st.subheader("📊 Institutional Cash & Float Cornering Summary")
    st.markdown("""
    Monitors high-conviction cash market accumulation against tradable free float.
    """)
    
    col1, col2 = st.columns(2)
    with col1:
        st.info("💡 **Float Cornering Index (FCI)** identifies supply squeezes where whales absorb >2% of free float.")
    with col2:
        st.info("🎯 **Super Investor Engine** flags transactions from Tier-1 funds and super investors.")

# -------------------------------------------------------------
# VIEW 2: OPTIONS & DERIVATIVES OVERLAY
# -------------------------------------------------------------
elif selected_view == "Options & Derivatives Overlay":
    st.subheader("🎯 Participant-Wise Options & Derivatives Positioning")
    st.markdown("""
    Tracking FII and Proprietary Desk **Net Delta Scores** and **Put-Call Ratios (PCR)** from NSE Open Interest data.
    """)

    fetch_date = st.date_input("Select Date for Options Data", value=pd.to_datetime("today") - pd.Timedelta(days=1))
    date_str = fetch_date.strftime("%d%m%Y")

    if st.button("Fetch Options Positioning"):
        with st.spinner("Retrieving participant OI from NSE archives..."):
            options_df = tracker.get_options_overlay(date_str)
            
            if not options_df.empty:
                st.dataframe(options_df, use_container_width=True)
                
                st.markdown("### Key Derivatives Signals")
                for _, row in options_df.iterrows():
                    bias = "🔥 Bullish" if row['Net Delta Score'] > 0 else "🐻 Bearish / Hedged"
                    st.metric(
                        label=f"{row['Client Type']} Net Delta Score", 
                        value=f"{row['Net Delta Score']:,}", 
                        delta=f"PCR: {row['Index Option PCR']} ({bias})"
                    )
            else:
                st.warning("No options data available for the selected date. Ensure it was an NSE trading day.")

# -------------------------------------------------------------
# VIEW 3: DARK ACCUMULATION SCANNER
# -------------------------------------------------------------
elif selected_view == "Dark Accumulation Scanner":
    st.subheader("👁️ Dark Accumulation (Stealth Volume Absorption)")
    st.markdown("""
    Flags trading days with **3x+ average volume** where price action remains tight (**<1.5% range**), indicating institutional absorption algorithms.
    """)
    st.info("Scanner will execute automatically when daily OHLCV price quotes are fed into the tracker pipeline.")

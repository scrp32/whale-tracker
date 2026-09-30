import os
import sys

# Force root directory into sys.path for Streamlit Cloud path resolution
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import numpy as np
import pandas as pd
import streamlit as st
from tracker import InstitutionalTracker

# Page Setup
st.set_page_config(
    page_title="WhaleWisdom NSE | Institutional Alpha Engine",
    page_icon="🐋",
    layout="wide",
)

st.title("🐋 Institutional Intelligence Engine (NSE)")

# Initialize Backend Tracker
tracker = InstitutionalTracker()

# Global Multi-Tab Navigation
tab1, tab2, tab3, tab4, tab5 = st.tabs(
    [
        "📊 Cash Flow & Bulk Deals",
        "🎯 Consensus Clusters & Super Investors",
        "📈 Structural Volume Profile (POC/VAH/VAL)",
        "🎲 Participant Options & OI Overlay",
        "⚡ Squeeze & Stealth Absorption (FCI/Dark)",
    ]
)

# -------------------------------------------------------------
# TAB 1: INSTITUTIONAL CASH FLOW & BULK DEALS
# -------------------------------------------------------------
with tab1:
    st.subheader("🏦 Stealth Drip & Aggressive Block Flows")
    st.markdown(
        "Track institutional cash deployments across NSE bulk/block feeds."
    )

    col1, col2, col3 = st.columns(3)
    col1.metric("Institutional Net Flow (1D)", "₹1,420 Cr", "+18.4%")
    col2.metric("FII Net Cash Buy", "₹890 Cr", "+12.1%")
    col3.metric("DII Net Cash Buy", "₹530 Cr", "+6.3%")

    st.markdown("---")
    st.subheader("Raw Bulk / Block Deal Stream")

    # Sample structural layout for live/uploaded cash deals
    sample_deals = pd.DataFrame(
        {
            "Symbol": ["RELIANCE", "HDFCBANK", "INFY", "TATAMOTORS", "PERSISTENT"],
            "Client Name": [
                "SOOCIETE GENERALE",
                "GOLDMAN SACHS INVESTMENT",
                "NIPPON INDIA MUTUAL FUND",
                "ASHISH KACHOLIA",
                "NALANDA INDIA EQUITY FUND",
            ],
            "Deal Type": ["BUY", "BUY", "BUY", "BUY", "BUY"],
            "Quantity": [1250000, 3100000, 850000, 450000, 210000],
            "Price": [2980.50, 1640.20, 1890.00, 980.40, 4850.10],
            "Value (Cr)": [372.56, 508.46, 160.65, 44.11, 101.85],
        }
    )
    st.dataframe(sample_deals, use_container_width=True)

# -------------------------------------------------------------
# TAB 2: CONSENSUS CLUSTERS & SUPER INVESTORS
# -------------------------------------------------------------
with tab2:
    st.subheader("🎯 Tier-1 Super Investor Co-Investment Engine")
    st.markdown(
        "Filters institutional deal feeds specifically for high-alpha Indian Super Investors."
    )

    super_inv_df = tracker.filter_super_investors(
        pd.DataFrame(
            {
                "investor_name": [
                    "ASHISH KACHOLIA",
                    "NALANDA INDIA EQUITY FUND",
                    "RADHAKISHAN DAMANI",
                    "RETAIL TRADER",
                ],
                "symbol": ["TATAMOTORS", "PERSISTENT", "VGUARD", "XYZ"],
                "quantity": [450000, 210000, 1000000, 5000],
                "price": [980.40, 4850.10, 420.00, 50.00],
            }
        )
    )

    if not super_inv_df.empty:
        st.success("🔥 High-Conviction Super Investor Entries Detected!")
        st.dataframe(super_inv_df, use_container_width=True)
    else:
        st.info("No Tier-1 Super Investor activity detected in recent feed.")

# -------------------------------------------------------------
# TAB 3: VOLUME PROFILE (POC / VAH / VAL)
# -------------------------------------------------------------
with tab3:
    st.subheader("📈 Structural Volume Nodes & Liquidity Pools")
    st.markdown(
        "Identifies Point of Control (POC), Value Area High (VAH), and Value Area Low (VAL)."
    )

    col1, col2 = st.columns([1, 2])
    with col1:
        selected_symbol = st.selectbox(
            "Select Stock for Profile Node Analysis",
            ["RELIANCE", "HDFCBANK", "INFY"],
        )
        st.metric("Point of Control (POC)", "₹2,975.00")
        st.metric("Value Area High (VAH)", "₹3,010.00")
        st.metric("Value Area Low (VAL)", "₹2,940.00")
    with col2:
        st.info(
            "💡 Institutional accumulation occurs predominantly within the Value Area ($VAL \leftrightarrow VAH$). Breakthroughs beyond $VAH$ on high FCI indicate structural price discovery."
        )

# -------------------------------------------------------------
# TAB 4: PARTICIPANT OPTIONS & DERIVATIVES OVERLAY
# -------------------------------------------------------------
with tab4:
    st.subheader("🎲 FII & Proprietary Desk Options Positioning")
    st.markdown(
        "Fetches participant-wise Open Interest (OI) from NSE archives to calculate Net Delta Bias and PCR."
    )

    fetch_date = st.date_input(
        "Select Date for Options Data",
        value=pd.to_datetime("today") - pd.Timedelta(days=1),
    )
    date_str = fetch_date.strftime("%d%m%Y")

    if st.button("Fetch Options Positioning from NSE Archives"):
        with st.spinner("Retrieving participant OI from NSE..."):
            options_df = tracker.get_options_overlay(date_str)

            if not options_df.empty:
                st.dataframe(options_df, use_container_width=True)

                st.markdown("### Institutional Bias Highlights")
                for _, row in options_df.iterrows():
                    bias = (
                        "🔥 Bullish Delta"
                        if row["Net Delta Score"] > 0
                        else "🐻 Bearish / Hedged"
                    )
                    st.metric(
                        label=f"{row['Client Type']} Net Delta Score",
                        value=f"{row['Net Delta Score']:,}",
                        delta=f"PCR: {row['Index Option PCR']} ({bias})",
                    )
            else:
                st.warning(
                    "No derivatives data found for the selected date. Ensure it was a valid NSE trading day."
                )

# -------------------------------------------------------------
# TAB 5: SQUEEZE & STEALTH ABSORPTION (FCI / DARK)
# -------------------------------------------------------------
with tab5:
    st.subheader("⚡ Float Cornering Index (FCI) & Dark Accumulation")

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("#### Float Cornering Index (Squeeze Setup)")
        st.info(
            "Identifies stocks where institutional net buying has absorbed a large portion of tradable free float."
        )

    with col2:
        st.markdown("#### Dark Accumulation Scanner")
        st.info(
            "Flags stealth volume absorption: 3x+ volume spikes inside a tight daily price range (<1.5%)."
        )

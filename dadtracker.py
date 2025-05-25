import pandas as pd
import streamlit as st
from datetime import datetime
import pytz

st.set_page_config("NEPSE Portfolio Tracker", layout="wide")

# --- Configuration ---
SHEET_ID = "1wS0n3SaoUsoWkp654IRh5hUT4QXKsdkC8uamOYBDIB0"
HOLDINGS_GID = "0"
TRANSACTIONS_GID = "1347762871"

# --- Helper to build CSV URL ---
@st.cache_data(ttl=3600)
def get_csv_url(sheet_id, sheet_gid):
    return f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={sheet_gid}"

# --- Portfolio Calculation ---
def calculate_portfolio(holdings, transactions):
    numeric_cols = ['Quantity', 'Avg Buy Price', 'Last Traded Price', 'Prev Close Price']
    for col in numeric_cols:
        holdings[col] = pd.to_numeric(holdings[col], errors='coerce').fillna(0)
    
    holdings = holdings[holdings['Quantity'] > 0]
    
    holdings['Current Value'] = holdings['Quantity'] * holdings['Last Traded Price']
    holdings['Invested Amount'] = holdings['Quantity'] * holdings['Avg Buy Price']
    holdings['Unrealised P&L'] = holdings['Current Value'] - holdings['Invested Amount']
    holdings['Daily P&L'] = (holdings['Last Traded Price'] - holdings['Prev Close Price']) * holdings['Quantity']
    holdings['P&L %'] = (holdings['Unrealised P&L'] / holdings['Invested Amount']) * 100

    realised_pnl = 0
    try:
        transactions['Quantity'] = pd.to_numeric(transactions['Quantity'], errors='coerce')
        transactions['Price'] = pd.to_numeric(transactions['Price'], errors='coerce')
        transactions['Date'] = pd.to_datetime(transactions['Date'], errors='coerce')
        
        buy_data = transactions[transactions['Type'].str.lower() == 'buy']
        sell_data = transactions[transactions['Type'].str.lower() == 'sell']
        
        for _, row in sell_data.iterrows():
            symbol = row['Symbol']
            qty = row['Quantity']
            price = row['Price']
            avg_buy = buy_data[buy_data['Symbol'] == symbol]['Price'].mean()
            if not pd.isna(avg_buy):
                realised_pnl += (price - avg_buy) * qty
    except Exception as e:
        st.warning(f"Couldn't calculate realized P&L: {str(e)}")
    
    return holdings, realised_pnl

# --- Style DataFrames ---
def style_dataframe(df):
    if 'Unrealised P&L' in df.columns:
        df = df.style.applymap(
            lambda x: 'color: green' if x > 0 else 'color: red',
            subset=['Unrealised P&L', 'Daily P&L', 'P&L %']
        ).format({
            'Current Value': 'Rs {:,.2f}',
            'Invested Amount': 'Rs {:,.2f}',
            'Unrealised P&L': 'Rs {:,.2f}',
            'Daily P&L': 'Rs {:,.2f}',
            'P&L %': '{:.2f}%',
            'Avg Buy Price': 'Rs {:,.2f}',
            'Last Traded Price': 'Rs {:,.2f}',
            'Prev Close Price': 'Rs {:,.2f}'
        }, na_rep="-")
    return df

# --- Main App ---
def main():
    st.title("📈 NEPSE Portfolio Tracker")
    
    with st.expander("ℹ️ About this app"):
        st.markdown("""
        This app automatically tracks your NEPSE portfolio using data from a public Google Sheet.
        
        **Features:**
        - Real-time portfolio valuation
        - Unrealized and realized P&L tracking
        - Daily performance monitoring
        """)

    try:
        with st.spinner("Loading data from Google Sheets..."):
            holdings_url = get_csv_url(SHEET_ID, HOLDINGS_GID)
            transactions_url = get_csv_url(SHEET_ID, TRANSACTIONS_GID)

            holdings = pd.read_csv(holdings_url)
            transactions = pd.read_csv(transactions_url)

            required_holding_cols = ['Symbol', 'Quantity', 'Avg Buy Price', 'Last Traded Price', 'Prev Close Price']
            if not all(col in holdings.columns for col in required_holding_cols):
                st.error(f"Holdings sheet missing required columns. Needed: {', '.join(required_holding_cols)}")
                return

            holdings, realised_pnl = calculate_portfolio(holdings, transactions)

        st.success("✅ Data loaded successfully!")
        
        total_value = holdings['Current Value'].sum()
        total_invested = holdings['Invested Amount'].sum()
        total_unrealised = holdings['Unrealised P&L'].sum()
        total_daily_pnl = holdings['Daily P&L'].sum()
        overall_return_pct = (total_unrealised / total_invested * 100) if total_invested > 0 else 0

        col1, col2, col3, col4, col5 = st.columns(5)
        col1.metric("Total Value", f"Rs {total_value:,.2f}")
        col2.metric("Invested", f"Rs {total_invested:,.2f}")
        col3.metric("Unrealised P&L", f"Rs {total_unrealised:,.2f}", f"{overall_return_pct:.2f}%")
        col4.metric("Realised P&L", f"Rs {realised_pnl:,.2f}")
        col5.metric("Daily P&L", f"Rs {total_daily_pnl:,.2f}")

        tab1, tab2 = st.tabs(["💼 Holdings", "🧾 Transactions"])

        with tab1:
            st.subheader("💼 Holdings")
            st.dataframe(style_dataframe(holdings), use_container_width=True)

        with tab2:
            st.subheader("🧾 Transactions")
            st.dataframe(transactions.sort_values('Date', ascending=False), use_container_width=True)

        st.divider()
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("Clear Cache"):
                st.cache_data.clear()
                st.rerun()

    except Exception as e:
        st.error(f"❌ Error loading data: {str(e)}")
        st.error("Please check your Google Sheet configuration and ensure it's publicly accessible.")
    
if __name__ == "__main__":
    main()

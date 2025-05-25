import pandas as pd
import streamlit as st
from datetime import datetime
import pytz

st.set_page_config("NEPSE Portfolio Tracker", layout="wide")

# --- Configuration ---
SHEET_ID = "1wS0n3SaoUsoWkp654IRh5hUT4QXKsdkC8uamOYBDIB0"
HOLDINGS_GID = "0"
TRANSACTIONS_GID = "1347762871"
LAST_UPDATED_GID = "1293420892"


# --- Helper to build CSV URL ---
@st.cache_data(ttl=3600)
def get_csv_url(sheet_id, sheet_gid):
    return f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={sheet_gid}"

def get_last_updated(sheet_id, gid):
    url = get_csv_url(sheet_id, gid)
    try:
        df = pd.read_csv(url, header=None)
        return df.iloc[0, 0] if not df.empty else "N/A"
    except Exception as e:
        return f"Error fetching update time: {str(e)}"

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
            'Quantity': '{:,.0f}',
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
    
    lang = st.selectbox("🌐 Select Language / भाषा छान्नुहोस्", ["English", "नेपाली"])

    st.title("📈 NEPSE Portfolio Tracker")

    st.markdown("### 📘 Prem Prakash Shrestha Portfolio (Since 2016-09-08)")

    last_updated = get_last_updated(SHEET_ID, LAST_UPDATED_GID)
    st.markdown(f"##### 🕒 Last Updated: `{last_updated}`")

    
    with st.expander("ℹ️ About this app"):
        if lang == "English":
            st.markdown("""
            This app automatically tracks your NEPSE portfolio using data from a public Google Sheet.

            ### 🚀 Key Features
            - 📊 **Portfolio Valuation** is powered by live market data that auto-refreshes via Google Sheets.  
            ✅ After the market closes, Google Sheets imports the final **close prices**, enabling **accurate calculation of your portfolio**.  
            🔔 For reference, you can also visit [NEPSE Today’s Price](https://nepalstock.com.np/today-price) after **3:25 P.M.** to view official closing prices.

            - 💹 **Unrealized and Realized Profit & Loss** calculations
            - 📅 **Daily P&L Tracking** to monitor short-term gains/losses
            - 🔄 **Auto-refresh support** with one-click cache clearing
            - 📈 **Dynamic and color-coded performance visualization**
            - 🕵️‍♂️ **Transaction history** with buy/sell breakdown

            ### 📌 How It Works
            - Data is fetched from your linked Google Sheet
            - Automatically calculates key performance metrics
            - Presents a clean and interactive dashboard using Streamlit

            ---  
            Developed with ❤️
            """)
        else:
            st.markdown("""
            यो एपले तपाईको NEPSE पोर्टफोलियोलाई सार्वजनिक Google Sheet बाट स्वतः ट्र्याक गर्छ।

            ### 🚀 प्रमुख विशेषताहरू
            - 📊 **पोर्टफोलियो मूल्याङ्कन** लाई Google Sheets को माध्यमबाट आउने प्रत्यक्ष बजार मूल्यले शक्ति दिन्छ।  
            ✅ बजार बन्द भएपछि Google Sheets मा अन्तिम **closing price** ल्याइन्छ जसले गर्दा तपाईको पोर्टफोलियोको **सटीक गणना** सम्भव हुन्छ।  
            🔔 अधिक जानकारीको लागि [NEPSE Today’s Price](https://nepalstock.com.np/today-price) मा **३:२५ बजे पछि** हेर्न सक्नुहुन्छ।

            - 💹 **Unrealized र Realized नाफा/नोक्सानी** को गणना
            - 📅 **दैनिक P&L ट्र्याकिङ** — छोटो अवधिको नाफा/नोक्सानी हेर्न
            - 📈 **रंग अनुसार प्रदर्शन देखाउने तालिका**
            - 🕵️‍♂️ **Buy/Sell लेनदेन हिसाब गर्ने लेनदेन इतिहास**

            ### 📌 यो कसरी काम गर्छ?
            - तपाईको Google Sheet बाट डेटा लिइन्छ
            - मुख्य वित्तीय गणनाहरू स्वचालित रूपमा गरिन्छ
            - Streamlit प्रयोग गरेर सफा र अन्तरक्रियात्मक ड्यासबोर्ड देखाइन्छ

            ---  
            ❤️ बाट निर्माण गरिएको
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

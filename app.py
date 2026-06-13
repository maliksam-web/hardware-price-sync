import streamlit as st
import pandas as pd

st.set_page_config(page_title="Hafiz Hardware Lookup", page_icon="🔍", layout="centered")

st.title("🔍 Hafiz Hardware")
st.subheader("Live Salesman Price Desk")

@st.cache_data(ttl=600) # Caches records for speed optimization
def load_synced_data():
    try:
        return pd.read_excel("salesman_prices.xlsx")
    except Exception:
        st.error("Pricing database synchronization in progress. Try again in 1 minute.")
        return pd.DataFrame()

df = load_synced_data()

if not df.empty:
    search_keyword = st.text_input("Type product keyword below:", placeholder="e.g., pipe, watti, bolt...", autocomplete="off")
    
    if search_keyword:
        # Scan data records 
        # Match column names ('Item Name') with your generated spreadsheet headers
        results = df[df["Item Name"].str.contains(search_keyword, case=False, na=False)]
        
        if not results.empty:
            st.dataframe(
                results,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Retail Price": st.column_config.NumberColumn("Selling Price", format="Rs. %d")
                }
            )
        else:
            st.warning("No matched inventory found.")
    else:
        st.info("💡 Input a search term to display the current retail rate.")
        

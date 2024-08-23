import streamlit as st
import pandas as pd
import numpy as np
from vnstock3 import *
import datetime as dt


st.title("Stock Data Viewer")


exchange = st.selectbox("Choose Exchange", options=["HSX", "HNX", "UPCOM"])

if exchange == "HSX":
    stock = Vnstock().stock()
    all_companies = stock.listing.symbols_by_exchange()
    hose_companies = all_companies[(all_companies['exchange'] == 'HSX') & (all_companies['type'] == 'STOCK')]
    hose_companies.index = range(1, len(hose_companies) + 1)
    # hnx_companies = all_companies[all_companies['comGroupCode'] == 'HNX']
    # upcom_companies = all_companies[all_companies['comGroupCode'] == 'UPCOM']

    hose_list = hose_companies['symbol'].to_list()
    data = pd.DataFrame(hose_list)
    st.write("Các mã chứng khoán thuộc sàn ", exchange)
    st.write(hose_companies)
    ticker_list = hose_list
    # Lựa chọn mã chứng khoán từ danh sách
    ticker_input = st.selectbox("Select Stock Ticker", options=ticker_list)
    # Nhập giá khuyến nghị
    recommended_price = st.number_input("Enter Recommended Price", min_value=0.0, step=0.01)
    def get_stock_data(ticker):
        stock = Vnstock().stock(symbol=ticker, source='VCI')
        today = dt.date.today().strftime('%Y-%m-%d')
        try:
            his = stock.quote.history(start=today, end=today)
            if not his.empty:
                return his['high'].values[0]
            else:
                return np.nan
        except IndexError:
            return np.nan
    highest_price = get_stock_data(ticker_input)
    profit = highest_price - recommended_price if not np.isnan(highest_price) else np.nan  
    if 'table_data' not in st.session_state:
        st.session_state.table_data = pd.DataFrame(columns=['Ticker', 'Recommend Price', 'Highest Price', 'Profit'])
    if st.button('Add to table'):
        new_row = pd.DataFrame({
        'Ticker': [ticker_input],
        'Recommend Price': [recommended_price],
        'Highest Price': [highest_price],
        'Profit': [profit]
    })
        new_row['Profit'] = new_row['Profit'].round(2).astype(str) + '%'
        new_row['Recommend Price'] = new_row['Recommend Price'].astype(str)
        new_row['Highest Price'] = new_row['Highest Price'].astype(str)
        st.session_state.table_data = pd.concat([st.session_state.table_data, new_row], ignore_index=True)
    st.write(st.session_state.table_data)
import streamlit as st
import pandas as pd
import numpy as np
from vnstock3 import Vnstock
import datetime as dt

st.title("Stock Data Viewer")

# Hàm lấy dữ liệu chứng khoán từ API và cache kết quả
@st.cache_data
def get_all_companies(exchange):
    stock = Vnstock().stock()
    all_companies = stock.listing.symbols_by_exchange()
    if exchange == "HSX":
        filtered_companies = all_companies[(all_companies['exchange'] == 'HSX') & (all_companies['type'] == 'STOCK')]
    elif exchange == "HNX":
        filtered_companies = all_companies[(all_companies['exchange'] == 'HNX') & (all_companies['type'] == 'STOCK')]
    else:  # UPCOM
        filtered_companies = all_companies[(all_companies['exchange'] == 'UPCOM') & (all_companies['type'] == 'STOCK')]
    filtered_companies.index = range(1, len(filtered_companies) + 1)
    return filtered_companies

# Hàm lấy giá cao nhất của chứng khoán và cache kết quả
@st.cache_data
def get_highest_price(ticker):
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

# Chọn sàn giao dịch
exchange = st.selectbox("Choose Exchange", options=["HSX", "HNX", "UPCOM"])

# Xác định nếu sàn giao dịch đã thay đổi, cần phải làm mới bảng dữ liệu
if 'current_exchange' not in st.session_state:
    st.session_state.current_exchange = exchange

if st.session_state.current_exchange != exchange:
    st.session_state.current_exchange = exchange
    st.session_state.table_data = pd.DataFrame(columns=['Ticker', 'Recommend Price', 'Highest Price', 'Profit'])

# Lấy dữ liệu chứng khoán cho sàn giao dịch hiện tại
companies = get_all_companies(exchange)

# Hiển thị các mã chứng khoán
st.write(f"Companies listed on {exchange}:")
st.write(companies)

# Chọn mã chứng khoán và nhập giá khuyến nghị
ticker_list = companies['symbol'].to_list()
ticker_input = st.selectbox("Select Stock Ticker", options=ticker_list)
recommended_price = st.number_input("Enter Recommended Price", min_value=0.0, step=0.01)

# Tính toán giá cao nhất và lợi nhuận
highest_price = get_highest_price(ticker_input)
profit = highest_price - recommended_price if not np.isnan(highest_price) else np.nan  

# Lưu dữ liệu vào bảng và hiển thị
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

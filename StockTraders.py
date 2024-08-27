import streamlit as st
import pandas as pd
import numpy as np
import pyodbc
import datetime as dt
from vnstock3 import Vnstock

# Thiết lập kết nối với SQL Server
def get_connection():
    try:
        conn_str = (
            r'DRIVER={ODBC Driver 17 for SQL Server};'
            r'SERVER=MEO;'  # Thay đổi thành tên máy chủ của bạn
            r'DATABASE=Stock;'  # Thay đổi thành tên cơ sở dữ liệu của bạn
            r'Trusted_Connection=yes;'
        )
        conn = pyodbc.connect(conn_str)
        #st.success("Kết nối SQL Server thành công!")
        return conn
    except pyodbc.Error as e:
        st.error(f"Có lỗi xảy ra khi kết nối SQL Server: {e}")
        return None

def save_to_sql(df, table_name):
    try:
        conn = get_connection()
        if conn is None:
            st.error("Không thể kết nối đến SQL Server.")
            return
        
        # Tạo cột kết hợp trong DataFrame
        df['concat_columns'] = df['Mã chứng khoán'].astype(str) + df['Giá vốn'].astype(str) + df['Giá cao nhất'].astype(str)

        # Đọc dữ liệu hiện tại từ bảng SQL để kiểm tra dữ liệu trùng lặp
        existing_data_query = f"SELECT MaChungKhoan, GiaVon, GiaCaoNhat FROM StockData WHERE TenBang = ?"
        existing_data = pd.read_sql(existing_data_query, conn, params=(table_name,))
        existing_data['concat_columns'] = existing_data['MaChungKhoan'].astype(str) + existing_data['GiaVon'].astype(str) + existing_data['GiaCaoNhat'].astype(str)

        # Lọc ra các hàng mới chưa tồn tại trong bảng SQL
        new_rows = df[~df['concat_columns'].isin(existing_data['concat_columns'])]

        cursor = conn.cursor()
        
        # Chỉ lưu những hàng chưa tồn tại trong bảng
        if not new_rows.empty:
            for index, row in new_rows.iterrows():
                cursor.execute("""
                    INSERT INTO StockData (Date, TenBang, MaChungKhoan, GiaVon, GiaCaoNhat, LoiNhuan)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (dt.datetime.now(), table_name, row['Mã chứng khoán'], 
                      row['Giá vốn'], row['Giá cao nhất'], row['Lợi nhuận']))
            conn.commit()  # Thực hiện cam kết tất cả các thay đổi
            st.toast(f"Dữ liệu đã được lưu vào bảng {table_name} trong SQL Server.")
        else:
            st.info("Không có dữ liệu mới để lưu vào bảng.")
        
        cursor.close()
        conn.close()
    except Exception as e:
        st.error(f"Có lỗi xảy ra khi lưu dữ liệu: {e}")


def load_from_sql(table_name):
    try:
        conn = get_connection()
        query = "SELECT * FROM StockData WHERE TenBang = ?"
        df = pd.read_sql(query, conn, params=(table_name,))
        conn.close()
        return df
    except Exception as e:
        st.error(f"Có lỗi xảy ra khi tải dữ liệu: {e}")
        return pd.DataFrame()

# Tạo giao diện ứng dụng Streamlit
st.title("Stock Data Viewer")

# Chọn chức năng trong sidebar
with st.sidebar:
    function = st.selectbox("Chọn chức năng", options=["Thêm thông tin chứng khoán", "Chỉnh sửa thông tin chứng khoán"])

# Khởi tạo `st.session_state.table_data` nếu chưa có
if 'table_data' not in st.session_state:
    st.session_state.table_data = pd.DataFrame(columns=['Mã chứng khoán', 'Giá vốn', 'Giá cao nhất', 'Lợi nhuận'])

if function == "Thêm thông tin chứng khoán":
    # Chọn sàn giao dịch
    exchange = st.selectbox("Chọn sàn giao dịch", options=["HSX", "HNX", "UPCOM"])

    # Khởi tạo dữ liệu nếu cần
    if 'current_exchange' not in st.session_state:
        st.session_state.current_exchange = exchange

    if st.session_state.current_exchange != exchange:
        st.session_state.current_exchange = exchange
        st.session_state.table_data = pd.DataFrame(columns=['Mã chứng khoán', 'Giá vốn', 'Giá cao nhất', 'Lợi nhuận'])

    # Lấy dữ liệu chứng khoán
    @st.cache_data
    def get_all_companies(exchange):
        stock = Vnstock().stock()
        all_companies = stock.listing.symbols_by_exchange()
        if exchange == "HSX":
            filtered_companies = all_companies[(all_companies['exchange'] == 'HSX') & (all_companies['type'] == 'STOCK')]
        elif exchange == "HNX":
            filtered_companies = all_companies[(all_companies['exchange'] == 'HNX') & (all_companies['type'] == 'STOCK')]
        else: 
            filtered_companies = all_companies[(all_companies['exchange'] == 'UPCOM') & (all_companies['type'] == 'STOCK')]

        filtered_companies = filtered_companies.sort_values(by='symbol', ascending=True).reset_index(drop=True)
        filtered_companies.index = range(1, len(filtered_companies) + 1)
        filtered_companies = filtered_companies.drop(columns='type')
        filtered_companies = filtered_companies.rename(columns={
            'symbol': 'Mã chứng khoán', 
            'id': 'ID', 
            'exchange': 'Sàn', 
            'en_organ_name': 'Tên tiếng anh', 
            'en_organ_short_name': 'Tên viết tắt tiếng anh', 
            'organ_short_name': 'Tên viết tắt tiếng việt', 
            'organ_name': 'Tên tiếng việt'})
        return filtered_companies

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

    companies = get_all_companies(exchange)
    st.write(f"Danh sách các mã chứng khoán của sàn {exchange}:")
    st.write(companies)

    ticker_list = companies['Mã chứng khoán'].to_list()
    ticker_input = st.selectbox("Chọn mã chứng khoán", options=ticker_list)
    recommended_price = st.number_input("Nhập giá vốn", min_value=0.0, step=0.01)

    highest_price = get_highest_price(ticker_input)
    profit = ((highest_price - recommended_price)/recommended_price) if not np.isnan(highest_price) else np.nan  

    if st.button('Thêm vào bảng'):
        new_row = pd.DataFrame({
            'Mã chứng khoán': [ticker_input],
            'Giá vốn': [recommended_price],
            'Giá cao nhất': [highest_price],
            'Lợi nhuận': [profit]
        })
        new_row['Ngày'] = dt.date.today().strftime('%Y-%m-%d')
        #new_row['Tên bảng'] = [recommended_price]
        new_row['Lợi nhuận'] = new_row['Lợi nhuận'].apply(lambda x: f"{x:.2f}%" if not np.isnan(x) else np.nan)
        new_row['Giá vốn'] = new_row['Giá vốn'].astype(str)
        new_row['Giá cao nhất'] = new_row['Giá cao nhất'].astype(str)
        st.session_state.table_data = pd.concat([st.session_state.table_data, new_row], ignore_index=True)

    st.write(st.session_state.table_data)
    
    table_name = st.text_input("Nhập tên bảng để lưu")
    if table_name:
        if st.button("Lưu"):
            save_to_sql(st.session_state.table_data, table_name)

elif function == "Chỉnh sửa thông tin chứng khoán":
    # Lấy danh sách các bảng đã lưu
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT TenBang FROM StockData")
        tables = [row[0] for row in cursor.fetchall()]
        cursor.close()
        conn.close()
    except Exception as e:
        st.error(f"Có lỗi xảy ra khi tải danh sách bảng: {e}")
        tables = []

    # Chọn bảng để chỉnh sửa
    table_name = st.selectbox("Chọn bảng để chỉnh sửa", options=tables)

    if table_name:
        df = load_from_sql(table_name)
        st.write(f"Dữ liệu hiện tại trong bảng {table_name}:")
        st.write(df)
    exchange = st.selectbox("Chọn sàn giao dịch", options=["HSX", "HNX", "UPCOM"])

    # Khởi tạo dữ liệu nếu cần
    if 'current_exchange' not in st.session_state:
        st.session_state.current_exchange = exchange

    if st.session_state.current_exchange != exchange:
        st.session_state.current_exchange = exchange
        st.session_state.table_data = pd.DataFrame(columns=['Mã chứng khoán', 'Giá vốn', 'Giá cao nhất', 'Lợi nhuận'])

    # Lấy dữ liệu chứng khoán
    @st.cache_data
    def get_all_companies(exchange):
        stock = Vnstock().stock()
        all_companies = stock.listing.symbols_by_exchange()
        if exchange == "HSX":
            filtered_companies = all_companies[(all_companies['exchange'] == 'HSX') & (all_companies['type'] == 'STOCK')]
        elif exchange == "HNX":
            filtered_companies = all_companies[(all_companies['exchange'] == 'HNX') & (all_companies['type'] == 'STOCK')]
        else: 
            filtered_companies = all_companies[(all_companies['exchange'] == 'UPCOM') & (all_companies['type'] == 'STOCK')]

        filtered_companies = filtered_companies.sort_values(by='symbol', ascending=True).reset_index(drop=True)
        filtered_companies.index = range(1, len(filtered_companies) + 1)
        filtered_companies = filtered_companies.drop(columns='type')
        filtered_companies = filtered_companies.rename(columns={
            'symbol': 'Mã chứng khoán', 
            'id': 'ID', 
            'exchange': 'Sàn', 
            'en_organ_name': 'Tên tiếng anh', 
            'en_organ_short_name': 'Tên viết tắt tiếng anh', 
            'organ_short_name': 'Tên viết tắt tiếng việt', 
            'organ_name': 'Tên tiếng việt'})
        return filtered_companies

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

    companies = get_all_companies(exchange)
    st.write(f"Danh sách các mã chứng khoán của sàn {exchange}:")
    st.write(companies)

    ticker_list = companies['Mã chứng khoán'].to_list()
    ticker_input = st.selectbox("Chọn mã chứng khoán", options=ticker_list)
    recommended_price = st.number_input("Nhập giá vốn", min_value=0.0, step=0.01)

    highest_price = get_highest_price(ticker_input)
    profit = ((highest_price - recommended_price)/recommended_price) if not np.isnan(highest_price) else np.nan  

    if st.button('Thêm vào bảng'):
        new_row = pd.DataFrame({
            'Mã chứng khoán': [ticker_input],
            'Giá vốn': [recommended_price],
            'Giá cao nhất': [highest_price],
            'Lợi nhuận': [profit]
        })
        new_row['Ngày'] = dt.date.today().strftime('%Y-%m-%d')
        #new_row['Tên bảng'] = [recommended_price]
        new_row['Lợi nhuận'] = new_row['Lợi nhuận'].apply(lambda x: f"{x:.2f}%" if not np.isnan(x) else np.nan)
        new_row['Giá vốn'] = new_row['Giá vốn'].astype(str)
        new_row['Giá cao nhất'] = new_row['Giá cao nhất'].astype(str)
        st.session_state.table_data = pd.concat([st.session_state.table_data, new_row], ignore_index=True)

    st.write(st.session_state.table_data)

    
    if st.button('Lưu thay đổi'):
        save_to_sql(st.session_state.table_data, table_name)
        st.success(f"Thay đổi đã được lưu vào bảng {table_name}.")

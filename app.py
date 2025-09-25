import streamlit as st
import pandas as pd
import plotly.express as px
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import time

# Page config
st.set_page_config(
    page_title="📊 Dashboard Real-time",
    page_icon="📊",
    layout="wide"
)

# Fungsi koneksi Google Sheets (menggunakan free tier)
@st.cache_resource
def connect_to_gsheet():
    """Koneksi ke Google Sheets menggunakan service account"""
    try:
        # Menggunakan credentials dari Streamlit secrets
        credentials = Credentials.from_service_account_info(
            st.secrets["gcp_service_account"],
            scopes=[
                "https://www.googleapis.com/auth/spreadsheets.readonly",
                "https://www.googleapis.com/auth/drive.readonly"
            ]
        )
        client = gspread.authorize(credentials)
        return client
    except Exception as e:
        st.error(f"Error koneksi: {e}")
        return None

# Fungsi load data dengan caching (efisien untuk free tier)
@st.cache_data(ttl=300)  # Cache 5 menit (sesuai free tier limits)
def load_data(sheet_url, sheet_name="Sheet1"):
    """Load data dari Google Sheets dengan caching"""
    try:
        client = connect_to_gsheet()
        if not client:
            return None
            
        # Buka sheet by URL
        sheet = client.open_by_url(sheet_url)
        worksheet = sheet.worksheet(sheet_name)
        
        # Ambil data
        data = worksheet.get_all_records()
        df = pd.DataFrame(data)
        
        # Auto convert types
        for col in df.columns:
            # Convert numeric
            if df[col].dtype == 'object':
                df[col] = pd.to_numeric(df[col], errors='ignore')
            
            # Convert dates (simple detection)
            if 'tanggal' in col.lower() or 'date' in col.lower():
                df[col] = pd.to_datetime(df[col], errors='ignore')
        
        return df
        
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return None

# Header
st.title("📊 Dashboard Real-time")
st.markdown("*Terhubung dengan Google Sheets via API (Free Tier)*")

# Sidebar config
with st.sidebar:
    st.header("⚙️ Konfigurasi")
    
    # Input sheet URL
    sheet_url = st.text_input(
        "URL Google Sheets:",
        placeholder="https://docs.google.com/spreadsheets/d/xxx..."
    )
    
    # Sheet name
    sheet_name = st.text_input("Nama Sheet:", value="Sheet1")
    
    # Auto refresh toggle
    auto_refresh = st.checkbox("🔄 Auto Refresh (5 menit)")
    
    # Manual refresh button
    if st.button("🔄 Refresh Sekarang"):
        st.cache_data.clear()
        st.rerun()

# Main content
if sheet_url:
    # Load data
    with st.spinner("📊 Memuat data dari Google Sheets..."):
        df = load_data(sheet_url, sheet_name)
    
    if df is not None and not df.empty:
        # Success message dengan timestamp
        current_time = datetime.now().strftime("%H:%M:%S")
        st.success(f"✅ Data berhasil dimuat! Update terakhir: {current_time}")
        
        # Quick stats
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("📋 Total Baris", len(df))
        with col2:
            st.metric("📊 Total Kolom", len(df.columns))
        with col3:
            numeric_cols = df.select_dtypes(include=['number']).columns
            st.metric("🔢 Kolom Numerik", len(numeric_cols))
        with col4:
            st.metric("📅 Data Terakhir", df.index[-1] + 1)
        
        # Tabs untuk organize content
        tab1, tab2, tab3 = st.tabs(["📋 Data", "📈 Charts", "📊 Analytics"])
        
        with tab1:
            st.subheader("📋 Data Terbaru")
            
            # Filter jumlah baris
            rows_to_show = st.slider("Tampilkan baris:", 5, 50, 20)
            
            # Show data
            st.dataframe(df.tail(rows_to_show), use_container_width=True)
            
            # Download option
            csv = df.to_csv(index=False)
            st.download_button(
                "📥 Download CSV",
                csv,
                f"data_{datetime.now().strftime('%Y%m%d')}.csv",
                "text/csv"
            )
        
        with tab2:
            st.subheader("📈 Visualisasi Real-time")
            
            # Detect columns
            numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
            text_cols = df.select_dtypes(include=['object']).columns.tolist()
            
            if numeric_cols:
                col1, col2 = st.columns(2)
                
                with col1:
                    # Line chart untuk trend
                    if len(numeric_cols) > 0:
                        y_col = st.selectbox("📈 Pilih data untuk Line Chart:", numeric_cols)
                        fig = px.line(df.reset_index(), y=y_col, 
                                    title=f"Trend {y_col}", markers=True)
                        st.plotly_chart(fig, use_container_width=True)
                
                with col2:
                    # Bar chart
                    if text_cols and numeric_cols:
                        cat_col = st.selectbox("📊 Kategori:", text_cols)
                        val_col = st.selectbox("📈 Value:", numeric_cols)
                        
                        # Group data
                        grouped = df.groupby(cat_col)[val_col].sum().reset_index()
                        fig = px.bar(grouped, x=cat_col, y=val_col,
                                   title=f"{val_col} per {cat_col}")
                        st.plotly_chart(fig, use_container_width=True)
                
                # Full width charts
                if len(numeric_cols) >= 2:
                    st.subheader("📊 Scatter Plot")
                    x_col = st.selectbox("X-axis:", numeric_cols, key="scatter_x")
                    y_col = st.selectbox("Y-axis:", numeric_cols, index=1, key="scatter_y")
                    
                    color_col = None
                    if text_cols:
                        color_col = st.selectbox("Warna berdasarkan:", [None] + text_cols)
                    
                    fig = px.scatter(df, x=x_col, y=y_col, color=color_col,
                                   title=f"{x_col} vs {y_col}")
                    st.plotly_chart(fig, use_container_width=True)
            
            else:
                st.info("Tidak ada kolom numerik untuk visualisasi")
        
        with tab3:
            st.subheader("📊 Analytics & Insights")
            
            # Summary statistics
            if numeric_cols:
                st.subheader("🔢 Statistik Deskriptif")
                st.dataframe(df[numeric_cols].describe(), use_container_width=True)
                
                # Latest vs Previous comparison (jika ada data cukup)
                if len(df) >= 2:
                    st.subheader("📈 Perbandingan Data Terbaru")
                    
                    latest_row = df.iloc[-1]
                    prev_row = df.iloc[-2]
                    
                    cols = st.columns(len(numeric_cols))
                    for i, col in enumerate(numeric_cols):
                        with cols[i]:
                            current_val = latest_row[col]
                            prev_val = prev_row[col]
                            delta = current_val - prev_val
                            
                            st.metric(
                                label=col,
                                value=f"{current_val:,.0f}" if isinstance(current_val, (int, float)) else current_val,
                                delta=f"{delta:,.0f}" if isinstance(delta, (int, float)) else None
                            )
            
            # Data quality check
            st.subheader("🔍 Kualitas Data")
            col1, col2 = st.columns(2)
            
            with col1:
                st.write("**Missing Values:**")
                missing = df.isnull().sum()
                if missing.sum() > 0:
                    st.dataframe(missing[missing > 0])
                else:
                    st.success("✅ Tidak ada missing values")
            
            with col2:
                st.write("**Data Types:**")
                dtypes_df = pd.DataFrame({
                    'Column': df.columns,
                    'Type': df.dtypes.astype(str)
                })
                st.dataframe(dtypes_df)
        
        # Auto refresh logic (bottom of page)
        if auto_refresh:
            with st.container():
                st.info("🔄 Auto-refresh aktif. Data akan diperbarui otomatis setiap 5 menit.")
                
                # Countdown timer
                placeholder = st.empty()
                for seconds in range(300, 0, -1):  # 5 menit countdown
                    mins, secs = divmod(seconds, 60)
                    placeholder.text(f"⏱️ Refresh berikutnya dalam: {mins:02d}:{secs:02d}")
                    time.sleep(1)
                
                # Clear cache dan refresh
                st.cache_data.clear()
                st.rerun()
    
    elif df is not None:
        st.warning("📋 Sheet kosong atau tidak ada data")
    else:
        st.error("❌ Gagal memuat data. Cek URL dan permissions!")

else:
    # Welcome screen
    st.info("👈 Masukkan URL Google Sheets di sidebar untuk mulai!")
    
    st.subheader("🚀 Cara Setup:")
    with st.expander("📝 Langkah-langkah Setup", expanded=True):
        st.markdown("""
        1. **Buat Google Sheet** dengan data Anda
        2. **Setup GCP Service Account** (gratis!)
        3. **Share sheet** dengan service account email
        4. **Masukkan URL** di sidebar
        5. **Nikmati dashboard real-time** Anda! 🎉
        """)
    
    st.subheader("💡 Contoh Format Data:")
    sample_data = pd.DataFrame({
        'Tanggal': ['2024-01-01', '2024-01-02', '2024-01-03'],
        'Penjualan': [5000000, 7500000, 6200000],
        'Produk': ['Laptop', 'Mouse', 'Keyboard'],
        'Kota': ['Jakarta', 'Surabaya', 'Bandung'],
        'Sales': ['John', 'Jane', 'Bob']
    })
    st.dataframe(sample_data, use_container_width=True)

# Footer info
st.markdown("---")
st.markdown("""
**ℹ️ Info:**
- 🆓 Menggunakan **Google Sheets API Free Tier**
- 📊 **Cache 5 menit** untuk efisiensi quota
- 🔄 **Auto-refresh** opsional
- 📱 **Responsive** untuk mobile
""")

st.markdown("""
**🔧 Troubleshooting:**
- Pastikan sheet sudah di-share dengan service account
- Cek nama sheet sudah benar
- URL harus format lengkap Google Sheets
""")
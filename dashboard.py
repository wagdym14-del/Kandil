import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
import yaml
import time
import os
from datetime import datetime

# ==========================================
# 💎 CONFIGURATION & THEME ENGINE
# ==========================================
st.set_page_config(
    page_title="SOVEREIGN APEX v1.5",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# نظام التجميل الاحترافي (Advanced CSS Injection)
st.markdown("""
    <style>
    /* تحسين شكل الحاويات الرئيسية */
    .stApp { background: radial-gradient(circle, #0e1117 0%, #050505 100%); }
    [data-testid="stMetricValue"] { font-family: 'JetBrains Mono', monospace; font-weight: bold; color: #00ffcc !important; }
    .stMetric { background: rgba(255, 255, 255, 0.03); border: 1px solid rgba(0, 255, 204, 0.1); border-radius: 12px; padding: 20px; transition: 0.3s; }
    .stMetric:hover { border: 1px solid #00ffcc; box-shadow: 0px 0px 15px rgba(0, 255, 204, 0.2); }
    /* تخصيص الجداول */
    [data-testid="stTable"] { border-radius: 10px; overflow: hidden; }
    </style>
    """, unsafe_allow_html=True)

# ==========================================
# 🧠 INTELLIGENCE DATA CORE
# ==========================================
class SovereignVault:
    """إدارة مركزية للبيانات المستمدة من الأرشيف السيادي [2026-02-03]"""
    
    @staticmethod
    def get_connection():
        # استخدام نمط القراءة فقط (Read-Only) لضمان عدم تلف البيانات أثناء عمل الرادار
        db_path = "./archive/sovereign_vault.sqlite"
        if not os.path.exists(db_path):
            return None
        return sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)

    @classmethod
    @st.cache_data(ttl=1) # تحديث فائق السرعة
    def fetch_live_registry(cls):
        conn = cls.get_connection()
        if not conn: return pd.DataFrame()
        try:
            # جلب البيانات مع تصنيف المخاطر برمجياً
            query = "SELECT * FROM mm_registry ORDER BY last_active DESC"
            df = pd.read_sql(query, conn)
            if not df.empty and 'last_active' in df.columns:
                df['last_active'] = pd.to_datetime(df['last_active'], unit='s')
            return df
        finally:
            conn.close()

# ==========================================
# 🖥️ SOVEREIGN INTERFACE BUILDER
# ==========================================
def render_dashboard():
    # 1. القائمة الجانبية الاستراتيجية
    with st.sidebar:
        st.image("https://img.icons8.com/nolan/96/security-shield.png", width=80)
        st.title("Sovereign Controls")
        st.markdown("---")
        
        trust_threshold = st.select_slider(
            "Target Risk Threshold",
            options=list(range(0, 101)),
            value=(0, 100)
        )
        
        st.divider()
        st.caption(f"Last Engine Pulse: {datetime.now().strftime('%H:%M:%S')}")
        st.status("System Integrity: Secure", state="complete")

    # 2. رأس الصفحة (The Header)
    head_col1, head_col2 = st.columns([3, 1])
    with head_col1:
        st.title("🛰️ Sovereign MM Intelligence")
        st.info("Live Monitoring: Detecting Market Maker fingerprints on Solana [2026-02-03]")
    
    # 3. جلب البيانات والمعالجة
    df_raw = SovereignVault.fetch_live_registry()
    
    if df_raw.empty:
        st.warning("📡 Waiting for Radar Pulse... Ensure main.py is running.")
        return

    # تطبيق الفلترة الذكية
    df = df_raw[(df_raw['trust_index'] >= trust_threshold[0]) & (df_raw['trust_index'] <= trust_threshold[1])]

    # 4. لوحة المؤشرات (The KPI Matrix)
    m1, m2, m3, m4 = st.columns(4)
    with m1: st.metric("Unique Entities", len(df_raw))
    with m2: st.metric("Live Threats", len(df[df['trust_index'] < 30]), delta="Critical", delta_color="inverse")
    with m3: st.metric("Safety Avg", f"{int(df['trust_index'].mean())}%")
    with m4: st.metric("Signal Density", f"{len(df)} Units")

    st.markdown("---")

    # 5. منطقة التحليل البصري
    c1, c2 = st.columns([2, 1])

    with c1:
        st.subheader("🧬 Behavioral Ledger")
        st.dataframe(
            df,
            column_config={
                "wallet_address": st.column_config.TextColumn("Wallet Address (Identity)", width="large"),
                "trust_index": st.column_config.ProgressColumn("Trust Level", min_value=0, max_value=100, format="%d%%"),
                "primary_tag": "Strategy Pattern",
                "last_active": "Detection Time"
            },
            hide_index=True,
            use_container_width=True
        )

    with c2:
        st.subheader("📊 Strategy Profile")
        fig = px.pie(
            df, 
            names='primary_tag', 
            hole=0.6,
            color_discrete_sequence=px.colors.qualitative.Pastel
        )
        fig.update_layout(
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font_color="white",
            margin=dict(t=0, b=0, l=0, r=0)
        )
        st.plotly_chart(fig, use_container_width=True)

    # 6. قسم التحميل الاحترافي
    with st.expander("📥 Data Export Center"):
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button("Generate Intelligence Report (CSV)", csv, "sovereign_intel.csv", "text/csv")

if __name__ == "__main__":
    try:
        render_dashboard()
        # التحديث التلقائي الفائق
        time.sleep(1)
        st.rerun()
    except Exception as e:
        st.error(f"UI Orchestration Error: {e}")

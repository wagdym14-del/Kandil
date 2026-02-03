import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
import yaml
import time
import os
import asyncio
import threading # ضروري لتشغيل الرادار دون تجميد الواجهة
from datetime import datetime
from core.archiver import MMArchiver
from core.sniffer import PumpSniffer

# ==========================================
# 🚀 SOVEREIGN ENGINE ORCHESTRATOR
# [cite: 2026-02-03] محرك التشغيل الخلفي للسحاب
# ==========================================

def launch_radar_in_background():
    """وظيفة تشغيل الرادار والأرشفة في مسار خلفي مستقل"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    # جلب الإعدادات من الخزنة السحابية (Secrets)
    db_path = st.secrets.get("DATABASE_URL", "./archive/sovereign_vault.sqlite")
    wss_url = st.secrets.get("WSS_URL_PRIMARY")
    
    # تحضير الأنظمة بكامل قدراتها الأصلية (5 Workers)
    archiver = MMArchiver(db_path=db_path)
    sniffer = PumpSniffer(wss_url=wss_url, archiver=archiver, workers=5)
    
    # بدء العمليات التسلسلية
    loop.run_until_complete(archiver.boot_system())
    loop.run_until_complete(sniffer.start_sniffing())

# منع تكرار التشغيل (Singleton Thread)
if 'engine_started' not in st.session_state:
    thread = threading.Thread(target=launch_radar_in_background, daemon=True)
    thread.start()
    st.session_state['engine_started'] = True

# ==========================================
# 💎 CONFIGURATION & THEME ENGINE (كودك الأصلي)
# ==========================================
st.set_page_config(
    page_title="SOVEREIGN APEX v1.5",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
    <style>
    .stApp { background: radial-gradient(circle, #0e1117 0%, #050505 100%); }
    [data-testid="stMetricValue"] { font-family: 'JetBrains Mono', monospace; font-weight: bold; color: #00ffcc !important; }
    .stMetric { background: rgba(255, 255, 255, 0.03); border: 1px solid rgba(0, 255, 204, 0.1); border-radius: 12px; padding: 20px; transition: 0.3s; }
    .stMetric:hover { border: 1px solid #00ffcc; box-shadow: 0px 0px 15px rgba(0, 255, 204, 0.2); }
    [data-testid="stTable"] { border-radius: 10px; overflow: hidden; }
    </style>
    """, unsafe_allow_html=True)

# ==========================================
# 🧠 INTELLIGENCE DATA CORE
# ==========================================
class SovereignVault:
    @staticmethod
    def get_connection():
        # التعديل: استخدام المسار من Secrets لضمان التوافق
        db_path = st.secrets.get("DATABASE_URL", "./archive/sovereign_vault.sqlite")
        if not os.path.exists(db_path):
            return None
        # نمط القراءة فقط مهم جداً هنا لأن الرادار يكتب في نفس الوقت
        return sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)

    @classmethod
    @st.cache_data(ttl=1) 
    def fetch_live_registry(cls):
        conn = cls.get_connection()
        if not conn: return pd.DataFrame()
        try:
            # ملاحظة: تأكد أن اسم الجدول في قاعدة بياناتك هو mm_intel كما في archiver.py
            query = "SELECT * FROM mm_intel ORDER BY last_seen_at DESC"
            df = pd.read_sql(query, conn)
            return df
        except Exception as e:
            return pd.DataFrame()
        finally:
            conn.close()

# ==========================================
# 🖥️ SOVEREIGN INTERFACE BUILDER (منطق العرض الخاص بك)
# ==========================================
def render_dashboard():
    with st.sidebar:
        st.image("https://img.icons8.com/nolan/96/security-shield.png", width=80)
        st.title("Sovereign Controls")
        st.markdown("---")
        trust_threshold = st.select_slider("Target Risk Threshold", options=list(range(0, 101)), value=(0, 100))
        st.divider()
        st.status("System Integrity: Secure", state="complete")

    head_col1, head_col2 = st.columns([3, 1])
    with head_col1:
        st.title("🛰️ Sovereign MM Intelligence")
        st.info("Live Monitoring: Detecting Market Maker fingerprints on Solana [2026-02-03]")
    
    df_raw = SovereignVault.fetch_live_registry()
    
    if df_raw.empty:
        st.warning("📡 Radar is scanning the blockchain... Waiting for the first signal.")
        return

    # معالجة البيانات وتصفيتها
    df = df_raw[(df_raw['threat_level'] >= trust_threshold[0]) & (df_raw['threat_level'] <= trust_threshold[1])]

    m1, m2, m3, m4 = st.columns(4)
    with m1: st.metric("Unique Entities", len(df_raw))
    with m2: st.metric("High Threats", len(df[df['threat_level'] > 80]), delta="Risk", delta_color="inverse")
    with m3: st.metric("Trust Avg", f"{int(df['trust_score'].mean())}%")
    with m4: st.metric("Captured Units", f"{len(df)}")

    st.markdown("---")
    c1, c2 = st.columns([2, 1])

    with c1:
        st.subheader("🧬 Behavioral Ledger")
        st.dataframe(
            df,
            column_config={
                "wallet_id": st.column_config.TextColumn("Identity", width="large"),
                "trust_score": st.column_config.ProgressColumn("Trust Level", min_value=0, max_value=100, format="%d%%"),
                "behavior_pattern": "Pattern",
                "last_seen_at": "Last Seen"
            },
            hide_index=True,
            use_container_width=True
        )

    with c2:
        st.subheader("📊 Strategy Profile")
        fig = px.pie(df, names='behavior_pattern', hole=0.6)
        fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color="white")
        st.plotly_chart(fig, use_container_width=True)

if __name__ == "__main__":
    render_dashboard()
    time.sleep(2)
    st.rerun()

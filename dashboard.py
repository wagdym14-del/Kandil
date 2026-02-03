import streamlit as st
import pandas as pd
import sqlite3
import json
import os
import time
import threading 
from core.sniffer import PumpSniffer 
from core.archiver import SovereignArchiver

# ==========================================
# 🧠 INTELLIGENCE DATA CORE
# ==========================================
class SovereignVault:
    @staticmethod
    def get_connection():
        db_path = "./archive/vault_v1.sqlite"
        if not os.path.exists(db_path): return None
        # استخدام التوصيل المتعدد للسماح بالقراءة أثناء الكتابة
        return sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)

    @classmethod
    @st.cache_data(ttl=2) # تحديث كل ثانيتين لضمان استقرار الواجهة
    def fetch_live_registry(cls):
        conn = cls.get_connection()
        if not conn: return pd.DataFrame()
        try:
            query = "SELECT * FROM mm_intel ORDER BY last_seen_at DESC"
            df = pd.read_sql(query, conn)
            enriched_rows = []
            for _, row in df.iterrows():
                row_dict = row.to_dict()
                try:
                    meta = json.loads(row['historical_data_json'])
                    api_data = meta.get('api', {}) or {}
                    stats = meta.get('stats', {}) or {} # استخراج الإحصائيات الجديدة
                except: 
                    api_data = {}
                    stats = {}
                
                row_dict['token_icon'] = api_data.get('image_url') or api_data.get('logo')
                row_dict['token_name'] = api_data.get('name', 'Scanning...')
                row_dict['Market_Cap'] = f"${stats.get('cap', 0):,.0f}" # عرض الكاب الجديد
                row_dict['Holders'] = stats.get('holders', 0) # عرض عدد الهولدرز
                enriched_rows.append(row_dict)
            return pd.DataFrame(enriched_rows) 
        except Exception: return pd.DataFrame()
        finally: conn.close()

# --- [دالة تشغيل البوت] ---
def start_bot_engine():
    if 'engine_running' not in st.session_state:
        try:
            archiver = SovereignArchiver(db_path="./archive/vault_v1.sqlite")
            wss_url = st.secrets.get("WSS_URL", "wss://api.mainnet-beta.solana.com")
            bot = PumpSniffer(wss_url=wss_url, archiver=archiver)
            
            thread = threading.Thread(target=bot.start, daemon=True)
            thread.start()
            st.session_state['engine_running'] = True
        except Exception as e:
            st.error(f"Engine failure: {e}")

# ==========================================
# 🖥️ SOVEREIGN INTERFACE BUILDER
# ==========================================
def render_dashboard():
    st.set_page_config(page_title="SOVEREIGN APEX", page_icon="🛡️", layout="wide")
    
    start_bot_engine()

    df = SovereignVault.fetch_live_registry()
    
    # رأس الصفحة بتصميم عصري
    st.title("🛰️ Sovereign MM Intelligence")
    st.info(f"Targets meeting criteria: **MCap > $11,000** & **Holders > 70**")

    if df.empty:
        st.warning("📡 Scanning Blockchain for Elite Targets...")
        time.sleep(3)
        st.rerun()
        return

    # الإحصائيات العلوية
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Elite Bots Detected", len(df))
    m2.metric("Top Market Cap", df.iloc[0]['Market_Cap'] if not df.empty else "0")
    m3.metric("Avg Holders", int(df['Holders'].mean()) if not df.empty else 0)
    m4.metric("Radar Status", "Active", delta="Normal")

    st.markdown("---")

    # عرض الجدول الاحترافي
    st.subheader("🧬 Behavioral Ledger (Recognized Patterns)")
    st.dataframe(
        df,
        column_config={
            "token_icon": st.column_config.ImageColumn("Icon", width="small"), 
            "token_name": "Name",
            "Market_Cap": "Current Cap",
            "Holders": "👥 Holders",
            "wallet_id": "Identity (Hash)",
            "trust_score": st.column_config.ProgressColumn("Confidence", min_value=0, max_value=100, format="%d%%"),
            "behavior_pattern": "Pattern Detected",
        },
        column_order=("token_icon", "token_name", "Market_Cap", "Holders", "behavior_pattern", "trust_score", "wallet_id"),
        hide_index=True,
        use_container_width=True
    )

    # التحديث التلقائي الذكي
    time.sleep(5)
    st.rerun()

if __name__ == "__main__":
    render_dashboard()

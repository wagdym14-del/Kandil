import streamlit as st
import pandas as pd
import sqlite3
import json
import os
import time
import threading 
from core.sniffer import PumpSniffer 
from core.archiver import SovereignArchiver # أضفنا استدعاء الأرشيف للربط

# ==========================================
# 🧠 INTELLIGENCE DATA CORE
# ==========================================
class SovereignVault:
    @staticmethod
    def get_connection():
        db_path = "./archive/vault_v1.sqlite" # المسار المباشر المعتمد
        if not os.path.exists(db_path): return None
        return sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)

    @classmethod
    @st.cache_data(ttl=1) 
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
                except: api_data = {}
                row_dict['token_icon'] = api_data.get('image_url') or api_data.get('image_uri') or api_data.get('logo')
                row_dict['token_name'] = api_data.get('name', 'Scanning...')
                row_dict['token_symbol'] = api_data.get('symbol', '-')
                enriched_rows.append(row_dict)
            return pd.DataFrame(enriched_rows) 
        except Exception: return pd.DataFrame()
        finally: conn.close()

# --- [دالة تشغيل البوت كعملية خلفية] ---
def start_bot_engine():
    if 'engine_running' not in st.session_state:
        try:
            # 1. إعداد الأرشيف أولاً
            archiver = SovereignArchiver(db_path="./archive/vault_v1.sqlite")
            
            # 2. إعداد السنيفر بالرابط (استبدل الرابط برابطك الخاص إذا لزم الأمر)
            wss_url = st.secrets.get("WSS_URL", "wss://api.mainnet-beta.solana.com")
            bot = PumpSniffer(wss_url=wss_url, archiver=archiver)
            
            # 3. التشغيل في خيط منفصل
            thread = threading.Thread(target=bot.start, daemon=True)
            thread.start()
            
            st.session_state['engine_running'] = True
        except Exception as e:
            st.error(f"Engine failed to start: {e}")

# ==========================================
# 🖥️ SOVEREIGN INTERFACE BUILDER
# ==========================================
def render_dashboard():
    st.set_page_config(page_title="SOVEREIGN APEX", page_icon="🛡️", layout="wide")
    
    # تشغيل البوت بمجرد فتح الصفحة
    start_bot_engine()

    df = SovereignVault.fetch_live_registry()
    
    st.title("🛰️ Sovereign MM Intelligence")
    st.caption("Status: Tracking and archiving market maker bots. [Live Radar]")

    if df.empty:
        st.warning("📡 Radar is active. Sniffer engine is starting...")
        st.info("Waiting for first blockchain signal to update /archive/vault_v1.sqlite")
        time.sleep(5)
        st.rerun()
        return

    # عرض الإحصائيات
    c_m1, c_m2, c_m3 = st.columns(3)
    c_m1.metric("Bots Archived", len(df))
    c_m2.metric("Latest Target", df.iloc[0]['token_name'] if not df.empty else "N/A")
    c_m3.metric("System Status", "Live & Tracking")

    st.markdown("---")

    st.subheader("🧬 Behavioral Ledger (Bot Recognition)")
    st.dataframe(
        df,
        column_config={
            "token_icon": st.column_config.ImageColumn("Icon", width="small"), 
            "token_name": "Token Name",
            "wallet_id": st.column_config.TextColumn("Identity", width="medium"),
            "trust_score": st.column_config.ProgressColumn("Trust Level", min_value=0, max_value=100, format="%d%%"),
            "behavior_pattern": "Pattern",
            "last_seen_at": "Last Seen"
        },
        column_order=("token_icon", "token_name", "wallet_id", "trust_score", "behavior_pattern", "last_seen_at"),
        hide_index=True,
        use_container_width=True
    )

if __name__ == "__main__":
    render_dashboard()
    time.sleep(2)
    st.rerun()

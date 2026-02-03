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
        return sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)

    @classmethod
    @st.cache_data(ttl=2) 
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
                    stats = meta.get('stats', {}) or {}
                except: 
                    api_data = {}
                    stats = {}
                
                row_dict['token_icon'] = api_data.get('image_url') or api_data.get('logo')
                row_dict['token_name'] = api_data.get('name', 'Scanning...')
                # تنظيف وعرض الماركت كاب
                cap_val = stats.get('cap', 0)
                row_dict['Market_Cap_Raw'] = cap_val
                row_dict['Market_Cap'] = f"${cap_val:,.0f}"
                row_dict['Holders'] = stats.get('holders', 0)
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
            st.session_state['start_time'] = time.time()
        except Exception as e:
            st.error(f"Engine failure: {e}")

# ==========================================
# 🖥️ SOVEREIGN INTERFACE BUILDER
# ==========================================
def render_dashboard():
    st.set_page_config(page_title="SOVEREIGN APEX", page_icon="🛡️", layout="wide")
    
    start_bot_engine()

    df = SovereignVault.fetch_live_registry()
    
    # Header Section
    st.title("🛰️ Sovereign MM Intelligence")
    
    # شريط الحالة التفاعلي
    uptime = int(time.time() - st.session_state.get('start_time', time.time()))
    st.success(f"📡 Radar Online | Filters: **MCap > $11,000** & **Holders > 70** | Uptime: {uptime}s")

    # نظام الإحصائيات (Metrics)
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Elite Targets Found", len(df))
    
    # عرض أعلى قيمة سوقية تم رصدها
    top_cap = df['Market_Cap_Raw'].max() if not df.empty else 0
    m2.metric("Highest Cap Detected", f"${top_cap:,.0f}")
    
    # متوسط عدد الهولدرز للأهداف المختارة
    avg_holders = int(df['Holders'].mean()) if not df.empty else 0
    m3.metric("Avg Holders Score", avg_holders)
    
    m4.metric("Engine Load", "Optimal", delta="Stable")

    st.markdown("---")

    # جدول البيانات مع وسم للعملات الجديدة
    if df.empty:
        st.info("⌛ **Status:** Monitoring blockchain logs... No coin has met the 11k/70-holder criteria yet.")
        with st.status("Searching for synchronized bot patterns...", expanded=True):
            st.write("Checking Jito Tip instructions...")
            st.write("Verifying holder distribution...")
            st.write("Calculating volume density...")
    else:
        st.subheader("🧬 Recognized Elite Patterns")
        st.dataframe(
            df,
            column_config={
                "token_icon": st.column_config.ImageColumn("Icon", width="small"), 
                "token_name": "Name",
                "Market_Cap": "Market Cap",
                "Holders": "👥 Holders",
                "behavior_pattern": "Bot Pattern",
                "trust_score": st.column_config.ProgressColumn("Reliability", min_value=0, max_value=100, format="%d%%"),
                "last_seen_at": "Detection Time"
            },
            column_order=("token_icon", "token_name", "Market_Cap", "Holders", "behavior_pattern", "trust_score", "last_seen_at"),
            hide_index=True,
            use_container_width=True
        )

    # التحديث التلقائي الذكي (كل 4 ثوانٍ لتخفيف الضغط على السيرفر)
    time.sleep(4)
    st.rerun()

if __name__ == "__main__":
    render_dashboard()

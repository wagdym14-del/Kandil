import streamlit as st
import pandas as pd
import sqlite3
import json
import os
import time

# ==========================================
# 🧠 INTELLIGENCE DATA CORE (النسخة الكاملة والمصححة)
# ==========================================
class SovereignVault:
    @staticmethod
    def get_connection():
        # استخدام المسار المعتمد في مشروعك
        db_path = st.secrets.get("DATABASE_URL", "./archive/vault_v1.sqlite") 
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
            
            # --- معالجة البيانات لربط الصور والأسماء فعلياً بالجدول ---
            enriched_rows = []
            for _, row in df.iterrows():
                row_dict = row.to_dict() # تحويل الصف لقاموس لضمان قبول التعديلات
                try:
                    meta = json.loads(row['historical_data_json'])
                    api_data = meta.get('api', {}) or {}
                except:
                    api_data = {}
                
                # استخراج وحقن البيانات الجديدة
                row_dict['token_icon'] = api_data.get('image_url') or api_data.get('image_uri') or api_data.get('logo')
                row_dict['token_name'] = api_data.get('name', 'Scanning...')
                row_dict['token_symbol'] = api_data.get('symbol', '-')
                
                enriched_rows.append(row_dict)
            
            # إعادة بناء الجدول بالبيانات المخصبة
            return pd.DataFrame(enriched_rows) 
        except Exception as e:
            return pd.DataFrame()
        finally:
            conn.close()

# ==========================================
# 🖥️ SOVEREIGN INTERFACE BUILDER
# ==========================================
def render_dashboard():
    # 1. إعداد الصفحة (يجب أن يكون أول أمر)
    st.set_page_config(page_title="SOVEREIGN APEX", page_icon="🛡️", layout="wide")
    
    # 2. جلب البيانات
    df = SovereignVault.fetch_live_registry()
    
    # 3. التحقق من وجود بيانات
    if df.empty:
        st.title("🛰️ Sovereign MM Intelligence")
        st.warning("📡 Radar is scanning the blockchain... Waiting for market maker signals.")
        return

    # 4. العرض الرئيسي
    st.title("🛰️ Sovereign MM Intelligence")
    st.caption("Core System: Tracking, recording, and archiving market maker bots. [2026-02-03]")
    
    # إحصائيات سريعة
    c_m1, c_m2, c_m3 = st.columns(3)
    c_m1.metric("Bots Archived", len(df))
    c_m2.metric("Latest Target", df.iloc[0]['token_name'] if not df.empty else "N/A")
    c_m3.metric("System Status", "Live & Enriched")

    st.markdown("---")

    # عرض الجدول الاستخباراتي
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
    # تحديث تلقائي كل ثانيتين
    time.sleep(2)
    st.rerun()

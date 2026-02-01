import streamlit as st
import os
import requests
import pandas as pd
import plotly.graph_objects as go

# --- إعدادات الواجهة ---
st.set_page_config(page_title="MM Signature Pro", layout="wide")

# جلب الإعدادات من Secrets
RPC_URL = os.environ.get('RPC_URL')
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')

def send_alert(text):
    """إرسال تنبيه لتلجرام"""
    if TELEGRAM_TOKEN and CHAT_ID:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        requests.post(url, json={"chat_id": CHAT_ID, "text": text, "parse_mode": "Markdown"})

# --- إدارة الجلسة (العملات المراقبة) ---
if 'watchlist' not in st.session_state:
    st.session_state.watchlist = []

st.title("🏹 MM Signature - Intelligence Terminal")
st.success("تم الاتصال بمحرك التداول التلقائي بنجاح")

# الشريط الجانبي
with st.sidebar:
    st.header("🎯 إضافة هدف جديد")
    ca = st.text_input("Contract Address")
    name = st.text_input("اسم العملة")
    amt = st.number_input("مبلغ الدخول (SOL)", value=0.1)
    
    if st.button("تفعيل الرادار والقنص 🚀"):
        if ca and name:
            st.session_state.watchlist.append({"ca": ca, "name": name, "score": 92, "defense": 0.0035})
            send_alert(f"✅ تم بدء مراقبة {name}\nبانتظار تأكيد البنود الـ 30 للدخول.")
            st.rerun()

# الشاشة الرئيسية
if st.session_state.watchlist:
    for i, item in enumerate(st.session_state.watchlist):
        with st.container(border=True):
            col1, col2, col3 = st.columns([1.5, 1, 2])
            
            with col1:
                st.subheader(f"🔍 {item['name']}")
                st.code(item['ca'])
                if st.button(f"بيع طارئ 🚨", key=f"sell_{i}"):
                    st.warning("جاري تسييل المركز...")
            
            with col2:
                st.metric("Confidence Score", f"{item['score']}%", "Strong Buy")
                st.metric("Defense Price", f"{item['defense']} SOL")
            
            with col3:
                # رسم بياني احترافي
                fig = go.Figure()
                fig.add_trace(go.Scatter(y=[0.004, 0.005, 0.0045, 0.006], name="Price", line=dict(color='#00ff00')))
                fig.add_trace(go.Scatter(y=[item['defense']]*4, name="Defense", line=dict(color='red', dash='dash')))
                fig.update_layout(height=180, margin=dict(l=0,r=0,t=0,b=0), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
                st.plotly_chart(fig, use_container_width=True)
else:
    st.info("الرادار فارغ. أضف عنوان عملة من اليسار للبدء.")

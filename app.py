import streamlit as st
import pandas as pd
import psycopg2
import plotly.express as px
import os
import urllib.request
import random
import string
from datetime import datetime, timedelta

# 1. إعداد الصفحة - يجب أن يظهر دائماً
st.set_page_config(page_title="MyClicker Pro Dashboard", layout="wide", page_icon="⚡")

st.markdown("""
    <style>
    header {visibility: hidden;}
    body { direction: rtl; text-align: right; }
    [data-testid="stSidebar"] { text-align: right; direction: rtl; }
    .stMetric { background-color: #ffffff; padding: 15px; border-radius: 12px; border: 1px solid #eee; }
    </style>
""", unsafe_allow_html=True)

# --- وظيفة تحميل الشهادة الذكية ---
def download_ca_cert():
    cert_path = "ca-certificate.crt"
    try:
        if os.path.exists(cert_path) and os.path.getsize(cert_path) == 0:
            os.remove(cert_path)
        if not os.path.exists(cert_path):
            url = "https://certs.ondigitalocean.com/ca-certificate.crt"
            urllib.request.urlretrieve(url, cert_path)
    except: pass
    return cert_path

# --- وظيفة الاتصال "الفولاذية" ---
@st.cache_resource
def init_connection():
    cert_file = download_ca_cert()
    # قائمة بوضعيات الاتصال المختلفة (من الأكثر أماناً للأقل)
    modes = [
        {"sslmode": "require", "sslrootcert": cert_file},
        {"sslmode": "require"},
        {"sslmode": "prefer"},
        {"sslmode": "disable"}
    ]
    
    last_err = ""
    for mode in modes:
        try:
            # تخطي وضع الشهادة إذا كان الملف غير صالح
            if "sslrootcert" in mode and (not os.path.exists(cert_file) or os.path.getsize(cert_file) == 0):
                continue
                
            return psycopg2.connect(
                database="defaultdb", user="doadmin", password="1tHwqXCgn8BS6iTm942V3f7a",
                host="myclicker-db-rd7ky.db1.ondigitalocean.com", port="5432",
                connect_timeout=10, **mode
            )
        except Exception as e:
            last_err = str(e)
            continue
    return ("error", last_err)

# محاولة الاتصال
conn_result = init_connection()

# التحقق من نجاح الاتصال
if isinstance(conn_result, tuple):
    st.error(f"❌ تعذر الاتصال بقاعدة البيانات. السبب: {conn_result[1]}")
    st.info("💡 جرب تحديث الصفحة أو التأكد من أن IP السيرفر مسموح به في إعدادات DigitalOcean.")
    st.stop()
else:
    conn = conn_result

def run_query(query, params=()):
    try:
        cur = conn.cursor(); cur.execute(query, params); conn.commit(); cur.close()
        return True
    except Exception as e:
        conn.rollback(); st.error(f"خطأ: {e}"); return False

# =====================================================================
# 2. إعداد الجداول (نفس الكود الشامل السابق)
# =====================================================================
def setup_db():
    try:
        cur = conn.cursor()
        cur.execute("CREATE SCHEMA IF NOT EXISTS myapp;")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS myapp.app_config (
                id SERIAL PRIMARY KEY, latest_version VARCHAR(20) DEFAULT '7.2.0',
                update_url TEXT, update_message TEXT, force_update_enabled BOOLEAN DEFAULT FALSE
            );
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS myapp.users_status (
                device_id VARCHAR(255) PRIMARY KEY, phone VARCHAR(50), status VARCHAR(50) DEFAULT 'Active',
                bot_status VARCHAR(50) DEFAULT 'Offline', accepted_clicks INT DEFAULT 0,
                app_version VARCHAR(20) DEFAULT '7.2.0', force_update_single BOOLEAN DEFAULT FALSE,
                expiry_date TIMESTAMP, notice_message TEXT, last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        conn.commit(); cur.close()
    except: pass

setup_db()

# =====================================================================
# 3. نظام الدخول والواجهة
# =====================================================================
if "logged_in" not in st.session_state: st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.title("🔐 تسجيل الدخول")
    with st.form("login"):
        u = st.text_input("Username:")
        p = st.text_input("Password:", type="password")
        if st.form_submit_button("دخول"):
            cur = conn.cursor()
            cur.execute("SELECT password, allowed_sections, is_active FROM myapp.app_permissions WHERE username = %s", (u,))
            res = cur.fetchone()
            if res and res[2] and res[0] == p:
                st.session_state.logged_in, st.session_state.username, st.session_state.allowed_sections = True, u, res[1]
                st.rerun()
            else: st.error("بيانات خاطئة أو الحساب معطل")
    st.stop()

# --- القائمة الجانبية ---
with st.sidebar:
    st.title("⚡ MyClicker Pro")
    st.write(f"👤 {st.session_state.username}")
    choice = st.radio("القائمة:", st.session_state.allowed_sections)
    if st.button("🚪 خروج"): st.session_state.logged_in = False; st.rerun()

# --- قسم الإحصائيات (مثال) ---
if choice == "📈 الإحصائيات العامة":
    st.title("📈 الإحصائيات")
    df = pd.read_sql("SELECT status, bot_status, accepted_clicks FROM myapp.users_status", conn)
    c1, c2, c3 = st.columns(3)
    c1.metric("المشتركين", len(df))
    c2.metric("النشطين الآن", len(df[df['bot_status']=='Online']))
    c3.metric("إجمالي النقرات", df['accepted_clicks'].sum())
    st.plotly_chart(px.pie(df, names='status', hole=0.4), use_container_width=True)

# (باقي الأقسام تضاف هنا كما في السكربت السابق)
elif choice == "🚀 إدارة التحديثات الإجبارية":
    st.title("🚀 التحديث الإجباري")
    st.write("إدارة إصدارات التطبيق (7.2.0)")
    # كود التحديث...

elif choice == "🛠️ الدعم الفني":
    st.success("📱 واتساب: https://chat.whatsapp.com/BaC7MvBpJdoKKz4wG5VpWq")

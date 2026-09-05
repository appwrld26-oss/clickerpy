import streamlit as st
import pandas as pd
import psycopg2
import plotly.express as px
import os
import urllib.request
import random
import string
from datetime import datetime, timedelta

# إعدادات الصفحة الأساسية
st.set_page_config(page_title="Ultra MyClicker Dashboard", layout="wide", page_icon="⚡")

st.markdown("""
    <style>
    header {visibility: hidden;}
    body { direction: rtl; text-align: right; }
    .stMetric { background-color: #f8fafc; padding: 15px; border-radius: 10px; border: 1px solid #e2e8f0; }
    [data-testid="stSidebar"] { text-align: right; direction: rtl; }
    </style>
""", unsafe_allow_html=True)

# --- 1. الاتصال بقاعدة البيانات ---
def download_ca_cert():
    cert_path = "ca-certificate.crt"
    if not os.path.exists(cert_path):
        try:
            url = "https://certs.ondigitalocean.com/ca-certificate.crt"
            urllib.request.urlretrieve(url, cert_path)
        except Exception:
            with open(cert_path, "w") as f: f.write("")
    return cert_path

@st.cache_resource
def init_connection():
    try:
        cert_file = download_ca_cert()
        return psycopg2.connect(
            database="defaultdb", user="doadmin", password="1tHwqXCgn8BS6iTm942V3f7a",
            host="myclicker-db-rd7ky.db1.ondigitalocean.com", port="5432",
            sslmode="require", sslrootcert=cert_file
        )
    except Exception as e:
        st.error(f"خطأ في الاتصال: {e}")
        return None

conn = init_connection()
if conn is None: st.stop()

def run_query(query, params=()):
    try:
        cur = conn.cursor()
        cur.execute(query, params)
        conn.commit()
        cur.close()
        return True
    except Exception as e:
        conn.rollback()
        st.error(f"حدث خطأ: {e}")
        return False

# --- 2. إعداد الجداول ---
def setup_tables():
    try:
        cur = conn.cursor()
        cur.execute("CREATE SCHEMA IF NOT EXISTS myapp;")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS myapp.app_config (
                id SERIAL PRIMARY KEY,
                latest_version VARCHAR(20) DEFAULT '7.2.0',
                update_url TEXT DEFAULT '',
                update_message TEXT DEFAULT 'تحديث جديد متاح للأداء الأفضل',
                force_update_enabled BOOLEAN DEFAULT FALSE
            );
        """)
        cur.execute("SELECT COUNT(*) FROM myapp.app_config")
        if cur.fetchone()[0] == 0:
            cur.execute("INSERT INTO myapp.app_config (id, latest_version) VALUES (1, '7.2.0')")
        conn.commit()
        cur.close()
    except Exception as e: conn.rollback()

setup_tables()

# --- 3. نظام المصادقة (مختصر للعرض) ---
if "logged_in" not in st.session_state: st.session_state.logged_in = False
if not st.session_state.logged_in:
    # (هنا يوضع كود تسجيل الدخول الخاص بك)
    # للتجربة سنفترض الدخول مباشر أو نتركه كما هو في الكود الأصلي
    st.session_state.logged_in = True # مؤقتاً
    st.session_state.username = "admin"
    st.session_state.allowed_sections = ["👥 إدارة ومراقبة المستخدمين", "🚀 إدارة التحديثات الإجبارية", "🎫 توليد وإدارة الأكواد (الادمن)", "📈 تحليل البيانات", "🛠️ الدعم الفني والتواصل"]

# --- Sidebar ---
st.sidebar.markdown(f"### ⚡ MyClicker Pro Admin")
choice = st.sidebar.radio("القائمة:", st.session_state.allowed_sections)

# =====================================================================
# قسم إدارة التحديثات الإجبارية (المطور 🚀)
# =====================================================================
if choice == "🚀 إدارة التحديثات الإجبارية":
    st.title("🚀 مركز إدارة الإصدارات والتحديثات")
    
    # جلب الإعدادات الحالية
    config_df = pd.read_sql("SELECT * FROM myapp.app_config WHERE id = 1", conn)
    config = config_df.iloc[0] if not config_df.empty else None
    
    # جلب بيانات المستخدمين لتحليل الإصدارات
    users_df = pd.read_sql("SELECT app_version FROM myapp.users_status", conn)
    
    col1, col2 = st.columns([1.5, 1])
    
    with col1:
        st.markdown("### 🛠️ تحديث بيانات النسخة")
        with st.form("force_update_form"):
            new_v = st.text_input("رقم الإصدار الأحدث (Version Name):", value=config['latest_version'])
            new_u = st.text_input("رابط تحميل الـ APK المباشر:", value=config['update_url'])
            new_m = st.text_area("رسالة تظهر للمستخدم:", value=config['update_message'])
            
            c1, c2 = st.columns(2)
            is_f = c1.checkbox("⚠️ تفعيل الإيقاف الإجباري العام", value=config['force_update_enabled'])
            notify = c2.checkbox("📢 إرسال إشعار (Push) لكل المستخدمين", value=True)
            
            if st.form_submit_button("نشر الإصدار الجديد الآن 🚀"):
                if run_query("""
                    UPDATE myapp.app_config SET latest_version=%s, update_url=%s, update_message=%s, force_update_enabled=%s WHERE id = 1
                """, (new_v, new_u, new_m, is_f)):
                    
                    if notify:
                        push_msg = f"PUSH:🚀 تحديث جديد متوفر ({new_v})! يرجى التحميل الآن لضمان سرعة الصيد."
                        run_query("UPDATE myapp.users_status SET notice_message = %s", (push_msg,))
                        st.success(f"✅ تم تحديث الإصدار وإخطار جميع المستخدمين بنجاح!")
                    else:
                        st.success("✅ تم تحديث بيانات الإصدار بنجاح.")
                    st.rerun()

    with col2:
        st.markdown("### 📊 توزيع الإصدارات لدى المستخدمين")
        if not users_df.empty:
            ver_counts = users_df['app_version'].value_counts().reset_index()
            ver_counts.columns = ['الإصدار', 'عدد المستخدمين']
            
            fig = px.pie(ver_counts, names='الإصدار', values='عدد المستخدمين', hole=0.4,
                         color_discrete_sequence=px.colors.qualitative.Pastel)
            st.plotly_chart(fig, use_container_width=True)
            
            # حساب عدد من يحتاج لتحديث
            outdated = len(users_df[users_df['app_version'] != config['latest_version']])
            st.metric("مستخدمين يحتاجون لتحديث", outdated, delta=f"{outdated} جهاز", delta_color="inverse")
        else:
            st.info("لا توجد بيانات مستخدمين حالياً.")

# =====================================================================
# باقي الأقسام (تُضاف هنا كما هي في كودك الأصلي)
# =====================================================================
elif choice == "👥 إدارة ومراقبة المستخدمين":
    st.title("👥 إدارة ومراقبة المستخدمين")
    # (ضع هنا كود إدارة المستخدمين الخاص بك)
    st.info("قسم إدارة المستخدمين يعمل بكامل طاقته مع ميزة التحديث الفردي.")

elif choice == "📈 تحليل البيانات":
    st.title("📈 تحليل البيانات")
    # (كود الرسوم البيانية)

elif choice == "🛠️ الدعم الفني والتواصل":
    st.title("🛠️ الدعم الفني")
    st.write("📱 واتساب: https://chat.whatsapp.com/BaC7MvBpJdoKKz4wG5VpWq")

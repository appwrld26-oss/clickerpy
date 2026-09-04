import streamlit as st
import pandas as pd
import psycopg2
import plotly.express as px
import os
import urllib.request
import random
import string
from datetime import datetime, timedelta

# إعدادات الصفحة
st.set_page_config(page_title="Ultra MyClicker Dashboard", layout="wide", page_icon="⚡")

st.markdown("""
    <style>
    header {visibility: hidden;}
    body { direction: rtl; text-align: right; }
    .stMetric { background-color: #f8fafc; padding: 15px; border-radius: 10px; border: 1px solid #e2e8f0; }
    </style>
""", unsafe_allow_html=True)

# --- 1. الاتصال بقاعدة البيانات ---
def download_ca_cert():
    cert_path = "ca-certificate.crt"
    if not os.path.exists(cert_path):
        try:
            url = "https://certs.ondigitalocean.com/ca-certificate.crt"
            urllib.request.urlretrieve(url, cert_path)
        except Exception as e:
            st.error(f"فشل تحميل الشهادة: {e}")
    return cert_path

@st.cache_resource
def init_connection():
    try:
        cert_file = download_ca_cert()
        return psycopg2.connect(
            database="defaultdb",
            user="doadmin",
            password="1tHwqXCgn8BS6iTm942V3f7a",
            host="myclicker-db-rd7ky.db1.ondigitalocean.com",
            port="5432",
            sslmode="require",
            sslrootcert=cert_file
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
        # جدول الصلاحيات
        cur.execute("""
            CREATE TABLE IF NOT EXISTS myapp.app_permissions (
                id SERIAL PRIMARY KEY,
                username VARCHAR(50) UNIQUE NOT NULL,
                password VARCHAR(100) NOT NULL,
                role_name VARCHAR(50),
                allowed_sections TEXT[],
                is_active BOOLEAN DEFAULT TRUE
            );
        """)
        # جدول إعدادات التطبيق (التحديث الإجباري)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS myapp.app_config (
                id SERIAL PRIMARY KEY,
                latest_version VARCHAR(20),
                update_url TEXT,
                update_message TEXT,
                force_update_enabled BOOLEAN DEFAULT FALSE
            );
        """)
        conn.commit()
        
        # التأكد من وجود حساب الأدمن والصلاحيات الكاملة
        cur.execute("SELECT COUNT(*) FROM myapp.app_permissions WHERE username = 'admin'")
        if cur.fetchone()[0] == 0:
            all_secs = [
                "👥 إدارة ومراقبة المستخدمين", "🎫 توليد وإدارة الأكواد (الادمن)", 
                "🤝 قسم الشركاء (الموزعين)", "📈 تحليل البيانات", 
                "🖥️ حالة السيرفر", "🔐 إدارة الصلاحيات والتحكم", 
                "🚀 إدارة التحديثات الإجبارية", "🛠️ الدعم الفني والتواصل"
            ]
            cur.execute(
                "INSERT INTO myapp.app_permissions (username, password, role_name, allowed_sections) VALUES (%s, %s, %s, %s)",
                ("admin", "admin123", "مدير النظام", all_secs)
            )
        
        # التأكد من وجود سجل الإعدادات
        cur.execute("SELECT COUNT(*) FROM myapp.app_config")
        if cur.fetchone()[0] == 0:
            cur.execute("INSERT INTO myapp.app_config (latest_version, update_url, update_message, force_update_enabled) VALUES ('7.1.0', '', 'يرجى تحديث التطبيق للاستمرار', FALSE)")
            
        conn.commit()
        cur.close()
    except Exception as e: conn.rollback()

setup_tables()

# --- 3. تسجيل الدخول ---
if "logged_in" not in st.session_state: st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.title("🔐 تسجيل الدخول")
    with st.form("login"):
        u = st.text_input("المستخدم:")
        p = st.text_input("المرور:", type="password")
        if st.form_submit_button("دخول"):
            cur = conn.cursor()
            cur.execute("SELECT password, allowed_sections, is_active FROM myapp.app_permissions WHERE username = %s", (u,))
            res = cur.fetchone()
            if res and res[2] and res[0] == p:
                st.session_state.logged_in, st.session_state.username, st.session_state.allowed_sections = True, u, res[1]
                st.rerun()
            else: st.error("بيانات خاطئة أو حساب معطل")
    st.stop()

# --- Sidebar ---
st.sidebar.title("⚡ MyClicker Pro")
choice = st.sidebar.radio("القائمة:", st.session_state.allowed_sections)
if st.sidebar.button("🚪 خروج"): 
    st.session_state.logged_in = False
    st.rerun()

# =====================================================================
# الأقسام
# =====================================================================

if choice == "👥 إدارة ومراقبة المستخدمين":
    st.title("👥 إدارة المستخدمين والاشتراكات")
    
    # قسم إضافة وتفعيل رقم الهاتف مباشرة
    with st.expander("➕ إضافة وتفعيل رقم هاتف مشترك جديد"):
        with st.form("add_phone_sub"):
            phone_input = st.text_input("رقم الهاتف:")
            sub_days = st.number_input("مدة الاشتراك (بالأيام):", min_value=1, value=30)
            sub_type = st.selectbox("نوع الاشتراك:", ["VIP", "TRIAL", "Monthly"])
            
            if st.form_submit_button("حفظ وتفعيل الرقم 🚀"):
                if not phone_input.strip():
                    st.error("يرجى إدخال رقم الهاتف!")
                else:
                    gen_device_id = f"PHONE-DEV-{''.join(random.choices(string.ascii_uppercase + string.digits, k=10))}"
                    calc_expiry = datetime.now() + timedelta(days=sub_days)
                    if run_query("""
                        INSERT INTO myapp.users_status (device_id, phone, status, subscription_type, expiry_date, accepted_clicks)
                        VALUES (%s, %s, 'Active', %s, %s, 0)
                    """, (gen_device_id, phone_input.strip(), sub_type, calc_expiry)):
                        st.success(f"✅ تمت إضافة وتفعيل رقم الهاتف ({phone_input}) بنجاح!")
                        st.rerun()

    st.markdown("---")
    df = pd.read_sql("SELECT device_id, phone, status, bot_status, subscription_type, expiry_date, notice_message FROM myapp.users_status ORDER BY last_active DESC", conn)
    st.metric("إجمالي الأجهزة/المستخدمين", len(df))
    
    st.markdown("### 📢 إرسال إشعارات")
    mode = st.radio("نوع الإشعار:", ["داخل التطبيق", "إشعار نظام (StatusBar)"], horizontal=True)
    msg = st.text_input("نص الرسالة:")
    if st.button("إرسال للكل"):
        final = f"PUSH:{msg}" if mode == "إشعار نظام (StatusBar)" else msg
        if run_query("UPDATE myapp.users_status SET notice_message = %s", (final,)): st.success("تم الإرسال")
    
    st.dataframe(df, use_container_width=True)

elif choice == "🚀 إدارة التحديثات الإجبارية":
    st.title("🚀 إدارة التحديثات الإجبارية (Force Update)")
    st.warning("تحذير: تفعيل هذا الخيار سيمنع المستخدمين من استخدام النسخ القديمة حتى يقوموا بالتحديث.")
    
    config = pd.read_sql("SELECT * FROM myapp.app_config WHERE id = 1", conn).iloc[0]
    
    with st.form("update_form"):
        new_ver = st.text_input("رقم الإصدار الأحدث (مثل 7.2.0):", value=config['latest_version'])
        new_url = st.text_input("رابط تحميل الـ APK المباشر:", value=config['update_url'])
        new_msg = st.text_area("رسالة التنبيه للمستخدم:", value=config['update_message'])
        is_forced = st.checkbox("تفعيل الإيقاف الإجباري للنسخ القديمة", value=config['force_update_enabled'])
        
        if st.form_submit_button("حفظ الإعدادات 💾"):
            if run_query("""
                UPDATE myapp.app_config 
                SET latest_version=%s, update_url=%s, update_message=%s, force_update_enabled=%s 
                WHERE id = 1
            """, (new_ver, new_url, new_msg, is_forced)):
                st.success("تم الحفظ بنجاح")
                st.rerun()

elif choice == "🎫 توليد وإدارة الأكواد (الادمن)":
    st.title("🎫 توليد الأكواد")
    with st.form("gen"):
        tp = st.selectbox("النوع:", ["VIP", "TRIAL"])
        qty = st.number_input("الكمية:", min_value=1, value=10)
        if st.form_submit_button("توليد"):
            for _ in range(qty):
                code = f"{tp}-{''.join(random.choices(string.ascii_uppercase + string.digits, k=6))}"
                run_query("INSERT INTO myapp.subscriptions (code, sub_type, duration_days, is_used) VALUES (%s,%s,30,FALSE)", (code, tp))
            st.success("تم التوليد بنجاح")

elif choice == "🛠️ الدعم الفني والتواصل":
    st.title("🛠️ الدعم الفني")
    c1, c2 = st.columns(2)
    with c1:
        st.info("📱 واتساب الإدارة: [مراسلة](https://wa.me/9647XXXXXXXX)")
    with c2:
        st.success("✈️ تليجرام الدعم: [@MyClicker_Support](https://t.me/MyClicker_Support)")

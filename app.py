import streamlit as st
import pandas as pd
import psycopg2
import plotly.express as px
import os
import random
import string
from datetime import datetime, timedelta

# =====================================================================
# 1. إعدادات الصفحة والتنسيق (RTL)
# =====================================================================
st.set_page_config(page_title="MyClicker Pro Ultra Dashboard", layout="wide", page_icon="⚡")

st.markdown("""
    <style>
    header {visibility: hidden;}
    body { direction: rtl; text-align: right; }
    [data-testid="stSidebar"] { text-align: right; direction: rtl; }
    .stMetric { background-color: #f8fafc; padding: 15px; border-radius: 12px; border: 1px solid #e2e8f0; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    .stTabs [data-baseweb="tab-list"] { gap: 10px; }
    .stTabs [data-baseweb="tab"] { background-color: #f1f5f9; border-radius: 8px 8px 0 0; padding: 10px 20px; }
    </style>
""", unsafe_allow_html=True)

# --- اتصال آمن ومباشر بقاعدة البيانات دون الاعتماد على ملف شهادة خارجي ---
@st.cache_resource
def init_connection():
    try:
        return psycopg2.connect(
            database="defaultdb", 
            user="doadmin", 
            password="1tHwqXCgn8BS6iTm942V3f7a",
            host="myclicker-db-rd7ky.db1.ondigitalocean.com", 
            port="5432",
            sslmode="require"
        )
    except Exception as e:
        st.error(f"فشل الاتصال بقاعدة البيانات: {e}")
        return None

conn = init_connection()
if conn is None: 
    st.error("❌ تعذر الاتصال بقاعدة البيانات. يرجى التحقق من بيانات الاتصال أو حالة السيرفر.")
    st.stop()

def run_query(query, params=()):
    try:
        cur = conn.cursor()
        cur.execute(query, params)
        conn.commit()
        cur.close()
        return True
    except Exception as e:
        conn.rollback()
        st.error(f"خطأ في التنفيذ: {e}")
        return False

# =====================================================================
# 2. إعداد الجداول (الذكاء الكامل للنظام)
# =====================================================================
def setup_full_system():
    try:
        cur = conn.cursor()
        cur.execute("CREATE SCHEMA IF NOT EXISTS myapp;")
        
        # جدول التحديثات الإجبارية
        cur.execute("""
            CREATE TABLE IF NOT EXISTS myapp.app_config (
                id SERIAL PRIMARY KEY,
                latest_version VARCHAR(20) DEFAULT '7.2.0',
                update_url TEXT DEFAULT '',
                update_message TEXT DEFAULT 'تحديث جديد متاح للأداء الأفضل',
                force_update_enabled BOOLEAN DEFAULT FALSE
            );
        """)
        
        # جدول المستخدمين المطور
        cur.execute("""
            CREATE TABLE IF NOT EXISTS myapp.users_status (
                device_id VARCHAR(255) PRIMARY KEY,
                phone VARCHAR(50) DEFAULT '',
                status VARCHAR(50) DEFAULT 'Active',
                bot_status VARCHAR(50) DEFAULT 'Offline',
                accepted_clicks INT DEFAULT 0,
                subscription_type VARCHAR(50) DEFAULT 'VIP',
                app_version VARCHAR(20) DEFAULT '7.1.0',
                force_update_single BOOLEAN DEFAULT FALSE,
                expiry_date TIMESTAMP DEFAULT NULL,
                notice_message TEXT DEFAULT '',
                last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

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

        # جدول الأكواد والموزعين
        cur.execute("""
            CREATE TABLE IF NOT EXISTS myapp.subscriptions (
                id SERIAL PRIMARY KEY,
                code VARCHAR(100) UNIQUE NOT NULL,
                sub_type VARCHAR(50) DEFAULT 'VIP',
                duration_days INT DEFAULT 30,
                is_used BOOLEAN DEFAULT FALSE,
                used_by_device VARCHAR(255) DEFAULT NULL,
                used_at TIMESTAMP DEFAULT NULL
            );
        """)
        
        # تأكيد وجود الأعمدة الجديدة
        cur.execute("ALTER TABLE myapp.users_status ADD COLUMN IF NOT EXISTS app_version VARCHAR(20) DEFAULT '7.1.0';")
        cur.execute("ALTER TABLE myapp.users_status ADD COLUMN IF NOT EXISTS force_update_single BOOLEAN DEFAULT FALSE;")
        cur.execute("ALTER TABLE myapp.app_permissions ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE;")
        
        # تأكيد حساب الأدمن
        all_sections = [
            "📈 الإحصائيات العامة", "👥 إدارة المستخدمين", "🚀 إدارة التحديثات", 
            "🎫 توليد الأكواد", "🤝 قسم الموزعين", "🖥️ حالة السيرفر", 
            "🔐 الصلاحيات", "🛠️ الدعم الفني"
        ]
        cur.execute("SELECT COUNT(*) FROM myapp.app_permissions WHERE username = 'admin'")
        if cur.fetchone()[0] == 0:
            cur.execute("INSERT INTO myapp.app_permissions (username, password, role_name, allowed_sections, is_active) VALUES (%s,%s,%s,%s,%s)",
                        ("admin", "admin123", "مدير النظام", all_sections, True))
        else:
            cur.execute("UPDATE myapp.app_permissions SET allowed_sections = %s WHERE username = 'admin'", (all_sections,))
        
        cur.execute("SELECT COUNT(*) FROM myapp.app_config")
        if cur.fetchone()[0] == 0:
            cur.execute("INSERT INTO myapp.app_config (id, latest_version) VALUES (1, '7.2.0')")
            
        conn.commit()
        cur.close()
    except Exception as e: 
        conn.rollback()
        st.error(f"خطأ أثناء تهيئة قاعدة البيانات: {e}")

setup_full_system()

# =====================================================================
# 3. نظام الدخول والمصادقة
# =====================================================================
if "logged_in" not in st.session_state: 
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.title("🔐 تسجيل الدخول - MyClicker Pro")
    with st.form("login_form"):
        u = st.text_input("اسم المستخدم:")
        p = st.text_input("كلمة المرور:", type="password")
        submit_btn = st.form_submit_button("دخول")
        if submit_btn:
            try:
                cur = conn.cursor()
                cur.execute("SELECT password, allowed_sections, is_active FROM myapp.app_permissions WHERE username = %s", (u,))
                res = cur.fetchone()
                cur.close()
                if res and res[2] and res[0] == p:
                    st.session_state.logged_in = True
                    st.session_state.username = u
                    st.session_state.allowed_sections = res[1]
                    st.rerun()
                else: 
                    st.error("خطأ في البيانات أو الحساب معطل")
            except Exception as ex:
                st.error(f"خطأ أثناء تسجيل الدخول: {ex}")
    st.stop()

# --- الشريط الجانبي ---
with st.sidebar:
    st.markdown(f"### ⚡ MyClicker Pro\n👤 {st.session_state.username}")
    choice = st.radio("القائمة الرئيسية:", st.session_state.allowed_sections)
    if st.sidebar.button("🚪 خروج"): 
        st.session_state.logged_in = False
        st.rerun()

# =====================================================================
# 4. الأقسام (كل المميزات المبرمجة)
# =====================================================================

# --- 1. الإحصائيات العامة ---
if choice == "📈 الإحصائيات العامة":
    st.title("📈 إحصائيات النظام والأداء")
    df_u = pd.read_sql("SELECT status, bot_status, accepted_clicks, app_version FROM myapp.users_status", conn)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("إجمالي المشتركين", len(df_u))
    c2.metric("البوتات النشطة ⚡", len(df_u[df_u['bot_status']=='Online']) if not df_u.empty else 0)
    c3.metric("إجمالي النقرات", int(df_u['accepted_clicks'].sum()) if not df_u.empty else 0)
    c4.metric("منتهية الصلاحية", len(df_u[df_u['status']=='Expired']) if not df_u.empty else 0)

# --- 2. إدارة المستخدمين ---
elif choice == "👥 إدارة المستخدمين":
    st.title("👥 إدارة الأجهزة والتحكم الفردي")
    df = pd.read_sql("SELECT device_id, phone, status, bot_status, app_version, force_update_single, notice_message, last_active FROM myapp.users_status ORDER BY last_active DESC", conn)
    
    with st.expander("📢 إرسال إشعار جماعي"):
        c_n1, c_n2 = st.columns(2)
        target = c_n1.selectbox("النطاق:", ["الكل", "Active", "Expired"])
        mode = c_n2.radio("نوع التنبيه:", ["رسالة تطبيق", "إشعار نظام (StatusBar)"], horizontal=True)
        msg = st.text_input("نص الرسالة:")
        if st.button("إرسال للكل"):
            final = f"PUSH:{msg}" if mode == "إشعار نظام (StatusBar)" else msg
            q = "UPDATE myapp.users_status SET notice_message = %s"
            if target != "الكل": q += f" WHERE status = '{target}'"
            if run_query(q, (final,)): st.success("تم الإرسال")

    st.dataframe(df, use_container_width=True)

# --- 3. إدارة التحديثات الإجبارية ---
elif choice == "🚀 إدارة التحديثات":
    st.title("🚀 إدارة التحديثات الإجبارية العامة")
    conf = pd.read_sql("SELECT * FROM myapp.app_config WHERE id = 1", conn).iloc[0]
    with st.form("force_up"):
        st.warning("تنبيه: تفعيل 'الإيقاف الإجباري' سيمنع النسخ القديمة من العمل.")
        v = st.text_input("الإصدار الأحدث:", value=conf['latest_version'])
        u = st.text_input("رابط الـ APK:", value=conf['update_url'])
        m = st.text_area("رسالة التحديث:", value=conf['update_message'])
        f = st.checkbox("تفعيل الإيقاف الإجباري العام", value=conf['force_update_enabled'])
        if st.form_submit_button("حفظ ونشر التحديث 🚀"):
            run_query("UPDATE myapp.app_config SET latest_version=%s, update_url=%s, update_message=%s, force_update_enabled=%s WHERE id = 1", (v, u, m, f))
            st.success("تم التحديث")

# --- 4. توليد الأكواد ---
elif choice == "🎫 توليد الأكواد":
    st.title("🎫 توليد أكواد اشتراكات جديدة")
    with st.form("gen"):
        tp = st.selectbox("النوع:", ["VIP", "TRIAL"])
        days = st.number_input("المدة بالأيام:", 30)
        qty = st.number_input("الكمية:", 10)
        if st.form_submit_button("توليد 🚀"):
            for _ in range(qty):
                code = f"{tp}-{''.join(random.choices(string.ascii_uppercase + string.digits, k=6))}"
                run_query("INSERT INTO myapp.subscriptions (code, sub_type, duration_days, is_used) VALUES (%s,%s,%s,FALSE)", (code, tp, days))
            st.success(f"تم توليد {qty} كود بنجاح")

# --- 5. الموزعين ---
elif choice == "🤝 قسم الموزعين":
    st.title("🤝 لوحة الموزعين والأكواد المفعلة")
    df_s = pd.read_sql("SELECT code, sub_type, duration_days, is_used, used_by_device, used_at FROM myapp.subscriptions ORDER BY id DESC", conn)
    t1, t2 = st.tabs(["الأكواد المتاحة", "الأكواد المستخدمة مع الأجهزة"])
    t1.dataframe(df_s[df_s['is_used']==False][['code', 'sub_type', 'duration_days']], use_container_width=True)
    t2.dataframe(df_s[df_s['is_used']==True][['code', 'sub_type', 'used_by_device', 'used_at']], use_container_width=True)

# --- 6. حالة السيرفر ---
elif choice == "🖥️ حالة السيرفر":
    st.title("🖥️ مراقبة الخادم وقاعدة البيانات")
    st.success("🟢 السيرفر متصل ويعمل بكفاءة عالية (DigitalOcean)")
    st.info("قاعدة البيانات: PostgreSQL | التشفير: SSL Active")

# --- 7. الصلاحيات ---
elif choice == "🔐 الصلاحيات":
    st.title("🔐 إدارة حسابات لوحة التحكم")
    col_a, col_b = st.columns([1, 1.5])
    with col_a:
        with st.form("new_acc"):
            nu = st.text_input("Username:")
            np = st.text_input("Password:", type="password")
            role = st.text_input("Role:")
            sel_secs = st.multiselect("الأقسام:", ["📈 الإحصائيات العامة", "👥 إدارة المستخدمين", "🚀 إدارة التحديثات", "🎫 توليد الأكواد", "🤝 قسم الموزعين", "🖥️ حالة السيرفر", "🔐 الصلاحيات", "🛠️ الدعم الفني"])
            if st.form_submit_button("إضافة حساب"):
                run_query("INSERT INTO myapp.app_permissions (username, password, role_name, allowed_sections, is_active) VALUES (%s,%s,%s,%s,%s)", (nu, np, role, sel_secs, True))
                st.rerun()
    with col_b:
        df_p = pd.read_sql("SELECT username, role_name, is_active FROM myapp.app_permissions", conn)
        st.dataframe(df_p, use_container_width=True)

# --- 8. الدعم الفني ---
elif choice == "🛠️ الدعم الفني":
    st.title("🛠️ قنوات الدعم والتواصل")
    st.markdown("---")
    st.success("📱 **واتساب الدعم:** https://chat.whatsapp.com/BaC7MvBpJdoKKz4wG5VpWq")
    st.info("✈️ **تليجرام الإدارة:** @MyClicker_Admin")

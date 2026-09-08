import streamlit as st
import pandas as pd
import psycopg2
from psycopg2 import pool
import plotly.express as px
import random
import string
import hashlib
from datetime import datetime, timedelta

# =====================================================================
# 1. إعدادات الصفحة والتنسيق (Dashboard Setup)
# =====================================================================
st.set_page_config(page_title="MyClicker Pro Center", layout="wide", page_icon="⚡")

# تنسيق واجهة المستخدم الاحترافية
st.markdown("""
<style>
header {visibility: hidden;}
.stApp { background-color: #f8fafc !important; color: #1e293b !important; }
.stMetric { background-color: #ffffff !important; padding: 15px !important; border-radius: 12px !important; border: 1px solid #e2e8f0 !important; }
.stButton button { width: 100% !important; border-radius: 8px !important; font-weight: 600 !important; }
</style>
""", unsafe_allow_html=True)

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode('utf-8')).hexdigest()

# =====================================================================
# 2. إدارة الاتصال بقاعدة البيانات (PostgreSQL Connection)
# =====================================================================
@st.cache_resource
def init_connection_pool():
    try:
        # يفضل استخدام st.secrets، ولكن سنضع البيانات الحالية كخيار افتراضي
        db_config = st.secrets.get("postgres", {
            "dbname": "defaultdb",
            "user": "doadmin",
            "password": "1tHwqXCgn8BS6iTm942V3f7a",
            "host": "myclicker-db-rd7ky.db1.ondigitalocean.com",
            "port": "5432",
            "sslmode": "require"
        })
        return pool.SimpleConnectionPool(1, 20, **db_config)
    except Exception as e:
        st.error(f"❌ فشل الاتصال بقاعدة البيانات: {e}")
        return None

db_pool = init_connection_pool()

def execute_query(sql, params=(), fetch=False):
    if not db_pool: return None
    conn = None
    try:
        conn = db_pool.getconn()
        with conn.cursor() as cur:
            cur.execute(sql, params)
            if fetch:
                colnames = [desc[0] for desc in cur.description] if cur.description else []
                data = cur.fetchall()
                conn.commit()
                return pd.DataFrame(data, columns=colnames) if colnames else pd.DataFrame()
            conn.commit()
            return True
    except Exception as e:
        if conn: conn.rollback()
        st.error(f"خطأ: {e}")
        return None
    finally:
        if conn: db_pool.putconn(conn)

# =====================================================================
# 3. تهيئة الجداول (Schema Setup)
# =====================================================================
execute_query("CREATE SCHEMA IF NOT EXISTS myapp;")

# جدول حالة المستخدمين
execute_query("""
    CREATE TABLE IF NOT EXISTS myapp.users_status (
        device_id VARCHAR(100) PRIMARY KEY,
        phone VARCHAR(20),
        status VARCHAR(20) DEFAULT 'Expired',
        sub_tier VARCHAR(20) DEFAULT 'STANDARD',
        is_frozen BOOLEAN DEFAULT FALSE,
        expiry_date TIMESTAMP,
        app_version VARCHAR(20),
        bot_status VARCHAR(20),
        accepted_clicks INTEGER DEFAULT 0,
        notice_message TEXT,
        last_active TIMESTAMP DEFAULT NOW(),
        last_ip VARCHAR(50)
    );
""")

# جدول الإعدادات
execute_query("CREATE TABLE IF NOT EXISTS myapp.app_config (key VARCHAR(50) PRIMARY KEY, value TEXT);")

# جدول الأكواد
execute_query("""
    CREATE TABLE IF NOT EXISTS myapp.subscriptions (
        id SERIAL PRIMARY KEY,
        code VARCHAR(20) UNIQUE,
        sub_tier VARCHAR(20),
        duration_days INTEGER,
        is_used BOOLEAN DEFAULT FALSE,
        used_by_device VARCHAR(100),
        used_at TIMESTAMP
    );
""")

# جدول الصلاحيات
execute_query("""
    CREATE TABLE IF NOT EXISTS myapp.app_permissions (
        id SERIAL PRIMARY KEY,
        username VARCHAR(50) UNIQUE NOT NULL,
        password VARCHAR(100) NOT NULL,
        allowed_sections TEXT[],
        is_active BOOLEAN DEFAULT TRUE
    );
""")

# التأكد من وجود حساب الأدمن
admin_check = execute_query("SELECT COUNT(*) FROM myapp.app_permissions WHERE username = 'admin'", fetch=True)
if admin_check is not None and not admin_check.empty and admin_check.iloc[0, 0] == 0:
    sections = ["📊 نظرة عامة", "👥 إدارة الأجهزة", "🎫 الأكواد", "🔄 التحديثات الحية", "📢 الإشعارات", "🔐 الصلاحيات"]
    execute_query("INSERT INTO myapp.app_permissions (username, password, allowed_sections) VALUES ('admin', %s, %s)", (hash_password('admin123'), sections))

# =====================================================================
# 4. نظام تسجيل الدخول (Authentication)
# =====================================================================
if "logged_in" not in st.session_state: st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.title("🔐 تسجيل الدخول للوحة التحكم")
    with st.form("login"):
        u = st.text_input("المستخدم:")
        p = st.text_input("كلمة المرور:", type="password")
        if st.form_submit_button("دخول"):
            res = execute_query("SELECT password, allowed_sections FROM myapp.app_permissions WHERE username = %s AND is_active = TRUE", (u,), fetch=True)
            if res is not None and not res.empty:
                if res.iloc[0]['password'] == hash_password(p):
                    st.session_state.logged_in = True
                    st.session_state.user = u
                    st.session_state.sections = res.iloc[0]['allowed_sections']
                    st.rerun()
                else: st.error("كلمة مرور خاطئة")
            else: st.error("المستخدم غير موجود")
    st.stop()

# =====================================================================
# 5. القائمة الجانبية (Sidebar)
# =====================================================================
st.sidebar.title(f"👤 {st.session_state.user}")
page = st.sidebar.radio("القائمة الرئيسية:", st.session_state.sections)
if st.sidebar.button("🚪 خروج"):
    st.session_state.logged_in = False
    st.rerun()

# =====================================================================
# 6. الأقسام (Sections)
# =====================================================================

if page == "📊 نظرة عامة":
    st.title("📊 نظرة عامة على النظام")
    df = execute_query("SELECT status, bot_status, accepted_clicks FROM myapp.users_status", fetch=True)
    if not df.empty:
        c1, c2, c3 = st.columns(3)
        c1.metric("إجمالي الأجهزة", len(df))
        c2.metric("نشطة (Active)", len(df[df['status'] == 'Active']))
        c3.metric("بوتات أونلاين", len(df[df['bot_status'] == 'Online']))
        st.plotly_chart(px.pie(df, names='status', title="توزيع الحالات"), use_container_width=True)

elif page == "👥 إدارة الأجهزة":
    st.title("👥 إدارة الأجهزة والمشتركين")
    df_u = execute_query("SELECT * FROM myapp.users_status ORDER BY last_active DESC", fetch=True)
    st.dataframe(df_u, use_container_width=True)
    
    with st.expander("🛠️ التحكم في جهاز"):
        d_id = st.text_input("Device ID للجهاز:")
        col1, col2 = st.columns(2)
        with col1:
            n_status = st.selectbox("الحالة:", ["Active", "Expired", "Blocked"])
            n_tier = st.selectbox("الفئة:", ["TRIAL", "STANDARD", "VIP"])
        with col2:
            n_freeze = st.checkbox("تجميد (Freeze)")
            n_expiry = st.date_input("تاريخ الانتهاء الجديد:")
        
        if st.button("حفظ التغييرات"):
            execute_query("UPDATE myapp.users_status SET status=%s, sub_tier=%s, is_frozen=%s, expiry_date=%s WHERE device_id=%s", (n_status, n_tier, n_freeze, n_expiry, d_id))
            st.success("تم التحديث!")
            st.cache_data.clear()

elif page == "🎫 الأكواد":
    st.title("🎫 توليد وإدارة الأكواد")
    with st.form("gen"):
        t = st.selectbox("الفئة:", ["STANDARD", "VIP"])
        d = st.number_input("الأيام:", 30)
        q = st.number_input("العدد:", 5)
        if st.form_submit_button("توليد"):
            for _ in range(q):
                c = t[:3] + ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
                execute_query("INSERT INTO myapp.subscriptions (code, sub_tier, duration_days) VALUES (%s, %s, %s)", (c, t, d))
            st.success(f"تم توليد {q} كود")
    st.dataframe(execute_query("SELECT * FROM myapp.subscriptions WHERE is_used = FALSE", fetch=True))

elif page == "🔄 التحديثات الحية":
    st.title("🔄 التحكم الفوري (Live Update)")
    conf = execute_query("SELECT * FROM myapp.app_config", fetch=True)
    st.write("الإعدادات الحالية:", conf)
    with st.form("cfg"):
        k = st.text_input("المفتاح (مثلاً: click_delay):")
        v = st.text_input("القيمة:")
        if st.form_submit_button("حفظ"):
            execute_query("INSERT INTO myapp.app_config (key, value) VALUES (%s, %s) ON CONFLICT (key) DO UPDATE SET value=EXCLUDED.value", (k, v))
            st.success("تم الحفظ")
            st.cache_data.clear()

elif page == "📢 الإشعارات":
    st.title("📢 إرسال إشعارات للأجهزة")
    msg = st.text_area("نص الإشعار:")
    target = st.text_input("Device ID (فارغ للجميع):")
    if st.button("إرسال الإشعار"):
        if target: execute_query("UPDATE myapp.users_status SET notice_message=%s WHERE device_id=%s", (msg, target))
        else: execute_query("UPDATE myapp.users_status SET notice_message=%s", (msg,))
        st.success("تم الإرسال")

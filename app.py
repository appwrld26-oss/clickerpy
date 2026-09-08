import streamlit as st
import pandas as pd
import psycopg2
from psycopg2 import pool, InterfaceError, OperationalError
import plotly.express as px
import random
import string
import hashlib
import os
from datetime import datetime

# =====================================================================
# 1. إعدادات الصفحة والتنسيق (UI Design)
# =====================================================================
st.set_page_config(page_title="MyClicker Pro Center v7.2.7", layout="wide", page_icon="⚡")

st.markdown("""
<style>
header {visibility: hidden;}
.stApp { background-color: #f8fafc !important; color: #1e293b !important; }
.stMetric { background-color: #ffffff !important; padding: 20px !important; border-radius: 12px !important; border: 1px solid #e2e8f0 !important; box-shadow: 0 4px 6px rgba(0,0,0,0.05); }
.stButton button { width: 100% !important; border-radius: 8px !important; font-weight: 600 !important; }
</style>
""", unsafe_allow_html=True)

# =====================================================================
# 2. إدارة الاتصال بقاعدة البيانات (Stability Mode)
# =====================================================================
@st.cache_resource
def init_connection_pool():
    db_url = os.getenv("DATABASE_URL", "postgresql://doadmin:1tHwqXCgn8BS6iTm942V3f7a@myclicker-db-rd7ky.db1.ondigitalocean.com:5432/defaultdb?sslmode=require")
    try:
        return pool.ThreadedConnectionPool(1, 15, dsn=db_url)
    except Exception as e:
        st.error(f"❌ فشل إنشاء مجمع الاتصالات: {e}")
        return None

db_pool = init_connection_pool()

def execute_query(sql, params=(), fetch=False):
    if not db_pool: return None
    conn = None
    try:
        conn = db_pool.getconn()
        if conn.closed != 0:
            db_pool.putconn(conn, close=True)
            conn = db_pool.getconn()
        with conn.cursor() as cur:
            cur.execute(sql, params)
            if fetch:
                colnames = [desc[0] for desc in cur.description] if cur.description else []
                data = cur.fetchall()
                conn.commit()
                return pd.DataFrame(data, columns=colnames)
            conn.commit()
            return True
    except (InterfaceError, OperationalError):
        if conn: db_pool.putconn(conn, close=True)
        return None
    except Exception as e:
        if conn: conn.rollback()
        st.error(f"⚠️ خطأ: {e}")
        return None
    finally:
        if conn and conn.closed == 0: db_pool.putconn(conn)

# تهيئة الجداول تلقائياً
execute_query("CREATE SCHEMA IF NOT EXISTS myapp;")
execute_query("""
    CREATE TABLE IF NOT EXISTS myapp.users_status (
        device_id VARCHAR PRIMARY KEY, phone VARCHAR, status VARCHAR DEFAULT 'Active',
        sub_tier VARCHAR DEFAULT 'STANDARD', is_frozen BOOLEAN DEFAULT FALSE,
        expiry_date TIMESTAMP, app_version VARCHAR, bot_status VARCHAR,
        accepted_clicks INTEGER DEFAULT 0, notice_message TEXT, last_active TIMESTAMP DEFAULT NOW()
    );
""")
execute_query("CREATE TABLE IF NOT EXISTS myapp.app_config (key VARCHAR PRIMARY KEY, value TEXT);")
execute_query("CREATE TABLE IF NOT EXISTS myapp.subscriptions (id SERIAL PRIMARY KEY, code VARCHAR UNIQUE, sub_tier VARCHAR, duration_days INTEGER, is_used BOOLEAN DEFAULT FALSE);")

# =====================================================================
# 3. القائمة الجانبية والتحكم (Sidebar)
# =====================================================================
st.sidebar.markdown("# ⚡ MyClicker Pro v7.2.7")
menu = st.sidebar.radio("القائمة الرئيسية:", ["📈 الإحصائيات", "👥 الأجهزة", "🎫 الأكواد", "🔄 التحديثات الحية", "📢 الإشعارات"])

if menu == "📈 الإحصائيات":
    st.title("📈 إحصائيات النظام")
    df = execute_query("SELECT status, bot_status, accepted_clicks FROM myapp.users_status", fetch=True)
    if df is not None and not df.empty:
        c1, c2, c3 = st.columns(3)
        c1.metric("إجمالي الأجهزة", len(df))
        c2.metric("نشطة (Active)", len(df[df['status'] == 'Active']))
        c3.metric("إجمالي النقرات", int(df['accepted_clicks'].sum()))
        st.plotly_chart(px.pie(df, names='status', title="توزيع حالة المشتركين", hole=0.4), use_container_width=True)

elif menu == "👥 الأجهزة":
    st.title("👥 إدارة الأجهزة والمشتركين")
    df_u = execute_query("SELECT * FROM myapp.users_status ORDER BY last_active DESC", fetch=True)
    if df_u is not None:
        st.dataframe(df_u, use_container_width=True)
        with st.expander("📝 تعديل حالة جهاز"):
            d_id = st.text_input("أدخل Device ID:")
            col1, col2 = st.columns(2)
            with col1: n_stat = st.selectbox("الحالة:", ["Active", "Expired", "Blocked"])
            with col2: n_frz = st.checkbox("تجميد؟")
            if st.button("حفظ التعديل"):
                execute_query("UPDATE myapp.users_status SET status=%s, is_frozen=%s WHERE device_id=%s", (n_stat, n_frz, d_id))
                st.success("تم التحديث!")
                st.rerun()

elif menu == "🎫 الأكواد":
    st.title("🎫 توليد وإدارة الأكواد")
    with st.form("gen"):
        tier = st.selectbox("الفئة:", ["STANDARD", "VIP"])
        days = st.number_input("الأيام:", 30)
        qty = st.number_input("الكمية:", 5)
        if st.form_submit_button("توليد"):
            for _ in range(qty):
                code = tier[:3] + ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
                execute_query("INSERT INTO myapp.subscriptions (code, sub_tier, duration_days) VALUES (%s, %s, %s)", (code, tier, days))
            st.success("تم التوليد")
    st.dataframe(execute_query("SELECT code, sub_tier, duration_days FROM myapp.subscriptions WHERE is_used = FALSE", fetch=True))

elif menu == "🔄 التحديثات الحية":
    st.title("🔄 التحديث الفوري (Live Update)")
    with st.form("cfg"):
        delay = st.text_input("تأخير النقرات (ms):", "500")
        keys = st.text_area("الكلمات المفتاحية:")
        if st.form_submit_button("نشر الآن"):
            execute_query("INSERT INTO myapp.app_config (key, value) VALUES ('click_delay', %s) ON CONFLICT (key) DO UPDATE SET value=EXCLUDED.value", (delay,))
            execute_query("INSERT INTO myapp.app_config (key, value) VALUES ('live_keywords', %s) ON CONFLICT (key) DO UPDATE SET value=EXCLUDED.value", (keys,))
            st.success("تم النشر بنجاح")

elif menu == "📢 الإشعارات":
    st.title("📢 إرسال إشعار فوري")
    msg = st.text_area("نص الرسالة:")
    if st.button("إرسال للجميع"):
        execute_query("UPDATE myapp.users_status SET notice_message = %s", (msg,))
        st.success("تم إرسال الإشعار لجميع الأجهزة")

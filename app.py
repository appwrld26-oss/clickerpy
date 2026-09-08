import streamlit as st
import pandas as pd
import psycopg2
from psycopg2 import pool
import plotly.express as px
import random
import string
import hashlib
from datetime import datetime

# إعدادات الصفحة والتنسيق
st.set_page_config(page_title="MyClicker Pro 7.2.7 Admin", layout="wide", page_icon="⚡")

st.markdown("""
<style>
header {visibility: hidden;}
.stApp { background-color: #f8fafc !important; color: #1e293b !important; }
.stMetric { background-color: #ffffff !important; padding: 15px !important; border-radius: 12px !important; border: 1px solid #e2e8f0 !important; }
.stButton button { width: 100% !important; border-radius: 8px !important; font-weight: 600 !important; }
</style>
""", unsafe_allow_html=True)

@st.cache_resource
def init_pool():
    db_config = {
        "dbname": "defaultdb", "user": "doadmin", "password": "1tHwqXCgn8BS6iTm942V3f7a",
        "host": "myclicker-db-rd7ky.db1.ondigitalocean.com", "port": "5432", "sslmode": "require"
    }
    return pool.SimpleConnectionPool(1, 10, **db_config)

db_pool = init_pool()

def run_query(sql, params=(), fetch=False):
    conn = db_pool.getconn()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            if fetch:
                colnames = [d[0] for d in cur.description]
                return pd.DataFrame(cur.fetchall(), columns=colnames)
            conn.commit()
            return True
    finally:
        db_pool.putconn(conn)

# تهيئة الجداول
run_query("CREATE SCHEMA IF NOT EXISTS myapp;")
run_query("CREATE TABLE IF NOT EXISTS myapp.users_status (device_id VARCHAR PRIMARY KEY, phone VARCHAR, status VARCHAR, sub_tier VARCHAR DEFAULT 'STANDARD', is_frozen BOOLEAN DEFAULT FALSE, expiry_date TIMESTAMP, app_version VARCHAR, bot_status VARCHAR, accepted_clicks INTEGER DEFAULT 0, notice_message TEXT, last_active TIMESTAMP, last_ip VARCHAR);")
run_query("CREATE TABLE IF NOT EXISTS myapp.app_config (key VARCHAR PRIMARY KEY, value TEXT);")
run_query("CREATE TABLE IF NOT EXISTS myapp.subscriptions (id SERIAL PRIMARY KEY, code VARCHAR UNIQUE, sub_tier VARCHAR, duration_days INTEGER, is_used BOOLEAN DEFAULT FALSE, used_by_device VARCHAR, used_at TIMESTAMP);")

st.sidebar.title("⚡ MyClicker Admin")
menu = st.sidebar.radio("القائمة:", ["📈 نظرة عامة", "👥 المستخدمين", "🎫 الأكواد", "🔄 تحديثات حية", "🤝 الشركاء"])

if menu == "📈 نظرة عامة":
    df = run_query("SELECT * FROM myapp.users_status", fetch=True)
    if not df.empty:
        c1, c2, c3 = st.columns(3)
        c1.metric("إجمالي الأجهزة", len(df))
        c2.metric("المشتركين النشطين", len(df[df['status'] == 'Active']))
        c3.metric("إجمالي النقرات", int(df['accepted_clicks'].sum()))
        st.subheader("توزيع الإصدارات")
        st.plotly_chart(px.pie(df, names='app_version'), use_container_width=True)

elif menu == "👥 المستخدمين":
    st.subheader("إدارة الأجهزة")
    df_u = run_query("SELECT * FROM myapp.users_status ORDER BY last_active DESC", fetch=True)
    st.dataframe(df_u, use_container_width=True)
    
    with st.expander("تعديل مستخدم"):
        did = st.text_input("Device ID:")
        stat = st.selectbox("الحالة:", ["Active", "Expired", "Blocked"])
        frz = st.checkbox("تجميد؟")
        if st.button("حفظ"):
            run_query("UPDATE myapp.users_status SET status=%s, is_frozen=%s WHERE device_id=%s", (stat, frz, did))
            st.success("تم التعديل")

elif menu == "🎫 الأكواد":
    with st.form("gen"):
        tier = st.selectbox("الفئة:", ["STANDARD", "VIP"])
        days = st.number_input("الأيام:", 30)
        num = st.number_input("العدد:", 10)
        if st.form_submit_button("توليد الأكواد"):
            for _ in range(num):
                c = tier[:3] + ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
                run_query("INSERT INTO myapp.subscriptions (code, sub_tier, duration_days) VALUES (%s, %s, %s)", (c, tier, days))
            st.success("تم التوليد")
    st.dataframe(run_query("SELECT * FROM myapp.subscriptions WHERE is_used = FALSE", fetch=True))

elif menu == "🔄 تحديثات حية":
    with st.form("config"):
        delay = st.text_input("تأخير النقرات (click_delay):", "500")
        keys = st.text_area("الكلمات المفتاحية:")
        if st.form_submit_button("نشر التحديث"):
            run_query("INSERT INTO myapp.app_config (key, value) VALUES ('click_delay', %s) ON CONFLICT (key) DO UPDATE SET value=EXCLUDED.value", (delay,))
            run_query("INSERT INTO myapp.app_config (key, value) VALUES ('live_keywords', %s) ON CONFLICT (key) DO UPDATE SET value=EXCLUDED.value", (keys,))
            st.success("تم النشر")

elif menu == "🤝 الشركاء":
    st.subheader("سجل استخدام الأكواد")
    st.dataframe(run_query("SELECT * FROM myapp.subscriptions WHERE is_used = TRUE", fetch=True))

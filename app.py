import streamlit as st
import pandas as pd
import psycopg2
from psycopg2 import pool
import plotly.express as px
import random
import string
import hashlib
from datetime import datetime

# =====================================================================
# إعدادات الصفحة والتنسيقات (نفس الـ CSS السابق)
# =====================================================================
st.set_page_config(page_title="MyClicker Pro 7.2.7", layout="wide", page_icon="⚡")

st.markdown("""
<style>
header {visibility: hidden;}
.stApp { background-color: #f8fafc !important; color: #1e293b !important; }
.stMetric { background-color: #ffffff !important; padding: 15px !important; border-radius: 12px !important; border: 1px solid #e2e8f0 !important; }
.stButton button { width: 100% !important; border-radius: 8px !important; font-weight: 600 !important; }
</style>
""", unsafe_allow_html=True)

# الاتصال بقاعدة البيانات
@st.cache_resource
def init_connection_pool():
    db_config = {
        "dbname": "defaultdb",
        "user": "doadmin",
        "password": "1tHwqXCgn8BS6iTm942V3f7a",
        "host": "myclicker-db-rd7ky.db1.ondigitalocean.com",
        "port": "5432",
        "sslmode": "require"
    }
    return pool.SimpleConnectionPool(1, 10, **db_config)

db_pool = init_connection_pool()

def execute_query(sql, params=(), fetch=False):
    conn = db_pool.getconn()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            if fetch:
                colnames = [desc[0] for desc in cur.description]
                data = cur.fetchall()
                conn.commit()
                return pd.DataFrame(data, columns=colnames)
            conn.commit()
            return True
    finally:
        db_pool.putconn(conn)

# الأقسام الرئيسية
st.title("⚡ لوحة تحكم MyClicker 7.2.7")

menu = st.sidebar.radio("القائمة:", ["📈 نظرة عامة", "👥 المستخدمين", "🎫 الأكواد", "🔄 تحديثات حية", "🚀 تحديثات إجبارية"])

if menu == "📈 نظرة عامة":
    df = execute_query("SELECT status, bot_status, accepted_clicks FROM myapp.users_status", fetch=True)
    if not df.empty:
        c1, c2, c3 = st.columns(3)
        c1.metric("إجمالي الأجهزة", len(df))
        c2.metric("النشطة الآن", len(df[df['status'] == 'Active']))
        c3.metric("إجمالي النقرات", int(df['accepted_clicks'].sum()))

elif menu == "👥 المستخدمين":
    st.subheader("إدارة الأجهزة المتصلة")
    df_u = execute_query("SELECT * FROM myapp.users_status ORDER BY last_active DESC", fetch=True)
    st.dataframe(df_u, use_container_width=True)
    
    with st.expander("التحكم السريع بجهاز"):
        d_id = st.text_input("Device ID:")
        col1, col2 = st.columns(2)
        with col1:
            stat = st.selectbox("الحالة:", ["Active", "Expired", "Blocked"])
        with col2:
            frz = st.checkbox("تجميد الحساب؟")
        
        if st.button("حفظ التعديلات"):
            execute_query("UPDATE myapp.users_status SET status=%s, is_frozen=%s WHERE device_id=%s", (stat, frz, d_id))
            st.success("تم التحديث")

elif menu == "🎫 الأكواد":
    st.subheader("توليد أكواد اشتراك")
    with st.form("gen_codes"):
        tier = st.selectbox("الفئة:", ["STANDARD", "VIP"])
        days = st.number_input("الأيام:", 30)
        num = st.number_input("الكمية:", 10)
        if st.form_submit_button("توليد"):
            for _ in range(num):
                code = tier[:3] + ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
                execute_query("INSERT INTO myapp.subscriptions (code, sub_tier, duration_days) VALUES (%s, %s, %s)", (code, tier, days))
            st.success("تم التوليد بنجاح")
    
    st.dataframe(execute_query("SELECT * FROM myapp.subscriptions WHERE is_used = FALSE", fetch=True))

elif menu == "🔄 تحديثات حية":
    st.subheader("تعديل إعدادات البوت فورياً")
    with st.form("live"):
        delay = st.text_input("تأخير النقر (ms):", "500")
        keys = st.text_area("الكلمات المفتاحية:")
        if st.form_submit_button("نشر التحديث"):
            execute_query("INSERT INTO myapp.app_config (key, value) VALUES ('click_delay', %s) ON CONFLICT (key) DO UPDATE SET value=EXCLUDED.value", (delay,))
            execute_query("INSERT INTO myapp.app_config (key, value) VALUES ('live_keywords', %s) ON CONFLICT (key) DO UPDATE SET value=EXCLUDED.value", (keys,))
            st.success("تم النشر")

elif menu == "🚀 تحديثات إجبارية":
    st.subheader("إدارة إصدار التطبيق")
    with st.form("force"):
        ver = st.text_input("الإصدار الأحدث:", "7.2.7")
        url = st.text_input("رابط الـ APK:")
        if st.form_submit_button("طلب تحديث من الجميع"):
            execute_query("INSERT INTO myapp.app_config (key, value) VALUES ('latest_version', %s) ON CONFLICT (key) DO UPDATE SET value=EXCLUDED.value", (ver,))
            execute_query("INSERT INTO myapp.app_config (key, value) VALUES ('update_url', %s) ON CONFLICT (key) DO UPDATE SET value=EXCLUDED.value", (url,))
            execute_query("INSERT INTO myapp.app_config (key, value) VALUES ('force_update', 'true') ON CONFLICT (key) DO UPDATE SET value=EXCLUDED.value")
            st.success("تم طلب التحديث")

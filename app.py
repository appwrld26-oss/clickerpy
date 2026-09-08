import streamlit as st
import pandas as pd
import psycopg2
from psycopg2 import pool
import plotly.express as px
import random, string, os

st.set_page_config(page_title="MyClicker Admin 7.2.7", layout="wide")

@st.cache_resource
def get_pool():
    url = os.getenv("DATABASE_URL", "postgresql://doadmin:1tHwqXCgn8BS6iTm942V3f7a@myclicker-db-rd7ky.db1.ondigitalocean.com:5432/defaultdb?sslmode=require")
    return psycopg2.pool.ThreadedConnectionPool(1, 2, dsn=url)

db_pool = get_pool()

def run_query(sql, params=(), fetch=False):
    conn = db_pool.getconn()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            if fetch:
                df = pd.DataFrame(cur.fetchall(), columns=[d[0] for d in cur.description])
                conn.commit()
                return df
            conn.commit()
            return True
    finally: db_pool.putconn(conn)

st.title("⚡ MyClicker Pro Dashboard")
menu = st.sidebar.radio("القائمة:", ["📊 الإحصائيات", "👥 الأجهزة", "🎫 الأكواد"])

if menu == "📊 الإحصائيات":
    df = run_query("SELECT status, accepted_clicks FROM myapp.users_status", fetch=True)
    if not df.empty:
        c1, c2 = st.columns(2)
        c1.metric("إجمالي الأجهزة", len(df))
        c2.metric("إجمالي النقرات", int(df['accepted_clicks'].sum()))
        st.plotly_chart(px.pie(df, names='status', hole=0.4))

elif menu == "👥 الأجهزة":
    df = run_query("SELECT * FROM myapp.users_status", fetch=True)
    st.dataframe(df)
    with st.expander("تعديل حالة"):
        did = st.text_input("Device ID:")
        stat = st.selectbox("الحالة:", ["Active", "Expired", "Blocked"])
        if st.button("حفظ"):
            run_query("UPDATE myapp.users_status SET status=%s WHERE device_id=%s", (stat, did))
            st.success("تم!")

elif menu == "🎫 الأكواد":
    with st.form("gen"):
        tier = st.selectbox("الفئة:", ["STANDARD", "VIP"])
        num = st.number_input("الكمية:", 5)
        if st.form_submit_button("توليد"):
            for _ in range(num):
                c = tier[:3] + ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
                run_query("INSERT INTO myapp.subscriptions (code, sub_tier, duration_days) VALUES (%s, %s, 30)", (c, tier))
            st.success("تم التوليد")
    st.dataframe(run_query("SELECT code, sub_tier FROM myapp.subscriptions WHERE is_used = FALSE", fetch=True))

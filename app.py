import streamlit as st
import pandas as pd
import psycopg2
from psycopg2 import pool
import plotly.express as px
import random, string, os

# إعداد الصفحة
st.set_page_config(page_title="MyClicker Admin 7.2.7", layout="wide", page_icon="⚡")

@st.cache_resource
def get_pool():
    # الرابط مع منفذ المجمع 25060 لضمان عدم حدوث زحام
    url = os.getenv("DATABASE_URL", "postgresql://doadmin:1tHwqXCgn8BS6iTm942V3f7a@myclicker-db-rd7ky.db1.ondigitalocean.com:25060/mypool?sslmode=require")
    return psycopg2.pool.ThreadedConnectionPool(1, 2, dsn=url)

db_pool = get_pool()

def run_query(sql, params=(), fetch=False):
    if not db_pool: return None
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
    except Exception as e:
        if conn: conn.rollback()
        st.error(f"Error: {e}")
        return None
    finally:
        db_pool.putconn(conn)

st.title("⚡ MyClicker Pro Dashboard v7.2.7")
menu = st.sidebar.radio("القائمة الرئيسية:", ["📊 الإحصائيات", "👥 الأجهزة", "🎫 الأكواد", "🔄 التحديثات الحية", "📢 الإشعارات"])

if menu == "📊 الإحصائيات":
    df = run_query("SELECT status, accepted_clicks FROM myapp.users_status", fetch=True)
    if df is not None and not df.empty:
        c1, c2 = st.columns(2)
        c1.metric("إجمالي الأجهزة", len(df))
        c2.metric("إجمالي النقرات", int(df['accepted_clicks'].sum()))
        st.plotly_chart(px.pie(df, names='status', title="توزيع حالة المشتركين", hole=0.4))
    else: st.info("لا توجد بيانات لعرضها.")

elif menu == "👥 الأجهزة":
    df = run_query("SELECT device_id, phone, status, sub_tier, is_frozen, last_active FROM myapp.users_status ORDER BY last_active DESC", fetch=True)
    if df is not None:
        st.dataframe(df, use_container_width=True)
        with st.expander("🛠️ تعديل حالة جهاز"):
            did = st.text_input("أدخل Device ID:")
            stat = st.selectbox("الحالة:", ["Active", "Expired", "Blocked"])
            frz = st.checkbox("تجميد الحساب؟")
            if st.button("حفظ التعديلات"):
                run_query("UPDATE myapp.users_status SET status=%s, is_frozen=%s WHERE device_id=%s", (stat, frz, did))
                st.success("تم التحديث!")
                st.rerun()

elif menu == "🎫 الأكواد":
    with st.form("gen"):
        tier = st.selectbox("فئة الكود:", ["STANDARD", "VIP"])
        days = st.number_input("الأيام:", 30)
        num = st.number_input("الكمية:", 10)
        if st.form_submit_button("توليد الأكواد 🚀"):
            for _ in range(num):
                c = tier[:3] + ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
                run_query("INSERT INTO myapp.subscriptions (code, sub_tier, duration_days) VALUES (%s, %s, %s)", (c, tier, days))
            st.success("تم التوليد بنجاح")
    st.dataframe(run_query("SELECT code, sub_tier, duration_days FROM myapp.subscriptions WHERE is_used = FALSE", fetch=True))

elif menu == "🔄 التحديثات الحية":
    st.subheader("التحكم في إعدادات البوت عن بُعد")
    with st.form("cfg"):
        delay = st.text_input("تأخير النقرات (click_delay):", value="450")
        keys = st.text_area("الكلمات المفتاحية للقبول:", placeholder="طلب,توصيل...")
        if st.form_submit_button("نشر التحديث فوراً"):
            run_query("INSERT INTO myapp.app_config (key, value) VALUES ('click_delay', %s) ON CONFLICT (key) DO UPDATE SET value=EXCLUDED.value", (delay,))
            run_query("INSERT INTO myapp.app_config (key, value) VALUES ('live_keywords', %s) ON CONFLICT (key) DO UPDATE SET value=EXCLUDED.value", (keys,))
            st.success("تم التحديث!")

elif menu == "📢 الإشعارات":
    st.subheader("إرسال رسائل منبثقة للمستخدمين")
    msg = st.text_area("نص الرسالة:")
    target = st.text_input("Device ID (اتركه فارغاً للكل):")
    if st.button("إرسال الإشعار"):
        if target: run_query("UPDATE myapp.users_status SET notice_message=%s WHERE device_id=%s", (msg, target))
        else: run_query("UPDATE myapp.users_status SET notice_message=%s", (msg,))
        st.success("تم الإرسال!")

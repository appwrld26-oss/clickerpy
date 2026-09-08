import streamlit as st
import pandas as pd
import psycopg2
from psycopg2 import pool
import plotly.express as px
import random
import string
import hashlib
import os
from datetime import datetime

# =====================================================================
# 1. إعدادات الصفحة والتنسيق الاحترافي
# =====================================================================
st.set_page_config(page_title="MyClicker Pro Center", layout="wide", page_icon="⚡")

st.markdown("""
<style>
header {visibility: hidden;}
.stApp { background-color: #f8fafc !important; color: #1e293b !important; }
.stMetric { background-color: #ffffff !important; padding: 20px !important; border-radius: 12px !important; border: 1px solid #e2e8f0 !important; box-shadow: 0 4px 6px rgba(0,0,0,0.05); }
.stButton button { width: 100% !important; border-radius: 8px !important; font-weight: 600 !important; height: 3em !important; }
</style>
""", unsafe_allow_html=True)

# =====================================================================
# 2. إدارة الاتصال بقاعدة البيانات (باستخدام DATABASE_URL)
# =====================================================================
@st.cache_resource
def init_connection_pool():
    # جلب رابط قاعدة البيانات من المتغيرات البيئية (كما في .env)
    # ملاحظة: أضفنا sslmode=require لضمان الأمان مع DigitalOcean
    db_url = os.getenv("DATABASE_URL", "postgresql://doadmin:1tHwqXCgn8BS6iTm942V3f7a@myclicker-db-rd7ky.db1.ondigitalocean.com:5432/defaultdb?sslmode=require")
    try:
        return pool.SimpleConnectionPool(1, 20, dsn=db_url)
    except Exception as e:
        st.error(f"❌ خطأ في الاتصال بقاعدة البيانات: {e}")
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
                return pd.DataFrame(data, columns=colnames)
            conn.commit()
            return True
    except Exception as e:
        if conn: conn.rollback()
        st.error(f"⚠️ خطأ في الاستعلام: {e}")
        return None
    finally:
        if conn: db_pool.putconn(conn)

# =====================================================================
# 3. واجهة المستخدم الرئيسية
# =====================================================================
st.sidebar.markdown("# ⚡ MyClicker Pro v7.2.7")
menu = st.sidebar.radio("انتقل إلى:", ["📈 الإحصائيات العامة", "👥 إدارة الأجهزة", "🎫 نظام الأكواد", "🔄 التحكم الفوري", "📢 الإشعارات"])

# دالة تشفير (نفس المستخدمة في السيرفر للمطابقة)
def hash_pass(p): return hashlib.sha256(p.encode()).hexdigest()

if menu == "📈 الإحصائيات العامة":
    st.title("📈 لوحة الأداء والمراقبة")
    df = execute_query("SELECT status, bot_status, accepted_clicks FROM myapp.users_status", fetch=True)
    if df is not None and not df.empty:
        col1, col2, col3 = st.columns(3)
        col1.metric("إجمالي الأجهزة", len(df))
        col2.metric("نشطة (Active)", len(df[df['status'] == 'Active']))
        col3.metric("إجمالي النقرات", int(df['accepted_clicks'].sum()))
        
        st.markdown("---")
        fig = px.pie(df, names='status', title="توزيع حالة المشتركين", hole=0.5, color_discrete_sequence=px.colors.qualitative.Pastel)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("لا توجد بيانات لعرضها حالياً.")

elif menu == "👥 إدارة الأجهزة":
    st.title("👥 إدارة الأجهزة المتصلة")
    search = st.text_input("🔍 ابحث عن هاتف أو Device ID:")
    df_u = execute_query("SELECT device_id, phone, status, sub_tier, is_frozen, expiry_date, last_active FROM myapp.users_status ORDER BY last_active DESC", fetch=True)
    
    if df_u is not None:
        if search:
            df_u = df_u[df_u['phone'].str.contains(search, na=False) | df_u['device_id'].str.contains(search, na=False)]
        st.dataframe(df_u, use_container_width=True)

        with st.expander("📝 تعديل حالة جهاز محدد"):
            target_id = st.text_input("أدخل Device ID للجهاز المراد تعديله:")
            c1, c2 = st.columns(2)
            with c1:
                new_status = st.selectbox("الحالة الجديدة:", ["Active", "Expired", "Blocked"])
            with c2:
                freeze = st.checkbox("تجميد الحساب (Freeze)")
            
            if st.button("تحديث الحالة الآن"):
                if execute_query("UPDATE myapp.users_status SET status=%s, is_frozen=%s WHERE device_id=%s", (new_status, freeze, target_id)):
                    st.success("✅ تم التحديث بنجاح!")
                    st.rerun()

elif menu == "🎫 نظام الأكواد":
    st.title("🎫 توليد وإدارة أكواد الاشتراك")
    with st.form("generate_form"):
        tier = st.selectbox("فئة الكود:", ["STANDARD", "VIP"])
        days = st.number_input("مدة الصلاحية (بالأيام):", 30)
        count = st.number_input("الكمية:", 10)
        if st.form_submit_button("توليد الأكواد الآن 🚀"):
            for _ in range(count):
                code = tier[:3].upper() + ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
                execute_query("INSERT INTO myapp.subscriptions (code, sub_tier, duration_days) VALUES (%s, %s, %s)", (code, tier, days))
            st.success(f"تم توليد {count} كود بنجاح.")

    st.markdown("### الأكواد المتاحة")
    df_codes = execute_query("SELECT code, sub_tier, duration_days FROM myapp.subscriptions WHERE is_used = FALSE", fetch=True)
    st.dataframe(df_codes, use_container_width=True)

elif menu == "🔄 التحكم الفوري":
    st.title("🔄 تحديثات حية للنظام (Live Update)")
    st.warning("أي تغيير هنا سيظهر للمستخدمين في غضون ثوانٍ.")
    
    with st.form("live_cfg"):
        delay = st.text_input("تأخير النقرات (click_delay):", value="450")
        keywords = st.text_area("الكلمات المفتاحية للقبول:", placeholder="طلب,توصيل,عاجل...")
        if st.form_submit_button("نشر التحديث فوراً 🚀"):
            execute_query("INSERT INTO myapp.app_config (key, value) VALUES ('click_delay', %s) ON CONFLICT (key) DO UPDATE SET value=EXCLUDED.value", (delay,))
            execute_query("INSERT INTO myapp.app_config (key, value) VALUES ('live_keywords', %s) ON CONFLICT (key) DO UPDATE SET value=EXCLUDED.value", (keywords,))
            st.success("✅ تم النشر بنجاح.")

elif menu == "📢 الإشعارات":
    st.title("📢 إرسال إشعارات منبثقة")
    msg = st.text_area("نص الإشعار المراد عرضه للمستخدم:")
    target = st.text_input("Device ID (أتركه فارغاً للإرسال للجميع):")
    if st.button("بث الإشعار الآن"):
        if target:
            execute_query("UPDATE myapp.users_status SET notice_message = %s WHERE device_id = %s", (msg, target))
        else:
            execute_query("UPDATE myapp.users_status SET notice_message = %s", (msg,))
        st.success("✅ تم إرسال الإشعار.")

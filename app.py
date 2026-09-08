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
# 1. إعدادات الصفحة
# =====================================================================
st.set_page_config(page_title="MyClicker Pro Center", layout="wide", page_icon="⚡")

# =====================================================================
# 2. إدارة الاتصال بقاعدة البيانات (نسخة محسنة)
# =====================================================================
@st.cache_resource
def init_connection_pool():
    # تأكد من إزالة أي علامات استفهام زائدة في نهاية الرابط إذا وجدت
    db_url = os.getenv("DATABASE_URL", "postgresql://doadmin:1tHwqXCgn8BS6iTm942V3f7a@myclicker-db-rd7ky.db1.ondigitalocean.com:5432/defaultdb?sslmode=require")
    
    try:
        # استخدام ThreadedConnectionPool لضمان الاستقرار في بيئة Streamlit
        return pool.ThreadedConnectionPool(1, 10, dsn=db_url)
    except Exception as e:
        st.error(f"❌ فشل إنشاء مجمع الاتصالات: {e}")
        return None

db_pool = init_connection_pool()

def execute_query(sql, params=(), fetch=False):
    if not db_pool:
        st.error("❌ قاعدة البيانات غير متصلة.")
        return None
    
    conn = None
    try:
        conn = db_pool.getconn()
        # فحص إذا كان الاتصال لا يزال حياً
        if conn.closed != 0:
            db_pool.putconn(conn, close=True)
            conn = db_pool.getconn()
            
        with conn.cursor() as cur:
            cur.execute(sql, params)
            if fetch:
                if cur.description:
                    colnames = [desc[0] for desc in cur.description]
                    data = cur.fetchall()
                    conn.commit()
                    return pd.DataFrame(data, columns=colnames)
                return pd.DataFrame()
            conn.commit()
            return True
            
    except (InterfaceError, OperationalError) as e:
        # في حال حدوث خطأ في الاتصال، نحاول إعادة الاتصال
        st.warning("⚠️ تم فقد الاتصال، جاري إعادة المحاولة...")
        if conn:
            db_pool.putconn(conn, close=True)
        return None
    except Exception as e:
        if conn:
            conn.rollback()
        st.error(f"⚠️ خطأ في الاستعلام: {e}")
        return None
    finally:
        if conn and conn.closed == 0:
            db_pool.putconn(conn)

# =====================================================================
# 3. واجهة المستخدم (التأكد من وجود البيانات قبل العرض)
# =====================================================================

# تشغيل الفحص الأولي للجداول
execute_query("CREATE SCHEMA IF NOT EXISTS myapp;")

st.sidebar.markdown("# ⚡ MyClicker Admin")
menu = st.sidebar.radio("القائمة:", ["📈 الإحصائيات", "👥 الأجهزة", "🎫 الأكواد", "🔄 التحديثات الحية"])

if menu == "📈 الإحصائيات":
    st.title("📈 إحصائيات النظام")
    df = execute_query("SELECT status, bot_status, accepted_clicks FROM myapp.users_status", fetch=True)
    
    if df is not None:
        if not df.empty:
            c1, c2, c3 = st.columns(3)
            c1.metric("إجمالي الأجهزة", len(df))
            c2.metric("النشطة", len(df[df['status'] == 'Active']))
            c3.metric("النقرات", int(df['accepted_clicks'].sum()))
        else:
            st.info("لا توجد بيانات حالياً.")
    else:
        st.error("تعذر جلب البيانات من السيرفر. تأكد من إعدادات الـ Firewall في DigitalOcean.")

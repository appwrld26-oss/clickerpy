import streamlit as st
import pandas as pd
import psycopg2
from psycopg2.extras import RealDictCursor
import hashlib
import os

# 1. إعدادات الصفحة والربط المضمون
st.set_page_config(page_title="MyClicker Admin", layout="wide", page_icon="⚡")

def get_db_connection():
    # استخدام st.secrets لضمان العمل على Streamlit Cloud
    db_url = st.secrets["DATABASE_URL"]
    return psycopg2.connect(db_url, sslmode='require')

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# 2. التحقق من تسجيل الدخول
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.title("🔐 بوابة إدارة MyClicker Pro")
    user = st.text_input("اسم المستخدم")
    pw = st.text_input("كلمة المرور", type="password")
    if st.button("دخول"):
        # admin / admin123
        if user == "admin" and hash_password(pw) == "240be518fabd2724ddb6f04eeb1da5967448d7e831c08c8fa822809f74c720a9":
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.error("❌ بيانات الدخول غير صحيحة")
    st.stop()

# 3. وظائف جلب البيانات
def fetch_data(query):
    try:
        conn = get_db_connection()
        df = pd.read_sql(query, conn)
        conn.close()
        return df
    except Exception as e:
        st.error(f"خطأ في قاعدة البيانات: {e}")
        return pd.DataFrame()

def run_query(query, params=None):
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(query, params)
        conn.commit()
        cur.close()
        conn.close()
        return True
    except Exception as e:
        st.error(f"فشل التنفيذ: {e}")
        return False

# 4. القائمة الجانبية
menu = st.sidebar.radio("التحكم", ["📊 نظرة عامة", "👥 الأجهزة", "🎫 الأكواد", "📢 التنبيهات"])

# --- قسم نظرة عامة ---
if menu == "📊 نظرة عامة":
    st.header("📊 حالة النظام")
    
    # التأكد من وجود مفتاح التفعيل الجماعي
    run_query("INSERT INTO myapp.app_config (key, value) VALUES ('global_free_mode', 'false') ON CONFLICT (key) DO NOTHING")
    
    res = fetch_data("SELECT value FROM myapp.app_config WHERE key = 'global_free_mode'")
    is_free = res['value'][0] == 'true' if not res.empty else False
    
    col1, col2 = st.columns([3, 1])
    if is_free:
        col1.success("🚀 وضع التفعيل الجماعي: مفعّل (النظام مفتوح مجاناً)")
    else:
        col1.info("🔒 وضع التفعيل الجماعي: معطّل (الاشتراكات سارية)")
    
    if col2.button("تبديل الحالة 🔄"):
        new_val = 'false' if is_free else 'true'
        run_query("UPDATE myapp.app_config SET value = %s WHERE key = 'global_free_mode'", (new_val,))
        st.rerun()

# --- قسم الأجهزة ---
elif menu == "👥 الأجهزة":
    st.header("👥 إدارة الأجهزة")
    df = fetch_data("SELECT device_id, phone, status, expiry_date, last_active, bot_status, accepted_clicks FROM myapp.users_status ORDER BY last_active DESC")
    st.dataframe(df, use_container_width=True)

# --- قسم الأكواد ---
elif menu == "🎫 الأكواد":
    st.header("🎫 توليد الأكواد")
    c1, c2, c3 = st.columns(3)
    prefix = c1.text_input("البادئة", "PRO")
    days = c2.number_input("الأيام", 1, 365, 30)
    count = c3.number_input("العدد", 1, 50, 5)
    
    if st.button("توليد الآن ✨"):
        for _ in range(count):
            code = f"{prefix}-{days}-{os.urandom(3).hex().upper()}"
            run_query("INSERT INTO myapp.subscriptions (code, duration_days) VALUES (%s, %s)", (code, days))
        st.success("تم التوليد بنجاح")

# --- قسم التنبيهات ---
elif menu == "📢 التنبيهات":
    st.header("📢 إرسال إشعار للجميع")
    msg = st.text_area("نص الإشعار")
    if st.button("بث الإشعار 📢"):
        run_query("INSERT INTO myapp.app_config (key, value) VALUES ('global_notice', %s) ON CONFLICT (key) DO UPDATE SET value = %s", (msg, msg))
        st.success("تم بث الإشعار")

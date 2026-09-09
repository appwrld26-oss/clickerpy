import streamlit as st
import pandas as pd
import psycopg2
from psycopg2.extras import RealDictCursor
import datetime
import hashlib
import plotly.express as px
import os
from dotenv import load_dotenv

# 1. إعدادات الصفحة
load_dotenv()
st.set_page_config(page_title="MyClicker Control Center", layout="wide", page_icon="⚡")

# اتصال قاعدة البيانات (Neon)
def get_db_connection():
    return psycopg2.connect(os.getenv("DATABASE_URL"), sslmode='require')

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# 2. نظام الدخول
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.title("🔐 بوابة الإدارة")
    user = st.text_input("اسم المستخدم")
    pw = st.text_input("كلمة المرور", type="password")
    if st.button("دخول"):
        if user == "admin" and hash_password(pw) == "240be518fabd2724ddb6f04eeb1da5967448d7e831c08c8fa822809f74c720a9": # admin123
            st.session_state.authenticated = True
            st.session_state.username = user
            st.rerun()
        else:
            st.error("خطأ في البيانات")
    st.stop()

# 3. القائمة الجانبية
menu = st.sidebar.radio("التحكم", ["📊 نظرة عامة", "👥 الأجهزة", "🎫 الأكواد", "📢 التحديثات والاشعارات", "🛡️ الأمن"])

def fetch_data(query):
    conn = get_db_connection()
    df = pd.read_sql(query, conn)
    conn.close()
    return df

# ---------------------------------------------------------
# 📊 نظرة عامة & التفعيل الجماعي
# ---------------------------------------------------------
if menu == "📊 نظرة عامة":
    st.header("📊 حالة النظام")
    
    # ميزة التفعيل الجماعي (Global Free Mode)
    st.subheader("⚡ التحكم الجماعي بالاشتراكات")
    current_free = fetch_data("SELECT value FROM myapp.app_config WHERE key = 'global_free_mode'")
    is_free = current_free['value'][0] == 'true' if not current_free.empty else False
    
    col_a, col_b = st.columns([3, 1])
    if is_free:
        col_a.success("🟢 النظام حالياً مفتوح للجميع مجاناً!")
    else:
        col_a.warning("🔴 النظام حالياً يعمل بنظام الاشتراكات الفردية")
    
    if col_b.button("تبديل وضع التفعيل الجماعي 🔄"):
        conn = get_db_connection()
        cur = conn.cursor()
        new_val = 'false' if is_free else 'true'
        cur.execute("INSERT INTO myapp.app_config (key, value) VALUES ('global_free_mode', %s) ON CONFLICT (key) DO UPDATE SET value = %s", (new_val, new_val))
        conn.commit()
        st.rerun()

# ---------------------------------------------------------
# 👥 إدارة الأجهزة
# ---------------------------------------------------------
elif menu == "👥 الأجهزة":
    st.header("👥 إدارة المستخدمين")
    df_users = fetch_data("SELECT device_id, phone, status, sub_tier, expiry_date, app_version, last_active FROM myapp.users_status ORDER BY last_active DESC")
    st.dataframe(df_users, use_container_width=True)
    
    st.subheader("🛠️ إجراء على جهاز")
    target = st.selectbox("اختر الجهاز", df_users['device_id'])
    act = st.selectbox("الإجراء", ["حظر", "تفعيل", "تجميد", "تنبيه خاص"])
    val = st.text_input("نص التنبيه (في حال اخترت تنبيه)")
    
    if st.button("تنفيذ ⚡"):
        conn = get_db_connection()
        cur = conn.cursor()
        if act == "حظر": cur.execute("UPDATE myapp.users_status SET status = 'Blocked' WHERE device_id = %s", (target,))
        elif act == "تفعيل": cur.execute("UPDATE myapp.users_status SET status = 'Active', is_frozen = FALSE WHERE device_id = %s", (target,))
        elif act == "تنبيه خاص": cur.execute("UPDATE myapp.users_status SET notice_message = %s WHERE device_id = %s", (val, target))
        conn.commit()
        st.success("تم")

# ---------------------------------------------------------
# 🎫 إدارة الأكواد
# ---------------------------------------------------------
elif menu == "🎫 الأكواد":
    st.header("🎫 نظام الأكواد")
    t1, t2 = st.tabs(["توليد أكواد", "سجل الاستخدام"])
    
    with t1:
        prefix = st.text_input("البادئة", "VIP")
        days = st.number_input("الأيام", 1, 365, 30)
        num = st.number_input("العدد", 1, 50, 10)
        if st.button("توليد الآن ✨"):
            conn = get_db_connection()
            cur = conn.cursor()
            for _ in range(num):
                code = f"{prefix}-{days}-{os.urandom(3).hex().upper()}"
                cur.execute("INSERT INTO myapp.subscriptions (code, duration_days) VALUES (%s, %s)", (code, days))
            conn.commit()
            st.success("تم التوليد")

    with t2:
        df_used = fetch_data("""
            SELECT s.code, u.phone, s.used_at, s.used_by_device 
            FROM myapp.subscriptions s 
            JOIN myapp.users_status u ON s.used_by_device = u.device_id 
            WHERE s.is_used = TRUE
        """)
        st.table(df_used)

# ---------------------------------------------------------
# 📢 التحديثات والاشعارات
# ---------------------------------------------------------
elif menu == "📢 التحديثات والاشعارات":
    st.header("📢 التحكم العام بالبوت")
    
    st.subheader("🚀 تحديث إجباري للجميع")
    v = st.text_input("رقم الإصدار (مثل 7.2.8)")
    url = st.text_input("رابط التحميل المباشر")
    if st.button("إجبار الجميع على التحديث ⚠️"):
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("UPDATE myapp.app_config SET value = %s WHERE key = 'latest_version'", (v,))
        cur.execute("UPDATE myapp.app_config SET value = %s WHERE key = 'next_url'", (url,))
        cur.execute("UPDATE myapp.app_config SET value = 'true' WHERE key = 'force_update'")
        conn.commit()
        st.success("تم إرسال أمر التحديث لكافة الأجهزة")

    st.subheader("🔔 إشعار عام (بث)")
    msg = st.text_area("نص الرسالة")
    if st.button("بث الإشعار الآن 📢"):
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("INSERT INTO myapp.app_config (key, value) VALUES ('global_notice', %s) ON CONFLICT (key) DO UPDATE SET value = %s", (msg, msg))
        conn.commit()
        st.success("تم البث")

# ---------------------------------------------------------
# 🛡️ الأمن
# ---------------------------------------------------------
elif menu == "🛡️ الأمن":
    st.header("🛡️ سجل الرقابة")
    df_logs = fetch_data("SELECT * FROM myapp.security_logs ORDER BY created_at DESC LIMIT 50")
    st.table(df_logs)

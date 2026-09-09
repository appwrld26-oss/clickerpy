import streamlit as st
import pandas as pd
import psycopg2
from psycopg2.extras import RealDictCursor
import hashlib
import os
import datetime

# 1. إعدادات الصفحة والهوية
st.set_page_config(page_title="MyClicker Pro | لوحة التحكم المركزية", layout="wide", page_icon="⚡")

# اتصال آمن بقاعدة البيانات (Neon)
def get_db_connection():
    try:
        db_url = st.secrets["DATABASE_URL"]
        return psycopg2.connect(db_url, sslmode='require')
    except Exception as e:
        st.error(f"❌ فشل الاتصال بقاعدة البيانات: {e}")
        st.stop()

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# 2. نظام تسجيل الدخول المحمي
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.title("🔐 تسجيل دخول المدراء")
    col_login, _ = st.columns([1, 2])
    with col_login:
        user = st.text_input("اسم المستخدم")
        pw = st.text_input("كلمة المرور", type="password")
        if st.button("دخول للنظام"):
            # admin / admin123
            if user == "admin" and hash_password(pw) == "240be518fabd2724ddb6f04eeb1da5967448d7e831c08c8fa822809f74c720a9":
                st.session_state.authenticated = True
                st.rerun()
            else:
                st.error("❌ البيانات غير صحيحة")
    st.stop()

# 3. وظائف جلب وتنفيذ البيانات
def fetch_df(query):
    conn = get_db_connection()
    df = pd.read_sql(query, conn)
    conn.close()
    return df

def run_cmd(query, params=None):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(query, params)
    conn.commit()
    cur.close()
    conn.close()

# 4. القائمة الجانبية (الشريط الرئيسي)
st.sidebar.title("🚀 التحكم المركزي")
menu = st.sidebar.radio("القائمة", 
    ["📊 نظرة عامة", "👥 إدارة الأجهزة", "🎫 نظام الأكواد", "📢 البث والاشعارات", "🛡️ سجل الأمان"])

# ---------------------------------------------------------
# 📊 قسم نظرة عامة & التفعيل الجماعي
# ---------------------------------------------------------
if menu == "📊 نظرة عامة":
    st.header("📊 حالة النظام المباشرة")
    
    # بطاقات الملخص
    stats = fetch_df("SELECT (SELECT count(*) FROM myapp.users_status) as users, (SELECT count(*) FROM myapp.subscriptions WHERE is_used = FALSE) as free_codes")
    c1, c2, c3 = st.columns(3)
    c1.metric("إجمالي السائقين", stats['users'][0])
    c2.metric("أكواد متوفرة", stats['free_codes'][0])
    c3.metric("حالة السيرفر", "Online ✅")

    st.divider()

    # --- ميزة التفعيل الجماعي (Global Free Mode) ---
    st.subheader("⚡ تفعيل كافة الأجهزة بنقرة واحدة")
    config = fetch_df("SELECT value FROM myapp.app_config WHERE key = 'global_free_mode'")
    is_on = config['value'][0] == 'true' if not config.empty else False
    
    ca, cb = st.columns([3, 1])
    if is_on:
        ca.success("🚀 وضع التفعيل الجماعي: [مفعّل] - كافة الأجهزة تعمل الآن مجاناً!")
        if cb.button("إيقاف الوضع المجاني 🔒"):
            run_cmd("UPDATE myapp.app_config SET value = 'false' WHERE key = 'global_free_mode'")
            st.rerun()
    else:
        ca.info("🔒 وضع التفعيل الجماعي: [معطّل] - الاشتراكات الفردية هي التي تعمل")
        if cb.button("فتح النظام للكل مجاناً 🚀"):
            run_cmd("INSERT INTO myapp.app_config (key, value) VALUES ('global_free_mode', 'true') ON CONFLICT (key) DO UPDATE SET value = 'true'")
            st.rerun()

# ---------------------------------------------------------
# 👥 إدارة الأجهزة (Device Management)
# ---------------------------------------------------------
elif menu == "👥 إدارة الأجهزة":
    st.header("👥 التحكم في السائقين والأجهزة")
    
    search = st.text_input("🔍 بحث برقم الهاتف أو Device ID")
    q = "SELECT device_id, phone, status, sub_tier, expiry_date, app_version, last_active FROM myapp.users_status"
    if search:
        q += f" WHERE phone LIKE '%%{search}%%' OR device_id LIKE '%%{search}%%'"
    
    df_users = fetch_df(q + " ORDER BY last_active DESC")
    st.dataframe(df_users, use_container_width=True)

    st.subheader("🛠️ إجراءات سريعة")
    col1, col2, col3 = st.columns(3)
    target_id = col1.selectbox("اختر الجهاز للتحكم", df_users['device_id'])
    action = col2.selectbox("نوع الإجراء", ["تفعيل", "حظر (Block)", "إرسال رسالة خاصة"])
    val = col3.text_input("القيمة (في حال التنبيه)")

    if st.button("تنفيذ الإجراء الفوري ⚡"):
        if action == "حظر (Block)": run_cmd("UPDATE myapp.users_status SET status = 'Blocked' WHERE device_id = %s", (target_id,))
        elif action == "تفعيل": run_cmd("UPDATE myapp.users_status SET status = 'Active' WHERE device_id = %s", (target_id,))
        elif action == "إرسال رسالة خاصة": run_cmd("UPDATE myapp.users_status SET notice_message = %s WHERE device_id = %s", (val, target_id))
        st.success("تم تنفيذ العملية")

# ---------------------------------------------------------
# 🎫 نظام الأكواد (Subscription Codes)
# ---------------------------------------------------------
elif menu == "🎫 نظام الأكواد":
    st.header("🎫 إدارة وتوليد أكواد التفعيل")
    
    tab1, tab2 = st.tabs(["✨ توليد أكواد جديدة", "📜 سجل الاستخدام"])
    
    with tab1:
        with st.form("gen"):
            pre = st.text_input("البادئة", "VIP")
            days = st.number_input("المدة (أيام)", 1, 365, 30)
            count = st.number_input("العدد", 1, 100, 10)
            if st.submit_button("توليد وتخزين ✨"):
                for _ in range(count):
                    code = f"{pre}-{days}-{os.urandom(3).hex().upper()}"
                    run_cmd("INSERT INTO myapp.subscriptions (code, duration_days) VALUES (%s, %s)", (code, days))
                st.success(f"تم توليد {count} كود بنجاح")

    with tab2:
        df_used = fetch_df("""
            SELECT s.code, u.phone, s.used_at, s.used_by_device 
            FROM myapp.subscriptions s 
            JOIN myapp.users_status u ON s.used_by_device = u.device_id 
            WHERE s.is_used = TRUE ORDER BY s.used_at DESC
        """)
        st.dataframe(df_used, use_container_width=True)

# ---------------------------------------------------------
# 📢 البث والاشعارات (Global Broadcast)
# ---------------------------------------------------------
elif menu == "📢 البث والاشعارات":
    st.header("📢 بث تنبيهات لكافة السائقين")
    msg = st.text_area("نص الرسالة (سيظهر كإشعار نظام خارج التطبيق)")
    if st.button("بث الإشعار الآن 🚀"):
        run_cmd("INSERT INTO myapp.app_config (key, value) VALUES ('global_notice', %s) ON CONFLICT (key) DO UPDATE SET value = %s", (msg, msg))
        st.success("تم إرسال الإشعار لجميع السائقين المتصلين")

# ---------------------------------------------------------
# 🛡️ سجل الأمان (Security Logs)
# ---------------------------------------------------------
elif menu == "🛡️ سجل الأمان":
    st.header("🛡️ مراقبة نشاط النظام")
    df_logs = fetch_df("SELECT * FROM myapp.security_logs ORDER BY created_at DESC LIMIT 100")
    st.table(df_logs)

# 5. التذييل
st.sidebar.markdown("---")
if st.sidebar.button("تسجيل الخروج"):
    st.session_state.authenticated = False
    st.rerun()

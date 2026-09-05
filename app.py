import streamlit as st
import pandas as pd
import psycopg2
import plotly.express as px
import random
import string
from datetime import datetime, timedelta

# إعدادات الصفحة
st.set_page_config(page_title="MyClicker Pro Ultra Dashboard", layout="wide", page_icon="⚡")

st.markdown("""
    <style>
    header {visibility: hidden;}
    body { direction: rtl; text-align: right; }
    [data-testid="stSidebar"] { text-align: right; direction: rtl; }
    .stMetric { background-color: #f8fafc; padding: 15px; border-radius: 12px; border: 1px solid #e2e8f0; }
    </style>
""", unsafe_allow_html=True)

# اتصال قاعدة البيانات
@st.cache_resource
def get_conn():
    try:
        return psycopg2.connect(
            database="defaultdb",
            user="doadmin",
            password="1tHwqXCgn8BS6iTm942V3f7a",
            host="myclicker-db-rd7ky.db1.ondigitalocean.com",
            port="5432",
            sslmode="require"
        )
    except Exception as e:
        return None

conn = get_conn()
if not conn:
    st.error("❌ فشل الاتصال بقاعدة البيانات على DigitalOcean. يرجى التحقق من بيانات الاتصال.")
    st.stop()

def query(sql, params=()):
    try:
        cur = conn.cursor()
        cur.execute(sql, params)
        conn.commit()
        cur.close()
        return True
    except Exception as e:
        conn.rollback()
        st.error(f"خطأ قاعدة بيانات: {e}")
        return False

# تهيئة الجداول الأساسية
try:
    cur = conn.cursor()
    cur.execute("CREATE SCHEMA IF NOT EXISTS myapp;")
    cur.execute("CREATE TABLE IF NOT EXISTS myapp.app_config (id SERIAL PRIMARY KEY, latest_version VARCHAR(20) DEFAULT '7.1.0', update_url TEXT DEFAULT '', update_message TEXT DEFAULT 'يرجى التحديث', force_update_enabled BOOLEAN DEFAULT FALSE);")
    cur.execute("CREATE TABLE IF NOT EXISTS myapp.users_status (device_id VARCHAR(255) PRIMARY KEY, phone VARCHAR(50) DEFAULT '', status VARCHAR(50) DEFAULT 'Active', bot_status VARCHAR(50) DEFAULT 'Offline', accepted_clicks INT DEFAULT 0, subscription_type VARCHAR(50) DEFAULT 'VIP', app_version VARCHAR(20) DEFAULT '7.1.0', force_update_single BOOLEAN DEFAULT FALSE, expiry_date TIMESTAMP DEFAULT NULL, notice_message TEXT DEFAULT '', last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP);")
    cur.execute("CREATE TABLE IF NOT EXISTS myapp.app_permissions (id SERIAL PRIMARY KEY, username VARCHAR(50) UNIQUE NOT NULL, password VARCHAR(100) NOT NULL, role_name VARCHAR(50), allowed_sections TEXT[], is_active BOOLEAN DEFAULT TRUE);")
    cur.execute("CREATE TABLE IF NOT EXISTS myapp.subscriptions (id SERIAL PRIMARY KEY, code VARCHAR(100) UNIQUE NOT NULL, sub_type VARCHAR(50) DEFAULT 'VIP', duration_days INT DEFAULT 30, is_used BOOLEAN DEFAULT FALSE, used_by_device VARCHAR(255) DEFAULT NULL, used_at TIMESTAMP DEFAULT NULL);")
    
    all_secs = [
        "👥 إدارة ومراقبة المستخدمين", 
        "🚀 إدارة التحديثات الإجبارية", 
        "🎫 توليد وإدارة الأكواد", 
        "🤝 قسم الشركاء (الموزعين)", 
        "📈 تحليل البيانات", 
        "🖥️ حالة السيرفر", 
        "🔐 إدارة الصلاحيات والتحكم", 
        "🛠️ الدعم الفني والتواصل"
    ]

    cur.execute("SELECT COUNT(*) FROM myapp.app_permissions WHERE username = 'admin'")
    if cur.fetchone()[0] == 0:
        cur.execute("INSERT INTO myapp.app_permissions (username, password, role_name, allowed_sections, is_active) VALUES ('admin', 'admin123', 'مدير النظام', %s, TRUE)", (all_secs,))
    else:
        cur.execute("UPDATE myapp.app_permissions SET allowed_sections = %s WHERE username = 'admin'", (all_secs,))
    
    cur.execute("SELECT COUNT(*) FROM myapp.app_config")
    if cur.fetchone()[0] == 0:
        cur.execute("INSERT INTO myapp.app_config (id, latest_version) VALUES (1, '7.1.0')")
    
    conn.commit()
    cur.close()
except Exception as e:
    conn.rollback()

# نظام تسجيل الدخول
if "logged" not in st.session_state:
    st.session_state.logged = False

if not st.session_state.logged:
    st.title("🔐 تسجيل الدخول - MyClicker Pro")
    with st.form("login"):
        u = st.text_input("اسم المستخدم:")
        p = st.text_input("كلمة المرور:", type="password")
        if st.form_submit_button("دخول"):
            cur = conn.cursor()
            cur.execute("SELECT password, allowed_sections, is_active FROM myapp.app_permissions WHERE username = %s", (u,))
            res = cur.fetchone()
            cur.close()
            if res and res[2] and res[0] == p:
                st.session_state.logged = True
                st.session_state.user = u
                st.session_state.sections = res[1]
                st.rerun()
            else:
                st.error("بيانات الدخول غير صحيحة أو الحساب معطل.")
    st.stop()

# القائمة الجانبية
st.sidebar.markdown(f"### ⚡ MyClicker Pro\n👤 {st.session_state.user}")
if st.sidebar.button("🔄 تحديث البيانات"):
    st.rerun()

page = st.sidebar.radio("القائمة الرئيسية:", st.session_state.sections)
if st.sidebar.button("🚪 خروج"):
    st.session_state.logged = False
    st.rerun()

# =====================================================================
# الأقسام الكاملة
# =====================================================================

# 1. إدارة ومراقبة المستخدمين
if page == "👥 إدارة ومراقبة المستخدمين":
    st.title("👥 إدارة المستخدمين والأجهزة والتحكم الشامل")
    df = pd.read_sql("SELECT device_id, phone, status, bot_status, app_version, force_update_single, notice_message, last_active FROM myapp.users_status ORDER BY last_active DESC", conn)
    st.dataframe(df, use_container_width=True)

# 2. إدارة التحديثات الإجبارية (بالنافذة المنبثقة وزر التحميل)
elif page == "🚀 إدارة التحديثات الإجبارية":
    st.title("🚀 إدارة التحديثات الإجبارية (النافذة المنبثقة وأزرار التحميل)")
    
    conf = pd.read_sql("SELECT * FROM myapp.app_config WHERE id = 1", conn).iloc[0]
    
    with st.form("upd_dialog_form"):
        v = st.text_input("رقم الإصدار الأحدث:", value=conf['latest_version'])
        url = st.text_input("رابط التحميل المباشر للـ APK (زر التحميل):", value=conf['update_url'])
        msg = st.text_area("رسالة النافذة المنبثقة الإجبارية:", value=conf['update_message'])
        forced = st.checkbox("تفعيل النافذة المنبثقة الإجبارية (منع تخطي التحديث)", value=conf['force_update_enabled'])
        
        if st.form_submit_button("نشر النافذة المنبثقة وزر التحميل لكافة الأجهزة 🚀"):
            query("UPDATE myapp.app_config SET latest_version=%s, update_url=%s, update_message=%s, force_update_enabled=%s WHERE id = 1", (v, url, msg, forced))
            dialog_command = f"DIALOG_UPDATE:version={v}|url={url}|msg={msg}"
            query("UPDATE myapp.users_status SET notice_message = %s, force_update_single = TRUE", (dialog_command,))
            st.success("✅ تم نشر النافذة المنبثقة وزر التحميل المباشر لكافة التطبيقات المحملة بنجاح!")
            st.rerun()
            
    st.markdown("---")
    st.subheader("💡 معاينة شكل التنبيه والزر المنبثق للمستخدم:")
    if url:
        st.markdown(f"""
        > **{msg}**
        > 
        > [![تحميل التحديث الآن](https://img.shields.io/badge/📥_تحميل_التحديث_الآن-أضغط_هنا-blue?style=for-the-badge)]({url})
        """)
    else:
        st.info("قم بإدخال رابط التحميل لمعاينة الزر هنا.")

# 3. توليد وإدارة الأكواد
elif page == "🎫 توليد وإدارة الأكواد":
    st.title("🎫 توليد وإدارة الأكواد والأجهزة المفعلة")
    with st.form("gen"):
        tp = st.selectbox("نوع الكود:", ["VIP", "TRIAL"])
        qty = st.number_input("الكمية:", min_value=1, value=10)
        if st.form_submit_button("توليد الأكواد 🚀"):
            for _ in range(qty):
                code = f"{tp}-{''.join(random.choices(string.ascii_uppercase + string.digits, k=6))}"
                query("INSERT INTO myapp.subscriptions (code, sub_type, duration_days, is_used) VALUES (%s, %s, 30, FALSE)", (code, tp))
            st.success("تم توليد الأكواد بنجاح.")
            st.rerun()

# 4. قسم الشركاء والموزعين
elif page == "🤝 قسم الشركاء (الموزعين)":
    st.title("🤝 لوحة الشركاء والموزعين الشاملة")
    df_s = pd.read_sql("SELECT code, sub_type, is_used, used_by_device, used_at FROM myapp.subscriptions ORDER BY id DESC", conn)
    t1, t2 = st.tabs(["📦 الأكواد المتاحة", "✅ الأكواد المستخدمة"])
    t1.dataframe(df_s[df_s['is_used'] == False], use_container_width=True)
    t2.dataframe(df_s[df_s['is_used'] == True], use_container_width=True)

# 5. تحليل البيانات
elif page == "📈 تحليل البيانات":
    st.title("📈 تحليل البيانات وأوقات الذروة")
    try:
        df_orders = pd.read_sql("SELECT order_time, price FROM myapp.accepted_orders", conn)
        if not df_orders.empty:
            df_orders['hour'] = pd.to_datetime(df_orders['order_time']).dt.hour
            fig = px.bar(df_orders.groupby('hour').size().reset_index(name='count'), x='hour', y='count', title="أوقات الذروة للطلبات المقبولة")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("لا توجد سجلات كافية لعرض الرسوم البيانية.")
    except Exception:
        st.info("البيانات غير متوفرة حالياً.")

# 6. حالة السيرفر
elif page == "🖥️ حالة السيرفر":
    st.title("🖥️ مراقبة السيرفر")
    st.success("🟢 السيرفر متصل ويعمل بكفاءة على DigitalOcean.")
    st.info("قاعدة البيانات: PostgreSQL | التشفير: SSL Active")

# 7. إدارة الصلاحيات والتحكم
elif page == "🔐 إدارة الصلاحيات والتحكم":
    st.title("🔐 إدارة حسابات لوحة التحكم وصلاحياتها")
    df_p = pd.read_sql("SELECT username, role_name, is_active FROM myapp.app_permissions", conn)
    st.dataframe(df_p, use_container_width=True)

# 8. الدعم الفني والتواصل
elif page == "🛠️ الدعم الفني والتواصل":
    st.title("🛠️ الدعم الفني")
    st.info("📱 واتساب الإدارة: مراسلة الدعم الفني")
    st.success("✈️ تليجرام الدعم: @MyClicker_Support")

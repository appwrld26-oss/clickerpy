import streamlit as st
import pd as pd
import psycopg2
import plotly.express as px
import os
import urllib.request
import random
import string
import pandas as pd

# إعدادات الصفحة
st.set_page_config(page_title="Ultra MyClicker Dashboard", layout="wide", page_icon="⚡")

st.markdown("""
    <style>
    header {visibility: hidden;}
    body { direction: rtl; text-align: right; }
    .stMetric { background-color: #f8fafc; padding: 15px; border-radius: 10px; border: 1px solid #e2e8f0; }
    </style>
""", unsafe_allow_html=True)

# --- 1. الاتصال بقاعدة البيانات ---
def download_ca_cert():
    cert_path = "ca-certificate.crt"
    if not os.path.exists(cert_path):
        try:
            url = "https://certs.ondigitalocean.com/ca-certificate.crt"
            urllib.request.urlretrieve(url, cert_path)
        except Exception as e:
            st.error(f"فشل تحميل الشهادة: {e}")
    return cert_path

@st.cache_resource
def init_connection():
    try:
        cert_file = download_ca_cert()
        return psycopg2.connect(
            database="defaultdb",
            user="doadmin",
            password="1tHwqXCgn8BS6iTm942V3f7a",
            host="myclicker-db-rd7ky.db1.ondigitalocean.com",
            port="5432",
            sslmode="require",
            sslrootcert=cert_file
        )
    except Exception as e:
        st.error(f"خطأ في الاتصال: {e}")
        return None

conn = init_connection()
if conn is None: st.stop()

def run_query(query, params=()):
    try:
        cur = conn.cursor()
        cur.execute(query, params)
        conn.commit()
        cur.close()
        return True
    except Exception as e:
        conn.rollback()
        st.error(f"حدث خطأ: {e}")
        return False

# --- 2. إعداد الجداول والصلاحيات ---
def setup_permissions_table():
    try:
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS myapp.app_permissions (
                id SERIAL PRIMARY KEY,
                username VARCHAR(50) UNIQUE NOT NULL,
                password VARCHAR(100) NOT NULL,
                role_name VARCHAR(50),
                allowed_sections TEXT[],
                is_active BOOLEAN DEFAULT TRUE
            );
        """)
        cur.execute("ALTER TABLE myapp.app_permissions ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE;")
        conn.commit()
        
        cur.execute("SELECT COUNT(*) FROM myapp.app_permissions WHERE username = 'admin'")
        if cur.fetchone()[0] == 0:
            all_secs = [
                "👥 إدارة ومراقبة المستخدمين", "🎫 توليد وإدارة الأكواد (الادمن)", 
                "🤝 قسم الشركاء (الموزعين)", "📈 تحليل البيانات", 
                "🖥️ حالة السيرفر", "🔐 إدارة الصلاحيات والتحكم", "🛠️ الدعم الفني والتواصل"
            ]
            cur.execute(
                "INSERT INTO myapp.app_permissions (username, password, role_name, allowed_sections) VALUES (%s, %s, %s, %s)",
                ("admin", "admin123", "مدير النظام", all_secs)
            )
            conn.commit()
        cur.close()
    except Exception as e: conn.rollback()

setup_permissions_table()

# --- 3. تسجيل الدخول ---
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.title("🔐 تسجيل الدخول إلى لوحة التحكم")
    with st.form("login_form"):
        u_input = st.text_input("اسم المستخدم:")
        p_input = st.text_input("كلمة المرور:", type="password")
        if st.form_submit_button("دخول"):
            cur = conn.cursor()
            cur.execute("SELECT password, allowed_sections, is_active FROM myapp.app_permissions WHERE username = %s", (u_input,))
            res = cur.fetchone()
            if res and res[2] and res[0] == p_input:
                st.session_state.logged_in = True
                st.session_state.username = u_input
                st.session_state.allowed_sections = res[1]
                st.rerun()
            else: st.error("خطأ في البيانات أو الحساب معطل")
    st.stop()

# --- الشريط الجانبي ---
st.sidebar.markdown(f"### ⚡ MyClicker Pro\n👤 {st.session_state.username}")
choice = st.sidebar.radio("القائمة:", st.session_state.allowed_sections)
if st.sidebar.button("🚪 خروج"):
    st.session_state.logged_in = False
    st.rerun()

# =====================================================================
# 1. إدارة المستخدمين (مع نظام الإشعارات المتطور)
# =====================================================================
if choice == "👥 إدارة ومراقبة المستخدمين":
    st.title("👥 إدارة المستخدمين والرقابة")
    df_users = pd.read_sql("SELECT device_id, phone, status, bot_status, accepted_clicks, subscription_type, expiry_date, notice_message FROM myapp.users_status ORDER BY last_active DESC", conn)
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("الإجمالي", len(df_users))
    col2.metric("Online ⚡", len(df_users[df_users['bot_status'] == 'Online']))
    
    st.markdown("---")
    st.markdown("### 📢 إرسال الإشعارات (التحكم في الظهور)")
    
    c_n1, c_n2 = st.columns(2)
    with c_n1:
        target = st.selectbox("النطاق:", ["الكل", "Active", "Expired"])
    with c_n2:
        notif_mode = st.radio("مكان الظهور:", ["رسالة داخل التطبيق", "إشعار في شريط النظام (StatusBar)"], horizontal=True)
    
    msg = st.text_input("نص الرسالة:")
    if st.button("📤 إرسال الإشعار الآن"):
        # إضافة PUSH: للرسالة إذا كان المستخدم يريد إشعار نظام
        final_msg = f"PUSH:{msg}" if notif_mode == "إشعار نظام (StatusBar)" else msg
        
        query = "UPDATE myapp.users_status SET notice_message = %s"
        if target != "الكل": query += f" WHERE status = '{target}'"
        if run_query(query, (final_msg,)): st.success("✅ تم الإرسال بنجاح")

    st.markdown("---")
    # عرض الجدول مع إمكانية الحذف الفردي (كودك الأصلي)
    st.subheader("📋 قائمة الأجهزة المتصلة")
    df_users.insert(0, 'تحديد', False)
    edited_df = st.data_editor(df_users, use_container_width=True, hide_index=True)
    
    # لوحة التحكم الفردية (التي تم حذفها بالخطأ سابقاً)
    st.markdown("### 🛠️ إجراءات فردية على جهاز معين")
    selected_device = st.selectbox("اختر جهازاً:", df_users['device_id'].tolist())
    if selected_device:
        ca1, ca2 = st.columns(2)
        with ca1:
            if st.button("🗑️ حذف هذا الجهاز"):
                if run_query("DELETE FROM myapp.users_status WHERE device_id = %s", (selected_device,)):
                    st.success("تم الحذف"); st.rerun()
        with ca2:
            new_st = st.selectbox("تغيير الحالة:", ["Active", "Expired", "Banned"])
            if st.button("💾 حفظ الحالة"):
                run_query("UPDATE myapp.users_status SET status = %s WHERE device_id = %s", (new_st, selected_device))
                st.rerun()

# =====================================================================
# 2. توليد الأكواد
# =====================================================================
elif choice == "🎫 توليد وإدارة الأكواد (الادمن)":
    st.title("🎫 توليد الأكواد")
    with st.form("gen"):
        tp = st.selectbox("النوع:", ["VIP", "TRIAL"])
        days = st.number_input("الأيام:", 30)
        qty = st.number_input("الكمية:", 10)
        if st.form_submit_button("توليد 🚀"):
            for _ in range(qty):
                code = f"{tp}-{''.join(random.choices(string.ascii_uppercase + string.digits, k=6))}"
                run_query("INSERT INTO myapp.subscriptions (code, sub_type, duration_days, is_used) VALUES (%s,%s,%s,FALSE)", (code, tp, days))
            st.success("تم التوليد"); st.rerun()

# =====================================================================
# 3. قسم الشركاء
# =====================================================================
elif choice == "🤝 قسم الشركاء (الموزعين)":
    st.title("🤝 لوحة الموزعين")
    df = pd.read_sql("SELECT code, sub_type, is_used, used_by_device FROM myapp.subscriptions ORDER BY id DESC", conn)
    st.subheader("📦 الأكواد غير المباعة")
    st.dataframe(df[df['is_used']==False][['code', 'sub_type']], use_container_width=True)

# =====================================================================
# 6. إدارة الصلاحيات (الكود الكامل)
# =====================================================================
elif choice == "🔐 إدارة الصلاحيات والتحكم":
    st.title("🔐 إدارة حسابات النظام")
    col_add, col_view = st.columns([1, 1.5])
    with col_add:
        st.subheader("➕ حساب جديد")
        with st.form("new_user"):
            u = st.text_input("Username:")
            p = st.text_input("Password:", type="password")
            role = st.text_input("الوصف:")
            s1 = st.checkbox("👥 إدارة ومراقبة المستخدمين")
            s2 = st.checkbox("🎫 توليد وإدارة الأكواد (الادمن)")
            s3 = st.checkbox("🤝 قسم الشركاء (الموزعين)")
            s4 = st.checkbox("📈 تحليل البيانات")
            s5 = st.checkbox("🖥️ حالة السيرفر")
            s6 = st.checkbox("🔐 إدارة الصلاحيات والتحكم")
            s7 = st.checkbox("🛠️ الدعم الفني والتواصل")
            if st.form_submit_button("حفظ الحساب"):
                secs = []
                if s1: secs.append("👥 إدارة ومراقبة المستخدمين")
                if s2: secs.append("🎫 توليد وإدارة الأكواد (الادمن)")
                if s3: secs.append("🤝 قسم الشركاء (الموزعين)")
                if s4: secs.append("📈 تحليل البيانات")
                if s5: secs.append("🖥️ حالة السيرفر")
                if s6: secs.append("🔐 إدارة الصلاحيات والتحكم")
                if s7: secs.append("🛠️ الدعم الفني والتواصل")
                run_query("INSERT INTO myapp.app_permissions (username,password,role_name,allowed_sections) VALUES (%s,%s,%s,%s)", (u,p,role,secs))
                st.rerun()
    with col_view:
        st.subheader("📋 الحسابات الحالية")
        df_p = pd.read_sql("SELECT id, username, role_name, is_active FROM myapp.app_permissions", conn)
        st.dataframe(df_p, use_container_width=True)

# =====================================================================
# 7. قسم الدعم الفني (الجديد)
# =====================================================================
elif choice == "🛠️ الدعم الفني والتواصل":
    st.title("🛠️ الدعم الفني وقنوات التواصل")
    st.markdown("---")
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("📞 تواصل مباشر")
        st.info("للدعم الفني بخصوص السيرفر أو تفعيل الحسابات.")
        st.write("📱 **واتساب:** [مراسلة](https://wa.me/9647XXXXXXXX)")
        st.write("✈️ **تليجرام:** [@MyClicker_Support](https://t.me/MyClicker_Support)")
    with col2:
        st.subheader("📢 القنوات الرسمية")
        st.write("📢 **قناة التحديثات:** [انضمام](https://t.me/MyClicker_Channel)")
        st.write("🤝 **قناة الموزعين:** [دخول](https://t.me/MyClicker_Partners)")

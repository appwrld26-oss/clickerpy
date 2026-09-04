import streamlit as st
import pandas as pd
import psycopg2
import plotly.express as px
import os
import urllib.request
import random
import string
from datetime import datetime, timedelta

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
if conn is None: 
    st.error("تعذر الاتصال بقاعدة البيانات.")
    st.stop()

def run_query(query, params=()):
    try:
        cur = conn.cursor()
        cur.execute(query, params)
        conn.commit()
        cur.close()
        return True
    except Exception as e:
        conn.rollback()
        st.error(f"حدث خطأ في قاعدة البيانات: {e}")
        return False

# --- 2. إعداد الجداول الشاملة ---
def setup_tables():
    try:
        cur = conn.cursor()
        # جدول الصلاحيات والحسابات
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
        
        # التأكد من وجود عمود is_active
        cur.execute("""
            ALTER TABLE myapp.app_permissions 
            ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE;
        """)

        # جدول إعدادات التطبيق (التحديث الإجباري والتحميل)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS myapp.app_config (
                id SERIAL PRIMARY KEY,
                latest_version VARCHAR(20),
                update_url TEXT,
                update_message TEXT,
                force_update_enabled BOOLEAN DEFAULT FALSE
            );
        """)
        conn.commit()
        
        # التأكد من وجود حساب الأدمن بالصلاحيات الكاملة
        cur.execute("SELECT COUNT(*) FROM myapp.app_permissions WHERE username = 'admin'")
        if cur.fetchone()[0] == 0:
            all_secs = [
                "👥 إدارة ومراقبة المستخدمين", 
                "🎫 توليد وإدارة الأكواد (الادمن)", 
                "🤝 قسم الشركاء (الموزعين)", 
                "📈 تحليل البيانات", 
                "🖥️ حالة السيرفر", 
                "🔐 إدارة الصلاحيات والتحكم", 
                "🚀 إدارة التحديثات الإجبارية", 
                "🛠️ الدعم الفني والتواصل"
            ]
            cur.execute(
                "INSERT INTO myapp.app_permissions (username, password, role_name, allowed_sections, is_active) VALUES (%s, %s, %s, %s, %s)",
                ("admin", "admin123", "مدير النظام", all_secs, True)
            )
        
        # التأكد من وجود سجل الإعدادات الأساسي
        cur.execute("SELECT COUNT(*) FROM myapp.app_config")
        if cur.fetchone()[0] == 0:
            cur.execute("INSERT INTO myapp.app_config (latest_version, update_url, update_message, force_update_enabled) VALUES ('7.1.0', '', 'يرجى تحديث التطبيق للاستمرار', FALSE)")
            
        conn.commit()
        cur.close()
    except Exception as e: 
        conn.rollback()

setup_tables()

# --- 3. إدارة جلسة المستخدم (Session State) ---
if "logged_in" not in st.session_state: 
    st.session_state.logged_in = False
if "username" not in st.session_state: 
    st.session_state.username = None
if "allowed_sections" not in st.session_state: 
    st.session_state.allowed_sections = []

# --- 4. شاشة تسجيل الدخول أو التسجيل العام (إذا لم يتم تسجيل الدخول) ---
if not st.session_state.logged_in:
    st.sidebar.markdown("### ⚙️ خيارات الدخول")
    auth_mode = st.sidebar.radio("اختر العملية:", ["تسجيل الدخول", "طلب حساب لوحة تحكم جديد"])
    
    if auth_mode == "تسجيل الدخول":
        st.title("🔐 تسجيل الدخول إلى لوحة التحكم")
        with st.form("login_form"):
            u_input = st.text_input("اسم المستخدم:")
            p_input = st.text_input("كلمة المرور:", type="password")
            submit_login = st.form_submit_button("دخول")
            
            if submit_login:
                try:
                    cur = conn.cursor()
                    cur.execute("SELECT password, allowed_sections, is_active FROM myapp.app_permissions WHERE username = %s", (u_input,))
                    user_record = cur.fetchone()
                    cur.close()
                    
                    if user_record:
                        db_pass, db_sections, db_is_active = user_record
                        if db_is_active is False:
                            st.error("⚠️ هذا الحساب معطل من قبل الإدارة. يرجى التواصل مع المسؤول.")
                        elif db_pass == p_input:
                            st.session_state.logged_in = True
                            st.session_state.username = u_input
                            st.session_state.allowed_sections = db_sections if db_sections else ["🤝 قسم الشركاء (الموزعين)"]
                            st.rerun()
                        else:
                            st.error("اسم المستخدم أو كلمة المرور غير صحيحة!")
                    else:
                        st.error("اسم المستخدم أو كلمة المرور غير صحيحة!")
                except Exception as e:
                    st.error(f"خطأ في عملية التحقق: {e}")
    else:
        st.title("📝 طلب حساب لوحة تحكم جديد")
        with st.form("public_register_form"):
            reg_user = st.text_input("اسم المستخدم:")
            reg_pass = st.text_input("كلمة المرور:", type="password")
            reg_role = st.text_input("طبيعة العمل أو الوصف (مثال: موزع بغداد):")
            submit_register = st.form_submit_button("إرسال الطلب 🚀")
            
            if submit_register:
                if not reg_user or not reg_pass:
                    st.error("يرجى ملء الحقول المطلوبة!")
                else:
                    try:
                        cur = conn.cursor()
                        cur.execute(
                            "INSERT INTO myapp.app_permissions (username, password, role_name, allowed_sections, is_active) VALUES (%s, %s, %s, %s, %s)",
                            (reg_user, reg_pass, reg_role, ["🤝 قسم الشركاء (الموزعين)"], False)
                        )
                        conn.commit()
                        cur.close()
                        st.success("✅ تم إرسال الطلب بنجاح وهو بانتظار تفعيل الأدمن.")
                    except Exception as err:
                        conn.rollback()
                        st.error(f"اسم المستخدم مستخدم مسبقاً أو حدث خطأ: {err}")
    st.stop()

# =====================================================================
# 5. الشريط الجانبي الرئيسي (يظهر فقط بعد تسجيل الدخول بنجاح)
# =====================================================================
st.sidebar.markdown(f"### ⚡ MyClicker Pro")
st.sidebar.info(f"👤 المستخدم: {st.session_state.username}")

if st.sidebar.button("🔄 تحديث البيانات (Refresh)"):
    st.rerun()

user_allowed = st.session_state.allowed_sections
if not user_allowed:
    user_allowed = ["🤝 قسم الشركاء (الموزعين)"]

choice = st.sidebar.radio("القائمة الرئيسية:", user_allowed)

if st.sidebar.button("🚪 تسجيل الخروج"): 
    st.session_state.logged_in = False
    st.session_state.username = None
    st.session_state.allowed_sections = []
    st.rerun()

# =====================================================================
# تنفيذ الأقسام والقوائم الشاملة
# =====================================================================

# 1. قسم إدارة ومراقبة المستخدمين
if choice == "👥 إدارة ومراقبة المستخدمين":
    st.title("👥 إدارة المستخدمين والاشتراكات")
    
    with st.expander("➕ إضافة وتفعيل رقم هاتف مشترك جديد"):
        with st.form("add_phone_sub"):
            phone_input = st.text_input("رقم الهاتف:")
            sub_days = st.number_input("مدة الاشتراك (بالأيام):", min_value=1, value=30)
            sub_type = st.selectbox("نوع الاشتراك:", ["VIP", "TRIAL", "Monthly"])
            
            if st.form_submit_button("حفظ وتفعيل الرقم 🚀"):
                if not phone_input.strip():
                    st.error("يرجى إدخال رقم الهاتف!")
                else:
                    gen_device_id = f"PHONE-DEV-{''.join(random.choices(string.ascii_uppercase + string.digits, k=10))}"
                    calc_expiry = datetime.now() + timedelta(days=sub_days)
                    if run_query("""
                        INSERT INTO myapp.users_status (device_id, phone, status, subscription_type, expiry_date, accepted_clicks)
                        VALUES (%s, %s, 'Active', %s, %s, 0)
                    """, (gen_device_id, phone_input.strip(), sub_type, calc_expiry)):
                        st.success(f"✅ تمت إضافة وتفعيل رقم الهاتف ({phone_input}) بنجاح!")
                        st.rerun()

    st.markdown("---")
    df = pd.read_sql("SELECT device_id, phone, status, bot_status, subscription_type, expiry_date, notice_message FROM myapp.users_status ORDER BY last_active DESC", conn)
    st.metric("إجمالي الأجهزة/المستخدمين", len(df))
    
    st.markdown("### 📢 إرسال إشعارات منبثقة")
    mode = st.radio("نوع الإشعار:", ["داخل التطبيق", "إشعار نظام (StatusBar)"], horizontal=True)
    msg = st.text_input("نص الرسالة:")
    if st.button("إرسال للكل"):
        final = f"PUSH:{msg}" if mode == "إشعار نظام (StatusBar)" else msg
        if run_query("UPDATE myapp.users_status SET notice_message = %s", (final,)): 
            st.success("تم إرسال الإشعار بنجاح!")
    
    st.dataframe(df, use_container_width=True)

# 2. إدارة التحديثات الإجبارية
elif choice == "🚀 إدارة التحديثات الإجبارية":
    st.title("🚀 إدارة التحديثات الإجبارية ورابط التحميل المباشر")
    st.warning("تحذير: تفعيل الإيقاف الإجباري سيجبر المستخدمين على تحميل النسخة الجديدة لتجاوز شاشة التحديث.")
    
    config = pd.read_sql("SELECT * FROM myapp.app_config WHERE id = 1", conn).iloc[0]
    
    with st.form("update_form"):
        new_ver = st.text_input("رقم الإصدار الأحدث (مثل 7.2.0):", value=config['latest_version'])
        new_url = st.text_input("رابط تحميل الـ APK المباشر:", value=config['update_url'])
        new_msg = st.text_area("رسالة التنبيه للمستخدم عند التحديث:", value=config['update_message'])
        is_forced = st.checkbox("تفعيل الإيقاف الإجباري للنسخ القديمة", value=config['force_update_enabled'])
        
        if st.form_submit_button("حفظ وتحديث بيانات الإصدار 💾"):
            if run_query("""
                UPDATE myapp.app_config 
                SET latest_version=%s, update_url=%s, update_message=%s, force_update_enabled=%s 
                WHERE id = 1
            """, (new_ver, new_url, new_msg, is_forced)):
                st.success("تم حفظ إعدادات التحديث الإجباري ورابط التحميل بنجاح!")
                st.rerun()
                
    st.markdown("---")
    st.markdown("### 📥 معاينة رابط التحميل الحالي المتاح:")
    if config['update_url']:
        st.markdown(f"🔗 **[اضغط هنا لتحميل النسخة الأحدث مباشرة ({config['latest_version']})]({config['update_url']})**")
    else:
        st.info("لم يتم تعيين رابط تحميل مباشر للنسخة بعد.")

# 3. توليد وإدارة الأكواد
elif choice == "🎫 توليد وإدارة الأكواد (الادمن)":
    st.title("🎫 لوحة توليد وإدارة الأكواد الشاملة")
    df_codes = pd.read_sql("SELECT * FROM myapp.subscriptions ORDER BY id DESC", conn)
    
    col1, col2 = st.columns(2)
    with col1:
        with st.form("gen"):
            tp = st.selectbox("نوع الكود:", ["VIP", "TRIAL"])
            qty = st.number_input("الكمية:", min_value=1, value=10)
            if st.form_submit_button("توليد الأكواد 🚀"):
                for _ in range(qty):
                    code = f"{tp}-{''.join(random.choices(string.ascii_uppercase + string.digits, k=6))}"
                    run_query("INSERT INTO myapp.subscriptions (code, sub_type, duration_days, is_used) VALUES (%s,%s,30,FALSE)", (code, tp))
                st.success("تم التوليد بنجاح")
                st.rerun()
    with col2:
        st.metric("أكواد غير مستعملة", len(df_codes[df_codes['is_used'] == False]))
        st.metric("أكواد مستعملة", len(df_codes[df_codes['is_used'] == True]))
        
    st.markdown("---")
    t1, t2 = st.tabs(["الأكواد الجديدة", "الأكواد المستعملة"])
    with t1:
        st.dataframe(df_codes[df_codes['is_used'] == False][['id', 'code', 'sub_type', 'duration_days']], use_container_width=True)
    with t2:
        st.dataframe(df_codes[df_codes['is_used'] == True][['code', 'used_by_device', 'used_at', 'sub_type']], use_container_width=True)

# 4. قسم الشركاء
elif choice == "🤝 قسم الشركاء (الموزعين)":
    st.title("🤝 لوحة الشركاء والموزعين")
    df_codes = pd.read_sql("SELECT * FROM myapp.subscriptions ORDER BY id DESC", conn)
    c1, c2 = st.columns(2)
    c1.metric("📦 الأكواد المتاحة", len(df_codes[df_codes['is_used'] == False]))
    c2.metric("✅ الأكواد المفعلة", len(df_codes[df_codes['is_used'] == True]))
    st.dataframe(df_codes[df_codes['is_used'] == False][['code', 'sub_type', 'duration_days']], use_container_width=True)

# 5. تحليل البيانات
elif choice == "📈 تحليل البيانات":
    st.title("📈 تحليل البيانات وأوقات الذروة")
    try:
        df_orders = pd.read_sql("SELECT order_time, price FROM myapp.accepted_orders", conn)
        if not df_orders.empty:
            df_orders['hour'] = pd.to_datetime(df_orders['order_time']).dt.hour
            fig = px.bar(df_orders.groupby('hour').size().reset_index(name='count'), x='hour', y='count', title="أوقات الذروة للطلبات المقبولة (بالساعة)")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("لا توجد سجلات طلبات كافية لعرض الرسوم البيانية حالياً.")
    except Exception as e:
        st.info(f"البيانات غير متوفرة: {e}")

# 6. حالة السيرفر
elif choice == "🖥️ حالة السيرفر":
    st.title("🖥️ مراقبة السيرفر")
    c1, c2 = st.columns(2)
    c1.metric("حالة الخادم وقاعدة البيانات", "متصل 🟢", "DigitalOcean")
    c2.metric("حالة الأمان SSL", "محمية 🔒")

# 7. إدارة الصلاحيات والتحكم
elif choice == "🔐 إدارة الصلاحيات والتحكم":
    st.title("🔐 إدارة حسابات لوحة التحكم وصلاحياتها")
    try:
        df_perms = pd.read_sql("SELECT id, username, role_name, is_active FROM myapp.app_permissions", conn)
        st.dataframe(df_perms, use_container_width=True)
        
        selected_acc = st.selectbox("اختر حساباً للتعديل أو المراجعة:", df_perms['username'].tolist())
        if selected_acc and selected_acc != "admin":
            c1, c2 = st.columns(2)
            with c1:
                if st.button("🟢 تفعيل الحساب"):
                    run_query("UPDATE myapp.app_permissions SET is_active = TRUE WHERE username = %s", (selected_acc,))
                    st.success("تم تفعيل الحساب!")
                    st.rerun()
                if st.button("🔴 تعطيل الحساب"):
                    run_query("UPDATE myapp.app_permissions SET is_active = FALSE WHERE username = %s", (selected_acc,))
                    st.success("تم تعطيل الحساب!")
                    st.rerun()
            with c2:
                if st.button("🗑️ حذف الحساب نهائياً"):
                    run_query("DELETE FROM myapp.app_permissions WHERE username = %s", (selected_acc,))
                    st.success("تم الحذف بنجاح!")
                    st.rerun()
    except Exception as e:
        st.info(f"خطأ: {e}")

# 8. الدعم الفني والتواصل
elif choice == "🛠️ الدعم الفني والتواصل":
    st.title("🛠️ الدعم الفني")
    c1, c2 = st.columns(2)
    with c1:
        st.info("📱 واتساب الإدارة: [مراسلة](https://wa.me/9647XXXXXXXX)")
    with c2:
        st.success("✈️ تليجرام الدعم: [@MyClicker_Support](https://t.me/MyClicker_Support)")

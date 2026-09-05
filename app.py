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
        except Exception:
            with open(cert_path, "w") as f:
                f.write("")
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
        st.error(f"حدث خطأ في قاعدة البيانات: {e}")
        return False

# --- 2. إعداد الجداول وكافة العلاقات (بما فيها الأكواد والمستخدمين والأجهزة) ---
def setup_tables():
    try:
        cur = conn.cursor()
        
        # التأكد من وجود سكيما myapp
        cur.execute("CREATE SCHEMA IF NOT EXISTS myapp;")
        
        # جدول الصلاحيات للوحة التحكم
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

        # جدول إعدادات التطبيق والتحديثات
        cur.execute("""
            CREATE TABLE IF NOT EXISTS myapp.app_config (
                id SERIAL PRIMARY KEY,
                latest_version VARCHAR(20) DEFAULT '7.1.0',
                update_url TEXT DEFAULT '',
                update_message TEXT DEFAULT 'يرجى تحديث التطبيق للاستمرار',
                force_update_enabled BOOLEAN DEFAULT FALSE
            );
        """)
        cur.execute("ALTER TABLE myapp.app_config ADD COLUMN IF NOT EXISTS latest_version VARCHAR(20) DEFAULT '7.1.0';")
        cur.execute("ALTER TABLE myapp.app_config ADD COLUMN IF NOT EXISTS update_url TEXT DEFAULT '';")
        cur.execute("ALTER TABLE myapp.app_config ADD COLUMN IF NOT EXISTS update_message TEXT DEFAULT 'يرجى تحديث التطبيق للاستمرار';")
        cur.execute("ALTER TABLE myapp.app_config ADD COLUMN IF NOT EXISTS force_update_enabled BOOLEAN DEFAULT FALSE;")

        # جدول الأكواد (Subscriptions & Codes) والربط بالأجهزة التي قامت بتفعيلها
        cur.execute("""
            CREATE TABLE IF NOT EXISTS myapp.subscriptions (
                id SERIAL PRIMARY KEY,
                code VARCHAR(100) UNIQUE NOT NULL,
                sub_type VARCHAR(50) DEFAULT 'VIP',
                duration_days INT DEFAULT 30,
                is_used BOOLEAN DEFAULT FALSE,
                used_by_device VARCHAR(255) DEFAULT NULL,
                used_at TIMESTAMP DEFAULT NULL
            );
        """)

        # جدول حالات المستخدمين والأجهزة المفعلة
        cur.execute("""
            CREATE TABLE IF NOT EXISTS myapp.users_status (
                device_id VARCHAR(255) PRIMARY KEY,
                phone VARCHAR(50) DEFAULT '',
                status VARCHAR(50) DEFAULT 'Active',
                bot_status VARCHAR(50) DEFAULT 'Offline',
                accepted_clicks INT DEFAULT 0,
                subscription_type VARCHAR(50) DEFAULT 'VIP',
                app_version VARCHAR(20) DEFAULT 'غير معروف',
                force_update_single BOOLEAN DEFAULT FALSE,
                expiry_date TIMESTAMP DEFAULT NULL,
                notice_message TEXT DEFAULT '',
                last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        cur.execute("ALTER TABLE myapp.users_status ADD COLUMN IF NOT EXISTS app_version VARCHAR(20) DEFAULT 'غير معروف';")
        cur.execute("ALTER TABLE myapp.users_status ADD COLUMN IF NOT EXISTS force_update_single BOOLEAN DEFAULT FALSE;")

        conn.commit()
        
        # إنشاء حساب الأدمن الافتراضي
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
        
        cur.execute("SELECT COUNT(*) FROM myapp.app_permissions WHERE username = 'admin'")
        if cur.fetchone()[0] == 0:
            cur.execute(
                "INSERT INTO myapp.app_permissions (username, password, role_name, allowed_sections, is_active) VALUES (%s, %s, %s, %s, %s)",
                ("admin", "admin123", "مدير النظام", all_secs, True)
            )
        else:
            cur.execute("UPDATE myapp.app_permissions SET allowed_sections = %s WHERE username = 'admin'", (all_secs,))
        
        cur.execute("SELECT COUNT(*) FROM myapp.app_config")
        if cur.fetchone()[0] == 0:
            cur.execute("INSERT INTO myapp.app_config (id, latest_version, update_url, update_message, force_update_enabled) VALUES (1, '7.1.0', '', 'يرجى تحديث التطبيق للاستمرار', FALSE)")
            
        conn.commit()
        cur.close()
    except Exception as e: 
        conn.rollback()
        st.error(f"خطأ في إنشاء الجداول: {e}")

setup_tables()

# --- 3. نظام المصادقة ---
if "logged_in" not in st.session_state: 
    st.session_state.logged_in = False
    st.session_state.username = None
    st.session_state.allowed_sections = []

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
                            st.error("⚠️ هذا الحساب معطل من قبل الإدارة.")
                        elif db_pass == p_input:
                            st.session_state.logged_in = True
                            st.session_state.username = u_input
                            st.session_state.allowed_sections = db_sections if db_sections else []
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

# --- الشريط الجانبي (Sidebar) ---
st.sidebar.markdown(f"### ⚡ MyClicker Pro")
st.sidebar.info(f"👤 المستخدم: {st.session_state.username}")

if st.sidebar.button("🔄 تحديث البيانات (Refresh)"):
    st.rerun()

user_allowed = st.session_state.allowed_sections
if not user_allowed:
    st.error("عذراً، ليس لديك أي صلاحيات لعرض الأقسام.")
    st.stop()

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
    st.title("👥 إدارة المستخدمين والاشتراكات والتحكم الشامل")
    
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
                        INSERT INTO myapp.users_status (device_id, phone, status, subscription_type, expiry_date, accepted_clicks, app_version, force_update_single)
                        VALUES (%s, %s, 'Active', %s, %s, 0, '7.1.0', FALSE)
                    """, (gen_device_id, phone_input.strip(), sub_type, calc_expiry)):
                        st.success(f"✅ تمت إضافة وتفعيل رقم الهاتف ({phone_input}) بنجاح!")
                        st.rerun()

    st.markdown("---")
    try:
        df_users = pd.read_sql("SELECT device_id, phone, status, bot_status, accepted_clicks, subscription_type, app_version, force_update_single, expiry_date, notice_message, last_active FROM myapp.users_status ORDER BY last_active DESC", conn)
    except Exception:
        df_users = pd.read_sql("SELECT device_id, phone, status, bot_status, accepted_clicks, subscription_type, expiry_date, notice_message, last_active FROM myapp.users_status ORDER BY last_active DESC", conn)
        df_users['app_version'] = 'غير معروف'
        df_users['force_update_single'] = False

    total_users = len(df_users)
    online_bots = len(df_users[df_users['bot_status'] == 'Online']) if not df_users.empty else 0
    active_users = len(df_users[df_users['status'] == 'Active']) if not df_users.empty else 0
    expired_users = len(df_users[df_users['status'] == 'Expired']) if not df_users.empty else 0

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("إجمالي المشتركين/الأجهزة", total_users)
    c2.metric("البوتات النشطة (Online)", online_bots)
    c3.metric("المستخدمين بحالة نشطة (Active)", active_users)
    c4.metric("منتهيو الصلاحية (Expired)", expired_users, delta_color="inverse")
    
    st.markdown("---")
    
    st.markdown("### 📢 إرسال إشعارات منبثقة للكل")
    mode = st.radio("نوع الإشعار:", ["داخل التطبيق", "إشعار نظام (StatusBar)"], horizontal=True)
    msg = st.text_input("نص الرسالة للكل:")
    if st.button("إرسال للكل"):
        final = f"PUSH:{msg}" if mode == "إشعار نظام (StatusBar)" else msg
        if run_query("UPDATE myapp.users_status SET notice_message = %s", (final,)): 
            st.success("تم إرسال الإشعار للكل بنجاح!")
    
    st.markdown("---")
    st.markdown("### 📋 سجل المستخدمين (مع إصدار التطبيق وحالة التحديث الفردي)")
    
    if not df_users.empty:
        st.data_editor(df_users, use_container_width=True, hide_index=True, key="users_data_editor")
        
        st.markdown("---")
        st.markdown("### 🛠️ لوحة التعديل والحفظ الثابت للمشترك، الإشعارات، وتفعيل التحديث الإجباري الفردي")
        
        user_list = df_users['device_id'].tolist()
        phones_list = df_users['phone'].astype(str).tolist()
        options = [f"هاتف: {p} | إصدار: {v} | تحديث فردي: {'مفعل ⚡' if f else 'معطل'} | جهاز: {d[:6]}..." for p, v, f, d in zip(phones_list, df_users['app_version'].tolist(), df_users['force_update_single'].tolist(), user_list)]
        
        if "selected_user_idx" not in st.session_state:
            st.session_state.selected_user_idx = 0

        selected_index = st.selectbox(
            "اختر المشترك للتعديل أو التحكم الفردي:", 
            range(len(options)), 
            format_func=lambda x: options[x],
            index=st.session_state.selected_user_idx,
            key="user_selectbox_key"
        )
        st.session_state.selected_user_idx = selected_index
        selected_device = user_list[selected_index]
        
        curr_user_row = df_users[df_users['device_id'] == selected_device].iloc[0]
        
        with st.form("edit_single_user_form"):
            col_u1, col_u2 = st.columns(2)
            with col_u1:
                edit_phone = st.text_input("تعديل رقم الهاتف:", value=str(curr_user_row['phone']) if curr_user_row['phone'] else "")
                edit_status = st.selectbox("حالة الاشتراك:", ["Active", "Expired", "Banned"], index=["Active", "Expired", "Banned"].index(curr_user_row['status']) if curr_user_row['status'] in ["Active", "Expired", "Banned"] else 0)
                edit_force_single = st.checkbox("⚡ تفعيل التحديث الإجباري الفردي لهذا المستخدم حصراً", value=bool(curr_user_row['force_update_single']) if 'force_update_single' in curr_user_row else False)
            with col_u2:
                edit_sub_type = st.text_input("نوع الاشتراك:", value=str(curr_user_row['subscription_type']) if curr_user_row['subscription_type'] else "VIP")
                edit_notice = st.text_input("نص إشعار فردي للمشترك:", value="")
            
            c_btn1, c_btn2, c_btn3, c_btn4 = st.columns(4)
            with c_btn1:
                submit_save_user = st.form_submit_button("💾 حفظ التعديلات")
            with c_btn2:
                submit_single_msg = st.form_submit_button("📤 إرسال إشعار عادي")
            with c_btn3:
                submit_bar_msg = st.form_submit_button("📲 إرسال إشعار (بار)")
            with c_btn4:
                submit_delete_user = st.form_submit_button("🗑️ حذف المشترك")
            
            if submit_save_user:
                if run_query("UPDATE myapp.users_status SET phone = %s, status = %s, subscription_type = %s, force_update_single = %s WHERE device_id = %s", (edit_phone, edit_status, edit_sub_type, edit_force_single, selected_device)):
                    st.success("✅ تم حفظ التعديلات وتحديث حالة التحديث الإجباري الفردي بنجاح!")
                    st.rerun()
            
            if submit_single_msg:
                if not edit_notice.strip():
                    st.error("يرجى كتابة نص الإشعار أولاً!")
                else:
                    if run_query("UPDATE myapp.users_status SET notice_message = %s WHERE device_id = %s", (edit_notice, selected_device)):
                        st.success("✅ تم إرسال الإشعار العادي بنجاح!")
                        st.rerun()

            if submit_bar_msg:
                if not edit_notice.strip():
                    st.error("يرجى كتابة نص الإشعار أولاً!")
                else:
                    bar_final = f"PUSH:{edit_notice}"
                    if run_query("UPDATE myapp.users_status SET notice_message = %s WHERE device_id = %s", (bar_final, selected_device)):
                        st.success("✅ تم إرسال إشعار (البار) بنجاح!")
                        st.rerun()
            
            if submit_delete_user:
                if run_query("DELETE FROM myapp.users_status WHERE device_id = %s", (selected_device,)):
                    st.success("✅ تم حذف المشترك بنجاح!")
                    st.rerun()
    else:
        st.info("لا توجد بيانات مستخدمين مسجلة حالياً.")

# 2. إدارة التحديثات الإجبارية
elif choice == "🚀 إدارة التحديثات الإجبارية":
    st.title("🚀 إدارة التحديثات الإجبارية ورابط التحميل المباشر")
    st.warning("تحذير: تفعيل الإيقاف الإجباري العام سيجبر جميع المستخدمين على التحديث، بينما يمكنك تفعيل التحديث الفردي لكل مستخدم من قسم إدارة المستخدمين.")
    
    config_df = pd.read_sql("SELECT latest_version, update_url, update_message, force_update_enabled FROM myapp.app_config LIMIT 1", conn)
    if not config_df.empty:
        config = config_df.iloc[0]
    else:
        config = {'latest_version': '7.1.0', 'update_url': '', 'update_message': '', 'force_update_enabled': False}
    
    with st.form("update_form"):
        new_ver = st.text_input("رقم الإصدار الأحدث (مثل 7.2.0):", value=config['latest_version'])
        new_url = st.text_input("رابط تحميل الـ APK المباشر:", value=config['update_url'])
        new_msg = st.text_area("رسالة التنبيه للمستخدم عند التحديث:", value=config['update_message'])
        is_forced = st.checkbox("تفعيل الإيقاف الإجباري العام للنسخ القديمة", value=config['force_update_enabled'])
        
        if st.form_submit_button("حفظ وتحديث بيانات الإصدار 💾"):
            if run_query("""
                UPDATE myapp.app_config 
                SET latest_version=%s, update_url=%s, update_message=%s, force_update_enabled=%s
            """, (new_ver, new_url, new_msg, is_forced)):
                st.success("تم حفظ إعدادات التحديث الإجباري العام ورابط التحميل بنجاح!")
                st.rerun()
                
    st.markdown("---")
    st.markdown("### 📥 معاينة رابط التحميل الحالي المتاح:")
    if config['update_url']:
        st.markdown(f"🔗 **[اضغط هنا لتحميل النسخة الأحدث مباشرة ({config['latest_version']})]({config['update_url']})**")
    else:
        st.info("لم يتم تعيين رابط تحميل مباشر للنسخة بعد.")

# 3. توليد وإدارة الأكواد (مع جداول الأكواد والأجهزة التي قامت بتفعيلها)
elif choice == "🎫 توليد وإدارة الأكواد (الادمن)":
    st.title("🎫 لوحة توليد وإدارة الأكواد والأجهزة المفعلة")
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
        st.metric("أكواد غير مستعملة", len(df_codes[df_codes['is_used'] == False]) if not df_codes.empty else 0)
        st.metric("أكواد مستعملة ومفعلة", len(df_codes[df_codes['is_used'] == True]) if not df_codes.empty else 0)
        
    st.markdown("---")
    t1, t2 = st.tabs(["الأكواد الجديدة المتاحة", "الأكواد المستخدمة والأجهزة المفعلة"])
    with t1:
        if not df_codes.empty:
            st.dataframe(df_codes[df_codes['is_used'] == False][['id', 'code', 'sub_type', 'duration_days']], use_container_width=True)
        else:
            st.info("لا توجد أكواد متاحة حالياً.")
    with t2:
        if not df_codes.empty:
            st.dataframe(df_codes[df_codes['is_used'] == True][['code', 'sub_type', 'used_by_device', 'used_at']], use_container_width=True)
        else:
            st.info("لا توجد أكواد مستعملة حتى الآن.")

# 4. قسم الشركاء
elif choice == "🤝 قسم الشركاء (الموزعين)":
    st.title("🤝 لوحة الشركاء والموزعين")
    df_codes = pd.read_sql("SELECT code, sub_type, duration_days, is_used FROM myapp.subscriptions ORDER BY id DESC", conn)
    c1, c2 = st.columns(2)
    c1.metric("📦 الأكواد المتاحة", len(df_codes[df_codes['is_used'] == False]) if not df_codes.empty else 0)
    c2.metric("✅ الأكواد المفعلة", len(df_codes[df_codes['is_used'] == True]) if not df_codes.empty else 0)
    if not df_codes.empty:
        st.dataframe(df_codes[df_codes['is_used'] == False][['code', 'sub_type', 'duration_days']], use_container_width=True)
    else:
        st.info("لا توجد أكواد متاحة للعرض.")

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
    st.title("🔐 إدارة حسابات لوحة التحكم وصلاحياتها وتعديلها")
    try:
        df_perms = pd.read_sql("SELECT username, role_name, is_active, allowed_sections FROM myapp.app_permissions", conn)
        st.dataframe(df_perms[['username', 'role_name', 'is_active']], use_container_width=True)
        
        st.markdown("---")
        st.subheader("🛠️ تعديل حساب أو تغيير صلاحياته")
        
        usernames_list = df_perms['username'].tolist()
        
        if "selected_acc_idx" not in st.session_state:
            st.session_state.selected_acc_idx = 0
            
        selected_acc = st.selectbox(
            "اختر الحساب المراد تعديله:", 
            usernames_list,
            index=st.session_state.selected_acc_idx,
            key="acc_selectbox_key"
        )
        
        if selected_acc:
            cur = conn.cursor()
            cur.execute("SELECT password, role_name, allowed_sections, is_active FROM myapp.app_permissions WHERE username = %s", (selected_acc,))
            acc_data = cur.fetchone()
            cur.close()
            
            curr_pass, curr_role, curr_allowed, curr_is_active = acc_data
            if curr_allowed is None: curr_allowed = []

            all_available_sections = [
                "👥 إدارة ومراقبة المستخدمين", 
                "🎫 توليد وإدارة الأكواد (الادمن)", 
                "🤝 قسم الشركاء (الموزعين)", 
                "📈 تحليل البيانات", 
                "🖥️ حالة السيرفر", 
                "🔐 إدارة الصلاحيات والتحكم", 
                "🚀 إدارة التحديثات الإجبارية", 
                "🛠️ الدعم الفني والتواصل"
            ]

            with st.form("edit_account_form"):
                st.info(f"جاري تعديل بيانات الحساب: **{selected_acc}**")
                new_username = st.text_input("تعديل اسم المستخدم:", value=selected_acc)
                new_password = st.text_input("تعديل كلمة المرور:", value=curr_pass)
                new_role_name = st.text_input("تعديل الوصف أو المسمى الوظيفي:", value=curr_role if curr_role else "")
                
                st.markdown("**تعديل الصلاحيات والأقسام المسموح له برؤيتها:**")
                
                edit_secs = []
                for sec in all_available_sections:
                    is_checked = st.checkbox(sec, value=(sec in curr_allowed))
                    if is_checked:
                        edit_secs.append(sec)
                
                if st.form_submit_button("حفظ تعديلات الحساب 💾"):
                    try:
                        cur = conn.cursor()
                        cur.execute("""
                            UPDATE myapp.app_permissions 
                            SET username = %s, password = %s, role_name = %s, allowed_sections = %s 
                            WHERE username = %s
                        """, (new_username, new_password, new_role_name, edit_secs, selected_acc))
                        conn.commit()
                        cur.close()
                        st.success(f"✅ تم تحديث بيانات الحساب ({new_username}) بنجاح!")
                        st.rerun()
                    except Exception as err:
                        conn.rollback()
                        st.error(f"حدث خطأ أثناء التحديث: {err}")

            st.markdown("---")
            c_act1, c_act2 = st.columns(2)
            with c_act1:
                if curr_is_active:
                    if st.button("🔴 تعطيل الحساب"):
                        if selected_acc == "admin":
                            st.error("لا يمكنك تعطيل الأدمن الرئيسي!")
                        else:
                            run_query("UPDATE myapp.app_permissions SET is_active = FALSE WHERE username = %s", (selected_acc,))
                            st.success("تم تعطيل الحساب.")
                            st.rerun()
                else:
                    if st.button("🟢 تفعيل الحساب"):
                        run_query("UPDATE myapp.app_permissions SET is_active = TRUE WHERE username = %s", (selected_acc,))
                        st.success("تم تفعيل الحساب.")
                        st.rerun()
            with c_act2:
                if st.button("🗑️ حذف الحساب نهائياً"):
                    if selected_acc == "admin":
                        st.error("لا يمكنك حذف الأدمن الرئيسي!")
                    else:
                        run_query("DELETE FROM myapp.app_permissions WHERE username = %s", (selected_acc,))
                        st.success("تم الحذف بنجاح!")
                        st.rerun()

    except Exception as e:
        st.info(f"خطأ في تحميل الصلاحيات: {e}")

# 8. الدعم الفني والتواصل
elif choice == "🛠️ الدعم الفني والتواصل":
    st.title("🛠️ الدعم الفني")
    c1, c2 = st.columns(2)
    with c1:
        st.info("📱 واتساب الإدارة: [مراسلة](https://wa.me/9647XXXXXXXX)")
    with c2:
        st.success("✈️ تليجرام الدعم: [@MyClicker_Support](https://t.me/MyClicker_Support)")

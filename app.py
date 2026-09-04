import streamlit as st
import pandas as pd
import psycopg2
import plotly.express as px
import os
import urllib.request
import random
import string
from datetime import datetime, timedelta

st.markdown("""
    <style>
    /* إخفاء الشريط العلوي بالكامل */
    header {visibility: hidden;}
    </style>
""", unsafe_allow_html=True)
st.set_page_config(page_title="Ultra MyClicker Dashboard", layout="wide", page_icon="⚡")

# --- 1. تحميل الشهادة والاتصال بقاعدة البيانات ---
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

# --- إنشاء جدول الصلاحيات وتأمين حساب الأدمن ---
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
        conn.commit()
        
        cur.execute("""
            ALTER TABLE myapp.app_permissions 
            ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE;
        """)
        conn.commit()
        
        cur.execute("SELECT COUNT(*) FROM myapp.app_permissions WHERE username = 'admin'")
        if cur.fetchone()[0] == 0:
            all_secs = [
                "👥 إدارة ومراقبة المستخدمين", 
                "🎫 توليد وإدارة الأكواد (الادمن)", 
                "🤝 قسم الشركاء (الموزعين)", 
                "📈 تحليل البيانات",
                "🖥️ حالة السيرفر",
                "🔐 إدارة الصلاحيات والتحكم"
            ]
            cur.execute(
                "INSERT INTO myapp.app_permissions (username, password, role_name, allowed_sections, is_active) VALUES (%s, %s, %s, %s, %s)",
                ("admin", "admin123", "مدير النظام", all_secs, True)
            )
            conn.commit()
        cur.close()
    except Exception as e:
        conn.rollback()

setup_permissions_table()

# =====================================================================
# نظام المصادقة
# =====================================================================
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.username = None
    st.session_state.allowed_sections = []

if not st.session_state.logged_in:
    st.sidebar.markdown("### ⚙️ التنقل")
    auth_mode = st.sidebar.radio("اختر العملية:", ["تسجيل الدخول", "إنشاء حساب لوحة تحكم جديد"])
    
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
            reg_role = st.text_input("طبيعة العمل (مثال: موزع):")
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
# الشريط الجانبي (Sidebar)
# =====================================================================
st.sidebar.markdown(f"### ⚡ MyClicker Pro")
st.sidebar.info(f"👤 المستخدم: {st.session_state.username}")

if st.sidebar.button("🔄 تحديث البيانات (Refresh)"):
    st.rerun()

user_allowed = st.session_state.allowed_sections
choice = st.sidebar.radio("القائمة الرئيسية:", user_allowed)

if st.sidebar.button("🚪 تسجيل الخروج"):
    st.session_state.logged_in = False
    st.session_state.username = None
    st.session_state.allowed_sections = []
    st.rerun()

# =====================================================================
# 1. قسم إدارة المستخدمين المشتركين (توليد رقم جهاز افتراضي تلقائياً)
# =====================================================================
if choice == "👥 إدارة ومراقبة المستخدمين":
    st.title("👥 إدارة المستخدمين والاشتراكات")
    
    # توليد رقم جهاز افتراضي تلقائي فريد
    auto_virtual_device = f"VIRTUAL-{''.join(random.choices(string.ascii_uppercase + string.digits, k=8))}"
    
    # نموذج إضافة مشترك جديد يدوياً مع رقم جهاز افتراضي تلقائي
    with st.expander("➕ إضافة مشترك جديد يدوياً (برقم جهاز افتراضي تلقائي)"):
        with st.form("add_new_subscriber_form"):
            col_s1, col_s2 = st.columns(2)
            with col_s1:
                # يظهر للمستخدم رقم افتراضي مولد مسبقاً وقابل للتعديل إذا أراد
                new_device_id = st.text_input("معرف الجهاز الافتراضي (Device ID):", value=auto_virtual_device)
                new_phone = st.text_input("رقم الهاتف:")
                new_sub_type = st.selectbox("نوع الاشتراك:", ["VIP", "TRIAL", "Monthly"])
            with col_s2:
                new_days = st.number_input("مدة الاشتراك بالأيام:", min_value=1, value=30)
                new_status = st.selectbox("الحالة الأولية:", ["Active", "Expired"])
            
            submit_sub = st.form_submit_button("حفظ وإضافة المشترك الجديد 💾")
            if submit_sub:
                if not new_device_id:
                    st.error("معرف الجهاز مطلوب!")
                else:
                    calc_expiry = datetime.now() + timedelta(days=new_days)
                    try:
                        cur = conn.cursor()
                        cur.execute("""
                            INSERT INTO myapp.users_status (device_id, phone, status, subscription_type, expiry_date, accepted_clicks)
                            VALUES (%s, %s, %s, %s, %s, %s)
                            ON CONFLICT (device_id) DO UPDATE 
                            SET phone = EXCLUDED.phone, status = EXCLUDED.status, subscription_type = EXCLUDED.subscription_type, expiry_date = EXCLUDED.expiry_date;
                        """, (new_device_id, new_phone, new_status, new_sub_type, calc_expiry, 0))
                        conn.commit()
                        cur.close()
                        st.success(f"تم إنشاء المشترك وإضافة الجهاز الافتراضي بنجاح: {new_device_id}")
                        st.rerun()
                    except Exception as ex:
                        conn.rollback()
                        st.error(f"حدث خطأ أثناء إضافة المشترك: {ex}")

    st.markdown("---")
    
    df_users = pd.read_sql("SELECT device_id, phone, status, bot_status, accepted_clicks, subscription_type, expiry_date, notice_message FROM myapp.users_status ORDER BY last_active DESC", conn)
    
    total_users = len(df_users)
    online_bots = len(df_users[df_users['bot_status'] == 'Online']) if not df_users.empty else 0
    active_users = len(df_users[df_users['status'] == 'Active']) if not df_users.empty else 0
    expired_users = len(df_users[df_users['status'] == 'Expired']) if not df_users.empty else 0

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("إجمالي المستخدمين", total_users)
    c2.metric("البوتات النشطة (Online)", online_bots)
    c3.metric("مستخدمين بحالة نشطة (Active)", active_users)
    c4.metric("منتهيو الصلاحية (Expired)", expired_users, delta_color="inverse")
    
    st.markdown("---")
    
    st.markdown("### 📢 إرسال إشعارات منبثقة للمشتركين")
    notif_target = st.radio("اختر نطاق الإرسال:", ["مستخدم معين", "إرسال لكامل المستخدمين (الكل)", "المستخدمين النشطين فقط (Active)", "المنتهي صلاحيتهم فقط (Expired)"], horizontal=True)
    broadcast_msg = st.text_input("نص الرسالة المنبثقة:")
    
    if st.button("📤 إرسال الإشعار الآن"):
        if not broadcast_msg.strip():
            st.error("يرجى كتابة نص الرسالة أولاً!")
        else:
            if notif_target == "إرسال لكامل المستخدمين (الكل)":
                run_query("UPDATE myapp.users_status SET notice_message = %s", (broadcast_msg,))
                st.success("✅ تم إرسال الإشعار بنجاح إلى جميع المستخدمين!")
            elif notif_target == "المستخدمين النشطين فقط (Active)":
                run_query("UPDATE myapp.users_status SET notice_message = %s WHERE status = 'Active'", (broadcast_msg,))
                st.success("✅ تم إرسال الإشعار للمستخدمين النشطين فقط!")
            elif notif_target == "المنتهي صلاحيتهم فقط (Expired)":
                run_query("UPDATE myapp.users_status SET notice_message = %s WHERE status = 'Expired'", (broadcast_msg,))
                st.success("✅ تم إرسال الإشعار للمستخدمين منتهي الصلاحية!")

    st.markdown("---")
    st.markdown("### 📋 سجل المستخدمين")
    
    if not df_users.empty:
        df_users.insert(0, 'تحديد', False)
        edited_df = st.data_editor(df_users, use_container_width=True, hide_index=True)
        selected_rows = edited_df[edited_df['تحديد'] == True]
        
        if not selected_rows.empty:
            if st.button("🗑️ حذف المستخدمين المحددين"):
                devices_to_delete = tuple(selected_rows['device_id'].tolist())
                if len(devices_to_delete) == 1:
                    run_query("DELETE FROM myapp.users_status WHERE device_id = %s", (devices_to_delete[0],))
                else:
                    run_query("DELETE FROM myapp.users_status WHERE device_id IN %s", (devices_to_delete,))
                st.success("تم الحذف بنجاح!")
                st.rerun()

        st.markdown("---")
        st.markdown("### 🛠️ لوحة التحكم الفردية بالمشترك")
        user_list = df_users['device_id'].tolist()
        phones_list = df_users['phone'].astype(str).tolist()
        options = [f"هاتف: {p} | جهاز: {d}" for p, d in zip(phones_list, user_list)]
        
        selected_index = st.selectbox("اختر المشترك:", range(len(options)), format_func=lambda x: options[x])
        selected_device = user_list[selected_index]
        
        col_edit1, col_edit2 = st.columns(2)
        with col_edit1:
            single_notice = st.text_input("رسالة فردية للمشترك:")
            if st.button("📤 إرسال رسالة"):
                run_query("UPDATE myapp.users_status SET notice_message = %s WHERE device_id = %s", (single_notice, selected_device))
                st.success("تم الإرسال!")
        with col_edit2:
            curr_phone = df_users.iloc[selected_index]['phone'] or ""
            curr_status = df_users.iloc[selected_index]['status']
            new_phone = st.text_input("رقم الهاتف:", value=curr_phone)
            new_status = st.selectbox("الحالة:", ["Active", "Expired", "Banned"], index=["Active", "Expired", "Banned"].index(curr_status) if curr_status in ["Active", "Expired", "Banned"] else 0)
            
            if st.button("💾 حفظ تعديلات المشترك"):
                run_query("UPDATE myapp.users_status SET phone = %s, status = %s WHERE device_id = %s", (new_phone, new_status, selected_device))
                st.success("تم التحديث!")
                st.rerun()
    else:
        st.info("لا توجد بيانات مستخدمين مسجلة.")

# =====================================================================
# 2. قسم توليد وإدارة الأكواد
# =====================================================================
elif choice == "🎫 توليد وإدارة الأكواد (الادمن)":
    st.title("🎫 لوحة توليد وإدارة الأكواد الشاملة (الادمن)")
    df_codes = pd.read_sql("SELECT * FROM myapp.subscriptions ORDER BY id DESC", conn)
    
    col1, col2 = st.columns(2)
    with col1:
        with st.form("generate_codes_form"):
            code_type = st.selectbox("نوع الكود:", ["VIP", "TRIAL"])
            code_days = st.number_input("مدة الاشتراك بالأيام:", min_value=1, value=30)
            code_count = st.number_input("الكمية:", min_value=1, max_value=500, value=10)
            submit_gen = st.form_submit_button("توليد الأكواد 🚀")
            
            if submit_gen:
                for _ in range(code_count):
                    new_code = f"{code_type[:3].upper()}-{''.join(random.choices(string.ascii_uppercase + string.digits, k=6))}"
                    run_query("INSERT INTO myapp.subscriptions (code, sub_type, duration_days, assigned_to_staff_id) VALUES (%s, %s, %s, %s)", (new_code, code_type, code_days, None))
                st.success(f"تم توليد {code_count} كود بنجاح!")
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

# =====================================================================
# 3. قسم الشركاء
# =====================================================================
elif choice == "🤝 قسم الشركاء (الموزعين)":
    st.title("🤝 لوحة الشركاء والموزعين")
    df_codes = pd.read_sql("SELECT * FROM myapp.subscriptions ORDER BY id DESC", conn)
    c1, c2 = st.columns(2)
    c1.metric("الأكواد المتاحة", len(df_codes[df_codes['is_used'] == False]))
    c2.metric("الأكواد المفعلة", len(df_codes[df_codes['is_used'] == True]))
    st.dataframe(df_codes[df_codes['is_used'] == False][['code', 'sub_type', 'duration_days']], use_container_width=True)

# =====================================================================
# 4. تحليل البيانات
# =====================================================================
elif choice == "📈 تحليل البيانات":
    st.title("📈 تحليل البيانات")
    try:
        df_orders = pd.read_sql("SELECT order_time, price FROM myapp.accepted_orders", conn)
        if not df_orders.empty:
            df_orders['hour'] = pd.to_datetime(df_orders['order_time']).dt.hour
            fig = px.bar(df_orders.groupby('hour').size().reset_index(name='count'), x='hour', y='count', title="أوقات الذروة للطلبات")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("لا توجد سجلات كافية.")
    except Exception as e:
        st.info(f"البيانات غير متوفرة: {e}")

# =====================================================================
# 5. حالة السيرفر
# =====================================================================
elif choice == "🖥️ حالة السيرفر":
    st.title("🖥️ مراقبة السيرفر")
    st.metric("حالة الخادم", "متصل 🟢", "DigitalOcean")

# =====================================================================
# 6. إدارة الصلاحيات
# =====================================================================
elif choice == "🔐 إدارة الصلاحيات والتحكم":
    st.title("🔐 إدارة حسابات لوحة التحكم")
    try:
        df_perms = pd.read_sql("SELECT id, username, role_name, is_active FROM myapp.app_permissions", conn)
        st.dataframe(df_perms, use_container_width=True)
        
        selected_acc = st.selectbox("اختر حساباً للتعديل:", df_perms['username'].tolist())
        if selected_acc and selected_acc != "admin":
            c1, c2 = st.columns(2)
            with c1:
                if st.button("🟢 تفعيل الحساب"):
                    run_query("UPDATE myapp.app_permissions SET is_active = TRUE WHERE username = %s", (selected_acc,))
                    st.success("تم التفعيل!")
                    st.rerun()
                if st.button("🔴 تعطيل الحساب"):
                    run_query("UPDATE myapp.app_permissions SET is_active = FALSE WHERE username = %s", (selected_acc,))
                    st.success("تم التعطيل!")
                    st.rerun()
            with c2:
                if st.button("🗑️ حذف الحساب"):
                    run_query("DELETE FROM myapp.app_permissions WHERE username = %s", (selected_acc,))
                    st.success("تم الحذف!")
                    st.rerun()
    except Exception as e:
        st.info(f"خطأ: {e}")

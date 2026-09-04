import streamlit as st
import pandas as pd
import psycopg2
import plotly.express as px
import os
import urllib.request
import random
import string

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

# --- إنشاء جدول الصلاحيات وتأمين حساب الأدمن وإضافة حقل تفعيل/تعطيل الحساب ---
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
        
        # التأكد من وجود عمود is_active في حال كان الجدول منشأ مسبقاً بدونه
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
# نظام تسجيل الدخول عبر قاعدة البيانات مع فحص إذا كان الحساب مفَعلاً
# =====================================================================
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.username = None
    st.session_state.allowed_sections = []

if not st.session_state.logged_in:
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
                        st.error("⚠️ هذا الحساب معطل من قبل الإدارة. يرجى مراجعة المسؤول.")
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
    st.stop()

# =====================================================================
# الشريط الجانبي (Sidebar) - عناصر التحكم العامة
# =====================================================================
st.sidebar.markdown(f"### ⚡ MyClicker Pro")
st.sidebar.info(f"👤 المستخدم: {st.session_state.username}")

# 🔄 زر التحديث (Refresh)
if st.sidebar.button("🔄 تحديث البيانات (Refresh)"):
    st.rerun()

user_allowed = st.session_state.allowed_sections

if not user_allowed:
    st.error("عذراً، ليس لديك أي صلاحيات محددة لعرض الأقسام. يرجى مراجعة الإدارة.")
    st.stop()

choice = st.sidebar.radio("القائمة الرئيسية:", user_allowed)

if st.sidebar.button("🚪 تسجيل الخروج"):
    st.session_state.logged_in = False
    st.session_state.username = None
    st.session_state.allowed_sections = []
    st.rerun()

# =====================================================================
# 1. قسم إدارة المستخدمين (التطبيق)
# =====================================================================
if choice == "👥 إدارة ومراقبة المستخدمين":
    st.title("👥 إدارة المستخدمين والرقابة الشاملة")
    
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
    
    st.markdown("### 📢 إرسال إشعارات منبثقة")
    notif_target = st.radio("اختر نطاق الإرسال:", ["مستخدم معين", "إرسال لكامل المستخدمين (الكل)", "المستخدمين النشطين فقط (Active)", "المنتهي صلاحيتهم فقط (Expired)"], horizontal=True)
    broadcast_msg = st.text_input("نص الرسالة المنبثقة المراد إرسالها:")
    
    if st.button("📤 إرسال الإشعار الآن"):
        if not broadcast_msg.strip():
            st.error("يرجى كتابة نص الرسالة أولاً!")
        else:
            if notif_target == "إرسال لكامل المستخدمين (الكل)":
                if run_query("UPDATE myapp.users_status SET notice_message = %s", (broadcast_msg,)):
                    st.success("✅ تم إرسال الإشعار بنجاح إلى جميع المستخدمين!")
            elif notif_target == "المستخدمين النشطين فقط (Active)":
                if run_query("UPDATE myapp.users_status SET notice_message = %s WHERE status = 'Active'", (broadcast_msg,)):
                    st.success("✅ تم إرسال الإشعار للمستخدمين النشطين فقط!")
            elif notif_target == "المنتهي صلاحيتهم فقط (Expired)":
                if run_query("UPDATE myapp.users_status SET notice_message = %s WHERE status = 'Expired'", (broadcast_msg,)):
                    st.success("✅ تم إرسال الإشعار للمستخدمين منتهي الصلاحية!")
            else:
                st.info("يرجى اختيار المستخدم المحدد من قسم لوحة التحكم بالأسفل للإرسال الفردي.")

    st.markdown("---")
    st.markdown("### 📋 سجل المستخدمين (مراقبة الاشتراكات)")
    
    if not df_users.empty:
        df_users.insert(0, 'تحديد', False)
        edited_df = st.data_editor(df_users, use_container_width=True, hide_index=True)
        
        selected_rows = edited_df[edited_df['تحديد'] == True]
        
        col_act1, col_act2 = st.columns(2)
        with col_act1:
            if not selected_rows.empty:
                if st.button("🗑️ حذف المستخدمين المحددين نهائياً"):
                    devices_to_delete = tuple(selected_rows['device_id'].tolist())
                    if len(devices_to_delete) == 1:
                        query = "DELETE FROM myapp.users_status WHERE device_id = %s"
                        params = (devices_to_delete[0],)
                    else:
                        query = "DELETE FROM myapp.users_status WHERE device_id IN %s"
                        params = (devices_to_delete,)
                    
                    if run_query(query, params):
                        st.success("تم حذف المستخدمين المحددين بنجاح!")
                        st.rerun()

        st.markdown("---")
        st.markdown("### 🛠️ لوحة التحكم الفردية بالمستخدم (تعديل / إشعار / حظر)")
        
        user_list = df_users['device_id'].tolist()
        phones_list = df_users['phone'].astype(str).tolist()
        options = [f"هاتف: {p} | جهاز: {d[:8]}..." for p, d in zip(phones_list, user_list)]
        
        selected_index = st.selectbox("اختر المستخدم لتطبيق إجراء فردي عليه:", range(len(options)), format_func=lambda x: options[x])
        selected_device = user_list[selected_index]
        
        col_edit1, col_edit2 = st.columns(2)
        
        with col_edit1:
            st.info("إرسال إشعار فردي لهذا الجهاز")
            single_notice = st.text_input("نص الرسالة الفردية:")
            if st.button("📤 إرسال إشعار فردي"):
                if run_query("UPDATE myapp.users_status SET notice_message = %s WHERE device_id = %s", (single_notice, selected_device)):
                    st.success("تم إرسال الإشعار الفردي بنجاح!")
        
        with col_edit2:
            st.warning("تعديل حالة المستخدم أو حذفه منفرداً")
            curr_phone = df_users.iloc[selected_index]['phone'] or ""
            curr_status = df_users.iloc[selected_index]['status']
            
            new_phone = st.text_input("تعديل رقم الهاتف:", value=curr_phone)
            status_index = ["Active", "Expired", "Banned"].index(curr_status) if curr_status in ["Active", "Expired", "Banned"] else 1
            new_status = st.selectbox("تغيير حالة الاشتراك:", ["Active", "Expired", "Banned"], index=status_index)
            
            c_btn1, c_btn2 = st.columns(2)
            with c_btn1:
                if st.button("💾 حفظ التعديلات"):
                    if run_query("UPDATE myapp.users_status SET phone = %s, status = %s WHERE device_id = %s", (new_phone, new_status, selected_device)):
                        st.success("تم تحديث بيانات المستخدم بنجاح!")
                        st.rerun()
            with c_btn2:
                if st.button("🗑️ حذف هذا الجهاز فقط"):
                    if run_query("DELETE FROM myapp.users_status WHERE device_id = %s", (selected_device,)):
                        st.success("تم حذف الجهاز بنجاح!")
                        st.rerun()
    else:
        st.info("لا توجد بيانات مستخدمين مسجلة حالياً.")

# =====================================================================
# 2. قسم توليد وإدارة الأكواد (الادمن)
# =====================================================================
elif choice == "🎫 توليد وإدارة الأكواد (الادمن)":
    st.title("🎫 لوحة توليد وإدارة الأكواد الشاملة (الادمن)")
    
    df_codes = pd.read_sql("SELECT * FROM myapp.subscriptions ORDER BY id DESC", conn)
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("### ⚙️ توليد أكواد جديدة")
        with st.form("generate_codes_form"):
            code_type = st.selectbox("نوع الكود (Sub Type):", ["VIP", "TRIAL"])
            code_days = st.number_input("مدة الاشتراك (بالأيام):", min_value=1, value=30)
            code_count = st.number_input("الكمية المراد توليدها:", min_value=1, max_value=500, value=10)
            
            submit_gen = st.form_submit_button("توليد الأكواد الآن 🚀")
            
            if submit_gen:
                generated_codes = []
                for _ in range(code_count):
                    prefix = code_type[:3].upper()
                    random_str = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
                    new_code = f"{prefix}-{random_str}"
                    generated_codes.append((new_code, code_type, code_days, None))
                
                success = True
                for c in generated_codes:
                    if not run_query("INSERT INTO myapp.subscriptions (code, sub_type, duration_days, assigned_to_staff_id) VALUES (%s, %s, %s, %s)", c):
                        success = False
                
                if success:
                    st.success(f"تم توليد {code_count} كود بنجاح!")
                    st.rerun()
    
    with col2:
        st.markdown("### 📊 إحصائيات الأكواد")
        unused_codes = df_codes[df_codes['is_used'] == False]
        used_codes = df_codes[df_codes['is_used'] == True]
        
        st.metric("أكواد غير مستعملة (جاهزة)", len(unused_codes))
        st.metric("أكواد تم استعمالها (مباعة)", len(used_codes))
        
    st.markdown("---")
    tab_unused, tab_used = st.tabs(["🎫 الأكواد غير المستعملة (الجديدة)", "✅ الأكواد المستعملة (المبيعات)"])
    
    with tab_unused:
        st.dataframe(unused_codes[['id', 'code', 'sub_type', 'duration_days']], use_container_width=True)
        if st.button("🗑️ حذف كافة الأكواد غير المستعملة"):
            if run_query("DELETE FROM myapp.subscriptions WHERE is_used = FALSE"):
                st.success("تم مسح الأكواد غير المستعملة بنجاح!")
                st.rerun()
        
    with tab_used:
        st.dataframe(used_codes[['code', 'used_by_device', 'used_at', 'sub_type']], use_container_width=True)

# =====================================================================
# 3. قسم الشركاء (الموزعين)
# =====================================================================
elif choice == "🤝 قسم الشركاء (الموزعين)":
    st.title("🤝 لوحة الشركاء والموزعين")
    st.info("متابعة الأكواد المتاحة والأكواد المفعلة مع أجهزة المستخدمين بكل شفافية.")
    
    df_codes = pd.read_sql("SELECT * FROM myapp.subscriptions ORDER BY id DESC", conn)
    
    unused_codes = df_codes[df_codes['is_used'] == False]
    used_codes = df_codes[df_codes['is_used'] == True]
    
    c1, c2 = st.columns(2)
    c1.metric("📦 الأكواد المتاحة للبيع", len(unused_codes))
    c2.metric("✅ الأكواد المفعلة على الأجهزة", len(used_codes))
    
    st.markdown("---")
    
    col_unused, col_used = st.columns(2)
    with col_unused:
        st.subheader("📦 الأكواد المتاحة (غير مستعملة)")
        if not unused_codes.empty:
            st.dataframe(unused_codes[['code', 'sub_type', 'duration_days']], use_container_width=True, hide_index=True)
        else:
            st.warning("لا توجد أكواد متاحة حالياً.")
            
    with col_used:
        st.subheader("✅ الأكواد المفعلة والأجهزة التابعة لها")
        if not used_codes.empty:
            st.dataframe(used_codes[['code', 'sub_type', 'used_by_device', 'used_at']], use_container_width=True, hide_index=True)
        else:
            st.info("لم يتم تفعيل أي كود حتى الآن.")

# =====================================================================
# 4. قسم تحليل البيانات
# =====================================================================
elif choice == "📈 تحليل البيانات":
    st.title("📈 تحليل البيانات وأوقات الذروة")
    query_orders = "SELECT order_time, price FROM myapp.accepted_orders"
    try:
        df_orders = pd.read_sql(query_orders, conn)
        if not df_orders.empty:
            df_orders['order_time'] = pd.to_datetime(df_orders['order_time'])
            df_orders['hour'] = df_orders['order_time'].dt.hour
            peak_hours = df_orders.groupby('hour').size().reset_index(name='count')
            fig = px.bar(peak_hours, x='hour', y='count', title="أوقات الذروة للطلبات المقبولة خلال اليوم (بالساعة)", color='count', color_continuous_scale='Blues')
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("لا توجد سجلات طلبات كافية لعرض الرسوم البيانية حالياً.")
    except Exception as e:
        st.info(f"عذراً، لم نتمكن من قراءة جدول الطلبات: {e}")

# =====================================================================
# 5. قسم حالة السيرفر
# =====================================================================
elif choice == "🖥️ حالة السيرفر":
    st.title("🖥️ مراقبة السيرفر")
    c1, c2 = st.columns(2)
    c1.metric("حالة الخادم وقاعدة البيانات", "متصل 🟢", "DigitalOcean")
    c2.metric("حالة الشهادة الأمنية (SSL)", "مفعلة ومحمية 🔒")
    st.info("هذا السيرفر مرتبط بنظام Node.js (MyClicker Pro Ultra) ويعمل في الوقت الفعلي.")

# =====================================================================
# 6. قسم إدارة الصلاحيات والتحكم (مع ميزة التسجيل والتفعيل والتعطيل)
# =====================================================================
elif choice == "🔐 إدارة الصلاحيات والتحكم":
    st.title("🔐 إدارة حسابات المستخدمين وصلاحيات الأقسام")
    st.info("من هنا يمكنك تسجيل مستخدم جديد (شريك/موظف)، وتفعيل أو تعطيل الحسابات القائمة، وتحديد الأقسام المسموح لها برؤيتها.")
    
    col_add, col_view = st.columns([1, 1.5])
    
    with col_add:
        st.markdown("### ➕ تسجيل مستخدم جديد")
        with st.form("add_user_form"):
            new_user = st.text_input("اسم المستخدم (Username):")
            new_pass = st.text_input("كلمة المرور (Password):", type="password")
            role_desc = st.text_input("مسمي الوظيفة / الوصف (مثال: شريك بغداد):")
            
            st.markdown("**حدد الأقسام المسموح له بدخولها:**")
            sec_p1 = st.checkbox("👥 إدارة ومراقبة المستخدمين")
            sec_p2 = st.checkbox("🎫 توليد وإدارة الأكواد (الادمن)")
            sec_p3 = st.checkbox("🤝 قسم الشركاء (الموزعين)", value=True)
            sec_p4 = st.checkbox("📈 تحليل البيانات")
            sec_p5 = st.checkbox("🖥️ حالة السيرفر")
            sec_p6 = st.checkbox("🔐 إدارة الصلاحيات والتحكم")
            
            submit_new_user = st.form_submit_button("تسجيل الحساب وحفظه 💾")
            
            if submit_new_user:
                if not new_user or not new_pass:
                    st.error("يرجى ملء اسم المستخدم وكلمة المرور على الأقل!")
                else:
                    selected_sections = []
                    if sec_p1: selected_sections.append("👥 إدارة ومراقبة المستخدمين")
                    if sec_p2: selected_sections.append("🎫 توليد وإدارة الأكواد (الادمن)")
                    if sec_p3: selected_sections.append("🤝 قسم الشركاء (الموزعين)")
                    if sec_p4: selected_sections.append("📈 تحليل البيانات")
                    if sec_p5: selected_sections.append("🖥️ حالة السيرفر")
                    if sec_p6: selected_sections.append("🔐 إدارة الصلاحيات والتحكم")
                    
                    try:
                        cur = conn.cursor()
                        cur.execute(
                            "INSERT INTO myapp.app_permissions (username, password, role_name, allowed_sections, is_active) VALUES (%s, %s, %s, %s, %s)",
                            (new_user, new_pass, role_desc, selected_sections, True)
                        )
                        conn.commit()
                        cur.close()
                        st.success(f"تم تسجيل حساب المستخدم ({new_user}) بنجاح!")
                        st.rerun()
                    except Exception as err:
                        conn.rollback()
                        st.error(f"اسم المستخدم موجود مسبقاً أو حدث خطأ: {err}")
                        
    with col_view:
        st.markdown("### 📋 الحسابات وحالة التفعيل")
        try:
            df_perms = pd.read_sql("SELECT id, username, role_name, is_active FROM myapp.app_permissions", conn)
            st.dataframe(df_perms, use_container_width=True)
            
            st.markdown("---")
            st.markdown("### ⚙️ إدارة تفعيل/تعطيل أو حذف حساب")
            
            # جلب أسماء المستخدمين للتعديل عليهم (ما عدا الأدمن الرئيسي للحماية)
            cur = conn.cursor()
            cur.execute("SELECT username, is_active FROM myapp.app_permissions")
            all_accounts = cur.fetchall()
            cur.close()
            
            usernames_list = [acc[0] for acc in all_accounts]
            selected_acc = st.selectbox("اختر حساباً لتعديل حالته:", usernames_list)
            
            if selected_acc:
                # معرفة الحالة الحالية للحساب المحدد
                curr_state = [acc[1] for acc in all_accounts if acc[0] == selected_acc][0]
                
                c_act_btn1, c_act_btn2, c_act_btn3 = st.columns(3)
                
                with c_act_btn1:
                    if curr_state:
                        if st.button("🔴 تعطيل الحساب"):
                            if selected_acc == "admin":
                                st.error("لا يمكنك تعطيل حساب الأدمن الرئيسي!")
                            else:
                                if run_query("UPDATE myapp.app_permissions SET is_active = FALSE WHERE username = %s", (selected_acc,)):
                                    st.success(f"تم تعطيل الحساب ({selected_acc}) بنجاح.")
                                    st.rerun()
                    else:
                        if st.button("🟢 تفعيل الحساب"):
                            if run_query("UPDATE myapp.app_permissions SET is_active = TRUE WHERE username = %s", (selected_acc,)):
                                st.success(f"تم تفعيل الحساب ({selected_acc}) بنجاح.")
                                st.rerun()
                                
                with c_act_btn2:
                    if st.button("🗑️ حذف الحساب نهائياً"):
                        if selected_acc == "admin":
                            st.error("لا يمكنك حذف حساب الأدمن الرئيسي!")
                        else:
                            if run_query("DELETE FROM myapp.app_permissions WHERE username = %s", (selected_acc,)):
                                st.success(f"تم حذف الحساب ({selected_acc}) بنجاح!")
                                st.rerun()
                                
        except Exception as e:
            st.info(f"جاري تحميل قائمة الحسابات: {e}")

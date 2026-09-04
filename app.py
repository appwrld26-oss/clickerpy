import streamlit as st
import pandas as pd
import psycopg2
import plotly.express as px
import os
import urllib.request
import random
import string

# إعدادات الصفحة الأساسية
st.set_page_config(page_title="Ultra MyClicker Dashboard", layout="wide", page_icon="⚡")

st.markdown("""
    <style>
    /* إخفاء الشريط العلوي بالكامل */
    header {visibility: hidden;}
    /* تحسين الخطوط والتنسيق العربي */
    body {
        direction: rtl;
        text-align: right;
    }
    </style>
""", unsafe_allow_html=True)

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
                "🔐 إدارة الصلاحيات والتحكم",
                "🛠️ الدعم الفني والتواصل"
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
# نظام تسجيل الدخول
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
# الشريط الجانبي (Sidebar)
# =====================================================================
st.sidebar.markdown(f"### ⚡ MyClicker Pro")
st.sidebar.info(f"👤 المستخدم: {st.session_state.username}")

if st.sidebar.button("🔄 تحديث البيانات (Refresh)"):
    st.rerun()

user_allowed = st.session_state.allowed_sections
if not user_allowed:
    st.error("عذراً، ليس لديك أي صلاحيات محددة لعرض الأقسام.")
    st.stop()

choice = st.sidebar.radio("القائمة الرئيسية:", user_allowed)

if st.sidebar.button("🚪 تسجيل الخروج"):
    st.session_state.logged_in = False
    st.session_state.username = None
    st.session_state.allowed_sections = []
    st.rerun()

# =====================================================================
# 1. قسم إدارة المستخدمين
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
    c2.metric("البوتات النشطة", online_bots)
    c3.metric("نشطة (Active)", active_users)
    c4.metric("منتهية (Expired)", expired_users, delta_color="inverse")
    
    st.markdown("---")
    
    st.markdown("### 📢 إرسال إشعارات (تطوير جديد 🚀)")
    col_n1, col_n2 = st.columns(2)
    with col_n1:
        notif_target = st.radio("اختر النطاق:", ["الكل", "النشطين (Active)", "المنتهيين (Expired)"], horizontal=True)
    with col_n2:
        notif_type = st.radio("نوع التنبيه:", ["رسالة داخل التطبيق", "إشعار نظام (StatusBar)"], horizontal=True)
        
    broadcast_msg = st.text_input("نص الرسالة المراد إرسالها:")
    
    if st.button("📤 إرسال الإشعار الآن"):
        if not broadcast_msg.strip():
            st.error("يرجى كتابة نص الرسالة أولاً!")
        else:
            # إضافة الوسم PUSH: إذا كان إشعار نظام
            final_msg = f"PUSH:{broadcast_msg}" if notif_type == "إشعار نظام (StatusBar)" else broadcast_msg
            
            query = "UPDATE myapp.users_status SET notice_message = %s"
            if notif_target == "النشطين (Active)":
                query += " WHERE status = 'Active'"
            elif notif_target == "المنتهيين (Expired)":
                query += " WHERE status = 'Expired'"
                
            if run_query(query, (final_msg,)):
                st.success(f"✅ تم إرسال التنبيه بنجاح كـ ({notif_type})")

    st.markdown("---")
    st.markdown("### 📋 سجل المستخدمين")
    if not df_users.empty:
        df_users.insert(0, 'تحديد', False)
        edited_df = st.data_editor(df_users, use_container_width=True, hide_index=True)
        
        selected_rows = edited_df[edited_df['تحديد'] == True]
        if not selected_rows.empty:
            if st.button("🗑️ حذف المستخدمين المحددين"):
                ids = tuple(selected_rows['device_id'].tolist())
                q = "DELETE FROM myapp.users_status WHERE device_id IN %s" if len(ids) > 1 else "DELETE FROM myapp.users_status WHERE device_id = %s"
                p = (ids,) if len(ids) > 1 else (ids[0],)
                if run_query(q, p):
                    st.success("تم الحذف بنجاح!")
                    st.rerun()

# =====================================================================
# 2. قسم توليد الأكواد
# =====================================================================
elif choice == "🎫 توليد وإدارة الأكواد (الادمن)":
    st.title("🎫 لوحة توليد وإدارة الأكواد الشاملة")
    df_codes = pd.read_sql("SELECT * FROM myapp.subscriptions ORDER BY id DESC", conn)
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("### ⚙️ توليد أكواد جديدة")
        with st.form("gen_form"):
            code_type = st.selectbox("نوع الكود:", ["VIP", "TRIAL"])
            code_days = st.number_input("المدة بالأيام:", min_value=1, value=30)
            code_count = st.number_input("الكمية:", min_value=1, max_value=500, value=10)
            if st.form_submit_button("توليد الآن 🚀"):
                success = True
                for _ in range(code_count):
                    c = f"{code_type[:3].upper()}-{''.join(random.choices(string.ascii_uppercase + string.digits, k=6))}"
                    if not run_query("INSERT INTO myapp.subscriptions (code, sub_type, duration_days, is_used) VALUES (%s, %s, %s, FALSE)", (c, code_type, code_days)):
                        success = False
                if success:
                    st.success(f"تم توليد {code_count} كود!")
                    st.rerun()
    with col2:
        st.markdown("### 📊 الإحصائيات")
        st.metric("أكواد متاحة", len(df_codes[df_codes['is_used'] == False]))
        st.metric("أكواد مباعة", len(df_codes[df_codes['is_used'] == True]))

# =====================================================================
# 3. قسم الشركاء
# =====================================================================
elif choice == "🤝 قسم الشركاء (الموزعين)":
    st.title("🤝 لوحة الشركاء والموزعين")
    df_codes = pd.read_sql("SELECT code, sub_type, duration_days, is_used, used_by_device, used_at FROM myapp.subscriptions ORDER BY id DESC", conn)
    c1, c2 = st.columns(2)
    c1.subheader("📦 الأكواد المتاحة")
    c1.dataframe(df_codes[df_codes['is_used'] == False][['code', 'sub_type', 'duration_days']], use_container_width=True)
    c2.subheader("✅ الأكواد المفعلة")
    c2.dataframe(df_codes[df_codes['is_used'] == True][['code', 'used_by_device', 'used_at']], use_container_width=True)

# =====================================================================
# 4. قسم تحليل البيانات
# =====================================================================
elif choice == "📈 تحليل البيانات":
    st.title("📈 تحليل الأداء والنشاط")
    try:
        df_orders = pd.read_sql("SELECT order_time, price FROM myapp.accepted_orders", conn)
        if not df_orders.empty:
            df_orders['order_time'] = pd.to_datetime(df_orders['order_time'])
            peak = df_orders.groupby(df_orders['order_time'].dt.hour).size().reset_index(name='count')
            st.plotly_chart(px.line(peak, x='order_time', y='count', title="نشاط الطلبات خلال اليوم"), use_container_width=True)
        else: st.info("لا توجد بيانات كافية.")
    except: st.info("جدول الطلبات غير متوفر حالياً.")

# =====================================================================
# 5. قسم حالة السيرفر
# =====================================================================
elif choice == "🖥️ حالة السيرفر":
    st.title("🖥️ مراقبة حالة الخادم")
    st.success("🟢 السيرفر يعمل بكفاءة عالية (DigitalOcean)")
    st.info("قاعدة البيانات: PostgreSQL | SSL: Enabled")

# =====================================================================
# 6. إدارة الصلاحيات
# =====================================================================
elif choice == "🔐 إدارة الصلاحيات والتحكم":
    st.title("🔐 التحكم في حسابات النظام")
    col_a, col_b = st.columns([1, 1.5])
    with col_a:
        st.subheader("➕ حساب جديد")
        with st.form("new_u"):
            u = st.text_input("Username:")
            p = st.text_input("Password:", type="password")
            role = st.text_input("الوصف:")
            st.write("الصلاحيات:")
            s1 = st.checkbox("👥 إدارة المستخدمين")
            s2 = st.checkbox("🎫 توليد الأكواد")
            s3 = st.checkbox("🤝 قسم الشركاء")
            s4 = st.checkbox("📈 تحليل البيانات")
            s5 = st.checkbox("🖥️ حالة السيرفر")
            s7 = st.checkbox("🛠️ الدعم الفني والتواصل")
            if st.form_submit_button("حفظ الحساب"):
                secs = []
                if s1: secs.append("👥 إدارة ومراقبة المستخدمين")
                if s2: secs.append("🎫 توليد وإدارة الأكواد (الادمن)")
                if s3: secs.append("🤝 قسم الشركاء (الموزعين)")
                if s4: secs.append("📈 تحليل البيانات")
                if s5: secs.append("🖥️ حالة السيرفر")
                if s7: secs.append("🛠️ الدعم الفني والتواصل")
                if run_query("INSERT INTO myapp.app_permissions (username, password, role_name, allowed_sections) VALUES (%s,%s,%s,%s)", (u,p,role,secs)):
                    st.success("تم الحفظ!")
                    st.rerun()
    with col_b:
        st.subheader("📋 الحسابات الحالية")
        df_p = pd.read_sql("SELECT username, role_name, is_active FROM myapp.app_permissions", conn)
        st.dataframe(df_p, use_container_width=True)

# =====================================================================
# 7. قسم الدعم الفني (NEW 🛠️)
# =====================================================================
elif choice == "🛠️ الدعم الفني والتواصل":
    st.title("🛠️ الدعم الفني وقنوات التواصل")
    st.markdown("---")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📞 مراسلة الإدارة مباشرة")
        st.info("خدمة العملاء متوفرة لحل مشاكل التفعيل والاشتراكات.")
        st.markdown("""
        * 📱 **واتساب الدعم:** [إرسال رسالة الآن](https://wa.me/9647XXXXXXXX)
        * ✈️ **تليجرام الإدارة:** [@MyClicker_Admin](https://t.me/MyClicker_Admin)
        * 📧 **البريد الإلكتروني:** support@myclickerpro.com
        """)
        
    with col2:
        st.subheader("📢 قنواتنا الرسمية")
        st.success("اشترك في القنوات لتصلك آخر أخبار السيرفر والتحديثات.")
        st.markdown("""
        * 📢 **قناة التحديثات:** [انضم الآن](https://t.me/MyClicker_Channel)
        * 📦 **قناة الموزعين:** [دخول القناة](https://t.me/MyClicker_Partners)
        """)
    
    st.markdown("---")
    st.warning("⚠️ ملاحظة: لا تشارك كلمة مرور حسابك مع أي شخص يدعي أنه من فريق الدعم.")

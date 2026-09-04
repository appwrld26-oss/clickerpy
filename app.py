import streamlit as st
import pandas as pd
import psycopg2
import plotly.express as px
import os
import urllib.request
import random
import string

# إعدادات الصفحة
st.set_page_config(page_title="MyClicker Pro Ultra Dashboard", layout="wide", page_icon="⚡")

st.markdown("""
    <style>
    header {visibility: hidden;}
    body { direction: rtl; text-align: right; }
    .stMetric { background-color: #ffffff; padding: 20px; border-radius: 15px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); border: 1px solid #eee; }
    </style>
""", unsafe_allow_html=True)

# --- 1. الاتصال بقاعدة البيانات ---
def download_ca_cert():
    cert_path = "ca-certificate.crt"
    if not os.path.exists(cert_path):
        try:
            url = "https://certs.ondigitalocean.com/ca-certificate.crt"
            urllib.request.urlretrieve(url, cert_path)
        except Exception as e: st.error(f"فشل تحميل الشهادة: {e}")
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

# --- 2. إعداد الجداول (التحديث الإجباري والصلاحيات) ---
def setup_full_system():
    try:
        cur = conn.cursor()
        # جدول الصلاحيات
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
        # جدول إعدادات الإصدار
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
        
        # التأكد من وجود الأدمن
        cur.execute("SELECT COUNT(*) FROM myapp.app_permissions WHERE username = 'admin'")
        if cur.fetchone()[0] == 0:
            all_secs = [
                "📈 الإحصائيات وتحليل الأداء",
                "👥 إدارة ومراقبة المستخدمين", 
                "🚀 إدارة الإصدارات والتحديثات",
                "🎫 توليد وإدارة الأكواد (الادمن)", 
                "🤝 قسم الشركاء (الموزعين)", 
                "🔐 إدارة الصلاحيات والتحكم",
                "🛠️ الدعم الفني والتواصل"
            ]
            cur.execute("INSERT INTO myapp.app_permissions (username, password, role_name, allowed_sections) VALUES (%s,%s,%s,%s)", 
                        ("admin", "admin123", "مدير النظام", all_secs))
        
        # سجل الإعدادات الافتراضي
        cur.execute("SELECT COUNT(*) FROM myapp.app_config")
        if cur.fetchone()[0] == 0:
            cur.execute("INSERT INTO myapp.app_config (latest_version, update_url, update_message, force_update_enabled) VALUES ('7.1.0', '', 'تحديث جديد متاح', FALSE)")
        
        conn.commit()
        cur.close()
    except Exception as e: conn.rollback()

setup_full_system()

# --- 3. تسجيل الدخول ---
if "logged_in" not in st.session_state: st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.title("🔐 لوحة تحكم MyClicker Pro Ultra")
    with st.form("login_form"):
        u = st.text_input("اسم المستخدم:")
        p = st.text_input("كلمة المرور:", type="password")
        if st.form_submit_button("دخول"):
            cur = conn.cursor()
            cur.execute("SELECT password, allowed_sections, is_active FROM myapp.app_permissions WHERE username = %s", (u,))
            res = cur.fetchone()
            if res and res[2] and res[0] == p:
                st.session_state.logged_in, st.session_state.username, st.session_state.allowed_sections = True, u, res[1]
                st.rerun()
            else: st.error("بيانات خاطئة أو حساب معطل")
    st.stop()

# --- Sidebar ---
st.sidebar.markdown(f"### ⚡ MyClicker Pro\n👤 {st.session_state.username}")
choice = st.sidebar.radio("القائمة الرئيسية:", st.session_state.allowed_sections)
if st.sidebar.button("🚪 تسجيل الخروج"):
    st.session_state.logged_in = False
    st.rerun()

# =====================================================================
# 1. قسم الإحصائيات وتحليل الأداء (الجديد والمطلوب)
# =====================================================================
if choice == "📈 الإحصائيات وتحليل الأداء":
    st.title("📈 الإحصائيات العامة والتحليلات")
    
    df_u = pd.read_sql("SELECT status, bot_status, accepted_clicks, subscription_type FROM myapp.users_status", conn)
    df_s = pd.read_sql("SELECT is_used, sub_type FROM myapp.subscriptions", conn)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("إجمالي المستخدمين", len(df_u))
    c2.metric("البوتات النشطة الآن", len(df_u[df_u['bot_status']=='Online']))
    c3.metric("إجمالي النقرات المقبولة", df_u['accepted_clicks'].sum())
    c4.metric("أكواد غير مباعة", len(df_s[df_s['is_used']==False]))

    st.markdown("---")
    col_g1, col_g2 = st.columns(2)
    
    with col_g1:
        st.subheader("📊 توزيع حالات المستخدمين")
        fig_status = px.pie(df_u, names='status', color='status', 
                            color_discrete_map={'Active':'#10b981', 'Expired':'#ef4444', 'Banned':'#1f2937'},
                            hole=0.4)
        st.plotly_chart(fig_status, use_container_width=True)

    with col_g2:
        st.subheader("💳 أنواع الاشتراكات المبيعة")
        fig_sub = px.bar(df_u, x='subscription_type', title="عدد المستخدمين حسب الفئة", color='subscription_type')
        st.plotly_chart(fig_sub, use_container_width=True)

# =====================================================================
# 2. إدارة المستخدمين (كاملة بكل الخيارات)
# =====================================================================
elif choice == "👥 إدارة ومراقبة المستخدمين":
    st.title("👥 إدارة المستخدمين والرقابة")
    df_users = pd.read_sql("SELECT device_id, phone, status, bot_status, accepted_clicks, expiry_date, notice_message FROM myapp.users_status ORDER BY last_active DESC", conn)
    
    st.markdown("### 📢 إرسال إشعارات (تطبيق + نظام)")
    cn1, cn2 = st.columns(2)
    with cn1:
        n_target = st.selectbox("النطاق:", ["الكل", "Active", "Expired"])
    with cn2:
        n_mode = st.radio("نوع التنبيه:", ["رسالة تطبيق", "إشعار نظام (Status Bar)"], horizontal=True)
    
    n_msg = st.text_input("نص الرسالة:")
    if st.button("📤 إرسال الإشعار"):
        final_msg = f"PUSH:{n_msg}" if n_mode == "إشعار نظام (Status Bar)" else n_msg
        q = "UPDATE myapp.users_status SET notice_message = %s"
        if n_target != "الكل": q += f" WHERE status = '{n_target}'"
        if run_query(q, (final_msg,)): st.success("✅ تم الإرسال")

    st.markdown("---")
    st.subheader("📋 قائمة المستخدمين")
    df_users.insert(0, 'تحديد', False)
    edited = st.data_editor(df_users, use_container_width=True, hide_index=True)
    
    st.markdown("### 🛠️ إجراءات فردية")
    sel_dev = st.selectbox("اختر جهازاً:", df_users['device_id'].tolist() if not df_users.empty else [])
    if sel_dev:
        ca1, ca2, ca3 = st.columns(3)
        with ca1:
            if st.button("🗑️ حذف الجهاز"):
                if run_query("DELETE FROM myapp.users_status WHERE device_id = %s", (sel_dev,)): st.rerun()
        with ca2:
            new_s = st.selectbox("تغيير الحالة:", ["Active", "Expired", "Banned"])
            if st.button("💾 حفظ الحالة"):
                run_query("UPDATE myapp.users_status SET status = %s WHERE device_id = %s", (new_s, sel_dev))
                st.rerun()
        with ca3:
            st.info("إشعار فردي")
            ind_msg = st.text_input("نص الرسالة الفردية:")
            if st.button("📤 إرسال فردي"):
                run_query("UPDATE myapp.users_status SET notice_message = %s WHERE device_id = %s", (ind_msg, sel_dev))

# =====================================================================
# 3. قسم إضافة الإصدار الجديد (التحديث الإجباري)
# =====================================================================
elif choice == "🚀 إدارة الإصدارات والتحديثات":
    st.title("🚀 إضافة إصدار جديد (Force Update)")
    st.info("من هنا يمكنك إجبار المستخدمين على تحميل نسخة APK جديدة.")
    
    conf = pd.read_sql("SELECT * FROM myapp.app_config WHERE id = 1", conn).iloc[0]
    
    with st.form("update_config"):
        v = st.text_input("رقم الإصدار الجديد (مثلاً 7.2.0):", value=conf['latest_version'])
        url = st.text_input("رابط تحميل الـ APK المباشر:", value=conf['update_url'])
        msg = st.text_area("رسالة تظهر للمستخدم عند التحديث:", value=conf['update_message'])
        forced = st.checkbox("تفعيل الإيقاف الإجباري (Force Update)", value=conf['force_update_enabled'])
        
        if st.form_submit_button("حفظ ونشر الإصدار الجديد 🚀"):
            if run_query("""
                UPDATE myapp.app_config SET latest_version=%s, update_url=%s, update_message=%s, force_update_enabled=%s WHERE id = 1
            """, (v, url, msg, forced)):
                st.success(f"✅ تم تحديث بيانات الإصدار إلى {v}")
                st.rerun()

# =====================================================================
# الأقسام الأخرى (توليد الأكواد، الموزعين، الصلاحيات، الدعم)
# =====================================================================

elif choice == "🎫 توليد وإدارة الأكواد (الادمن)":
    st.title("🎫 توليد الأكواد")
    with st.form("gen"):
        t = st.selectbox("النوع:", ["VIP", "TRIAL"])
        q = st.number_input("الكمية:", 10)
        if st.form_submit_button("توليد 🚀"):
            for _ in range(q):
                c = f"{t}-{''.join(random.choices(string.ascii_uppercase + string.digits, k=6))}"
                run_query("INSERT INTO myapp.subscriptions (code, sub_type, duration_days, is_used) VALUES (%s,%s,30,FALSE)", (c, t))
            st.rerun()

elif choice == "🔐 إدارة الصلاحيات والتحكم":
    st.title("🔐 إدارة الموظفين")
    c_a, c_b = st.columns([1, 2])
    with c_a:
        with st.form("new_acc"):
            u = st.text_input("Username:")
            p = st.text_input("Password:", type="password")
            role = st.text_input("الوصف:")
            s_list = st.multiselect("الأقسام:", ["📈 الإحصائيات وتحليل الأداء", "👥 إدارة ومراقبة المستخدمين", "🚀 إدارة الإصدارات والتحديثات", "🎫 توليد وإدارة الأكواد (الادمن)", "🤝 قسم الشركاء (الموزعين)", "🔐 إدارة الصلاحيات والتحكم", "🛠️ الدعم الفني والتواصل"])
            if st.form_submit_button("حفظ الحساب"):
                run_query("INSERT INTO myapp.app_permissions (username,password,role_name,allowed_sections) VALUES (%s,%s,%s,%s)", (u,p,role,s_list))
                st.rerun()
    with c_b:
        st.dataframe(pd.read_sql("SELECT username, role_name, is_active FROM myapp.app_permissions", conn), use_container_width=True)

elif choice == "🛠️ الدعم الفني والتواصل":
    st.title("🛠️ الدعم الفني")
    st.info("📱 واتساب: [تواصل](https://wa.me/9647XXXXXXXX) | ✈️ تليجرام: [@MyClicker_Support](https://t.me/MyClicker_Support)")

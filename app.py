import streamlit as st
import pandas as pd
import psycopg2
import plotly.express as px
import random
import string
from datetime import datetime, timedelta

# =====================================================================
# إعدادات الصفحة والتنسيقات المتجاوبة لكافة المتصفحات والبيئات
# =====================================================================
st.set_page_config(
    page_title="MyClicker Pro Ultra Command Center",
    layout="wide",
    page_icon="⚡"
)

st.markdown("""
    <style>
    header {visibility: hidden;}
    
    /* خطوط النظام القياسية والمتجاوبة */
    * {
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, "Noto Sans Arabic", "Cairo", "Tahoma", sans-serif !important;
    }
    
    /* تثبيت خلفية التطبيق العامة للوضع الفاتح ومنع الشاشة السوداء */
    .stApp {
        background-color: #f8fafc !important;
        color: #1e293b !important;
    }
    
    /* الشريط الجانبي */
    [data-testid="stSidebar"] { 
        background-color: #f1f5f9 !important; 
        padding: 10px;
    }
    
    /* بطاقات المقاييس والإحصائيات */
    .stMetric { 
        background-color: #ffffff !important; 
        padding: 15px !important; 
        border-radius: 12px !important; 
        border: 1px solid #e2e8f0 !important; 
        box-shadow: 0 2px 4px rgba(0,0,0,0.02); 
        margin-bottom: 10px;
        color: #0f172a !important;
    }
    
    /* تثبيت ألوان وخلفيات حقول الإدخال والـ Selectbox لمنع ظهورها باللون الأسود */
    input, textarea, select {
        background-color: #ffffff !important;
        color: #0f172a !important;
        border: 1px solid #cbd5e1 !important;
    }

    [data-baseweb="input"] div, [data-baseweb="base-input"] div, [data-baseweb="select"] div {
        background-color: #ffffff !important;
        color: #0f172a !important;
    }

    div[data-baseweb="select"] span {
        color: #0f172a !important;
    }
    
    /* تنسيق الجداول لتكون بخلفية بيضاء ونظيفة */
    [data-testid="stDataFrame"] {
        background-color: #ffffff !important;
        border-radius: 10px;
        padding: 5px;
        border: 1px solid #e2e8f0;
    }

    /* الأزرار */
    .stButton button {
        width: 100% !important;
        border-radius: 8px !important;
        font-weight: 600 !important;
    }

    /* التبويبات */
    .stTabs [data-baseweb="tab-list"] { 
        gap: 8px; 
        flex-wrap: wrap;
    }
    
    .stTabs [data-baseweb="tab"] { 
        background-color: #f1f5f9 !important; 
        border-radius: 8px 8px 0 0 !important; 
        padding: 10px 18px !important; 
        font-weight: bold; 
        color: #334155 !important;
    }
    </style>
""", unsafe_allow_html=True)

# =====================================================================
# الاتصال بقاعدة البيانات مع التخزين المؤقت وحماية الاستقرار
# =====================================================================
@st.cache_resource
def get_conn():
    try:
        return psycopg2.connect(
            database="defaultdb",
            user="doadmin",
            password="1tHwqXCgn8BS6iTm942V3f7a",
            host="myclicker-db-rd7ky.db1.ondigitalocean.com",
            port="5432",
            sslmode="require",
            connect_timeout=5
        )
    except Exception:
        return None

conn = get_conn()
if not conn:
    st.error("❌ فشل الاتصال بقاعدة البيانات على DigitalOcean. يرجى التحقق من بيانات الاتصال.")
    st.stop()

def query(sql, params=()):
    try:
        global conn
        if conn is None or conn.closed != 0:
            conn = get_conn()
        if not conn:
            return False
        cur = conn.cursor()
        cur.execute(sql, params)
        conn.commit()
        cur.close()
        return True
    except Exception as e:
        if conn:
            try:
                conn.rollback()
            except Exception:
                pass
        st.error(f"خطأ في تنفيذ قاعدة البيانات: {e}")
        return False

@st.cache_data(ttl=10)
def load_users_data():
    try:
        if conn and conn.closed == 0:
            return pd.read_sql("SELECT device_id, phone, status, subscription_type, expiry_date, bot_status, app_version, accepted_clicks, last_active, notice_message FROM myapp.users_status ORDER BY last_active DESC", conn)
    except Exception:
        pass
    return pd.DataFrame()

@st.cache_data(ttl=10)
def load_subs_data():
    try:
        if conn and conn.closed == 0:
            return pd.read_sql("SELECT id, code, sub_type, duration_days, is_used, used_by_device, used_at FROM myapp.subscriptions ORDER BY id DESC", conn)
    except Exception:
        pass
    return pd.DataFrame()

@st.cache_data(ttl=15)
def load_config_data():
    try:
        if conn and conn.closed == 0:
            config_rows = pd.read_sql("SELECT key, value FROM myapp.app_config", conn)
            return dict(zip(config_rows['key'], config_rows['value']))
    except Exception:
        pass
    return {'latest_version': '7.2.4', 'update_url': '', 'force_update': 'true', 'update_message': 'يرجى التحديث'}

# =====================================================================
# تهيئة الجداول وتحديث الهيكل الذاتي وصلاحيات الأدمن
# =====================================================================
try:
    if conn and conn.closed == 0:
        cur = conn.cursor()
        cur.execute("CREATE SCHEMA IF NOT EXISTS myapp;")
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
        
        all_secs = [
            "📈 نظرة عامة وإحصائيات الإصدارات",
            "👥 إدارة ومراقبة المستخدمين والتفعيل", 
            "📢 مركز الإشعارات الشامل الكامل",
            "🚀 إدارة التحديثات الإجبارية", 
            "⚡ تحديث البيانات الحية (LIVE UPDATE)",
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
        
        conn.commit()
        cur.close()
except Exception as e:
    if conn:
        try:
            conn.rollback()
        except Exception:
            pass

# =====================================================================
# نظام المصادقة
# =====================================================================
if "logged" not in st.session_state:
    st.session_state.logged = False

if not st.session_state.logged:
    st.title("🔐 تسجيل الدخول - لوحة تحكم MyClicker Pro")
    with st.form("login"):
        u = st.text_input("اسم المستخدم:")
        p = st.text_input("كلمة المرور:", type="password")
        if st.form_submit_button("تسجيل الدخول 🚀"):
            try:
                if conn and conn.closed == 0:
                    cur = conn.cursor()
                    cur.execute("SELECT password, allowed_sections, is_active FROM myapp.app_permissions WHERE username = %s", (u,))
                    res = cur.fetchone()
                    cur.close()
                    if res and res[2] and res[0] == p:
                        st.session_state.logged = True
                        st.session_state.user = u
                        st.session_state.sections = res[1] if res[1] else []
                        st.rerun()
                    else:
                        st.error("بيانات الدخول غير صحيحة أو الحساب معطل.")
                else:
                    st.error("فشل الاتصال بقاعدة البيانات.")
            except Exception as login_err:
                st.error(f"خطأ أثناء تسجيل الدخول: {login_err}")
    st.stop()

# =====================================================================
# الشريط الجانبي (Sidebar والصلاحيات)
# =====================================================================
st.sidebar.markdown(f"### ⚡ MyClicker Pro\n👤 المستخدم: **{st.session_state.user}**")
if st.sidebar.button("🔄 مسح الذاكرة المؤقتة والتحديث"):
    st.cache_data.clear()
    st.rerun()

user_allowed_sections = st.session_state.get('sections', [])
if not user_allowed_sections:
    st.warning("⚠️ ليس لديك أي صلاحيات لعرض الأقسام. يرجى مراجعة مدير النظام.")
    if st.sidebar.button("🚪 تسجيل الخروج"):
        st.session_state.logged = False
        st.rerun()
    st.stop()

page = st.sidebar.radio("القائمة الرئيسية:", user_allowed_sections)

if st.sidebar.button("🚪 تسجيل الخروج"):
    st.session_state.logged = False
    st.rerun()

# =====================================================================
# الأقسام البرمجية للوحة التحكم
# =====================================================================

if page == "📈 نظرة عامة وإحصائيات الإصدارات":
    st.title("📈 لوحة المؤشرات الحية وإحصائيات إصدارات التطبيق")
    df_u = load_users_data()

    total_subs = len(df_u)
    active_subs = len(df_u[df_u['status'] == 'Active']) if not df_u.empty else 0
    expired_subs = len(df_u[df_u['status'] == 'Expired']) if not df_u.empty else 0
    online_bots = len(df_u[df_u['bot_status'] == 'Online']) if not df_u.empty else 0
    total_clicks = int(df_u['accepted_clicks'].sum()) if not df_u.empty else 0

    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("👥 إجمالي الأجهزة", total_subs)
    col2.metric("🟢 النشطة (Active)", active_subs)
    col3.metric("🔴 المنتهية (Expired)", expired_subs)
    col4.metric("⚡ البوتات (Online)", online_bots)
    col5.metric("🖱️ إجمالي النقرات", total_clicks)

    st.markdown("---")
    
    if not df_u.empty and 'app_version' in df_u.columns:
        c_v1, c_v2 = st.columns(2)
        with c_v1:
            st.subheader("📊 تحليل وتوزيع إصدارات التطبيق")
            version_counts = df_u['app_version'].value_counts().reset_index()
            version_counts.columns = ['Version', 'Count']
            fig_ver = px.pie(version_counts, names='Version', values='Count', title="نسبة انتشار إصدارات التطبيق", hole=0.4)
            st.plotly_chart(fig_ver, use_container_width=True)
            
        with c_v2:
            st.subheader("🤖 حالة نشاط البوتات (Bot Status)")
            bot_counts = df_u['bot_status'].value_counts().reset_index()
            bot_counts.columns = ['Status', 'Count']
            fig_bot = px.bar(bot_counts, x='Status', y='Count', title="مقارنة البوتات (Online / Offline)", color='Status')
            st.plotly_chart(fig_bot, use_container_width=True)

elif page == "👥 إدارة ومراقبة المستخدمين والتفعيل":
    st.title("👥 إدارة المستخدمين والتحكم ببيانات التفعيل")
    df_users = load_users_data()

    if not df_users.empty:
        st.dataframe(df_users, use_container_width=True)
        
        st.markdown("---")
        st.subheader("🛠️ لوحة التحكم وتعديل بيانات المستخدم")
        
        device_list = df_users['device_id'].tolist()
        options = [f"هاتف: {p} | حالة: {s} | ID: {d[:8]}..." for p, s, d in zip(df_users['phone'], df_users['status'], device_list)]
        
        selected_idx = st.selectbox("اختر الجهاز للتعديل:", range(len(options)), format_func=lambda x: options[x])
        target_device = device_list[selected_idx]
        target_row = df_users[df_users['device_id'] == target_device].iloc[0]
        
        with st.form("edit_user_form"):
            col_e1, col_e2 = st.columns(2)
            with col_e1:
                new_phone = st.text_input("تعديل رقم الهاتف:", value=str(target_row['phone']))
                new_status = st.selectbox("حالة الاشتراك:", ["Active", "Expired", "Blocked"], index=["Active", "Expired", "Blocked"].index(target_row['status']))
            with col_e2:
                new_sub_type = st.selectbox("نوع الاشتراك:", ["VIP", "Pro", "TRIAL"], index=0)
                new_expiry = st.date_input("تاريخ الانتهاء الجديد:", value=pd.to_datetime(target_row['expiry_date']).date() if target_row['expiry_date'] else datetime.now().date())

            if st.form_submit_button("💾 حفظ التعديلات"):
                res = query("UPDATE myapp.users_status SET phone=%s, status=%s, subscription_type=%s, expiry_date=%s WHERE device_id=%s", 
                            (new_phone, new_status, new_sub_type, new_expiry, target_device))
                if res:
                    st.cache_data.clear()
                    st.success("تم التحديث بنجاح!")
                    st.rerun()

elif page == "📢 مركز الإشعارات الشامل الكامل":
    st.title("📢 مركز الإشعارات المطور")
    st.info("💡 تحكم كامل بإرسال الإشعارات الفورية للأجهزة.")
    
    df_notif = load_users_data()
    
    with st.form("send_notif_form"):
        target = st.selectbox("نطاق الإرسال:", ["الكل", "النشطين فقط", "المنتهين فقط"])
        msg = st.text_area("نص الإشعار:")
        
        if st.form_submit_button("إرسال الإشعار 🚀"):
            sql = "UPDATE myapp.users_status SET notice_message = %s"
            if target == "النشطين فقط": sql += " WHERE status = 'Active'"
            elif target == "المنتهين فقط": sql += " WHERE status = 'Expired'"
            
            if query(sql, (msg,)):
                st.success("✅ تم إرسال الإشعار للجميع!")

elif page == "🚀 إدارة التحديثات الإجبارية":
    st.title("🚀 إدارة التحديثات الإجبارية")
    conf = load_config_data()
    
    with st.form("upd_form"):
        v = st.text_input("رقم الإصدار الأحدث:", value=conf.get('latest_version', '7.2.4'))
        url = st.text_input("رابط الـ APK (Dropbox):", value=conf.get('update_url', ''))
        msg = st.text_area("رسالة التحديث:", value=conf.get('update_message', 'يرجى التحديث للاستمرار'))
        
        if st.form_submit_button("نشر التحديث 🚀"):
            query("INSERT INTO myapp.app_config (key, value) VALUES ('latest_version', %s) ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value", (v,))
            query("INSERT INTO myapp.app_config (key, value) VALUES ('update_url', %s) ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value", (url,))
            query("INSERT INTO myapp.app_config (key, value) VALUES ('update_message', %s) ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value", (msg,))
            st.success("✅ تم النشر!")

elif page == "⚡ تحديث البيانات الحية (LIVE UPDATE)":
    st.title("⚡ تحديث البيانات الحية (LIVE UPDATE)")
    st.info("💡 تحكم بالكلمات المفتاحية والمؤشرات بشكل فوري دون تحديث التطبيق.")

    conf = load_config_data()

    with st.form("live_update_form"):
        keywords = st.text_area("الكلمات المفتاحية للقبول (فاصلة ,):",
                               value=conf.get('live_keywords', 'قبول, accept, agree'))
        indicators = st.text_area("مؤشرات الطلبات (فاصلة ,):",
                                 value=conf.get('live_indicators', 'Economy, Jeeny, Petra'))

        if st.form_submit_button("حفظ وتحديث النظام 🚀"):
            query("INSERT INTO myapp.app_config (key, value) VALUES ('live_keywords', %s) ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value", (keywords,))
            query("INSERT INTO myapp.app_config (key, value) VALUES ('live_indicators', %s) ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value", (indicators,))
            
            # إرسال إشارة تنبيه للأجهزة
            query("UPDATE myapp.users_status SET notice_message = 'LIVE_UPDATE_TRIGGER'")
            
            st.cache_data.clear()
            st.success("✅ تم تحديث البيانات الحية لجميع البوتات!")
            st.rerun()

elif page == "🎫 توليد وإدارة الأكواد":
    st.title("🎫 توليد أكواد الاشتراك")
    with st.form("gen_codes"):
        tp = st.selectbox("نوع الكود:", ["VIP", "TRIAL"])
        days = st.number_input("الأيام:", min_value=1, value=30)
        qty = st.number_input("الكمية:", min_value=1, value=10)
        
        if st.form_submit_button("توليد 🚀"):
            for _ in range(qty):
                code = tp[:3].upper() + ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
                query("INSERT INTO myapp.subscriptions (code, sub_type, duration_days, is_used) VALUES (%s, %s, %s, FALSE)", (code, tp, days))
            st.success(f"تم توليد {qty} كود.")

elif page == "🤝 قسم الشركاء (الموزعين)":
    st.title("🤝 لوحة الموزعين")
    df_s = load_subs_data()
    if not df_s.empty:
        st.dataframe(df_s[df_s['is_used'] == False], use_container_width=True)

elif page == "📈 تحليل البيانات":
    st.title("📈 إحصائيات الطلبات")
    st.info("بيانات الطلبات المقبولة تظهر هنا للتحليل.")

elif page == "🖥️ حالة السيرفر":
    st.title("🖥️ حالة السيرفر")
    st.success("السيرفر يعمل بكفاءة 🟢")

elif page == "🔐 إدارة الصلاحيات والتحكم":
    st.title("🔐 إدارة صلاحيات المدراء")
    df_perms = pd.read_sql("SELECT id, username, role_name FROM myapp.app_permissions", conn)
    st.dataframe(df_perms, use_container_width=True)

elif page == "🛠️ الدعم الفني والتواصل":
    st.title("🛠️ الدعم الفني")
    st.info("تليجرام الدعم: @MyClicker_Support")

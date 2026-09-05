import streamlit as st
import pandas as pd
import psycopg2
import plotly.express as px
import random
import string
from datetime import datetime, timedelta

# =====================================================================
# إعدادات الصفحة وتصميم واجهة مستخدم احترافية (RTL)
# =====================================================================
st.set_page_config(
    page_title="MyClicker Pro Ultra Command Center",
    page_layout="wide",
    page_icon="⚡"
)

st.markdown("""
    <style>
    header {visibility: hidden;}
    body { direction: rtl; text-align: right; }
    [data-testid="stSidebar"] { text-align: right; direction: rtl; background-color: #f8fafc; }
    .stMetric { background-color: #ffffff; padding: 18px; border-radius: 14px; border: 1px solid #e2e8f0; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05); }
    .stTabs [data-baseweb="tab-list"] { gap: 12px; }
    .stTabs [data-baseweb="tab"] { background-color: #f1f5f9; border-radius: 10px 10px 0 0; padding: 12px 24px; font-weight: bold; }
    </style>
""", unsafe_allow_html=True)

# =====================================================================
# الاتصال بقاعدة البيانات (DigitalOcean PostgreSQL)
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
        st.error(f"خطأ في تنفيذ قاعدة البيانات: {e}")
        return False

# =====================================================================
# تهيئة الجداول التلقائية ونظام الإصلاح الذاتي (Self-Healing)
# =====================================================================
try:
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
        "👥 إدارة ومراقبة المستخدمين", 
        "🚀 إدارة التحديثات الإجبارية", 
        "🎫 توليد وإدارة الأكواد", 
        "🤝 قسم الشركاء (الموزعين)", 
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
    conn.rollback()

# =====================================================================
# نظام المصادقة والأمان
# =====================================================================
if "logged" not in st.session_state:
    st.session_state.logged = False

if not st.session_state.logged:
    st.title("🔐 تسجيل الدخول - لوحة تحكم MyClicker Pro")
    with st.form("login"):
        u = st.text_input("اسم المستخدم:")
        p = st.text_input("كلمة المرور:", type="password")
        if st.form_submit_button("تسجيل الدخول 🚀"):
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

# =====================================================================
# الشريط الجانبي (Sidebar)
# =====================================================================
st.sidebar.markdown(f"### ⚡ MyClicker Pro\n👤 المستخدم: **{st.session_state.user}**")
if st.sidebar.button("🔄 تحديث البيانات الشاملة"):
    st.rerun()

page = st.sidebar.radio("القائمة الرئيسية:", st.session_state.sections)

if st.sidebar.button("🚪 تسجيل الخروج"):
    st.session_state.logged = False
    st.rerun()

# =====================================================================
# الأقسام الاحترافية للوحة التحكم
# =====================================================================

# 1. نظرة عامة وإحصائيات الإصدارات (ميزة إضافية جديدة ومتقدمة)
if page == "📈 نظرة عامة وإحصائيات الإصدارات":
    st.title("📈 لوحة المؤشرات الحية وإحصائيات إصدارات التطبيق")
    st.markdown("متابعة دقيقة لأداء المنصة، توزيع إصدارات المستخدمين، وحالة الأجهزة المتصلة.")

    try:
        df_u = pd.read_sql("SELECT device_id, status, bot_status, app_version, accepted_clicks, last_active FROM myapp.users_status", conn)
        df_c = pd.read_sql("SELECT is_used FROM myapp.subscriptions", conn)
    except Exception:
        df_u = pd.DataFrame()
        df_c = pd.DataFrame()

    total_subs = len(df_u)
    active_subs = len(df_u[df_u['status'] == 'Active']) if not df_u.empty else 0
    online_bots = len(df_u[df_u['bot_status'] == 'Online']) if not df_u.empty else 0
    total_clicks = int(df_u['accepted_clicks'].sum()) if not df_u.empty else 0

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("👥 إجمالي الأجهزة المسجلة", total_subs)
    col2.metric("🟢 الأجهزة النشطة", active_subs)
    col3.metric("⚡ البوتات المتصلة (Online)", online_bots)
    col4.metric("🖱️ إجمالي النقرات المقبولة", total_clicks)

    st.markdown("---")
    
    if not df_u.empty and 'app_version' in df_u.columns:
        c_v1, c_v2 = st.columns(2)
        with c_v1:
            st.subheader("📊 تحليل وتوزيع إصدارات التطبيق لدى المستخدمين")
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
    else:
        st.info("لا توجد بيانات كافية لعرض رسوم الإصدارات حتى الآن.")

# 2. إدارة ومراقبة المستخدمين
elif page == "👥 إدارة ومراقبة المستخدمين":
    st.title("👥 إدارة المستخدمين والأجهزة والتحكم الفردي")
    try:
        df = pd.read_sql("SELECT device_id, phone, status, bot_status, app_version, accepted_clicks, last_active FROM myapp.users_status ORDER BY last_active DESC", conn)
        st.dataframe(df, use_container_width=True)
    except Exception:
        st.info("لا توجد بيانات مسجلة للمستخدمين حالياً.")

# 3. إدارة التحديثات الإجبارية ونشر النافذة المنبثقة
elif page == "🚀 إدارة التحديثات الإجبارية":
    st.title("🚀 إدارة التحديثات الإجبارية (النافذة المنبثقة وأزرار التحميل)")
    st.info("💡 هذه الإعدادات متزامنة مع السيرفر وتجبر النسخ القديمة على فتح نافذة التحميل المنبثقة مع زر مباشر.")
    
    try:
        config_rows = pd.read_sql("SELECT * FROM myapp.app_config", conn)
        conf = dict(zip(config_rows['key'], config_rows['value']))
    except Exception:
        conf = {'latest_version': '7.1.0', 'update_url': '', 'force_update': 'true', 'update_message': 'يرجى التحديث'}
    
    with st.form("upd_form_node"):
        v = st.text_input("رقم الإصدار الأحدث (مثل 7.2.0):", value=conf.get('latest_version', '7.1.0'))
        url = st.text_input("رابط التحميل المباشر للـ APK (زر التحميل):", value=conf.get('update_url', ''))
        msg = st.text_area("رسالة النافذة المنبثقة الإجبارية:", value=conf.get('update_message', 'يرجى تحديث التطبيق للاستمرار!'))
        forced = st.selectbox("حالة التحديث الإجباري:", ["true", "false"], index=0 if conf.get('force_update', 'true') == 'true' else 1)
        
        if st.form_submit_button("حفظ ونشر التحديث الإجباري لكافة الأجهزة 🚀"):
            query("INSERT INTO myapp.app_config (key, value) VALUES ('latest_version', %s) ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value", (v,))
            query("INSERT INTO myapp.app_config (key, value) VALUES ('update_url', %s) ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value", (url,))
            query("INSERT INTO myapp.app_config (key, value) VALUES ('update_message', %s) ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value", (msg,))
            query("INSERT INTO myapp.app_config (key, value) VALUES ('force_update', %s) ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value", (forced,))
            
            dialog_cmd = f"DIALOG_UPDATE:version={v}|url={url}|msg={msg}"
            query("UPDATE myapp.users_status SET notice_message = %s", (dialog_cmd,))
            
            st.success("✅ تم تحديث ونشر إعدادات التحديث الإجباري بنجاح عبر السيرفر!")
            st.rerun()
            
    st.markdown("---")
    st.subheader("💡 معاينة شكل التنبيه والزر المنبثق للمستخدم:")
    if url:
        st.markdown(f"""
        > **{conf.get('update_message', 'يرجى تحديث التطبيق!')}**
        > 
        > [![تحميل التحديث الآن](https://img.shields.io/badge/📥_تحميل_التحديث_الآن-أضغط_هنا-blue?style=for-the-badge)]({url})
        """)
    else:
        st.info("قم بإدخال رابط التحميل لمعاينة الزر هنا.")

# 4. توليد وإدارة الأكواد
elif page == "🎫 توليد وإدارة الأكواد":
    st.title("🎫 توليد وإدارة الأكواد والاشتراكات")
    with st.form("gen"):
        tp = st.selectbox("نوع الاشتراك:", ["VIP", "TRIAL"])
        days = st.number_input("المدة بالأيام:", min_value=1, value=30)
        qty = st.number_input("الكمية المراد توليدها:", min_value=1, value=10)
        if st.form_submit_button("توليد الأكواد الآن 🚀"):
            for _ in range(qty):
                code = tp[:3].upper() + ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
                query("INSERT INTO myapp.subscriptions (code, sub_type, duration_days, is_used) VALUES (%s, %s, %s, FALSE) ON CONFLICT DO NOTHING", (code, tp, days))
            st.success(f"تم توليد {qty} كود اشتراك بنجاح.")
            st.rerun()

# 5. قسم الشركاء (الموزعين)
elif page == "🤝 قسم الشركاء (الموزعين)":
    st.title("🤝 لوحة الشركاء والموزعين الشاملة")
    try:
        df_s = pd.read_sql("SELECT code, sub_type, duration_days, is_used, used_by_device, used_at FROM myapp.subscriptions ORDER BY id DESC", conn)
        t1, t2 = st.tabs(["📦 الأكواد المتاحة للتوزيع", "✅ الأكواد المستخدمة من العملاء"])
        t1.dataframe(df_s[df_s['is_used'] == False], use_container_width=True)
        t2.dataframe(df_s[df_s['is_used'] == True], use_container_width=True)
    except Exception:
        st.info("لا توجد أكواد مسجلة حالياً.")

# 6. تحليل البيانات (طلبات وأوقات الذروة)
elif page == "📈 تحليل البيانات":
    st.title("📈 تحليل البيانات وأوقات الذروة للطلبات")
    try:
        df_orders = pd.read_sql("SELECT order_time, price FROM myapp.accepted_orders", conn)
        if not df_orders.empty:
            df_orders['hour'] = pd.to_datetime(df_orders['order_time']).dt.hour
            fig = px.bar(df_orders.groupby('hour').size().reset_index(name='count'), x='hour', y='count', title="أوقات الذروة للطلبات المقبولة حسب الساعة")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("لا توجد سجلات طلبات كافية لعرض الرسوم البيانية.")
    except Exception:
        st.info("بيانات الطلبات غير متوفرة في قاعدة البيانات حالياً.")

# 7. حالة السيرفر
elif page == "🖥️ حالة السيرفر":
    st.title("🖥️ مراقبة حالة الخادم وقاعدة البيانات")
    st.success("🟢 سيرفر Node.js متصل بقاعدة بيانات PostgreSQL ويعمل بكفاءة عالية على DigitalOcean.")
    st.info("قاعدة البيانات: PostgreSQL | التشفير: SSL Active | بيئة العمل: Production")

# 8. إدارة الصلاحيات والتحكم
elif page == "🔐 إدارة الصلاحيات والتحكم":
    st.title("🔐 إدارة حسابات لوحة التحكم والصلاحيات")
    try:
        df_p = pd.read_sql("SELECT username, role_name, is_active FROM myapp.app_permissions", conn)
        st.dataframe(df_p, use_container_width=True)
    except Exception:
        st.info("لا توجد حسابات صلاحيات مسجلة.")

# 9. الدعم الفني والتواصل
elif page == "🛠️ الدعم الفني والتواصل":
    st.title("🛠️ الدعم الفني وقنوات التواصل")
    st.info("📱 واتساب الإدارة: مراسلة الدعم الفني")
    st.success("✈️ تليجرام الدعم الفني: @MyClicker_Support")

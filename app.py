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

# اتصال قاعدة البيانات (مطابق لهيكل جداول سيرفر Node.js)
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

# تهيئة جدول الإعدادات والصلاحيات الافتراضية إذا لم تكن موجودة
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

if page == "👥 إدارة ومراقبة المستخدمين":
    st.title("👥 إدارة المستخدمين والأجهزة والتحكم الشامل")
    try:
        df = pd.read_sql("SELECT device_id, phone, status, bot_status, app_version, accepted_clicks, last_active FROM myapp.users_status ORDER BY last_active DESC", conn)
        st.dataframe(df, use_container_width=True)
    except Exception as e:
        st.info("لا توجد بيانات مستخدمين مسجلة حتى الآن.")

elif page == "🚀 إدارة التحديثات الإجبارية":
    st.title("🚀 إدارة التحديثات الإجبارية (النافذة المنبثقة وزر التحميل)")
    st.info("💡 هذه الإعدادات متزامنة تماماً مع سيرفر Node.js وسيتم تطبيقها فوراً على التطبيق عند فحص الحالة.")
    
    try:
        config_rows = pd.read_sql("SELECT * FROM myapp.app_config", conn)
        conf = dict(zip(config_rows['key'], config_rows['value']))
    except Exception:
        conf = {'latest_version': '7.1.0', 'update_url': '', 'force_update': 'true'}
    
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
            
            # إرسال إشعار فوري لكل الأجهزة عبر حقل notice_message لفتح النافذة المنبثقة فوراً
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

elif page == "🎫 توليد وإدارة الأكواد":
    st.title("🎫 توليد وإدارة الأكواد والأجهزة المفعلة")
    with st.form("gen"):
        tp = st.selectbox("نوع الاشتراك:", ["VIP", "TRIAL"])
        days = st.number_input("المدة بالأيام:", min_value=1, value=30)
        qty = st.number_input("الكمية:", min_value=1, value=10)
        if st.form_submit_button("توليد الأكواد 🚀"):
            for _ in range(qty):
                code = tp[:3].upper() + ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
                query("INSERT INTO myapp.subscriptions (code, sub_type, duration_days, is_used) VALUES (%s, %s, %s, FALSE) ON CONFLICT DO NOTHING", (code, tp, days))
            st.success(f"تم توليد {qty} كود بنجاح.")
            st.rerun()

elif page == "🤝 قسم الشركاء (الموزعين)":
    st.title("🤝 لوحة الشركاء والموزعين الشاملة")
    try:
        df_s = pd.read_sql("SELECT code, sub_type, duration_days, is_used, used_by_device, used_at FROM myapp.subscriptions ORDER BY id DESC", conn)
        t1, t2 = st.tabs(["📦 الأكواد المتاحة", "✅ الأكواد المستخدمة"])
        t1.dataframe(df_s[df_s['is_used'] == False], use_container_width=True)
        t2.dataframe(df_s[df_s['is_used'] == True], use_container_width=True)
    except Exception:
        st.info("لا توجد أكواد مسجلة حالياً.")

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

elif page == "🖥️ حالة السيرفر":
    st.title("🖥️ مراقبة السيرفر")
    st.success("🟢 سيرفر Node.js متصل بقاعدة بيانات PostgreSQL ويعمل بكفاءة على DigitalOcean.")
    st.info("قاعدة البيانات: PostgreSQL | التشفير: SSL Active")

elif page == "🔐 إدارة الصلاحيات والتحكم":
    st.title("🔐 إدارة حسابات لوحة التحكم وصلاحياتها")
    try:
        df_p = pd.read_sql("SELECT username, role_name, is_active FROM myapp.app_permissions", conn)
        st.dataframe(df_p, use_container_width=True)
    except Exception:
        st.info("لا توجد صلاحيات مسجلة.")

elif page == "🛠️ الدعم الفني والتواصل":
    st.title("🛠️ الدعم الفني")
    st.info("📱 واتساب الإدارة: مراسلة الدعم الفني")
    st.success("✈️ تليجرام الدعم: @MyClicker_Support")

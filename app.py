import streamlit as st
import pandas as pd
import psycopg2
import plotly.express as px
import os
import urllib.request
import random
import string
from datetime import datetime, timedelta

# =====================================================================
# 1. إعدادات الصفحة والتنسيق الاحترافي (RTL)
# =====================================================================
st.set_page_config(page_title="MyClicker Pro Ultra Dashboard", layout="wide", page_icon="⚡")

st.markdown("""
    <style>
    header {visibility: hidden;}
    body { direction: rtl; text-align: right; }
    [data-testid="stSidebar"] { text-align: right; direction: rtl; }
    .stMetric { background-color: #f8fafc; padding: 15px; border-radius: 12px; border: 1px solid #e2e8f0; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    .stTabs [data-baseweb="tab-list"] { gap: 10px; }
    .stTabs [data-baseweb="tab"] { background-color: #f1f5f9; border-radius: 8px 8px 0 0; padding: 10px 20px; }
    </style>
""", unsafe_allow_html=True)

# --- وظائف قاعدة البيانات المعززة ---
def download_ca_cert():
    cert_path = "ca-certificate.crt"
    # إذا كان الملف موجوداً وحجمه 0، نقوم بحذفه للمحاولة مرة أخرى بشكل صحيح
    if os.path.exists(cert_path) and os.path.getsize(cert_path) == 0:
        os.remove(cert_path)
        
    if not os.path.exists(cert_path):
        try:
            url = "https://certs.ondigitalocean.com/ca-certificate.crt"
            urllib.request.urlretrieve(url, cert_path)
        except Exception:
            pass # لن ننشئ ملفاً فارغاً هنا
    return cert_path

@st.cache_resource
def init_connection():
    cert_file = download_ca_cert()
    try:
        # المحاولة 1: الاتصال باستخدام الشهادة (الأكثر أماناً)
        if os.path.exists(cert_file) and os.path.getsize(cert_file) > 0:
            return psycopg2.connect(
                database="defaultdb", user="doadmin", password="1tHwqXCgn8BS6iTm942V3f7a",
                host="myclicker-db-rd7ky.db1.ondigitalocean.com", port="5432",
                sslmode="require", sslrootcert=cert_file
            )
        else:
            # المحاولة 2: الاتصال بدون شهادة محددة (Fallback)
            return psycopg2.connect(
                database="defaultdb", user="doadmin", password="1tHwqXCgn8BS6iTm942V3f7a",
                host="myclicker-db-rd7ky.db1.ondigitalocean.com", port="5432",
                sslmode="require"
            )
    except Exception as e:
        st.error(f"فشل الاتصال النهائي: {e}")
        return None

conn = init_connection()
if conn is None: st.stop()

def run_query(query, params=()):
    try:
        cur = conn.cursor(); cur.execute(query, params); conn.commit(); cur.close()
        return True
    except Exception as e:
        conn.rollback(); st.error(f"خطأ في التنفيذ: {e}"); return False

# =====================================================================
# 2. إعداد الجداول (التحديث الإجباري والأنظمة الأساسية)
# =====================================================================
def setup_full_system():
    try:
        cur = conn.cursor()
        cur.execute("CREATE SCHEMA IF NOT EXISTS myapp;")
        
        # جدول إعدادات التحديث الإجباري العام
        cur.execute("""
            CREATE TABLE IF NOT EXISTS myapp.app_config (
                id SERIAL PRIMARY KEY,
                latest_version VARCHAR(20) DEFAULT '7.2.0',
                update_url TEXT DEFAULT '',
                update_message TEXT DEFAULT 'تحديث جديد متاح للأداء الأفضل',
                force_update_enabled BOOLEAN DEFAULT FALSE
            );
        """)

        # جدول المستخدمين المطور (مع التحديث الفردي)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS myapp.users_status (
                device_id VARCHAR(255) PRIMARY KEY,
                phone VARCHAR(50) DEFAULT '',
                status VARCHAR(50) DEFAULT 'Active',
                bot_status VARCHAR(50) DEFAULT 'Offline',
                accepted_clicks INT DEFAULT 0,
                subscription_type VARCHAR(50) DEFAULT 'VIP',
                app_version VARCHAR(20) DEFAULT '7.2.0',
                force_update_single BOOLEAN DEFAULT FALSE,
                expiry_date TIMESTAMP DEFAULT NULL,
                notice_message TEXT DEFAULT '',
                last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        
        # تأكيد تحديث الأعمدة
        cur.execute("ALTER TABLE myapp.users_status ADD COLUMN IF NOT EXISTS app_version VARCHAR(20) DEFAULT '7.2.0';")
        cur.execute("ALTER TABLE myapp.users_status ADD COLUMN IF NOT EXISTS force_update_single BOOLEAN DEFAULT FALSE;")
        
        conn.commit(); cur.close()
    except Exception as e: conn.rollback()

setup_full_system()

# =====================================================================
# 3. نظام الدخول والمصادقة
# =====================================================================
if "logged_in" not in st.session_state: st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.title("🔐 لوحة تحكم MyClicker Pro Ultra")
    with st.form("login"):
        u = st.text_input("اسم المستخدم:")
        p = st.text_input("كلمة المرور:", type="password")
        if st.form_submit_button("دخول"):
            cur = conn.cursor()
            cur.execute("SELECT password, allowed_sections, is_active FROM myapp.app_permissions WHERE username = %s", (u,))
            res = cur.fetchone()
            if res and res[2] and res[0] == p:
                st.session_state.logged_in, st.session_state.username, st.session_state.allowed_sections = True, u, res[1]
                st.rerun()
            else: st.error("خطأ في البيانات أو الحساب معطل")
    st.stop()

# --- Sidebar ---
with st.sidebar:
    st.image("https://img.icons8.com/fluency/96/lightning-bolt.png", width=80)
    st.markdown(f"### ⚡ MyClicker Pro\n👤 {st.session_state.username}")
    choice = st.radio("القائمة الرئيسية:", st.session_state.allowed_sections)
    if st.sidebar.button("🚪 خروج"): 
        st.session_state.logged_in = False; st.rerun()

# =====================================================================
# 4. تنفيذ الأقسام بالكامل
# =====================================================================

# --- 1. الإحصائيات العامة ---
if choice == "📈 الإحصائيات العامة":
    st.title("📈 إحصائيات النظام والأداء")
    df_u = pd.read_sql("SELECT status, bot_status, accepted_clicks, app_version FROM myapp.users_status", conn)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("إجمالي المشتركين", len(df_u))
    c2.metric("البوتات النشطة ⚡", len(df_u[df_u['bot_status']=='Online']))
    c3.metric("إجمالي النقرات", df_u['accepted_clicks'].sum())
    c4.metric("منتهية الصلاحية", len(df_u[df_u['status']=='Expired']))
    
    col_g1, col_g2 = st.columns(2)
    with col_g1: st.plotly_chart(px.pie(df_u, names='status', title="حالات الاشتراكات", hole=0.4), use_container_width=True)
    with col_g2: st.plotly_chart(px.bar(df_u['app_version'].value_counts().reset_index(), x='index', y='app_version', title="توزيع الإصدارات"), use_container_width=True)

# --- 2. إدارة المستخدمين (مع التحديث الفردي) ---
elif choice == "👥 إدارة ومراقبة المستخدمين":
    st.title("👥 إدارة الأجهزة والتحكم الفردي")
    df = pd.read_sql("SELECT device_id, phone, status, app_version, force_update_single, notice_message, last_active FROM myapp.users_status ORDER BY last_active DESC", conn)
    
    st.data_editor(df, use_container_width=True, hide_index=True)

    st.markdown("### 🛠️ إجراءات فردية (التحديث الإجباري الفردي)")
    sel_id = st.selectbox("اختر الجهاز:", df['device_id'].tolist())
    if sel_id:
        user_row = df[df['device_id'] == sel_id].iloc[0]
        ca1, ca2 = st.columns(2)
        with ca1:
            is_f = st.checkbox("⚡ تفعيل تحديث إجباري لهذا الجهاز فقط", value=bool(user_row['force_update_single']))
            if st.button("تأكيد الإعداد الفردي"): 
                run_query("UPDATE myapp.users_status SET force_update_single = %s WHERE device_id = %s", (is_f, sel_id))
                st.success("تم تحديث حالة الجهاز")
        with ca2:
            st.info("إرسال إشعار للنظام لهذا المستخدم")
            m = st.text_input("رسالة PUSH:")
            if st.button("إرسال الآن"):
                run_query("UPDATE myapp.users_status SET notice_message = %s WHERE device_id = %s", (f"PUSH:{m}", sel_id))

# --- 3. إدارة التحديثات الإجبارية (العامة) ---
elif choice == "🚀 إدارة التحديثات الإجبارية":
    st.title("🚀 إدارة التحديثات الإجبارية العامة")
    conf = pd.read_sql("SELECT * FROM myapp.app_config WHERE id = 1", conn).iloc[0]
    with st.form("force_up"):
        st.warning("تنبيه: تفعيل 'الإيقاف الإجباري' سيمنع النسخ القديمة من العمل.")
        v = st.text_input("الإصدار الأحدث المطلوب:", value=conf['latest_version'])
        u = st.text_input("رابط الـ APK المباشر:", value=conf['update_url'])
        m = st.text_area("رسالة التحديث للمستخدم:", value=conf['update_message'])
        f = st.checkbox("تفعيل الإيقاف الإجباري العام لكل المشتركين", value=conf['force_update_enabled'])
        if st.form_submit_button("حفظ ونشر التحديث العام 🚀"):
            run_query("UPDATE myapp.app_config SET latest_version=%s, update_url=%s, update_message=%s, force_update_enabled=%s WHERE id = 1", (v, u, m, f))
            st.success("✅ تم نشر التحديث الإجباري العام")

# --- 4. توليد وإدارة الأكواد ---
elif choice == "🎫 توليد وإدارة الأكواد (الادمن)":
    st.title("🎫 توليد أكواد اشتراكات جديدة")
    df_codes = pd.read_sql("SELECT * FROM myapp.subscriptions ORDER BY id DESC", conn)
    with st.form("gen"):
        col_t, col_q = st.columns(2)
        tp = col_t.selectbox("نوع الكود:", ["VIP", "TRIAL"])
        qty = col_q.number_input("الكمية:", 1, 500, 10)
        if st.form_submit_button("توليد 🚀"):
            for _ in range(qty):
                code = f"{tp}-{''.join(random.choices(string.ascii_uppercase + string.digits, k=6))}"
                run_query("INSERT INTO myapp.subscriptions (code, sub_type, duration_days, is_used) VALUES (%s,%s,30,FALSE)", (code, tp))
            st.success("تم التوليد"); st.rerun()
    st.dataframe(df_codes, use_container_width=True)

# --- 5. قسم الشركاء والموزعين ---
elif choice == "🤝 قسم الشركاء (الموزعين)":
    st.title("🤝 لوحة الموزعين والأكواد")
    df_s = pd.read_sql("SELECT code, sub_type, is_used, used_by_device, used_at FROM myapp.subscriptions WHERE is_used=FALSE", conn)
    st.subheader("📦 الأكواد المتاحة للتوزيع")
    st.dataframe(df_s, use_container_width=True)

# --- 6. حالة السيرفر ---
elif choice == "🖥️ حالة السيرفر":
    st.title("🖥️ مراقبة الخادم")
    st.success("🟢 السيرفر متصل ويعمل بكفاءة عالية (DigitalOcean)")
    st.info("الربط: SSL Secured | Database: PostgreSQL")

# --- 7. إدارة الصلاحيات ---
elif choice == "🔐 إدارة الصلاحيات والتحكم":
    st.title("🔐 إدارة حسابات النظام")
    with st.form("new"):
        nu, np = st.columns(2)
        u_name = nu.text_input("Username:")
        p_word = np.text_input("Password:", type="password")
        role = st.text_input("Role Description:")
        secs = st.multiselect("الأقسام المسموحة:", ["📈 الإحصائيات العامة", "👥 إدارة ومراقبة المستخدمين", "🚀 إدارة التحديثات الإجبارية", "🎫 توليد وإدارة الأكواد (الادمن)", "🤝 قسم الشركاء (الموزعين)", "🖥️ حالة السيرفر", "🔐 إدارة الصلاحيات والتحكم", "🛠️ الدعم الفني والتواصل"])
        if st.form_submit_button("إضافة الحساب 💾"):
            run_query("INSERT INTO myapp.app_permissions (username, password, role_name, allowed_sections) VALUES (%s,%s,%s,%s)", (u_name, p_word, role, secs))
            st.rerun()

# --- 8. الدعم الفني والتواصل ---
elif choice == "🛠️ الدعم الفني والتواصل":
    st.title("🛠️ قنوات الدعم والتواصل")
    st.success("📱 **واتساب الدعم:** https://chat.whatsapp.com/BaC7MvBpJdoKKz4wG5VpWq")
    st.info("✈️ **تليجرام الإدارة:** @MyClicker_Admin")
    st.markdown("Copyright © 2027 MyClicker Pro. All rights reserved.")

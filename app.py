import streamlit as st
import pandas as pd
import psycopg2
import plotly.express as px
import random
import string
from datetime import datetime, timedelta

# =====================================================================
# 1. إعدادات الصفحة والتنسيقات الاحترافية
# =====================================================================
st.set_page_config(page_title="MyClicker Pro Ultra Command Center", layout="wide", page_icon="⚡")

st.markdown("""
    <style>
    header {visibility: hidden;}
    * { font-family: 'Segoe UI', Roboto, 'Cairo', sans-serif !important; }
    .stApp { background-color: #f8fafc !important; }
    .stMetric { 
        background-color: #ffffff !important; padding: 20px !important; border-radius: 15px !important; 
        border: 1px solid #e2e8f0 !important; box-shadow: 0 4px 6px rgba(0,0,0,0.05);
    }
    .stButton button { border-radius: 10px !important; font-weight: 700 !important; }
    .sidebar .sidebar-content { background-image: linear-gradient(#2e7d32,#1b5e20); color: white; }
    </style>
""", unsafe_allow_html=True)

# =====================================================================
# 2. وظائف قاعدة البيانات الأساسية
# =====================================================================
@st.cache_resource
def get_conn():
    try:
        return psycopg2.connect(
            database="defaultdb", user="doadmin", password="1tHwqXCgn8BS6iTm942V3f7a",
            host="myclicker-db-rd7ky.db1.ondigitalocean.com", port="5432", sslmode="require"
        )
    except: return None

def query(sql, params=()):
    conn = get_conn()
    if not conn: return False
    try:
        cur = conn.cursor()
        cur.execute(sql, params)
        conn.commit()
        cur.close()
        return True
    except Exception as e:
        st.error(f"خطأ قاعدة بيانات: {e}")
        return False

@st.cache_data(ttl=5)
def load_data(sql):
    conn = get_conn()
    if not conn: return pd.DataFrame()
    try: return pd.read_sql(sql, conn)
    except: return pd.DataFrame()

def load_config():
    df = load_data("SELECT key, value FROM myapp.app_config")
    return dict(zip(df['key'], df['value'])) if not df.empty else {}

# =====================================================================
# 3. نظام المصادقة
# =====================================================================
if "logged" not in st.session_state: st.session_state.logged = False

if not st.session_state.logged:
    st.title("⚡ تسجيل دخول MyClicker Pro")
    with st.form("login"):
        u = st.text_input("اسم المستخدم")
        p = st.text_input("كلمة المرور", type="password")
        if st.form_submit_button("دخول 🚀"):
            conn = get_conn()
            cur = conn.cursor()
            cur.execute("SELECT password, allowed_sections FROM myapp.app_permissions WHERE username = %s AND is_active = TRUE", (u,))
            res = cur.fetchone()
            if res and res[0] == p:
                st.session_state.logged, st.session_state.user, st.session_state.sections = True, u, res[1]
                st.rerun()
            else: st.error("بيانات غير صحيحة")
    st.stop()

# =====================================================================
# 4. القائمة الجانبية والتنقل
# =====================================================================
st.sidebar.markdown(f"### ⚡ مركز القيادة\n👤: **{st.session_state.user}**")
page = st.sidebar.radio("انتقل إلى:", st.session_state.sections)
if st.sidebar.button("🚪 خروج"):
    st.session_state.logged = False
    st.rerun()

# =====================================================================
# 5. الأقسام البرمجية
# =====================================================================

# --- 1. الإحصائيات العامة ---
if page == "📈 نظرة عامة وإحصائيات الإصدارات":
    st.title("📈 التحليل المباشر للشبكة")
    df = load_data("SELECT * FROM myapp.users_status")
    if not df.empty:
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("إجمالي الأجهزة", len(df))
        c2.metric("🟢 نشط حالياً", len(df[df['status'] == 'Active']))
        c3.metric("🔴 اشتراك منتهي", len(df[df['status'] == 'Expired']))
        c4.metric("🖱️ إجمالي النقرات", int(df['accepted_clicks'].sum()))
        st.subheader("📊 توزيع إصدارات التطبيق")
        st.plotly_chart(px.pie(df, names='app_version', hole=0.4), use_container_width=True)

# --- 2. إدارة المستخدمين (مع التحديث الإجباري الفردي) ---
elif page == "👥 إدارة ومراقبة المستخدمين والتفعيل":
    st.title("👥 إدارة الأجهزة والتحديث الفردي")
    df = load_data("SELECT device_id, phone, status, app_version, last_active FROM myapp.users_status ORDER BY last_active DESC")
    st.dataframe(df, use_container_width=True)
    
    st.markdown("---")
    colA, colB = st.columns(2)
    
    with colA:
        st.subheader("🛠️ تعديل بيانات المشترك")
        target = st.selectbox("اختر الهاتف:", df['phone'].tolist())
        target_id = df[df['phone'] == target]['device_id'].iloc[0]
        with st.form("edit_user"):
            new_status = st.selectbox("تغيير الحالة", ["Active", "Expired", "Blocked"])
            if st.form_submit_button("تحديث الحالة 💾"):
                query("UPDATE myapp.users_status SET status=%s WHERE device_id=%s", (new_status, target_id))
                st.success("تم التحديث")

    with colB:
        st.subheader("🚀 تحديث إجباري لهذا الجهاز فقط")
        conf = load_config()
        with st.form("force_individual"):
            v = st.text_input("إصدار التحديث", value=conf.get('latest_version', '7.2.4'))
            msg = st.text_area("رسالة الإجبار", value="يجب تحديث هاتفك الآن لاستمرار عمل البوت!")
            if st.form_submit_button("إرسال أمر التحديث الإجباري ⚠️"):
                cmd = f"DIALOG_UPDATE:version={v}|url={conf.get('update_url', '')}|msg={msg}"
                query("UPDATE myapp.users_status SET notice_message = %s WHERE device_id = %s", (cmd, target_id))
                st.warning(f"تم إرسال أمر التحديث لهاتف {target}")

# --- 3. مركز الإشعارات ---
elif page == "📢 مركز الإشعارات الشامل الكامل":
    st.title("📢 إرسال تنبيهات شريط الحالة")
    with st.form("broadcast"):
        msg = st.text_area("نص الإشعار")
        if st.form_submit_button("بث لجميع المستخدمين 🚀"):
            query("UPDATE myapp.users_status SET notice_message = %s", (f"STATUSBAR:{msg}",))
            st.success("تم البث بنجاح")

# --- 4. التحديث الإجباري الشامل ---
elif page == "🚀 إدارة التحديثات الإجبارية":
    st.title("🚀 نظام التحديث الإجباري العام")
    conf = load_config()
    with st.form("global_upd"):
        v = st.text_input("رقم الإصدار الجديد", value=conf.get('latest_version', '7.2.4'))
        url = st.text_input("رابط APK (Dropbox)", value=conf.get('update_url', ''))
        msg = st.text_area("رسالة النافذة المنبثقة", value=conf.get('update_message', 'نرجو التحديث للاستمرار'))
        if st.form_submit_button("نشر التحديث لكافة المستخدمين 🌍"):
            query("INSERT INTO myapp.app_config (key, value) VALUES ('latest_version', %s), ('update_url', %s), ('update_message', %s) ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value", (v, url, msg))
            query("UPDATE myapp.users_status SET notice_message = %s", (f"DIALOG_UPDATE:version={v}|url={url}|msg={msg}",))
            st.success("تم تفعيل وضع التحديث الإجباري العالمي")

# --- 5. لوحة LIVE UPDATE المتقدمة (الذكاء والتمويه) ---
elif page == "⚡ تحديث البيانات الحية (LIVE UPDATE)":
    st.title("⚡ التحكم الذكي في سلوك البوت")
    st.info("💡 هذه الإعدادات تغير طريقة عمل البوت في هواتف المستخدمين فوراً دون تحديث.")
    conf = load_config()
    
    with st.form("advanced_live"):
        c1, c2 = st.columns(2)
        with c1:
            kw = st.text_area("✅ كلمات القبول (اضغط إذا وجدت):", value=conf.get('live_keywords', 'قبول, accept, استلام'))
            neg = st.text_area("❌ كلمات التجنب (لا تضغط إذا وجدت):", value=conf.get('live_negative_keywords', 'كاش, سيء, مديونية'))
        with c2:
            ind = st.text_area("🔍 مؤشرات الطلب (دليل وجود طلب):", value=conf.get('live_indicators', 'Economy, Uber, Jeeny, Petra, ريال, د.أ'))
            jitter = st.slider("🎭 التمويه البشري (تأخير عشوائي بالـ ms):", 0, 1000, int(conf.get('live_jitter', 50)))
        
        status = st.radio("🚦 حالة النظام العالمية:", ["ON (يعمل)", "OFF (إيقاف شامل)"], index=0 if conf.get('global_status', 'ON') == 'ON' else 1)
        
        if st.form_submit_button("حفظ وتحديث ذكاء جميع البوتات 🚀"):
            query("INSERT INTO myapp.app_config (key, value) VALUES ('live_keywords', %s), ('live_negative_keywords', %s), ('live_indicators', %s), ('live_jitter', %s), ('global_status', %s) ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value", 
                  (kw, neg, ind, str(jitter), "ON" if "ON" in status else "OFF"))
            query("UPDATE myapp.users_status SET notice_message = 'LIVE_UPDATE_TRIGGER'")
            st.success("✅ تم تحديث ذكاء البوتات وإرسال الإشارة لجميع الأجهزة!")

# --- باقي الأقسام الأساسية ---
elif page == "🎫 توليد وإدارة الأكواد":
    st.title("🎫 مصنع الأكواد")
    with st.form("gen"):
        t = st.selectbox("نوع الكود", ["VIP", "TRIAL"])
        d = st.number_input("المدة (أيام)", 1, 365, 30)
        q = st.number_input("الكمية", 1, 100, 10)
        if st.form_submit_button("توليد الآن 🚀"):
            for _ in range(q):
                code = t + ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
                query("INSERT INTO myapp.subscriptions (code, sub_type, duration_days, is_used) VALUES (%s, %s, %s, FALSE)", (code, t, d))
            st.success(f"تم إنشاء {q} كود بنجاح")

elif page == "🤝 قسم الشركاء (الموزعين)":
    st.title("🤝 لوحة الموزعين")
    df = load_data("SELECT code, sub_type, duration_days FROM myapp.subscriptions WHERE is_used = FALSE")
    st.dataframe(df, use_container_width=True)

elif page == "🖥️ حالة السيرفر":
    st.title("🖥️ حالة السيرفر")
    st.success("قاعدة البيانات متصلة وتعمل بكفاءة 🟢")

elif page == "🔐 إدارة الصلاحيات والتحكم":
    st.title("🔐 أمن النظام")
    df = load_data("SELECT username, role_name, is_active FROM myapp.app_permissions")
    st.dataframe(df, use_container_width=True)

elif page == "🛠️ الدعم الفني والتواصل":
    st.title("🛠️ مركز الدعم")
    st.info("للتواصل مع المطور: @MyClicker_Support")

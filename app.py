import streamlit as st
import pandas as pd
import psycopg2
from psycopg2.extras import RealDictCursor
import hashlib
import os
import datetime
import plotly.express as px

# 1. إعدادات الهوية والجمالية
st.set_page_config(page_title="MyClicker Pro | المركز القيادي", layout="wide", page_icon="👑")

st.markdown("""
    <style>
    .main { background-color: #f8fafc; }
    .stMetric { background-color: #ffffff; padding: 20px; border-radius: 12px; border: 1px solid #e2e8f0; }
    .stButton>button { border-radius: 8px; font-weight: bold; }
    </style>
""", unsafe_allow_html=True)

# 2. محرك قاعدة البيانات
def get_db_connection():
    try:
        db_url = st.secrets["DATABASE_URL"]
        return psycopg2.connect(db_url, sslmode='require')
    except Exception as e:
        st.error(f"❌ فشل الاتصال بقاعدة البيانات: {e}")
        st.stop()

def run_query(query, params=None, fetch=False):
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        cur.execute(query, params)
        if fetch: return cur.fetchall()
        conn.commit()
        return True
    except Exception as e:
        st.error(f"❌ خطأ: {e}")
        return None
    finally: conn.close()

# 3. نظام تسجيل الدخول
if 'auth' not in st.session_state: st.session_state.auth = False

if not st.session_state.auth:
    st.title("🔐 تسجيل دخول المركز القيادي")
    with st.form("login_form"):
        u = st.text_input("اسم المستخدم")
        p = st.text_input("كلمة المرور", type="password")
        if st.form_submit_button("دخول آمن"):
            res = run_query("SELECT * FROM myapp.app_permissions WHERE username=%s AND password=%s AND is_active=TRUE", 
                           (u, hashlib.sha256(p.encode()).hexdigest()), fetch=True)
            if res:
                st.session_state.auth = True
                st.session_state.user = res[0]
                st.rerun()
            else: st.error("⚠️ بيانات خاطئة")
    st.stop()

# 4. القائمة الجانبية + [زر تحديث البيانات الشامل]
user_data = st.session_state.user
st.sidebar.title(f"👑 {user_data['role_name']}")
st.sidebar.info(f"المسؤول: {user_data['username']}")

if st.sidebar.button("🔄 تحديث كافة البيانات الآن"):
    st.cache_data.clear()
    st.rerun()

menu = st.sidebar.selectbox("القائمة القيادية", user_data['allowed_sections'])

# ---------------------------------------------------------
# 📊 القسم 1: الإحصائيات العامة
# ---------------------------------------------------------
if menu == "📊 نظرة عامة":
    st.header("📊 لوحة مؤشرات الأداء والتحكم الجماعي")
    stats = run_query("""
        SELECT (SELECT count(*) FROM myapp.users_status) as users,
        (SELECT count(*) FROM myapp.users_status WHERE last_active > NOW() - INTERVAL '5 minutes') as online,
        (SELECT sum(accepted_clicks) FROM myapp.users_status) as clicks,
        (SELECT count(*) FROM myapp.subscriptions WHERE is_used = FALSE) as stock
    """, fetch=True)[0]

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("إجمالي السائقين", stats['users'])
    c2.metric("أونلاين الآن 🟢", stats['online'])
    c3.metric("إجمالي النقرات 🎯", stats['clicks'] or 0)
    c4.metric("الأكواد الجاهزة", stats['stock'])

    st.divider()
    st.subheader("🚀 تفعيل الطوارئ الجماعي")
    free_res = run_query("SELECT value FROM myapp.app_config WHERE key='global_free_mode'", fetch=True)
    is_free = free_res[0]['value'] == 'true' if free_res else False
    days_res = run_query("SELECT value FROM myapp.app_config WHERE key='global_free_days'", fetch=True)
    current_granted = int(days_res[0]['value']) if days_res else 7

    col_t, col_d = st.columns(2)
    with col_t:
        st.write(f"**الحالة:** {'🟢 مفعّل' if is_free else '🔴 معطّل'}")
        if st.button("تبديل وضع التفعيل الجماعي 🔄"):
            run_query("INSERT INTO myapp.app_config (key, value) VALUES ('global_free_mode', %s) ON CONFLICT (key) DO UPDATE SET value=%s", 
                     ('false' if is_free else 'true', 'false' if is_free else 'true'))
            st.rerun()
    with col_d:
        n_days = st.number_input("أيام المنحة الجماعية", 1, 999, current_granted)
        if st.button("تحديث أيام المنحة ⏳"):
            run_query("INSERT INTO myapp.app_config (key, value) VALUES ('global_free_days', %s) ON CONFLICT (key) DO UPDATE SET value=%s", (str(n_days), str(n_days)))
            st.success("تم التحديث")

# ---------------------------------------------------------
# 👥 القسم 2: إدارة الأجهزة (المزامنة + تعديل النقرات + الإصدار)
# ---------------------------------------------------------
elif menu == "👥 إدارة الأجهزة":
    st.header("👥 قاعدة بيانات السائقين والتحكم الفردي")
    
    users = run_query("""
        SELECT device_id, phone, status, sub_tier, expiry_date, accepted_clicks, app_version,
        CASE WHEN last_active > NOW() - INTERVAL '5 minutes' THEN 'Online 🟢' ELSE 'Offline 🔴' END as live_status,
        last_active FROM myapp.users_status ORDER BY last_active DESC
    """, fetch=True)
    df_u = pd.DataFrame(users)
    
    search = st.text_input("🔍 بحث (هاتف / ID)")
    if search:
        df_u = df_u[df_u['phone'].str.contains(search, na=False) | df_u['device_id'].str.contains(search, na=False)]
    
    st.dataframe(df_u, use_container_width=True)

    st.subheader("🛠️ تعديل بيانات مستخدم محدد")
    target = st.selectbox("اختر الجهاز للمزامنة والتعديل", df_u['device_id'])
    t_row = df_u[df_u['device_id'] == target].iloc[0]

    c1, c2, c3 = st.columns(3)
    with c1:
        st.write("**📝 تعديل المعلومات**")
        n_phone = st.text_input("رقم الهاتف", t_row['phone'])
        n_clicks = st.number_input("تعديل عدد النقرات", value=int(t_row['accepted_clicks']))
        if st.button("حفظ المزامنة والنقرات 💾"):
            run_query("UPDATE myapp.users_status SET phone=%s, accepted_clicks=%s WHERE device_id=%s", (n_phone, n_clicks, target))
            st.success("تم تحديث بيانات النقرات والهاتف")

    with c2:
        st.write("**🔑 التحكم في العضوية**")
        n_tier = st.selectbox("نوع الباقة", ["STANDARD", "VIP", "GOLD"], index=["STANDARD", "VIP", "GOLD"].index(t_row['sub_tier'] if t_row['sub_tier'] in ["STANDARD", "VIP", "GOLD"] else "STANDARD"))
        n_status = st.selectbox("الحالة", ["Active", "Blocked", "Frozen"], index=["Active", "Blocked", "Frozen"].index(t_row['status']))
        if st.button("تحديث حالة العضوية"):
            run_query("UPDATE myapp.users_status SET sub_tier=%s, status=%s WHERE device_id=%s", (n_tier, n_status, target))
            st.success("تم")

    with c3:
        st.write("**🚀 التحديث والتنبيهات**")
        st.info(f"إصدار التطبيق الحالي: {t_row['app_version']}")
        if st.button("طلب تحديث إجباري ⚠️"):
            run_query("UPDATE myapp.users_status SET app_version='FORCE_UPDATE' WHERE device_id=%s", (target,))
            st.warning("تم طلب التحديث")
        if st.button("حذف السائق 🧨"):
            run_query("DELETE FROM myapp.users_status WHERE device_id=%s", (target,))
            st.rerun()

# ---------------------------------------------------------
# 📱 القسم 4: السوشال ميديا (Excel Sheet التفاعلي)
# ---------------------------------------------------------
elif menu == "📱 السوشال ميديا":
    st.header("📱 نظام رقابة السوشال ميديا (Excel Sheet)")
    run_query("CREATE TABLE IF NOT EXISTS myapp.social_tracker (id SERIAL PRIMARY KEY, ref TEXT, platform TEXT, notes TEXT, status TEXT, date_added TIMESTAMP DEFAULT NOW())", commit=True)
    df_social = pd.DataFrame(run_query("SELECT id, ref, platform, notes, status FROM myapp.social_tracker", fetch=True))
    
    st.write("يمكنك الإضافة والحذف والتعديل مباشرة في الجدول أدناه:")
    edited = st.data_editor(df_social, num_rows="dynamic", use_container_width=True)
    
    if st.button("حفظ ومزامنة بيانات الإكسل 📊"):
        run_query("DELETE FROM myapp.social_tracker")
        for _, r in edited.iterrows():
            run_query("INSERT INTO myapp.social_tracker (ref, platform, notes, status) VALUES (%s, %s, %s, %s)", (r['ref'], r['platform'], r['notes'], r['status']))
        st.success("تمت المزامنة بنجاح")

# ---------------------------------------------------------
# (بقية الأقسام: الأكواد، التحديثات الحية، الصلاحيات، الأمن) كما هي دون تغيير
# ---------------------------------------------------------
elif menu == "🎫 الأكواد":
    st.header("🎫 إدارة الأكواد")
    t1, t2 = st.tabs(["📥 المخزون", "✅ سجل التفعيل"])
    with t1:
        with st.form("gen"):
            pre = st.text_input("البادئة", "PRO")
            dur = st.number_input("المدة", 1, 365, 30)
            qty = st.number_input("الكمية", 1, 1000, 10)
            if st.form_submit_button("توليد ✨"):
                for _ in range(qty):
                    c = f"{pre}-{dur}-{os.urandom(3).hex().upper()}"
                    run_query("INSERT INTO myapp.subscriptions (code, duration_days) VALUES (%s, %s)", (c, dur))
                st.success("تم")
        st.dataframe(pd.DataFrame(run_query("SELECT code, duration_days FROM myapp.subscriptions WHERE is_used=FALSE ORDER BY id DESC", fetch=True)), use_container_width=True)
    with t2:
        df_used = pd.DataFrame(run_query("""
            SELECT s.code, u.phone, s.used_at, s.used_by_device, s.duration_days
            FROM myapp.subscriptions s JOIN myapp.users_status u ON s.used_by_device = u.device_id 
            WHERE s.is_used = TRUE ORDER BY s.used_at DESC
        """, fetch=True))
        st.dataframe(df_used, use_container_width=True)

elif menu == "🔄 التحديثات الحية":
    st.header("🔄 التحكم المباشر")
    conf = pd.DataFrame(run_query("SELECT key, value FROM myapp.app_config", fetch=True))
    edited_conf = st.data_editor(conf, use_container_width=True)
    if st.button("تطبيق حياً 🚀"):
        for _, r in edited_conf.iterrows(): run_query("UPDATE myapp.app_config SET value=%s WHERE key=%s", (r['value'], r['key']))
        st.success("تم")

elif menu == "🔐 الصلاحيات":
    st.header("🔐 إدارة الصلاحيات")
    with st.form("p"):
        u = st.text_input("المستخدم")
        p = st.text_input("كلمة المرور", type="password")
        r = st.selectbox("الرتبة", ["مدير شريك", "مشرف", "دعم فني"])
        s = st.multiselect("الأقسام", ["📊 نظرة عامة", "👥 إدارة الأجهزة", "🎫 الأكواد", "📱 السوشال ميديا", "🔄 التحديثات الحية", "📢 الإشعارات"])
        if st.form_submit_button("إضافة"):
            run_query("INSERT INTO myapp.app_permissions (username, password, role_name, allowed_sections) VALUES (%s, %s, %s, %s)", (u, hashlib.sha256(p.encode()).hexdigest(), r, s))
            st.success("تم")

elif menu == "🛡️ الأمن والرقابة":
    st.header("🛡️ سجل الرقابة")
    st.table(pd.DataFrame(run_query("SELECT * FROM myapp.security_logs ORDER BY created_at DESC LIMIT 200", fetch=True)))

elif menu == "📢 الإشعارات":
    st.header("📢 البث الجماعي")
    msg = st.text_area("نص البث")
    if st.button("بث للكل 📢"):
        run_query("INSERT INTO myapp.app_config (key, value) VALUES ('global_notice', %s) ON CONFLICT (key) DO UPDATE SET value=%s", (msg, msg))
        st.success("تم")

st.sidebar.markdown("---")
if st.sidebar.button("تسجيل الخروج"):
    st.session_state.auth = False
    st.rerun()

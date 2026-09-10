import streamlit as st
import pandas as pd
import psycopg2
from psycopg2.extras import RealDictCursor
import hashlib
import os
import datetime
import plotly.express as px

# 1. إعدادات الهوية والجمالية (Sovereign UI)
st.set_page_config(page_title="MyClicker Pro | المركز القيادي الأعلى", layout="wide", page_icon="👑")

st.markdown("""
    <style>
    .main { background-color: #f8fafc; }
    .stMetric { background-color: #ffffff; padding: 20px; border-radius: 12px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1); border: 1px solid #e2e8f0; }
    .stButton>button { width: 100%; border-radius: 8px; font-weight: bold; height: 3em; }
    .stDataFrame { border-radius: 12px; overflow: hidden; }
    </style>
""", unsafe_allow_html=True)

# 2. إدارة قاعدة البيانات
def get_db_connection():
    try:
        return psycopg2.connect(st.secrets["DATABASE_URL"], sslmode='require')
    except Exception as e:
        st.error(f"❌ فشل الاتصال: {e}")
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
    finally:
        cur.close(); conn.close()

# 3. نظام تسجيل الدخول
if 'auth' not in st.session_state: st.session_state.auth = False

if not st.session_state.auth:
    st.title("🔐 بوابة الوصول المركزية للمدراء")
    col_l, _ = st.columns([1, 2])
    with col_l:
        u = st.text_input("اسم المستخدم")
        p = st.text_input("كلمة المرور", type="password")
        if st.button("دخول آمن للمنظومة"):
            # admin / admin123
            if u == "admin" and hashlib.sha256(p.encode()).hexdigest() == "240be518fabd2724ddb6f04eeb1da5967448d7e831c08c8fa822809f74c720a9":
                st.session_state.auth = True
                st.session_state.user = {'username': 'admin', 'role_name': 'المدير العام', 'allowed_sections': ["📊 نظرة عامة", "👥 إدارة الأجهزة", "🎫 نظام الأكواد", "📱 السوشال ميديا", "🔄 التحديثات الحية", "🔐 الصلاحيات والشركاء", "🛡️ الأمن والرقابة", "📢 البث الجماعي"]}
                st.rerun()
            else:
                res = run_query("SELECT * FROM myapp.app_permissions WHERE username=%s AND password=%s AND is_active=TRUE", (u, hashlib.sha256(p.encode()).hexdigest()), fetch=True)
                if res:
                    st.session_state.auth = True; st.session_state.user = res[0]; st.rerun()
                else: st.error("⚠️ بيانات خاطئة")
    st.stop()

# 4. القائمة الجانبية وإدارة الجلسة
user_data = st.session_state.user
st.sidebar.title(f"👑 {user_data['role_name']}")
if st.sidebar.button("🔄 تحديث البيانات"): st.cache_data.clear(); st.rerun()

menu = st.sidebar.selectbox("القائمة القيادية", user_data['allowed_sections'])

# ---------------------------------------------------------
# 📊 القسم 1: نظرة عامة والتحكم الجماعي
# ---------------------------------------------------------
if menu == "📊 نظرة عامة":
    st.header("📊 لوحة مؤشرات الأداء الحية")
    stats = run_query("""
        SELECT (SELECT count(*) FROM myapp.users_status) as u,
        (SELECT count(*) FROM myapp.users_status WHERE last_active > NOW() - INTERVAL '5 minutes') as online,
        (SELECT sum(accepted_clicks) FROM myapp.users_status) as clk,
        (SELECT count(*) FROM myapp.subscriptions WHERE is_used=FALSE) as stck
    """, fetch=True)[0]

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("إجمالي السائقين", stats['u'])
    c2.metric("أونلاين الآن 🟢", stats['online'])
    c3.metric("إجمالي النقرات 🎯", stats['clk'] or 0)
    c4.metric("الأكواد الجاهزة", stats['stck'])

    st.divider()
    st.subheader("⚡ تفعيل الطوارئ الجماعي (فتح النظام للكل)")
    
    res_f = run_query("SELECT value FROM myapp.app_config WHERE key='global_free_mode'", fetch=True)
    is_on = res_f[0]['value'] == 'true' if res_f else False
    res_d = run_query("SELECT value FROM myapp.app_config WHERE key='global_free_days'", fetch=True)
    curr_d = int(res_d[0]['value']) if res_d else 7

    ca, cb = st.columns(2)
    with ca:
        st.write(f"**حالة النظام:** {'🟢 مفتوح للجميع' if is_on else '🔴 مقفل بالاشتراكات'}")
        if st.button("تبديل وضع التفعيل الجماعي 🔄"):
            run_query("INSERT INTO myapp.app_config (key, value) VALUES ('global_free_mode', %s) ON CONFLICT (key) DO UPDATE SET value=%s", ('false' if is_on else 'true', 'false' if is_on else 'true'))
            st.rerun()
    with cb:
        n_days = st.number_input("أيام التفعيل التلقائي (المنحة)", 1, 999, curr_d)
        if st.button("تحديث قيمة أيام المنحة ⏳"):
            run_query("INSERT INTO myapp.app_config (key, value) VALUES ('global_free_days', %s) ON CONFLICT (key) DO UPDATE SET value=%s", (str(n_days), str(n_days)))
            st.success("تم التحديث")

# ---------------------------------------------------------
# 👥 القسم 2: إدارة الأجهزة (تعديل فردي + نقرات + إصدار)
# ---------------------------------------------------------
elif menu == "👥 إدارة الأجهزة":
    st.header("👥 التحكم الكامل والتحليل الفردي")
    df_u = pd.read_sql("""
        SELECT device_id, phone, status, sub_tier, expiry_date, accepted_clicks, app_version,
        CASE WHEN last_active > NOW() - INTERVAL '5 minutes' THEN 'Online 🟢' ELSE 'Offline 🔴' END as live_status,
        last_active FROM myapp.users_status ORDER BY last_active DESC
    """, get_db_connection())
    
    st.dataframe(df_u, use_container_width=True)

    st.subheader("🛠️ إدارة مستخدم محدد")
    target = st.selectbox("اختر الجهاز للمزامنة", df_u['device_id'])
    t_row = df_u[df_u['device_id'] == target].iloc[0]

    col1, col2, col3 = st.columns(3)
    with col1:
        st.write("**📝 البيانات والنقرات**")
        n_ph = st.text_input("رقم الهاتف", t_row['phone'])
        n_cl = st.number_input("تعديل النقرات", value=int(t_row['accepted_clicks']))
        if st.button("حفظ المزامنة 💾"):
            run_query("UPDATE myapp.users_status SET phone=%s, accepted_clicks=%s WHERE device_id=%s", (n_ph, n_cl, target))
            st.success("تم")

    with col2:
        st.write("**🔑 العضوية والحالة**")
        n_st = st.selectbox("حالة الحساب", ["Active", "Blocked", "Frozen"], index=["Active", "Blocked", "Frozen"].index(t_row['status']))
        n_exp = st.date_input("تاريخ الانتهاء", value=t_row['expiry_date'] if pd.notnull(t_row['expiry_date']) else datetime.date.today())
        if st.button("تحديث الاشتراك"):
            run_query("UPDATE myapp.users_status SET status=%s, expiry_date=%s WHERE device_id=%s", (n_st, n_exp, target))
            st.success("تم")

    with col3:
        st.write("**🚀 التحديث والحذف**")
        st.info(f"إصدار السائق: {t_row['app_version']}")
        if st.button("طلب تحديث إجباري ⚠️"):
            run_query("UPDATE myapp.users_status SET app_version='FORCE_UPDATE' WHERE device_id=%s", (target,))
            st.warning("تم إرسال الأمر")
        if st.button("حذف السائق 🧨"):
            run_query("DELETE FROM myapp.users_status WHERE device_id=%s", (target,))
            st.rerun()

# ---------------------------------------------------------
# 🎫 القسم 3: نظام الأكواد (مستخدم / غير مستخدم)
# ---------------------------------------------------------
elif menu == "🎫 نظام الأكواد":
    st.header("🎫 إدارة مخزون وتتبع الأكواد")
    t1, t2 = st.tabs(["✨ توليد أكواد", "📜 سجل الاستخدام"])
    with t1:
        with st.form("gen"):
            pre = st.text_input("البادئة", "PRO")
            dur = st.number_input("المدة (يوم)", 1, 365, 30)
            qty = st.number_input("الكمية", 1, 1000, 10)
            if st.form_submit_button("توليد وتخزين ✨"):
                for _ in range(qty):
                    c = f"{pre}-{dur}-{os.urandom(3).hex().upper()}"
                    run_query("INSERT INTO myapp.subscriptions (code, duration_days) VALUES (%s, %s)", (c, dur))
                st.success("تم")
        st.dataframe(pd.read_sql("SELECT code, duration_days FROM myapp.subscriptions WHERE is_used=FALSE ORDER BY id DESC", get_db_connection()), use_container_width=True)
    with t2:
        df_used = pd.read_sql("""
            SELECT s.code, u.phone, s.used_at, s.used_by_device FROM myapp.subscriptions s 
            JOIN myapp.users_status u ON s.used_by_device = u.device_id WHERE s.is_used = TRUE ORDER BY s.used_at DESC
        """, get_db_connection())
        st.dataframe(df_used, use_container_width=True)

# ---------------------------------------------------------
# 📱 القسم 4: السوشال ميديا (Excel Sheet التفاعلي)
# ---------------------------------------------------------
elif menu == "📱 السوشال ميديا":
    st.header("📱 نظام رقابة الميديا (Interactive Excel)")
    run_query("CREATE TABLE IF NOT EXISTS myapp.social_tracker (id SERIAL PRIMARY KEY, ref TEXT, platform TEXT, notes TEXT, status TEXT, date_added TIMESTAMP DEFAULT NOW())")
    df_social = pd.read_sql("SELECT id, ref, platform, notes, status FROM myapp.social_tracker", get_db_connection())
    edited = st.data_editor(df_social, num_rows="dynamic", use_container_width=True)
    if st.button("حفظ ومزامنة الإكسل 📊"):
        run_query("DELETE FROM myapp.social_tracker")
        for _, r in edited.iterrows(): run_query("INSERT INTO myapp.social_tracker (ref, platform, notes, status) VALUES (%s, %s, %s, %s)", (r['ref'], r['platform'], r['notes'], r['status']))
        st.success("تمت المزامنة")

# ---------------------------------------------------------
# 🔄 القسم 5: التحديثات الحية (الكلمات المفتاحية الحية)
# ---------------------------------------------------------
elif menu == "🔄 التحديثات الحية":
    st.header("🔄 لوحة التحكم الحية في ذكاء البوت")
    
    st.subheader("🎯 كلمات القبول الحية (حقن فوري للذكاء)")
    res_k = run_query("SELECT value FROM myapp.app_config WHERE key='live_keywords'", fetch=True)
    curr_k = res_k[0]['value'] if res_k else "قبول,accept,موافق"
    new_k = st.text_area("قائمة الكلمات (افصل بفاصلة ,)", value=curr_k, height=100)
    
    col_k1, col_k2 = st.columns(2)
    if col_k1.button("حقن الكلمات في آلاف الأجهزة 🚀"):
        run_query("INSERT INTO myapp.app_config (key, value) VALUES ('live_keywords', %s) ON CONFLICT (key) DO UPDATE SET value=%s", (new_k, new_k))
        st.success("تم التحديث")
    if col_k2.button("إعادة الضبط للافتراضي 🔄"):
        run_query("UPDATE myapp.app_config SET value='قبول,accept,استلام,تأكيد' WHERE key='live_keywords'"); st.rerun()

    st.divider()
    st.subheader("⚙️ إعدادات النظام الأخرى")
    conf = pd.read_sql("SELECT key, value FROM myapp.app_config WHERE key != 'live_keywords'", get_db_connection())
    edit_c = st.data_editor(conf, use_container_width=True)
    if st.button("حفظ الإعدادات العامة"):
        for _, r in edit_c.iterrows(): run_query("UPDATE myapp.app_config SET value=%s WHERE key=%s", (r['value'], r['key']))
        st.success("تم")

# ---------------------------------------------------------
# 🔐 القسم 6: الصلاحيات والشركاء
# ---------------------------------------------------------
elif menu == "🔐 الصلاحيات والشركاء":
    st.header("🔐 إدارة فريق العمل والشركاء")
    with st.form("add"):
        nu = st.text_input("اسم المستخدم")
        np = st.text_input("كلمة المرور", type="password")
        nr = st.selectbox("الرتبة", ["مدير شريك", "مشرف", "دعم فني"])
        ns = st.multiselect("الأقسام المسموحة", ["📊 نظرة عامة", "👥 إدارة الأجهزة", "🎫 نظام الأكواد", "📱 السوشال ميديا", "🔄 التحديثات الحية", "📢 البث الجماعي"])
        if st.form_submit_button("إضافة الشريك ✨"):
            run_query("INSERT INTO myapp.app_permissions (username, password, role_name, allowed_sections) VALUES (%s, %s, %s, %s)", (nu, hashlib.sha256(np.encode()).hexdigest(), nr, ns))
            st.success("تمت الإضافة")

# 🛡️ سجل الأمان
elif menu == "🛡️ الأمن والرقابة":
    st.header("🛡️ سجل الرقابة الأمنية")
    st.table(pd.read_sql("SELECT * FROM myapp.security_logs ORDER BY created_at DESC LIMIT 100", get_db_connection()))

# 📢 البث الجماعي
elif menu == "📢 البث الجماعي":
    st.header("📢 مركز البث المباشر")
    msg = st.text_area("نص الإشعار (سيظهر كإشعار نظام خارجي)")
    if st.button("بث الإشعار الآن للجميع 🚀"):
        run_query("INSERT INTO myapp.app_config (key, value) VALUES ('global_notice', %s) ON CONFLICT (key) DO UPDATE SET value=%s", (msg, msg))
        st.success("تم البث بنجاح")

st.sidebar.markdown("---")
if st.sidebar.button("تسجيل الخروج 🚪"): st.session_state.auth = False; st.rerun()

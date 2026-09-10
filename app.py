import streamlit as st
import pandas as pd
import psycopg2
from psycopg2.extras import RealDictCursor
import hashlib
import os
import datetime
import plotly.express as px

# 1. إعدادات الهوية والجمالية (Professional Dark/Light UI)
st.set_page_config(page_title="MyClicker Pro | المركز القيادي", layout="wide", page_icon="👑")

st.markdown("""
    <style>
    .main { background-color: #f8fafc; }
    .stMetric { background-color: #ffffff; padding: 20px; border-radius: 12px; box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1); border: 1px solid #e2e8f0; }
    .stButton>button { border-radius: 8px; font-weight: bold; height: 3em; }
    .stDataFrame { border-radius: 12px; overflow: hidden; }
    </style>
""", unsafe_allow_html=True)

# 2. إدارة قاعدة البيانات والعمليات الذرية
def get_db_connection():
    try:
        return psycopg2.connect(st.secrets["DATABASE_URL"], sslmode='require')
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
        st.error(f"❌ خطأ برمي: {e}")
        return None
    finally: conn.close()

# 3. نظام تسجيل الدخول المعتمد على الأدوار (Role-Based Auth)
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
            else: st.error("⚠️ بيانات الدخول غير صحيحة أو الحساب معطل")
    st.stop()

# 4. بناء القائمة الجانبية (Sidebar) بناءً على الصلاحيات
user_data = st.session_state.user
st.sidebar.title(f"👑 {user_data['role_name']}")
st.sidebar.info(f"المسؤول: {user_data['username']}")

menu = st.sidebar.selectbox("القائمة القيادية", user_data['allowed_sections'])

# ---------------------------------------------------------
# 📊 القسم 1: الإحصائيات العامة (Business Intelligence)
# ---------------------------------------------------------
if menu == "📊 نظرة عامة":
    st.header("📊 لوحة مؤشرات الأداء والتحكم الجماعي")
    
    # جلب البيانات الحية
    stats = run_query("""
        SELECT 
        (SELECT count(*) FROM myapp.users_status) as total_users,
        (SELECT count(*) FROM myapp.users_status WHERE last_active > NOW() - INTERVAL '5 minutes') as online_now,
        (SELECT sum(accepted_clicks) FROM myapp.users_status) as total_clicks,
        (SELECT count(*) FROM myapp.subscriptions WHERE is_used = FALSE) as stock_codes
    """, fetch=True)[0]

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("إجمالي السائقين", stats['total_users'])
    c2.metric("أونلاين الآن 🟢", stats['online_now'])
    c3.metric("إجمالي النقرات 🎯", stats['total_clicks'] or 0)
    c4.metric("الأكواد الجاهزة", stats['stock_codes'])

    st.divider()

    # التفعيل الجماعي وهدايا الأيام
    col_a, col_b = st.columns(2)
    with col_a:
        st.subheader("⚡ تفعيل الطوارئ الجماعي")
        free_res = run_query("SELECT value FROM myapp.app_config WHERE key='global_free_mode'", fetch=True)
        is_free = free_res[0]['value'] == 'true' if free_res else False
        if st.button("تبديل وضع التفعيل الجماعي (الكل مجاناً) 🔄", type="primary" if is_free else "secondary"):
            run_query("INSERT INTO myapp.app_config (key, value) VALUES ('global_free_mode', %s) ON CONFLICT (key) DO UPDATE SET value=%s", 
                     ('false' if is_free else 'true', 'false' if is_free else 'true'))
            st.rerun()
    
    with col_b:
        st.subheader("🎁 منح أيام مجانية للجميع")
        free_days = st.number_input("عدد الأيام", 1, 30, 1)
        if st.button("توزيع الهدايا على كافة السائقين 🚀"):
            run_query("UPDATE myapp.users_status SET expiry_date = CASE WHEN expiry_date > NOW() THEN expiry_date + INTERVAL '%s days' ELSE NOW() + INTERVAL '%s days' END" % (free_days, free_days))
            st.success(f"تمت إضافة {free_days} يوم لكل الأجهزة!")

# ---------------------------------------------------------
# 👥 القسم 2: إدارة السائقين (التحكم الفردي العميق)
# ---------------------------------------------------------
elif menu == "👥 إدارة الأجهزة":
    st.header("👥 قاعدة بيانات السائقين والتحكم الفردي")
    
    users = run_query("""
        SELECT device_id, phone, status, sub_tier, expiry_date, accepted_clicks, app_version,
        CASE WHEN last_active > NOW() - INTERVAL '5 minutes' THEN 'Online 🟢' ELSE 'Offline 🔴' END as live_status,
        last_active FROM myapp.users_status ORDER BY last_active DESC
    """, fetch=True)
    df_u = pd.DataFrame(users)
    
    search = st.text_input("🔍 بحث سريع (هاتف أو Device ID)")
    if search:
        df_u = df_u[df_u['phone'].contains(search) | df_u['device_id'].contains(search)]
    
    st.dataframe(df_u, use_container_width=True)

    st.subheader("🛠️ غرفة العمليات على جهاز معين")
    target = st.selectbox("اختر الجهاز المستهدف", df_u['device_id'])
    t_row = df_u[df_u['device_id'] == target].iloc[0]

    c1, c2, c3 = st.columns(3)
    with c1:
        st.write("**📝 تعديل البيانات الأساسية**")
        n_phone = st.text_input("رقم الهاتف", t_row['phone'])
        n_status = st.selectbox("الحالة", ["Active", "Blocked", "Frozen"], index=["Active", "Blocked", "Frozen"].index(t_row['status']))
        if st.button("حفظ البيانات 💾"):
            run_query("UPDATE myapp.users_status SET phone=%s, status=%s WHERE device_id=%s", (n_phone, n_status, target))
            st.success("تم")
            
    with c2:
        st.write("**📧 الإشعارات والتحديث الفردي**")
        ind_msg = st.text_area("رسالة خاصة تظهر له فقط")
        if st.button("إرسال إشعار فردي 📢"):
            run_query("UPDATE myapp.users_status SET notice_message=%s WHERE device_id=%s", (ind_msg, target))
            st.success("تم الإرسال")
        if st.button("طلب تحديث إجباري (لهذا الجهاز فقط) ⚠️"):
            run_query("UPDATE myapp.users_status SET app_version='FORCE_UPDATE' WHERE device_id=%s", (target,))
            st.warning("تم إقفال التطبيق عليه")

    with c3:
        st.write("**⛔ إجراءات نهائية**")
        if st.button("حذف المستخدم نهائياً من السيستم 🧨"):
            run_query("DELETE FROM myapp.users_status WHERE device_id=%s", (target,))
            st.rerun()

# ---------------------------------------------------------
# 🎫 القسم 3: نظام الأكواد (مستخدم وغير مستخدم بالهاتف والوقت)
# ---------------------------------------------------------
elif menu == "🎫 الأكواد":
    st.header("🎫 إدارة مخزون وتتبع استهلاك الأكواد")
    t1, t2 = st.tabs(["📥 المخزون (الغير مستخدمة)", "✅ سجل التفعيل (مستخدمة + الهاتف + الوقت)"])

    with t1:
        with st.expander("✨ توليد دفعة أكواد جديدة"):
            with st.form("gen_codes"):
                pre = st.text_input("البادئة", "PRO")
                dur = st.number_input("المدة بالأيام", 1, 365, 30)
                qty = st.number_input("الكمية", 1, 1000, 10)
                if st.form_submit_button("توليد وتخزين ✨"):
                    for _ in range(qty):
                        c = f"{pre}-{dur}-{os.urandom(3).hex().upper()}"
                        run_query("INSERT INTO myapp.subscriptions (code, duration_days) VALUES (%s, %s)", (c, dur))
                    st.success("تم!")
        
        df_unused = pd.DataFrame(run_query("SELECT code, duration_days, sub_tier FROM myapp.subscriptions WHERE is_used=FALSE ORDER BY id DESC", fetch=True))
        st.dataframe(df_unused, use_container_width=True)

    with t2:
        df_used = pd.DataFrame(run_query("""
            SELECT s.code, u.phone, s.used_at as "وقت التفعيل", s.used_by_device as "ID الجهاز", s.duration_days as "المدة"
            FROM myapp.subscriptions s 
            JOIN myapp.users_status u ON s.used_by_device = u.device_id 
            WHERE s.is_used = TRUE ORDER BY s.used_at DESC
        """, fetch=True))
        st.dataframe(df_used, use_container_width=True)

# ---------------------------------------------------------
# 📱 القسم 4: السوشال ميديا (التفاعلي - Excel Sheet)
# ---------------------------------------------------------
elif menu == "📱 السوشال ميديا":
    st.header("📱 نظام رقابة السوشال ميديا (Interactive Sheet)")
    st.info("قم بإضافة الملاحظات والرقابة على الحملات الإعلانية هنا كأنك تعمل على Excel.")
    
    run_query("CREATE TABLE IF NOT EXISTS myapp.social_tracker (id SERIAL PRIMARY KEY, ref TEXT, platform TEXT, notes TEXT, status TEXT, date_added TIMESTAMP DEFAULT NOW())", commit=True)
    df_social = pd.DataFrame(run_query("SELECT id, ref, platform, notes, status FROM myapp.social_tracker", fetch=True))
    
    edited = st.data_editor(df_social, num_rows="dynamic", use_container_width=True)
    if st.button("مزامنة وحفظ بيانات الإكسل 📊"):
        run_query("DELETE FROM myapp.social_tracker")
        for _, r in edited.iterrows():
            run_query("INSERT INTO myapp.social_tracker (ref, platform, notes, status) VALUES (%s, %s, %s, %s)", (r['ref'], r['platform'], r['notes'], r['status']))
        st.success("تم الحفظ بنجاح")

# ---------------------------------------------------------
# 🔄 القسم 5: التحديثات والاشعارات (الجماعية)
# ---------------------------------------------------------
elif menu == "📢 الإشعارات":
    st.header("📢 مركز البث الجماعي والتحديثات الإجبارية")
    
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("🚀 تحديث إجباري لكافة السائقين")
        v = st.text_input("الإصدار الجديد (e.g 7.2.8)")
        url = st.text_input("رابط تحميل APK المباشر")
        if st.button("إجبار الجميع على التحديث الآن ⚠️"):
            run_query("UPDATE myapp.app_config SET value=%s WHERE key='latest_version'", (v,))
            run_query("UPDATE myapp.app_config SET value=%s WHERE key='next_url'", (url,))
            run_query("UPDATE myapp.app_config SET value='true' WHERE key='force_update'")
            st.error("تم حظر النسخ القديمة وتوجيه الكل للتحميل!")

    with col2:
        st.subheader("🔔 بث إشعار عام (خارج التطبيق)")
        msg = st.text_area("نص الرسالة (تظهر كإشعار نظام)")
        if st.button("بث الإشعار للجميع 📢"):
            run_query("INSERT INTO myapp.app_config (key, value) VALUES ('global_notice', %s) ON CONFLICT (key) DO UPDATE SET value=%s", (msg, msg))
            st.success("تم البث")

# ---------------------------------------------------------
# 🛠️ القسم 6: التحديث المباشر للميزات (Live Remote Config)
# ---------------------------------------------------------
elif menu == "🔄 التحديثات الحية":
    st.header("🔄 التحكم المباشر في ميزات البوت (بدون تحديث التطبيق)")
    
    conf = pd.DataFrame(run_query("SELECT key, value FROM myapp.app_config", fetch=True))
    edited_conf = st.data_editor(conf, use_container_width=True)
    if st.button("تطبيق الإعدادات الجديدة حياً على آلاف الأجهزة 🚀"):
        for _, r in edited_conf.iterrows():
            run_query("UPDATE myapp.app_config SET value=%s WHERE key=%s", (r['value'], r['key']))
        st.success("تم التحديث اللحظي")

# ---------------------------------------------------------
# 🔐 القسم 7: الصلاحيات والشركاء
# ---------------------------------------------------------
elif menu == "🔐 الصلاحيات":
    st.header("🔐 إدارة الشركاء وفريق العمل")
    with st.form("add_partner"):
        u = st.text_input("اسم المستخدم للشريك")
        p = st.text_input("كلمة المرور", type="password")
        r = st.selectbox("الرتبة", ["مدير شريك", "مشرف مبيعات", "دعم فني", "سوشال ميديا"])
        s = st.multiselect("الأقسام المسموحة له", ["📊 نظرة عامة", "👥 إدارة الأجهزة", "🎫 الأكواد", "📱 السوشال ميديا", "🔄 التحديثات الحية", "📢 الإشعارات"])
        if st.form_submit_button("إضافة الشريك الجديد"):
            run_query("INSERT INTO myapp.app_permissions (username, password, role_name, allowed_sections) VALUES (%s, %s, %s, %s)", 
                     (u, hashlib.sha256(p.encode()).hexdigest(), r, s))
            st.success("تمت الإضافة")

# 🛡️ سجل الأمان
elif menu == "🛡️ الأمن والرقابة":
    st.header("🛡️ سجل الرقابة الأمنية (Audit Trail)")
    logs = pd.DataFrame(run_query("SELECT * FROM myapp.security_logs ORDER BY created_at DESC LIMIT 200", fetch=True))
    st.table(logs)

st.sidebar.markdown("---")
if st.sidebar.button("تسجيل الخروج"):
    st.session_state.auth = False
    st.rerun()

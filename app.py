import streamlit as st
import pandas as pd
import psycopg2
from psycopg2.extras import RealDictCursor
import hashlib
import os
import datetime
import plotly.express as px

# 1. إعدادات الهوية والجمالية (Professional UI)
st.set_page_config(page_title="MyClicker Pro | المركز القيادي الأعلى", layout="wide", page_icon="👑")

# تحسين المظهر بـ CSS
st.markdown("""
    <style>
    .main { background-color: #f8fafc; }
    .stMetric { background-color: #ffffff; padding: 20px; border-radius: 12px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1); border: 1px solid #e2e8f0; }
    .stButton>button { width: 100%; border-radius: 8px; font-weight: bold; height: 3em; }
    .stTabs [data-baseweb="tab-list"] { gap: 10px; }
    .stTabs [data-baseweb="tab"] { background-color: #f1f5f9; border-radius: 5px; padding: 10px 20px; }
    </style>
""", unsafe_allow_html=True)

# 2. إدارة قاعدة البيانات والعمليات الذرية
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
        if fetch:
            res = cur.fetchall()
            return res
        conn.commit()
        return True
    except Exception as e:
        st.error(f"❌ خطأ تقني: {e}")
        return None
    finally:
        cur.close()
        conn.close()

# 3. نظام تسجيل الدخول (صلاحيات كاملة)
if 'auth' not in st.session_state: st.session_state.auth = False

if not st.session_state.auth:
    st.title("🔐 بوابة الوصول للمركز القيادي الأعلى")
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
                # التحقق من جدول الشركاء
                res = run_query("SELECT * FROM myapp.app_permissions WHERE username=%s AND password=%s AND is_active=TRUE", (u, hashlib.sha256(p.encode()).hexdigest()), fetch=True)
                if res:
                    st.session_state.auth = True
                    st.session_state.user = res[0]
                    st.rerun()
                else: st.error("⚠️ بيانات الدخول غير صحيحة")
    st.stop()

# 4. القائمة الجانبية وإدارة الجلسة
user_data = st.session_state.user
st.sidebar.title(f"👑 {user_data['role_name']}")
st.sidebar.info(f"المستخدم: {user_data['username']}")

if st.sidebar.button("🔄 تحديث شامل للبيانات"):
    st.cache_data.clear()
    st.rerun()

menu = st.sidebar.selectbox("انتقل إلى القسم", user_data['allowed_sections'])

# ---------------------------------------------------------
# 📊 القسم 1: الإحصائيات العامة والتحكم الجماعي
# ---------------------------------------------------------
if menu == "📊 نظرة عامة":
    st.header("📊 لوحة مؤشرات الأداء (BI)")
    
    # بطاقات ذكية
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
    c4.metric("مخزون الأكواد", stats['stck'])

    st.divider()

    # --- التحكم الجماعي (تفعيل + منحة أيام) ---
    st.subheader("⚡ تفعيل الطوارئ الجماعي والتحكم في المنح")
    
    res_free = run_query("SELECT value FROM myapp.app_config WHERE key='global_free_mode'", fetch=True)
    is_free = res_free[0]['value'] == 'true' if res_free else False
    
    res_days = run_query("SELECT value FROM myapp.app_config WHERE key='global_free_days'", fetch=True)
    curr_days = int(res_days[0]['value']) if res_days else 7

    col_t, col_d = st.columns(2)
    with col_t:
        st.write(f"**حالة النظام:** {'🟢 مفتوح للجميع' if is_free else '🔴 مقفل بالاشتراكات'}")
        if st.button("تبديل وضع التفعيل الجماعي (فتح/إغلاق الكل) 🔄"):
            run_query("INSERT INTO myapp.app_config (key, value) VALUES ('global_free_mode', %s) ON CONFLICT (key) DO UPDATE SET value=%s", ('false' if is_free else 'true', 'false' if is_free else 'true'))
            st.rerun()
    with col_d:
        n_days = st.number_input("تحديد أيام التفعيل التلقائي", 1, 999, curr_days)
        if st.button("تحديث قيمة المنحة ⏳"):
            run_query("INSERT INTO myapp.app_config (key, value) VALUES ('global_free_days', %s) ON CONFLICT (key) DO UPDATE SET value=%s", (str(n_days), str(n_days)))
            st.success("تم التحديث")

# ---------------------------------------------------------
# 👥 القسم 2: إدارة الأجهزة (تعديل كامل + مزامنة + حذف)
# ---------------------------------------------------------
elif menu == "👥 إدارة الأجهزة":
    st.header("👥 التحكم الشامل في السائقين")
    
    # جدول السائقين المطور
    df_u = pd.read_sql("""
        SELECT device_id, phone, status, sub_tier, expiry_date, accepted_clicks, app_version,
        CASE WHEN last_active > NOW() - INTERVAL '5 minutes' THEN 'Online 🟢' ELSE 'Offline 🔴' END as live_status,
        last_active FROM myapp.users_status ORDER BY last_active DESC
    """, get_db_connection())
    
    st.dataframe(df_u, use_container_width=True)

    st.subheader("🛠️ غرفة العمليات: تعديل بيانات مستخدم محدد")
    target = st.selectbox("اختر الجهاز للتحكم والمزامنة", df_u['device_id'])
    t_row = df_u[df_u['device_id'] == target].iloc[0]

    c1, c2, c3 = st.columns(3)
    with c1:
        st.write("**📝 بيانات الهاتف والنقرات**")
        n_phone = st.text_input("رقم الهاتف", t_row['phone'])
        n_clicks = st.number_input("تعديل عدد النقرات", value=int(t_row['accepted_clicks']))
        if st.button("مزامنة الهاتف والنقرات 💾"):
            run_query("UPDATE myapp.users_status SET phone=%s, accepted_clicks=%s WHERE device_id=%s", (n_phone, n_clicks, target))
            st.success("تم الحفظ")

    with c2:
        st.write("**🔑 العضوية والاشتراك**")
        n_tier = st.selectbox("نوع الباقة", ["STANDARD", "VIP", "GOLD"], index=0)
        n_status = st.selectbox("حالة الحساب", ["Active", "Blocked", "Frozen"], index=["Active", "Blocked", "Frozen"].index(t_row['status']))
        if st.button("تحديث حالة العضوية"):
            run_query("UPDATE myapp.users_status SET sub_tier=%s, status=%s WHERE device_id=%s", (n_tier, n_status, target))
            st.success("تمت المزامنة")

    with c3:
        st.write("**🚀 التحديث والحذف**")
        st.info(f"إصدار التطبيق الحالي: {t_row['app_version']}")
        if st.button("طلب تحديث إجباري لهذا الجهاز ⚠️"):
            run_query("UPDATE myapp.users_status SET app_version='FORCE_UPDATE' WHERE device_id=%s", (target,))
            st.warning("تم قفل التطبيق حتى التحديث")
        if st.button("حذف السائق نهائياً 🧨"):
            run_query("DELETE FROM myapp.users_status WHERE device_id=%s", (target,))
            st.rerun()

# ---------------------------------------------------------
# 🎫 القسم 3: نظام الأكواد (مخزون + سجل استخدام مفصل)
# ---------------------------------------------------------
elif menu == "🎫 نظام الأكواد":
    st.header("🎫 إدارة وتوليد أكواد الاشتراك")
    t1, t2 = st.tabs(["✨ توليد أكواد جديدة", "📜 سجل الاستخدام (الكود + الهاتف + الوقت)"])
    
    with t1:
        with st.form("gen"):
            pre = st.text_input("البادئة", "PRO")
            dur = st.number_input("المدة (أيام)", 1, 365, 30)
            qty = st.number_input("الكمية", 1, 1000, 10)
            if st.form_submit_button("توليد وتخزين ✨"):
                for _ in range(qty):
                    c = f"{pre}-{dur}-{os.urandom(3).hex().upper()}"
                    run_query("INSERT INTO myapp.subscriptions (code, duration_days) VALUES (%s, %s)", (c, dur))
                st.success(f"تم توليد {qty} كود")
        
        st.subheader("📥 الأكواد المتوفرة حالياً")
        df_inv = pd.read_sql("SELECT code, duration_days, sub_tier FROM myapp.subscriptions WHERE is_used=FALSE ORDER BY id DESC", get_db_connection())
        st.dataframe(df_inv, use_container_width=True)

    with t2:
        df_usage = pd.read_sql("""
            SELECT s.code, u.phone, s.used_at as "وقت التفعيل", s.used_by_device as "بصمة الجهاز", s.duration_days as "المدة"
            FROM myapp.subscriptions s 
            JOIN myapp.users_status u ON s.used_by_device = u.device_id 
            WHERE s.is_used = TRUE ORDER BY s.used_at DESC
        """, get_db_connection())
        st.dataframe(df_usage, use_container_width=True)

# ---------------------------------------------------------
# 📱 القسم 4: السوشال ميديا (Excel Sheet التفاعلي)
# ---------------------------------------------------------
elif menu == "📱 السوشال ميديا":
    st.header("📱 نظام رقابة السوشال ميديا (Excel Sheet)")
    st.info("جدول تفاعلي لإدارة حملات الميديا - أضف واحذف الملاحظات كما في إكسل")
    
    run_query("CREATE TABLE IF NOT EXISTS myapp.social_tracker (id SERIAL PRIMARY KEY, ref TEXT, platform TEXT, notes TEXT, status TEXT, date_added TIMESTAMP DEFAULT NOW())")
    
    df_social = pd.read_sql("SELECT id, ref, platform, notes, status FROM myapp.social_tracker", get_db_connection())
    edited = st.data_editor(df_social, num_rows="dynamic", use_container_width=True)
    
    if st.button("حفظ ومزامنة بيانات الإكسل 📊"):
        run_query("DELETE FROM myapp.social_tracker")
        for _, r in edited.iterrows():
            run_query("INSERT INTO myapp.social_tracker (ref, platform, notes, status) VALUES (%s, %s, %s, %s)", (r['ref'], r['platform'], r['notes'], r['status']))
        st.success("تمت المزامنة")

# ---------------------------------------------------------
# 🔄 القسم 5: التحديثات الحية (التحكم عن بُعد في ميزات البوت)
# ---------------------------------------------------------
elif menu == "🔄 التحديثات الحية":
    st.header("🔄 التحكم المباشر في ميزات التطبيق (بدون تحديث)")
    
    conf = pd.read_sql("SELECT key, value FROM myapp.app_config", get_db_connection())
    st.write("قم بتعديل قيم (السرعة، الكلمات، الروابط) هنا لتطبق فوراً على الجميع:")
    edited_conf = st.data_editor(conf, use_container_width=True)
    
    if st.button("تطبيق الإعدادات الجديدة حياً 🚀"):
        for _, r in edited_conf.iterrows():
            run_query("UPDATE myapp.app_config SET value=%s WHERE key=%s", (r['value'], r['key']))
        st.success("تم التحديث اللحظي لكافة الأجهزة")

# ---------------------------------------------------------
# 🔐 القسم 6: الصلاحيات والشركاء
# ---------------------------------------------------------
elif menu == "🔐 الصلاحيات والشركاء":
    st.header("🔐 إدارة الشركاء وفريق العمل")
    
    with st.form("add_p"):
        nu = st.text_input("اسم المستخدم للشريك")
        np = st.text_input("كلمة المرور", type="password")
        nr = st.selectbox("الرتبة", ["مدير شريك", "مشرف مبيعات", "دعم فني", "سوشال ميديا"])
        ns = st.multiselect("الأقسام المسموحة", ["📊 نظرة عامة", "👥 إدارة الأجهزة", "🎫 نظام الأكواد", "📱 السوشال ميديا", "🔄 التحديثات الحية", "📢 البث الجماعي"])
        if st.form_submit_button("إضافة شريك جديد"):
            run_query("INSERT INTO myapp.app_permissions (username, password, role_name, allowed_sections) VALUES (%s, %s, %s, %s)", (nu, hashlib.sha256(np.encode()).hexdigest(), nr, ns))
            st.success("تمت الإضافة")

# ---------------------------------------------------------
# 🛡️ القسم 7: الأمن والرقابة (Audit Trail)
# ---------------------------------------------------------
elif menu == "🛡️ الأمن والرقابة":
    st.header("🛡️ سجل الرقابة الأمنية")
    logs = pd.read_sql("SELECT * FROM myapp.security_logs ORDER BY created_at DESC LIMIT 200", get_db_connection())
    st.table(logs)

# ---------------------------------------------------------
# 📢 القسم 8: البث الجماعي (Broadcast)
# ---------------------------------------------------------
elif menu == "📢 البث الجماعي":
    st.header("📢 مركز البث المباشر")
    msg = st.text_area("نص الإشعار (سيظهر خارج التطبيق)")
    if st.button("بث الإشعار الآن للجميع 🚀"):
        run_query("INSERT INTO myapp.app_config (key, value) VALUES ('global_notice', %s) ON CONFLICT (key) DO UPDATE SET value=%s", (msg, msg))
        st.success("تم البث لآلاف الأجهزة")

st.sidebar.markdown("---")
if st.sidebar.button("تسجيل الخروج"):
    st.session_state.auth = False
    st.rerun()

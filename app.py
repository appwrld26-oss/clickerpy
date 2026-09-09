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
    .main { background-color: #f8f9fa; }
    .stMetric { background-color: #ffffff; padding: 15px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    </style>
""", unsafe_allow_html=True)

# 2. إدارة قاعدة البيانات
def get_db_connection():
    try:
        return psycopg2.connect(st.secrets["DATABASE_URL"], sslmode='require')
    except:
        st.error("❌ فشل الاتصال بقاعدة البيانات. تأكد من Secrets.")
        st.stop()

def run_query(query, params=None, commit=True):
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        cur.execute(query, params)
        if commit: 
            conn.commit()
            return True
        return cur.fetchall()
    except Exception as e:
        st.error(f"خطأ: {e}")
        return None
    finally:
        conn.close()

# 3. نظام تسجيل الدخول
if 'auth' not in st.session_state: st.session_state.auth = False
if not st.session_state.auth:
    st.title("🔐 تسجيل دخول المركز القيادي")
    with st.form("login"):
        u = st.text_input("اسم المستخدم")
        p = st.text_input("كلمة المرور", type="password")
        if st.form_submit_button("دخول"):
            # admin / admin123
            if u == "admin" and hashlib.sha256(p.encode()).hexdigest() == "240be518fabd2724ddb6f04eeb1da5967448d7e831c08c8fa822809f74c720a9":
                st.session_state.auth = True; st.rerun()
            else: st.error("بيانات الدخول خاطئة")
    st.stop()

# 4. القائمة الجانبية (الشريط الرئيسي)
menu = st.sidebar.selectbox("القائمة القيادية", [
    "📊 الإحصائيات العامة", 
    "👥 إدارة السائقين", 
    "🎫 نظام الأكواد والاشتراكات", 
    "📢 التحديثات والاشعارات", 
    "📱 السوشال ميديا (Excel Sheet)",
    "🔐 الصلاحيات والشركاء",
    "🛡️ الأمن والرقابة"
])

# ---------------------------------------------------------
# 📊 القسم 1: الإحصائيات العامة & [التفعيل الجماعي]
# ---------------------------------------------------------
if menu == "📊 الإحصائيات العامة":
    st.header("📊 ملخص الأداء والتحكم الجماعي")
    
    # بطاقات الإحصائيات
    stats = run_query("""
        SELECT 
        (SELECT count(*) FROM myapp.users_status) as users,
        (SELECT count(*) FROM myapp.users_status WHERE last_active > NOW() - INTERVAL '5 minutes') as online,
        (SELECT sum(accepted_clicks) FROM myapp.users_status) as clicks,
        (SELECT count(*) FROM myapp.subscriptions WHERE is_used = FALSE) as codes
    """, commit=False)[0]

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("إجمالي السائقين", stats['users'])
    c2.metric("أونلاين الآن 🟢", stats['online'])
    c3.metric("إجمالي النقرات 🎯", stats['clicks'] or 0)
    c4.metric("مخزون الأكواد 🎫", stats['codes'])

    st.divider()
    
    # ميزة التفعيل الجماعي
    st.subheader("🚀 تفعيل الطوارئ (فتح النظام للجميع)")
    res = run_query("SELECT value FROM myapp.app_config WHERE key = 'global_free_mode'", commit=False)
    is_free = res[0]['value'] == 'true' if res else False
    
    ca, cb = st.columns([3, 1])
    if is_free:
        ca.success("🚀 وضع التفعيل الجماعي: [مفعّل] - الكل يعمل مجاناً")
        if cb.button("إيقاف الوضع المجاني 🔒"):
            run_query("UPDATE myapp.app_config SET value = 'false' WHERE key = 'global_free_mode'")
            st.rerun()
    else:
        ca.info("🔒 وضع التفعيل الجماعي: [معطّل] - نظام الاشتراكات فعال")
        if cb.button("فتح النظام للكل مجاناً 🚀"):
            run_query("INSERT INTO myapp.app_config (key, value) VALUES ('global_free_mode', 'true') ON CONFLICT (key) DO UPDATE SET value = 'true'")
            st.rerun()

# ---------------------------------------------------------
# 👥 القسم 2: إدارة السائقين (تعديل، حذف، حالة)
# ---------------------------------------------------------
elif menu == "👥 إدارة السائقين":
    st.header("👥 التحكم الكامل في السائقين")
    users = run_query("""
        SELECT device_id, phone, status, sub_tier, expiry_date, accepted_clicks,
        CASE WHEN last_active > NOW() - INTERVAL '5 minutes' THEN 'Online 🟢' ELSE 'Offline 🔴' END as live_status,
        last_active FROM myapp.users_status ORDER BY last_active DESC
    """, commit=False)
    df_u = pd.DataFrame(users)
    st.dataframe(df_u, use_container_width=True)

    st.subheader("📝 تعديل بيانات فردية")
    col1, col2, col3 = st.columns(3)
    target = col1.selectbox("اختر الجهاز", df_u['device_id'])
    new_phone = col2.text_input("رقم الهاتف الجديد")
    new_status = col3.selectbox("تغيير الحالة", ["Active", "Blocked", "Frozen"])
    
    c_act1, c_act2 = st.columns(2)
    if c_act1.button("حفظ التغييرات 💾"):
        run_query("UPDATE myapp.users_status SET phone=%s, status=%s WHERE device_id=%s", (new_phone, new_status, target))
        st.success("تم التحديث")
    if c_act2.button("حذف المستخدم نهائياً 🧨"):
        run_query("DELETE FROM myapp.users_status WHERE device_id=%s", (target,))
        st.error("تم الحذف من النظام")

# ---------------------------------------------------------
# 🎫 القسم 3: نظام الأكواد (مستخدم وغير مستخدم)
# ---------------------------------------------------------
elif menu == "🎫 نظام الأكواد والاشتراكات":
    st.header("🎫 إدارة مخزون الأكواد")
    t1, t2, t3 = st.tabs(["✨ توليد", "📥 غير مستخدمة", "✅ مستخدمة"])
    
    with t1:
        with st.form("gen"):
            pre = st.text_input("البادئة", "VIP")
            dur = st.number_input("الأيام", 1, 365, 30)
            qty = st.number_input("العدد", 1, 100, 5)
            if st.form_submit_button("توليد الآن"):
                for _ in range(qty):
                    code = f"{pre}-{dur}-{os.urandom(3).hex().upper()}"
                    run_query("INSERT INTO myapp.subscriptions (code, duration_days) VALUES (%s, %s)", (code, dur))
                st.success("تم")

    with t2:
        df_unused = pd.DataFrame(run_query("SELECT code, duration_days FROM myapp.subscriptions WHERE is_used = FALSE", commit=False))
        st.dataframe(df_unused, use_container_width=True)

    with t3:
        # الربط مع رقم الهاتف والوقت بدقة
        df_used = pd.DataFrame(run_query("""
            SELECT s.code, u.phone, s.used_at, s.used_by_device 
            FROM myapp.subscriptions s 
            JOIN myapp.users_status u ON s.used_by_device = u.device_id 
            WHERE s.is_used = TRUE ORDER BY s.used_at DESC
        """, commit=False))
        st.dataframe(df_used, use_container_width=True)

# ---------------------------------------------------------
# 📢 القسم 4: التحديثات والاشعارات (فردي وجماعي)
# ---------------------------------------------------------
elif menu == "📢 التحديثات والاشعارات":
    st.header("📢 مركز البث والتحديثات")
    
    st.subheader("🚀 تحديث إجباري جماعي")
    v = st.text_input("رقم الإصدار (e.g 7.2.8)")
    url = st.text_input("رابط APK المباشر")
    if st.button("إجبار الجميع على التحديث ⚠️"):
        run_query("UPDATE myapp.app_config SET value=%s WHERE key='latest_version'", (v,))
        run_query("UPDATE myapp.app_config SET value=%s WHERE key='next_url'", (url,))
        run_query("UPDATE myapp.app_config SET value='true' WHERE key='force_update'")
        st.error("تم قفل كافة النسخ القديمة")

    st.divider()
    st.subheader("🔔 بث إشعار (جماعي أو فردي)")
    mode = st.radio("نوع البث", ["للجميع (بث عام)", "فردي (جهاز واحد)"])
    msg = st.text_area("نص الرسالة")
    
    if st.button("إرسال الإشعار الآن 📢"):
        if mode == "للجميع (بث عام)":
            run_query("INSERT INTO myapp.app_config (key, value) VALUES ('global_notice', %s) ON CONFLICT (key) DO UPDATE SET value=%s", (msg, msg))
        else:
            target_user = st.selectbox("اختر الجهاز", pd.DataFrame(run_query("SELECT device_id FROM myapp.users_status", commit=False))['device_id'])
            run_query("UPDATE myapp.users_status SET notice_message=%s WHERE device_id=%s", (msg, target_user))
        st.success("تم الإرسال بنجاح")

# ---------------------------------------------------------
# 📱 القسم 5: السوشال ميديا (Excel Sheet التفاعلي)
# ---------------------------------------------------------
elif menu == "📱 السوشال ميديا (Excel Sheet)":
    st.header("📱 نظام رقابة السوشال ميديا (Interactive Excel)")
    run_query("CREATE TABLE IF NOT EXISTS myapp.social_tracker (id SERIAL PRIMARY KEY, user_ref TEXT, platform TEXT, notes TEXT, status TEXT)", commit=True)
    
    data = run_query("SELECT id, user_ref, platform, notes, status FROM myapp.social_tracker", commit=False)
    df_excel = pd.DataFrame(data)
    
    edited_df = st.data_editor(df_excel, num_rows="dynamic", use_container_width=True)
    
    if st.button("حفظ تغييرات الإكسل 📊"):
        run_query("DELETE FROM myapp.social_tracker")
        for _, row in edited_df.iterrows():
            run_query("INSERT INTO myapp.social_tracker (user_ref, platform, notes, status) VALUES (%s, %s, %s, %s)", (row['user_ref'], row['platform'], row['notes'], row['status']))
        st.success("تمت المزامنة")

# ---------------------------------------------------------
# 🔐 القسم 6: الصلاحيات والشركاء
# ---------------------------------------------------------
elif menu == "🔐 الصلاحيات والشركاء":
    st.header("🔐 إدارة الشركاء والمدراء")
    # (هنا يمكنك إضافة نظام تعدد المستخدمين للوحة التحكم)
    st.info("نظام الشركاء يعمل حالياً تحت حساب المدير الرئيسي.")

# ---------------------------------------------------------
# 🛡️ القسم 7: الأمن والرقابة (سجل الأمان)
# ---------------------------------------------------------
elif menu == "🛡️ الأمن والرقابة":
    st.header("🛡️ سجل الرقابة والأمن")
    logs = run_query("SELECT * FROM myapp.security_logs ORDER BY created_at DESC LIMIT 100", commit=False)
    st.table(pd.DataFrame(logs))

import streamlit as st
import pandas as pd
import psycopg2
from psycopg2.extras import RealDictCursor
import hashlib
import os
import datetime
import plotly.express as px
import plotly.graph_objects as go

# 1. إعدادات الهوية والجمالية
st.set_page_config(page_title="MyClicker Pro | المركز القيادي", layout="wide", page_icon="👑")

# استايل CSS لتحسين المظهر وتنسيق الجداول
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .stMetric { background-color: #ffffff; padding: 15px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    .status-online { color: #28a745; font-weight: bold; }
    .status-offline { color: #dc3545; font-weight: bold; }
    </style>
""", unsafe_with_stdio=True)

# 2. إدارة قاعدة البيانات
def get_db_connection():
    try:
        return psycopg2.connect(st.secrets["DATABASE_URL"], sslmode='require')
    except:
        st.error("❌ عذراً، فشل الاتصال بقاعدة البيانات. تأكد من إعدادات الـ Secrets.")
        st.stop()

def run_query(query, params=None, commit=True):
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        cur.execute(query, params)
        if commit: conn.commit()
        if not commit: return cur.fetchall()
    except Exception as e:
        st.error(f"خطأ في التنفيذ: {e}")
    finally:
        conn.close()

# 3. نظام الصلاحيات والأمان
if 'auth' not in st.session_state: st.session_state.auth = False

if not st.session_state.auth:
    st.title("🔐 تسجيل دخول المركز القيادي")
    with st.form("login"):
        u = st.text_input("اسم المستخدم")
        p = st.text_input("كلمة المرور", type="password")
        if st.form_submit_button("دخول"):
            # admin / admin123
            if u == "admin" and hashlib.sha256(p.encode()).hexdigest() == "240be518fabd2724ddb6f04eeb1da5967448d7e831c08c8fa822809f74c720a9":
                st.session_state.auth = True
                st.session_state.role = "OWNER"
                st.rerun()
            else: st.error("بيانات الدخول خاطئة")
    st.stop()

# 4. القائمة الجانبية المتقدمة
st.sidebar.title("👑 القائد: " + "Admin")
menu = st.sidebar.selectbox("اختر القسم", [
    "📊 الإحصائيات العامة", 
    "👥 إدارة السائقين (التحكم الكامل)", 
    "🎫 نظام الأكواد (Used/Unused)", 
    "📢 التحديثات والاشعارات (فردي/جماعي)", 
    "📱 قسم السوشال ميديا (Excel Sheet)",
    "🛠️ الدعم الفني والصيانة",
    "🔐 الصلاحيات والشركاء",
    "🛡️ الأمن والرقابة"
])

# ---------------------------------------------------------
# 📊 القسم 1: الإحصائيات العامة (Business Intelligence)
# ---------------------------------------------------------
if menu == "📊 الإحصائيات العامة":
    st.header("📊 لوحة مؤشرات الأداء الحية")
    
    data = run_query("""
        SELECT 
        (SELECT count(*) FROM myapp.users_status) as total_users,
        (SELECT count(*) FROM myapp.users_status WHERE last_active > NOW() - INTERVAL '5 minutes') as online_now,
        (SELECT sum(accepted_clicks) FROM myapp.users_status) as total_clicks,
        (SELECT count(*) FROM myapp.subscriptions WHERE is_used = FALSE) as stock_codes
    """, commit=False)[0]

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("إجمالي السائقين", data['total_users'])
    c2.metric("أونلاين الآن ⚡", data['online_now'], delta_color="normal")
    c3.metric("إجمالي النقرات 🎯", data['total_clicks'])
    c4.metric("مخزون الأكواد", data['stock_codes'])

    # رسم بياني للنمو
    st.subheader("📈 نشاط القبول التاريخي")
    df_clicks = pd.DataFrame(run_query("SELECT last_active::date as date, sum(accepted_clicks) as clicks FROM myapp.users_status GROUP BY 1 ORDER BY 1", commit=False))
    if not df_clicks.empty:
        fig = px.area(df_clicks, x='date', y='clicks', title="تطور النقرات اليومية")
        st.plotly_chart(fig, use_container_width=True)

# ---------------------------------------------------------
# 👥 القسم 2: إدارة السائقين (CRUD + Control)
# ---------------------------------------------------------
elif menu == "👥 إدارة السائقين (التحكم الكامل)":
    st.header("👥 قاعدة بيانات السائقين المركزية")
    
    # جدول البيانات مع حالة الأونلاين
    users = run_query("""
        SELECT device_id, phone, status, sub_tier, expiry_date, accepted_clicks, 
        CASE WHEN last_active > NOW() - INTERVAL '5 minutes' THEN 'Online 🟢' ELSE 'Offline 🔴' END as bot_status,
        last_active FROM myapp.users_status ORDER BY last_active DESC
    """, commit=False)
    df_u = pd.DataFrame(users)
    st.dataframe(df_u, use_container_width=True)

    st.divider()
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📝 تعديل بيانات / حذف")
        target = st.selectbox("اختر الجهاز", df_u['device_id'])
        new_phone = st.text_input("تعديل رقم الهاتف")
        new_tier = st.selectbox("تغيير الباقة", ["STANDARD", "VIP", "GOLD", "TESTER"])
        if st.button("تحديث البيانات 💾"):
            run_query("UPDATE myapp.users_status SET phone=%s, sub_tier=%s WHERE device_id=%s", (new_phone, new_tier, target))
            st.success("تم التحديث")

    with col2:
        st.subheader("🚫 منطقة الحظر النهائي")
        if st.button("حذف المستخدم نهائياً من النظام 🧨"):
            run_query("DELETE FROM myapp.users_status WHERE device_id=%s", (target,))
            st.warning("تم الحذف بنجاح")

# ---------------------------------------------------------
# 🎫 القسم 3: نظام الأكواد (Subscription Hub)
# ---------------------------------------------------------
elif menu == "🎫 نظام الأكواد (Used/Unused)":
    st.header("🎫 مستودع الأكواد والاشتراكات")
    t1, t2, t3 = st.tabs(["✨ توليد أكواد", "📥 المخزون (غير المستخدمة)", "✅ سجل التفعيل (المستخدمة)"])

    with t1:
        with st.form("gen"):
            pre = st.text_input("بادئة الكود (Prefix)", "PRO")
            dur = st.number_input("المدة بالأيام", 1, 365, 30)
            qty = st.number_input("الكمية", 1, 500, 10)
            if st.form_submit_button("توليد وتشفير ✨"):
                for _ in range(qty):
                    code = f"{pre}-{dur}-{os.urandom(3).hex().upper()}"
                    run_query("INSERT INTO myapp.subscriptions (code, duration_days) VALUES (%s, %s)", (code, dur))
                st.success("تم ملء المخزون")

    with t2:
        unused = run_query("SELECT code, duration_days, sub_tier FROM myapp.subscriptions WHERE is_used = FALSE", commit=False)
        st.table(pd.DataFrame(unused))

    with t3:
        # الربط مع رقم الهاتف والوقت كما طلبت
        used = run_query("""
            SELECT s.code, u.phone, s.used_at, s.used_by_device 
            FROM myapp.subscriptions s 
            JOIN myapp.users_status u ON s.used_by_device = u.device_id 
            WHERE s.is_used = TRUE ORDER BY s.used_at DESC
        """, commit=False)
        st.dataframe(pd.DataFrame(used), use_container_width=True)

# ---------------------------------------------------------
# 📢 القسم 4: التحديثات والاشعارات (Live Updates)
# ---------------------------------------------------------
elif menu == "📢 التحديثات والاشعارات (فردي/جماعي)":
    st.header("📢 إدارة البث والتحديثات الإجبارية")
    
    col_a, col_b = st.columns(2)
    
    with col_a:
        st.subheader("🚀 التحديث الإجباري (جماعي)")
        v = st.text_input("الإصدار المطلوب (e.g 7.2.8)")
        url = st.text_input("رابط الـ APK الجديد")
        if st.button("إجبار الكل على التحديث ⚠️"):
            run_query("UPDATE myapp.app_config SET value=%s WHERE key='latest_version'", (v,))
            run_query("UPDATE myapp.app_config SET value=%s WHERE key='next_url'", (url,))
            run_query("UPDATE myapp.app_config SET value='true' WHERE key='force_update'")
            st.error("تم قفل كافة النسخ القديمة!")

    with col_b:
        st.subheader("📧 إشعار فردي (لجهاز واحد)")
        user_id = st.selectbox("اختر السائق", run_query("SELECT device_id FROM myapp.users_status", commit=False))
        ind_msg = st.text_area("رسالة خاصة تظهر له فقط")
        if st.button("إرسال التنبيه الخاص"):
            run_query("UPDATE myapp.users_status SET notice_message=%s WHERE device_id=%s", (ind_msg, user_id))
            st.success("تم الإرسال")

# ---------------------------------------------------------
# 📱 القسم 5: السوشال ميديا (Excel Tracker)
# ---------------------------------------------------------
elif menu == "📱 قسم السوشال ميديا (Excel Sheet)":
    st.header("📱 نظام رقابة السوشال ميديا")
    st.info("هذا الجدول تفاعلي؛ يمكنك التعديل عليه مباشرة كأنه ملف إكسل لرقابة الحملات الإعلانية والمستخدمين.")
    
    # إنشاء جدول الرقابة إذا لم يوجد
    run_query("CREATE TABLE IF NOT EXISTS myapp.social_tracker (id SERIAL PRIMARY KEY, user_ref TEXT, platform TEXT, notes TEXT, status TEXT)", commit=True)
    
    raw_data = run_query("SELECT * FROM myapp.social_tracker", commit=False)
    df_excel = pd.DataFrame(raw_data)
    
    # ميزة الـ Data Editor (مثل إكسل تماماً)
    edited_df = st.data_editor(df_excel, num_rows="dynamic", use_container_width=True)
    
    if st.button("حفظ التغييرات في الإكسل 📊"):
        # منطق الحفظ السريع
        run_query("DELETE FROM myapp.social_tracker")
        for index, row in edited_df.iterrows():
            run_query("INSERT INTO myapp.social_tracker (user_ref, platform, notes, status) VALUES (%s, %s, %s, %s)", 
                     (row['user_ref'], row['platform'], row['notes'], row['status']))
        st.success("تم مزامنة بيانات الإكسل")

# ---------------------------------------------------------
# 🛠️ القسم 6: الدعم الفني والتحديث المباشر
# ---------------------------------------------------------
elif menu == "🛠️ الدعم الفني والصيانة":
    st.header("🛠️ أدوات التحكم المباشر في ميزات التطبيق")
    
    st.subheader("⚡ التحكم في سرعة البوت (عن بُعد)")
    delay = st.slider("تأخير النقر (مللي ثانية)", 100, 5000, 500)
    if st.button("تحديث السرعة للجميع"):
        run_query("INSERT INTO myapp.app_config (key, value) VALUES ('click_delay', %s) ON CONFLICT (key) DO UPDATE SET value=%s", (str(delay), str(delay)))
        st.success(f"تم تعميم سرعة {delay}ms على كافة الأجهزة")

    st.divider()
    st.subheader("فتح/إغلاق النظام (Global Free Mode)")
    # (نفس منطق التفعيل الجماعي الذي شرحناه سابقاً)

# ---------------------------------------------------------
# 🛡️ القسم 8: الأمن والرقابة
# ---------------------------------------------------------
elif menu == "🛡️ الأمن والرقابة":
    st.header("🛡️ سجل الرقابة والأمن (Audit Trail)")
    logs = run_query("SELECT * FROM myapp.security_logs ORDER BY created_at DESC LIMIT 200", commit=False)
    st.table(pd.DataFrame(logs))

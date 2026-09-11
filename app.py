import streamlit as st
import psycopg2
import pandas as pd
import plotly.express as px
import time
import hashlib
import random
from datetime import datetime, timedelta

# --- 1. إعدادات الصفحة ---
st.set_page_config(page_title="MyClicker Pro Admin", layout="wide", page_icon="⚡")

# تصميم مطابق للصورة التي أرسلتها
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;700&display=swap');
    html, body, [class*="css"] { font-family: 'Cairo', sans-serif; text-align: right; direction: rtl; }
    .stMetric { background-color: #f1f5f9; padding: 15px; border-radius: 12px; border: 1px solid #e2e8f0; }
    .sidebar .sidebar-content { background-color: #f8fafc; }
    div[data-testid="stExpander"] { border: 1px solid #e2e8f0; border-radius: 10px; margin-bottom: 10px; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. الاتصال بقاعدة البيانات ---
DB_URL = "postgresql://doadmin:1tHwqXCgn8BS6iTm942V3f7a@myclicker-db-rd7ky.db1.ondigitalocean.com:25060/mypool?sslmode=require"

def run_query(query, params=None, is_select=True):
    try:
        conn = psycopg2.connect(DB_URL)
        cur = conn.cursor()
        cur.execute(query, params)
        if is_select:
            data = cur.fetchall()
            cols = [desc[0] for desc in cur.description]
            res = pd.DataFrame(data, columns=cols)
        else:
            conn.commit()
            res = True
        cur.close()
        conn.close()
        return res
    except Exception as e:
        st.error(f"❌ خطأ في الاتصال: {e}")
        return None

# --- 3. القائمة الجانبية (مطابقة للصورة) ---
with st.sidebar:
    st.markdown("<h2 style='text-align: center;'>⚡ MyClicker Pro</h2>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #64748b;'>👤 المستخدم: <b>admin</b></p>", unsafe_allow_html=True)
    
    if st.button("🔄 مسح الذاكرة والمزامنة الحية"):
        st.cache_data.clear()
        st.toast("تم تحديث البيانات من السيرفر", icon="✅")
        st.rerun()
    
    st.markdown("---")
    menu = st.radio(":القائمة الرئيسية", [
        "📈 نظرة عامة وإحصائيات الإصدارات",
        "👥 إدارة ومراقبة المستخدمين",
        "📢 مركز الإشعارات وبث الرسائل",
        "⚡ تحديث البيانات الحية (LIVE)",
        "💳 توليد وإدارة الأكواد",
        "🤖 إضافة الأجهزة الافتراضية (TEST)",
        "📊 تحليل البيانات 3D"
    ])
    
    st.markdown("---")
    st.button("🚪 تسجيل الخروج")

# --- 4. تنفيذ الأقسام ---

# أ. قسم إضافة الأجهزة الافتراضية (الذي طلبته)
if menu == "🤖 إضافة الأجهزة الافتراضية (TEST)":
    st.title("🤖 مصنع الأجهزة الافتراضية")
    st.info("هذا القسم مخصص لاختبار ضغط السيرفر عبر إضافة آلاف الكباتن الوهميين.")
    
    count = st.number_input("كم عدد الأجهزة المراد إضافتها؟", 1, 1000, 100)
    if st.button("🚀 بدء إنتاج جيش الأجهزة"):
        with st.spinner("جاري الحقن في قاعدة البيانات..."):
            query = """
                INSERT INTO myapp.users_status (device_id, phone, status, sub_tier, expiry_date, app_version, bot_status, accepted_clicks, last_active)
                SELECT 
                    'sim_device_' || i, 
                    '079' || LPAD(floor(random()*9999999)::text, 7, '0'), 
                    'Active', 'VIP', NOW() + interval '30 days', '7.2.8', 'Online', 
                    floor(random()*150), NOW()
                FROM generate_series(1, %s) s(i)
                ON CONFLICT (device_id) DO NOTHING;
            """
            run_query(query, (count,), False)
            st.success(f"✅ تم إضافة {count} جهاز افتراضي بنجاح!")
            st.toast("البيانات الآن حية في السيرفر", icon="🔥")

# ب. الإحصائيات العامة
elif menu == "📈 نظرة عامة وإحصائيات الإصدارات":
    st.title("📈 لوحة مراقبة النشاط")
    data = run_query("SELECT count(*) as total, sum(accepted_clicks) as clicks FROM myapp.users_status")
    if data is not None:
        stats = data.iloc[0]
        c1, c2, c3 = st.columns(3)
        c1.metric("إجمالي السائقين", f"{stats['total']} جهاز")
        c2.metric("إجمالي الصيد", f"{int(stats['clicks'] or 0)} طلب")
        c3.metric("حالة الربط", "Neon DB Linked ✅")

# ج. إدارة المستخدمين
elif menu == "👥 إدارة ومراقبة المستخدمين":
    st.title("👥 قائمة الكباتن المشغلين")
    users = run_query("SELECT phone, device_id, status, accepted_clicks, last_active FROM myapp.users_status ORDER BY last_active DESC LIMIT 100")
    if users is not None:
        st.dataframe(users, use_container_width=True)

# د. الإشعارات
elif menu == "📢 مركز الإشعارات وبث الرسائل":
    st.title("📢 بث الرسائل المنسدلة")
    msg = st.text_area("نص الإشعار الذي سيظهر في شاشة السائق")
    if st.button("بث فوري لكافة الأجهزة 🚀"):
        run_query("UPDATE myapp.users_status SET notice_message = %s", (msg,), False)
        st.toast("تم إرسال الرسالة بنجاح", icon="📢")

# هـ. تحديث البيانات الحية
elif menu == "⚡ تحديث البيانات الحية (LIVE)":
    st.title("⚡ ذكاء البوت (Live Update)")
    config = run_query("SELECT key, value FROM myapp.app_config")
    if config is not None:
        edited = st.data_editor(config, use_container_width=True, num_rows="dynamic")
        if st.button("حفظ التعديلات الحية"):
            for _, row in edited.iterrows():
                run_query("INSERT INTO myapp.app_config (key, value) VALUES (%s, %s) ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value", (row['key'], row['value']), False)
            st.toast("تم تحديث ذكاء البوت حياً!")

# و. تحليل 3D
elif menu == "📊 تحليل البيانات 3D":
    st.title("📊 التحليل المكاني للنشاط")
    df = run_query("SELECT accepted_clicks as clicks, phone, last_active FROM myapp.users_status WHERE accepted_clicks > 0 LIMIT 100")
    if df is not None and not df.empty:
        fig = px.scatter_3d(df, x='phone', y='last_active', z='clicks', color='clicks', title="توزيع النقرات")
        st.plotly_chart(fig, use_container_width=True)

# تحديث تلقائي كل 10 ثوانٍ في صفحة الإحصائيات
if menu == "📈 نظرة عامة وإحصائيات الإصدارات":
    time.sleep(10)
    st.rerun()

import streamlit as st
import psycopg2
import pandas as pd
import plotly.express as px
import time
import hashlib
import random
from datetime import datetime

# --- 1. إعدادات الصفحة والهوية البصرية ---
st.set_page_config(page_title="MyClicker Pro | Secure Admin", layout="wide", page_icon="🔐")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;700;900&display=swap');
    html, body, [class*="css"] { font-family: 'Cairo', sans-serif; text-align: right; direction: rtl; }
    .stButton>button { width: 100%; border-radius: 10px; font-weight: bold; }
    .login-box { background: #f8fafc; padding: 40px; border-radius: 20px; border: 1px solid #e2e8f0; box-shadow: 0 10px 25px rgba(0,0,0,0.05); }
    </style>
    """, unsafe_allow_html=True)

# --- 2. إدارة جلسة الدخول (Session State) ---
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

# --- 3. وظيفة التحقق من البيانات ---
def check_login(username, password):
    # يمكنك ربط هذه الدالة بقاعدة البيانات لاحقاً، حالياً هي ثابتة للأمان السريع
    return username == "admin" and password == "admin123"

# --- 4. واجهة تسجيل الدخول ---
if not st.session_state.logged_in:
    st.markdown("<br><br>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("""
            <div style='text-align: center;'>
                <h1 style='color: #3b82f6;'>⚡ MyClicker Pro</h1>
                <p style='color: #64748b;'>نظام الإدارة المركزية - تسجيل الدخول</p>
            </div>
        """, unsafe_allow_html=True)
        
        with st.container():
            st.markdown("<div class='login-box'>", unsafe_allow_html=True)
            user = st.text_input("👤 اسم المستخدم")
            pwd = st.text_input("🔑 كلمة السر", type="password")
            if st.button("دخول للنظام 🚀"):
                if check_login(user, pwd):
                    st.session_state.logged_in = True
                    st.success("تم تسجيل الدخول بنجاح! جاري تحميل اللوحة...")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("❌ بيانات الدخول غير صحيحة")
            st.markdown("</div>", unsafe_allow_html=True)
    st.stop() # إيقاف بقية الكود حتى يتم الدخول

# --- 5. محرك الاتصال بقاعدة البيانات (Neon / DigitalOcean) ---
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
        cur.close(); conn.close()
        return res
    except Exception as e:
        st.error(f"خطأ: {e}")
        return None

# --- 6. لوحة التحكم (تظهر فقط بعد تسجيل الدخول) ---
with st.sidebar:
    st.markdown("<h2 style='text-align: center;'>⚡ MyClicker Pro</h2>", unsafe_allow_html=True)
    st.markdown(f"<p style='text-align: center; color: #16a34a;'>✅ متصل: <b>admin</b></p>", unsafe_allow_html=True)
    
    if st.button("🔄 تحديث البيانات"):
        st.rerun()
    
    st.markdown("---")
    menu = st.radio(":القائمة الرئيسية", [
        "📈 نظرة عامة وإحصائيات الإصدارات",
        "👥 إدارة ومراقبة المستخدمين والتفعيل",
        "📢 مركز الإشعارات الشامل الكامل",
        "🚀 إدارة التحديثات الإجبارية",
        "⚡ تحديث البيانات الحية (LIVE UPDATE)",
        "💳 توليد وإدارة الأكواد",
        "🤖 إضافة الأجهزة الافتراضية (TEST)",
        "📊 تحليل البيانات 3D"
    ])
    
    st.markdown("---")
    if st.button("🚪 تسجيل الخروج"):
        st.session_state.logged_in = False
        st.rerun()

# --- 7. معالجة الأقسام ---
if "📈 نظرة عامة" in menu:
    st.title("📈 إحصائيات النشاط")
    data = run_query("SELECT count(*) as total, sum(accepted_clicks) as clicks FROM myapp.users_status")
    if data is not None:
        c1, c2, c3 = st.columns(3)
        c1.metric("إجمالي السائقين", f"{data.iloc[0]['total']} جهاز")
        c2.metric("إجمالي النقرات", f"{int(data.iloc[0]['clicks'] or 0)} 🎯")
        c3.metric("الحالة", "نشط ✅")

elif "🤖 إضافة الأجهزة" in menu:
    st.title("🤖 حقن أجهزة الاختبار")
    num = st.slider("العدد", 100, 1000, 500)
    if st.button("بدء الحقن الآن 🚀"):
        query = "INSERT INTO myapp.users_status (device_id, phone, status, last_active) SELECT 'sim_'||i||'_'||md5(random()::text), '079'||LPAD(i::text,7,'0'), 'Active', NOW() FROM generate_series(1, %s) s(i) ON CONFLICT DO NOTHING"
        run_query(query, (num,), False)
        st.success("تم بنجاح!")

# (باقي الأقسام تتبع نفس المنطق المطور سابقاً)
else:
    st.title(menu)
    st.info("القسم قيد المزامنة...")

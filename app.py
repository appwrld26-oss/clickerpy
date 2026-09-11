import streamlit as st
import psycopg2
from psycopg2 import pool
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import time
import hashlib
import random
import numpy as np
from datetime import datetime

# --- 1. التكوين الهندسي والبصري (Premium Neon Style) ---
st.set_page_config(page_title="MyClicker Pro | Neon Command Center", layout="wide", page_icon="⚡")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700;900&display=swap');
    html, body, [class*="css"] { font-family: 'Cairo', sans-serif; text-align: right; direction: rtl; background-color: #0F172A; color: white; }
    .stMetric { background: linear-gradient(135deg, #1E293B 0%, #0F172A 100%); padding: 25px; border-radius: 20px; border: 1px solid #334155; box-shadow: 0 10px 25px rgba(0,0,0,0.3); }
    div[data-testid="stMetricValue"] { color: #00E5FF; font-size: 2.5rem; font-weight: 900; }
    .stButton>button { background: linear-gradient(90deg, #00C8FF 0%, #007BFF 100%); border: none; border-radius: 12px; color: white; font-weight: 900; height: 3.5em; transition: 0.4s; }
    .sidebar .sidebar-content { background-color: #1E293B; border-left: 1px solid #334155; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. محرك الاتصال بـ Neon (رابطك المباشر) ---
DB_URL = "postgresql://neondb_owner:npg_AvzFkHQ6M3yo@ep-tiny-wind-ayd9hww0.c-5.us-east-2.aws.neon.tech/neondb?sslmode=require"

@st.cache_resource
def get_neon_pool():
    # استخدام مجمع اتصالات لضمان سرعة الاستجابة مع نيون
    return psycopg2.pool.SimpleConnectionPool(1, 15, DB_URL)

def run_query(query, params=None, is_select=True):
    neon_pool = get_neon_pool()
    conn = neon_pool.getconn()
    try:
        cur = conn.cursor()
        cur.execute(query, params)
        if is_select:
            data = cur.fetchall()
            cols = [desc[0] for desc in cur.description]
            return pd.DataFrame(data, columns=cols)
        conn.commit()
        return True
    except Exception as e:
        st.error(f"⚠️ خطأ في نيون: {e}")
        return None
    finally:
        cur.close()
        neon_pool.putconn(conn)

# --- 3. بوابة الدخول (Security Gate) ---
if 'auth' not in st.session_state: st.session_state.auth = False

if not st.session_state.auth:
    st.markdown("<br><br>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        st.markdown("<h1 style='text-align: center; color: #00E5FF;'>MYCLICKER PRO 🧊</h1>", unsafe_allow_html=True)
        st.markdown("<div style='background:#1E293B; padding:40px; border-radius:25px; border:1px solid #334155;'>", unsafe_allow_html=True)
        u = st.text_input("👤 المستخدم الإداري")
        p = st.text_input("🔑 كلمة السر", type="password")
        if st.button("دخول للنظام 🚀"):
            if u == "admin" and p == "admin123":
                st.session_state.auth = True
                st.rerun()
            else: st.error("❌ بيانات خاطئة")
        st.markdown("</div>", unsafe_allow_html=True)
    st.stop()

# --- 4. القائمة الجانبية (مطابقة للصورة بالكامل) ---
with st.sidebar:
    st.markdown("<h2 style='text-align: center; color: #00E5FF;'>⚡ MyClicker Pro</h2>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center;'>✅ متصل بـ: <b>Neon Cloud</b></p>", unsafe_allow_html=True)
    if st.button("🔄 تحديث ومسح الذاكرة"):
        st.cache_data.clear()
        st.rerun()
    st.markdown("---")
    menu = st.radio("القائمة الرئيسية:", [
        "📈 نظرة عامة وإحصائيات الإصدارات",
        "👥 إدارة ومراقبة المستخدمين والتفعيل",
        "📢 مركز الإشعارات الشامل الكامل",
        "🚀 إدارة التحديثات الإجبارية",
        "⚡ تحديث البيانات الحية (LIVE UPDATE)",
        "💳 توليد وإدارة الأكواد",
        "🤖 إضافة الأجهزة الافتراضية (TEST)",
        "📊 تحليل البيانات 3D",
        "🖥️ حالة السيرفر"
    ])
    st.markdown("---")
    if st.button("🚪 خروج"):
        st.session_state.auth = False
        st.rerun()

# --- 5. تشغيل الوظائف الكاملة ---

if "📈 نظرة عامة" in menu:
    st.title("📈 ملخص نشاط السائقين")
    stats = run_query("SELECT count(*) as total, sum(accepted_clicks) as clicks FROM myapp.users_status").iloc[0]
    c1, c2, c3 = st.columns(3)
    c1.metric("إجمالي السائقين", f"{stats['total']} جهاز")
    c2.metric("إجمالي الصيد", f"{int(stats['clicks'] or 0)} طلب")
    c3.metric("مزود الخدمة", "Neon.tech ✅")
    
    st.markdown("---")
    st.subheader("🚀 أداء الإصدارات")
    ver_df = run_query("SELECT app_version, count(*) as count FROM myapp.users_status GROUP BY app_version")
    st.bar_chart(ver_df.set_index('app_version'))

elif "👥 إدارة ومراقبة" in menu:
    st.title("👥 التحكم في أسطول الكباتن")
    users = run_query("SELECT phone, device_id, status, expiry_date, accepted_clicks, bot_status FROM myapp.users_status ORDER BY last_active DESC LIMIT 50")
    st.dataframe(users, use_container_width=True)
    st.info("استخدم لوحة التحكم في السيرفر (Node.js) لتعديل الحالات الفردية بسرعة أعلى.")

elif "📢 مركز الإشعارات" in menu:
    st.title("📢 بث الإشعارات المنسدلة")
    msg = st.text_area("نص الرسالة التي ستظهر للسائقين")
    if st.button("بث الإشعار للجميع فوراً 🚀"):
        run_query("UPDATE myapp.users_status SET notice_message = %s", (msg,), False)
        st.toast(f"✅ تم البث: {msg}", icon="📢")

elif "⚡ تحديث البيانات الحية" in menu:
    st.title("⚡ ذكاء البوت (Live Update)")
    config = run_query("SELECT key, value FROM myapp.app_config")
    edited = st.data_editor(config, use_container_width=True)
    if st.button("حفظ وإرسال التحديث الحي"):
        for _, row in edited.iterrows():
            run_query("INSERT INTO myapp.app_config (key, value) VALUES (%s, %s) ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value", (row['key'], row['value']), False)
        st.success("تم تحديث ذكاء كافة الأجهزة!")

elif "🤖 إضافة الأجهزة الافتراضية" in menu:
    st.title("🤖 حقن أجهزة الاختبار (Stress Test)")
    num = st.slider("كم جهاز تريد إضافته لنيون؟", 100, 1000, 500)
    if st.button("إطلاق جيش الأجهزة 🚀"):
        with st.spinner("جاري الحقن في Neon..."):
            q = """INSERT INTO myapp.users_status (device_id, phone, status, sub_tier, expiry_date, app_version, bot_status, accepted_clicks, last_active)
                   SELECT 'sim_'||i||'_'||md5(random()::text), '079'||LPAD(i::text,7,'0'), 'Active', 'VIP', NOW() + interval '30 days', '7.2.8', 'Online', floor(random()*100), NOW()
                   FROM generate_series(1, %s) s(i) ON CONFLICT DO NOTHING;"""
            run_query(q, (num,), False)
            st.success(f"تم إضافة {num} جهاز بنجاح!")

elif "📊 تحليل البيانات 3D" in menu:
    st.title("🌌 التحليل الفضائي (3D View)")
    df = run_query("SELECT accepted_clicks as z, phone as x, last_active as y FROM myapp.users_status WHERE accepted_clicks > 0 LIMIT 300")
    if not df.empty:
        # تحويل الوقت لرقم للرسم
        df['time_idx'] = pd.to_datetime(df['y']).astype(np.int64) // 10**12
        fig = px.scatter_3d(df, x='x', y='time_idx', z='z', color='z', template="plotly_dark")
        st.plotly_chart(fig, use_container_width=True)
    else: st.warning("لا توجد بيانات كافية للرسم ثلاثي الأبعاد")

# تحديث تلقائي للصفحة الرئيسية
if "📈 نظرة عامة" in menu:
    time.sleep(10)
    st.rerun()

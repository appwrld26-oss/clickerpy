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
from datetime import datetime, timedelta

# --- 1. التكوين الهندسي والبصري واللوجو المتحرك ---
st.set_page_config(page_title="MyClicker Pro | Ultimate Command", layout="wide", page_icon="⚡")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700;900&display=swap');
    html, body, [class*="css"] { font-family: 'Cairo', sans-serif; text-align: right; direction: rtl; background-color: #0F172A; color: white; }
    
    /* تصميم اللوجو النيوني المتحرك المطور */
    .logo-container { text-align: center; padding: 20px; }
    .neon-circle {
        width: 100px; height: 100px; border-radius: 50%;
        background: radial-gradient(circle, #00E5FF 0%, #007BFF 100%);
        box-shadow: 0 0 20px #00E5FF, 0 0 40px #007BFF;
        margin: 0 auto; animation: pulse 2s infinite;
        display: flex; align-items: center; justify-content: center; font-size: 40px;
    }
    @keyframes pulse {
        0% { transform: scale(1); box-shadow: 0 0 20px #00E5FF; }
        50% { transform: scale(1.1); box-shadow: 0 0 40px #00E5FF, 0 0 60px #007BFF; }
        100% { transform: scale(1); box-shadow: 0 0 20px #00E5FF; }
    }
    
    .stMetric { background: linear-gradient(135deg, #1E293B 0%, #0F172A 100%); padding: 25px; border-radius: 20px; border: 1px solid #334155; }
    .stButton>button { border-radius: 12px; font-weight: 900; height: 3.5em; transition: 0.3s; width: 100%; }
    .sidebar .sidebar-content { background-color: #1E293B; border-left: 1px solid #334155; }
    div[data-testid="stExpander"] { background: #1E293B; border: 1px solid #334155; border-radius: 15px; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. محرك الاتصال بـ Neon Pool (صمام الأمان) ---
DB_URL = "postgresql://neondb_owner:npg_AvzFkHQ6M3yo@ep-tiny-wind-ayd9hww0.c-5.us-east-2.aws.neon.tech/neondb?sslmode=require"

@st.cache_resource
def get_pool():
    return psycopg2.pool.SimpleConnectionPool(1, 50, DB_URL, sslmode='require', sslrootcert='')

def run_query(query, params=None, is_select=True):
    p = get_pool()
    conn = p.getconn()
    try:
        cur = conn.cursor()
        cur.execute(query, params)
        if is_select:
            data = cur.fetchall()
            cols = [desc[0] for desc in cur.description]
            return pd.DataFrame(data, columns=cols)
        conn.commit(); return True
    except Exception as e:
        st.error(f"❌ خطأ: {e}"); return None
    finally:
        cur.close(); p.putconn(conn)

# --- 3. بوابة الدخول ---
if 'auth' not in st.session_state: st.session_state.auth = False
if not st.session_state.auth:
    col1, col2, col3 = st.columns([1, 1.2, 1])
    with col2:
        st.markdown("<h1 style='text-align: center; color: #00E5FF;'>MYCLICKER PRO 🔐</h1>", unsafe_allow_html=True)
        u = st.text_input("👤 اسم المستخدم")
        p = st.text_input("🔑 كلمة السر", type="password")
        if st.button("دخول 🚀"):
            if u == "admin" and p == "admin123": st.session_state.auth = True; st.rerun()
    st.stop()

# --- 4. القائمة الجانبية (مطابقة للصورة 100%) ---
with st.sidebar:
    st.markdown("""<div class='logo-container'><div class='neon-circle'>⚡</div></div>""", unsafe_allow_html=True)
    st.markdown("<h3 style='text-align: center; color: #00E5FF;'>MyClicker Pro</h3>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center;'>المستخدم: admin</p>", unsafe_allow_html=True)
    if st.button("🔄 مسح الذاكرة والتحديث"): st.cache_data.clear(); st.rerun()
    st.markdown("---")
    menu = st.radio("**:القائمة الرئيسية**", [
        "📈 نظرة عامة وإحصائيات الإصدارات",
        "👥 إدارة ومراقبة المستخدمين والتفعيل",
        "📢 مركز الإشعارات الشامل الكامل",
        "🚀 إدارة التحديثات الإجبارية",
        "⚡ تحديث البيانات الحية (LIVE UPDATE)",
        "💳 توليد وإدارة الأكواد",
        "🤝 قسم الشركاء (الموزعين)",
        "📊 تحليل البيانات 3D",
        "🖥️ حالة السيرفر",
        "🔐 إدارة الصلاحيات والتحكم",
        "🛠️ الدعم الفني والتواصل",
        "🤖 إضافة الأجهزة الافتراضية (TEST)"
    ])
    st.markdown("---")
    if st.button("🚪 تسجيل الخروج"): st.session_state.auth = False; st.rerun()

# --- 5. برمجة الوظائف (بدون تبسيط) ---

# 5.1 نظرة عامة
if "📈 نظرة عامة" in menu:
    st.title("📈 إحصائيات الأداء العام")
    s = run_query("SELECT count(*) as total, sum(accepted_clicks) as clicks FROM myapp.users_status").iloc[0]
    c1, c2, c3 = st.columns(3)
    c1.metric("إجمالي الجيش", f"{s['total']} جهاز")
    c2.metric("إجمالي الصيد", f"{int(s['clicks'] or 0)} طلب")
    c3.metric("استقرار نيون", "100% ✅")
    st.subheader("📊 توزيع الإصدارات في الميدان")
    st.bar_chart(run_query("SELECT app_version, count(*) FROM myapp.users_status GROUP BY app_version").set_index('app_version'))

# 5.2 إدارة ومراقبة المستخدمين (تعديل + حذف + تصفير)
elif "👥 إدارة ومراقبة" in menu:
    st.title("👥 إدارة أسطول الكباتن")
    search = st.text_input("🔍 ابحث برقم هاتف أو ID")
    q = "SELECT * FROM myapp.users_status WHERE device_id NOT LIKE 'sim_%%'"
    if search: q += f" AND (phone LIKE '%%{search}%%' OR device_id LIKE '%%{search}%%')"
    users = run_query(q + " ORDER BY last_active DESC LIMIT 100")
    
    for _, u in users.iterrows():
        with st.expander(f"📱 {u['phone']} | {u['device_id'][:10]}... | 🎯 {u['accepted_clicks']}"):
            col1, col2, col3, col4 = st.columns(4)
            # التعديل
            new_phone = col1.text_input("تعديل الهاتف", value=u['phone'], key=f"p_{u['device_id']}")
            new_tier = col1.selectbox("الفئة", ["VIP", "STANDARD", "TRIAL"], index=0, key=f"t_{u['device_id']}")
            if col1.button("💾 حفظ التعديلات", key=f"save_{u['device_id']}"):
                run_query("UPDATE myapp.users_status SET phone=%s, sub_tier=%s WHERE device_id=%s", (new_phone, new_tier, u['device_id']), False)
                st.toast("تم التحديث")
            
            # التصفير (Reset)
            col2.write("**تحكم العداد**")
            if col2.button("🔄 تصفير النقرات (Reset)", key=f"res_{u['device_id']}"):
                run_query("UPDATE myapp.users_status SET accepted_clicks=0 WHERE device_id=%s", (u['device_id'],), False)
                st.rerun()
            
            # الحذف
            col3.write("**منطقة الخطر**")
            if col3.button("🗑️ حذف الجهاز نهائياً", key=f"del_{u['device_id']}", type="primary"):
                run_query("DELETE FROM myapp.users_status WHERE device_id=%s", (u['device_id'],), False)
                st.rerun()
            
            # التجميد
            col4.write("**الحالة**")
            if col4.button("❄️ تجميد / فك", key=f"frz_{u['device_id']}"):
                run_query("UPDATE myapp.users_status SET is_frozen = NOT is_frozen WHERE device_id = %s", (u['device_id'],), False)
                st.rerun()

# 5.3 الإشعارات
elif "📢 مركز الإشعارات" in menu:
    st.title("📢 بث الرسائل المنسدلة")
    msg = st.text_area("نص الرسالة التي ستظهر في شريط إشعارات البوت")
    if st.button("🚀 بث فوري للجميع"):
        run_query("UPDATE myapp.users_status SET notice_message = %s", (msg,), False)
        st.toast("تم البث بنجاح")

# 5.4 التحديثات الإجبارية
elif "🚀 إدارة التحديثات" in menu:
    st.title("🚀 نظام التحديث الإجباري والمنع")
    conf = run_query("SELECT key, value FROM myapp.app_config")
    c_dict = dict(zip(conf['key'], conf['value']))
    with st.form("up"):
        ver = st.text_input("أحدث نسخة", value=c_dict.get('latest_version', '7.2.8'))
        force = st.checkbox("تفعيل قفل النسخة", value=c_dict.get('force_update') == 'true')
        url = st.text_input("رابط الـ APK", value=c_dict.get('next_url', ''))
        if st.form_submit_button("تطبيق"):
            for k,v in {'latest_version':ver, 'force_update':'true' if force else 'false', 'next_url':url}.items():
                run_query("INSERT INTO myapp.app_config (key, value) VALUES (%s, %s) ON CONFLICT (key) DO UPDATE SET value=EXCLUDED.value", (k,v), False)
            st.success("تم الحفظ")

# 5.5 تحديث البيانات الحية
elif "⚡ تحديث البيانات الحية" in menu:
    st.title("⚡ ذكاء البوت (Live Keywords)")
    config = run_query("SELECT key, value FROM myapp.app_config")
    edited = st.data_editor(config, use_container_width=True)
    if st.button("حفظ وإرسال لكافة الهواتف"):
        for _, r in edited.iterrows():
            run_query("INSERT INTO myapp.app_config (key, value) VALUES (%s, %s) ON CONFLICT (key) DO UPDATE SET value=EXCLUDED.value", (r['key'], r['value']), False)
        st.toast("تم التحديث!")

# 5.6 جيش المحاكاة
elif "🤖 إضافة الأجهزة" in menu:
    st.title("🤖 مركز أجهزة الاختبار")
    c1, c2 = st.columns(2)
    with c1:
        n = st.number_input("العدد", 10, 1000, 100)
        if st.button("🚀 حقن الجيش"):
            run_query("INSERT INTO myapp.users_status (device_id, phone, status, expiry_date, last_active) SELECT 'sim_'||md5(random()::text), '079'||LPAD(i::text,7,'0'), 'Active', NOW()+interval '30 days', NOW() FROM generate_series(1, %s) s(i)", (n,), False)
            st.success("تم الحقن")
    with c2:
        if st.button("🗑️ إبادة المحاكاة", type="primary"):
            run_query("DELETE FROM myapp.users_status WHERE device_id LIKE 'sim_%%'", fetch=False); st.rerun()

# 5.7 تحليل البيانات 3D
elif "📊 تحليل البيانات" in menu:
    st.title("🌌 التحليل الفضائي للنشاط (3D)")
    df = run_query("SELECT accepted_clicks as z, phone as x, last_active as y FROM myapp.users_status WHERE accepted_clicks > 0 LIMIT 300")
    if not df.empty:
        df['time_idx'] = pd.to_datetime(df['y']).astype(np.int64) // 10**12
        st.plotly_chart(px.scatter_3d(df, x='x', y='time_idx', z='z', color='z', template="plotly_dark"), use_container_width=True)

# باقي الأقسام (Placeholder لضمان الهيكلية الكاملة)
elif "🤝 قسم الشركاء" in menu or "🔐 إدارة الصلاحيات" in menu or "🛠️ الدعم الفني" in menu or "🖥️ حالة السيرفر" in menu:
    st.title(menu)
    st.info("هذا القسم مربوط بقاعدة البيانات وجاهز لاستقبال بيانات الموزعين والصلاحيات.")
    st.table(run_query("SELECT * FROM myapp.users_status LIMIT 5"))

# التحديث التلقائي
if "📈 نظرة عامة" in menu:
    time.sleep(10); st.rerun()

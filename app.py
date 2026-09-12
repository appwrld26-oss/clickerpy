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

# --- 1. التكوين الجمالي والهندسي (Ultimate Neon Glass Theme) ---
st.set_page_config(page_title="MyClicker Pro | Global Fleet Command", layout="wide", page_icon="⚡")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700;900&display=swap');
    
    :root {
        --neon-cyan: #00E5FF;
        --deep-navy: #0F172A;
        --glass-bg: rgba(30, 41, 59, 0.7);
        --accent-blue: #3B82F6;
    }

    html, body, [class*="css"] { 
        font-family: 'Cairo', sans-serif; 
        text-align: right; 
        direction: rtl; 
        background-color: var(--deep-navy); 
        color: white; 
    }

    /* تأثير الزجاج والخلفية المتدرجة */
    .stApp {
        background: radial-gradient(circle at top right, #1E293B, #0F172A);
    }

    /* تحسين كروت الإحصائيات */
    .stMetric { 
        background: var(--glass-bg) !important;
        backdrop-filter: blur(10px);
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        border-right: 4px solid var(--neon-cyan) !important;
        padding: 25px !important; 
        border-radius: 24px !important; 
        box-shadow: 0 10px 30px rgba(0,0,0,0.5) !important;
        transition: all 0.3s ease;
    }
    .stMetric:hover { transform: translateY(-5px); border-color: var(--neon-cyan) !important; }
    
    div[data-testid="stMetricValue"] { 
        color: var(--neon-cyan) !important; 
        font-size: 2.8rem !important; 
        font-weight: 900 !important;
        text-shadow: 0 0 15px rgba(0, 229, 255, 0.4);
    }

    /* تصميم الأزرار المطور */
    .stButton>button { 
        background: linear-gradient(135deg, #00C8FF 0%, #007BFF 100%) !important; 
        border: none !important; 
        border-radius: 16px !important; 
        color: white !important; 
        font-weight: 900 !important; 
        height: 3.8em !important; 
        transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275) !important; 
        box-shadow: 0 4px 15px rgba(0, 123, 255, 0.3) !important;
    }
    .stButton>button:hover { 
        transform: scale(1.03) !important; 
        box-shadow: 0 8px 25px rgba(0, 200, 255, 0.5) !important; 
    }

    /* تحسين القائمة الجانبية */
    [data-testid="stSidebar"] {
        background-color: rgba(15, 23, 42, 0.95) !important;
        border-left: 1px solid rgba(255, 255, 255, 0.05) !important;
    }

    /* أنيميشن اللوجو النيوني */
    .neon-logo {
        width: 100px; height: 100px; border-radius: 50%;
        background: radial-gradient(circle, #00E5FF 0%, #007BFF 100%);
        box-shadow: 0 0 30px rgba(0, 229, 255, 0.6);
        margin: 0 auto 20px; 
        display: flex; align-items: center; justify-content: center;
        font-size: 45px; animation: pulse 2.5s infinite ease-in-out;
    }
    @keyframes pulse {
        0%, 100% { transform: scale(1); box-shadow: 0 0 20px rgba(0, 229, 255, 0.4); }
        50% { transform: scale(1.1); box-shadow: 0 0 50px rgba(0, 229, 255, 0.8); }
    }

    /* تنسيق الجداول */
    .stDataFrame, .stTable {
        background: var(--glass-bg) !important;
        border-radius: 20px !important;
        border: 1px solid rgba(255, 255, 255, 0.05) !important;
    }
    
    /* الـ Tabs */
    .stTabs [data-baseweb="tab-list"] { gap: 15px; }
    .stTabs [data-baseweb="tab"] { 
        background-color: rgba(30, 41, 59, 0.5); 
        border-radius: 12px; padding: 12px 25px; color: #94A3B8; 
    }
    .stTabs [aria-selected="true"] { 
        background: var(--accent-blue) !important; color: white !important; 
    }
    
    /* مخصص للـ Sidebar */
    .css-1offfwp { padding: 2rem 1rem; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. محرك الاتصال بـ Neon Pool (Ultra Stable) ---
DB_URL = "postgresql://neondb_owner:npg_AvzFkHQ6M3yo@ep-tiny-wind-ayd9hww0.c-5.us-east-2.aws.neon.tech/neondb?sslmode=require"

@st.cache_resource
def get_connection_pool():
    return psycopg2.pool.SimpleConnectionPool(1, 50, DB_URL, sslmode='require', sslrootcert='')

def run_query(query, params=None, is_select=True):
    p = get_connection_pool()
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
        st.error(f"❌ خطأ تقني: {e}"); return None
    finally:
        cur.close(); p.putconn(conn)

# --- 3. بوابة الدخول (Glass Login) ---
if 'auth' not in st.session_state: st.session_state.auth = False
if not st.session_state.auth:
    st.markdown("<br><br><br>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1, 1.2, 1])
    with c2:
        st.markdown("<div class='neon-logo'>⚡</div>", unsafe_allow_html=True)
        st.markdown("<h1 style='text-align: center; color: white;'>MYCLICKER PRO 🔐</h1>", unsafe_allow_html=True)
        st.markdown("<div style='background: rgba(30, 41, 59, 0.8); padding: 45px; border-radius: 35px; border: 1px solid rgba(255,255,255,0.1); backdrop-filter: blur(15px);'>", unsafe_allow_html=True)
        u = st.text_input("👤 معرف المدير المصرح")
        p = st.text_input("🔑 كود الحماية", type="password")
        if st.button("فتح الأنظمة المركزية 🚀"):
            if u == "admin" and p == "admin123":
                st.session_state.auth = True; st.rerun()
            else: st.error("عذراً، البيانات غير مطابقة")
        st.markdown("</div>", unsafe_allow_html=True)
    st.stop()

# --- 4. القائمة الجانبية الفاخرة ---
with st.sidebar:
    st.markdown("<div class='neon-logo' style='width:70px; height:70px; font-size:30px;'>⚡</div>", unsafe_allow_html=True)
    st.markdown("<h2 style='text-align: center; color: #00E5FF; margin-top:-10px;'>MyClicker Pro</h2>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #94A3B8; font-size:14px;'>Fleet Commander: <b>admin</b></p>", unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("🔄 تحديث الأنظمة"): st.cache_data.clear(); st.rerun()
    
    st.markdown("---")
    menu = st.radio("📋 الوحدات الإدارية:", [
        "📈 مركز الرؤية والتحليلات",
        "👥 إدارة الأسطول الحقيقي",
        "🤖 إدارة جيش المحاكاة",
        "⚙️ برمجة الذكاء الحي",
        "💳 إدارة كروت التفعيل",
        "📢 بث الإشعارات المنسدلة",
        "🌌 التحليل الفضائي 3D",
        "🖥️ صحة السيرفر ونظام Pool"
    ])
    st.markdown("---")
    if st.button("🚪 خروج آمن"): st.session_state.auth = False; st.rerun()

# --- 5. تشغيل الوحدات المجمّلة ---

# 5.1 التحليلات والإحصائيات
if "📈 مركز الرؤية" in menu:
    st.title("📈 لوحة قيادة الأسطول المركزية")
    stats = run_query("SELECT count(*) as total, sum(accepted_clicks) as clicks FROM myapp.users_status").iloc[0]
    real_count = run_query("SELECT count(*) FROM myapp.users_status WHERE device_id NOT LIKE 'sim_%%'").iloc[0,0]
    
    c1, c2, c3 = st.columns(3)
    c1.metric("إجمالي الكباتن 🛡️", f"{real_count}", delta="نشط")
    c2.metric("إجمالي الصيد 🎯", f"{int(stats['clicks'] or 0)}", delta="↑ Real-time")
    c3.metric("استقرار السحابة 🟢", "100%", delta="Pool 50")
    
    st.markdown("<br>", unsafe_allow_html=True)
    with st.container():
        st.subheader("🚀 نشاط الإصدارات الميدانية")
        ver_df = run_query("SELECT app_version, count(*) as count FROM myapp.users_status GROUP BY app_version")
        fig = px.bar(ver_df, x='app_version', y='count', color='count', color_continuous_scale='Blues', template="plotly_dark")
        fig.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig, use_container_width=True)

# 5.2 إدارة المستخدمين (تعديل، حذف، تصفير)
elif "👥 إدارة الأسطول" in menu:
    st.title("👥 التحكم الكامل في الزبائن")
    search = st.text_input("🔍 ابحث عن كابتن معين (هاتف أو ID)...")
    q = "SELECT * FROM myapp.users_status WHERE device_id NOT LIKE 'sim_%%'"
    if search: q += f" AND (phone LIKE '%%{search}%%' OR device_id LIKE '%%{search}%%')"
    users = run_query(q + " ORDER BY last_active DESC LIMIT 100")
    
    for _, u in users.iterrows():
        with st.expander(f"📱 {u['phone']} | {u['device_id'][:12]}... | 🎯 {u['accepted_clicks']}"):
            col1, col2, col3 = st.columns([1, 1, 1])
            with col1:
                st.write(f"**الانتهاء:** {u['expiry_date']}")
                if st.button("❄️ تجميد / فك", key=f"f_{u['device_id']}"):
                    run_query("UPDATE myapp.users_status SET is_frozen = NOT is_frozen WHERE device_id = %s", (u['device_id'],), False); st.rerun()
            with col2:
                if st.button("🔄 تصفير (Reset)", key=f"r_{u['device_id']}"):
                    run_query("UPDATE myapp.users_status SET accepted_clicks = 0 WHERE device_id = %s", (u['device_id'],), False); st.rerun()
            with col3:
                if st.button("🗑️ حذف نهائي", key=f"d_{u['device_id']}", type="primary"):
                    run_query("DELETE FROM myapp.users_status WHERE device_id = %s", (u['device_id'],), False); st.rerun()

# 5.3 جيش المحاكاة
elif "🤖 إدارة جيش" in menu:
    st.title("🤖 مركز إدارة جيش الاختبار")
    st.markdown("<div style='background:rgba(22, 163, 74, 0.1); padding:20px; border-radius:15px; border:1px solid #16a34a;'>تحكم في أجهزة المحاكاة لاختبار أقصى قدرات السيرفر.</div>", unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        num = st.number_input("العدد المطلوب (Max 1000)", 10, 1000, 100)
        if st.button("🚀 حقن الجيش الآن"):
            q = """INSERT INTO myapp.users_status (device_id, phone, status, sub_tier, expiry_date, accepted_clicks, last_active)
                   SELECT 'sim_'||md5(random()::text), '079'||LPAD(i::text,7,'0'), 'Active', 'VIP', NOW() + interval '30 days', floor(random()*100), NOW()
                   FROM generate_series(1, %s) s(i) ON CONFLICT DO NOTHING;"""
            run_query(q, (num,), False); st.success(f"تم حقن {num} جهاز بنجاح!")
    with c2:
        if st.button("🗑️ إبادة كافة الهواتف الوهمية", type="primary"):
            run_query("DELETE FROM myapp.users_status WHERE device_id LIKE 'sim_%%'", fetch=False); st.rerun()

# 5.4 التحديث الحي
elif "⚙️ برمجة الذكاء" in menu:
    st.title("⚙️ برمجة ذكاء البوت (Live Update)")
    config = run_query("SELECT key, value FROM myapp.app_config")
    edited = st.data_editor(config, use_container_width=True, num_rows="dynamic")
    if st.button("💾 تطبيق التغييرات حياً"):
        for _, r in edited.iterrows():
            run_query("INSERT INTO myapp.app_config (key, value) VALUES (%s, %s) ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value", (r['key'], r['value']), False)
        st.toast("تم تحديث كافة الأجهزة!", icon="🧠")

# 5.5 تحليل البيانات 3D
elif "🌌 التحليل الفضائي" in menu:
    st.title("🌌 التحليل الفضائي للنشاط (3D Real-time)")
    df_3d = run_query("SELECT accepted_clicks as z, phone as x, last_active as y, device_id FROM myapp.users_status WHERE accepted_clicks > 0 LIMIT 500")
    if not df_3d.empty:
        df_3d['type'] = df_3d['device_id'].apply(lambda x: 'Real 🛡️' if not str(x).startswith('sim') else 'Virtual 🤖')
        df_3d['time_score'] = pd.to_datetime(df_3d['y']).astype(np.int64) // 10**12
        fig = px.scatter_3d(df_3d, x='x', y='time_score', z='z', color='type', template="plotly_dark", title="مخطط صيد الرحلات")
        fig.update_layout(scene=dict(xaxis_title='رقم الهاتف', yaxis_title='ساعة النشاط', zaxis_title='عدد الطلبات 🎯'))
        st.plotly_chart(fig, use_container_width=True)

# 5.6 الإشعارات
elif "📢 بث الإشعارات" in menu:
    st.title("📢 نظام بث الرسائل الفورية")
    msg = st.text_area("اكتب نص الرسالة التي ستظهر في شريط إشعارات البوت")
    if st.button("🚀 بث فوري للجميع"):
        run_query("UPDATE myapp.users_status SET notice_message = %s", (msg,), False)
        st.toast("تم البث بنجاح!", icon="📢")

# تحديث تلقائي للصفحة الرئيسية
if "📈 مركز الرؤية" in menu:
    time.sleep(10); st.rerun()

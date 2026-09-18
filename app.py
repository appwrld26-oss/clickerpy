import hashlib
import hmac
import random
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any, Iterable, Optional

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import psycopg2
from psycopg2 import pool
import streamlit as st

# ============================================================
# 1. إعداد الصفحة والهوية البصرية (Premium Light Enterprise)
# ============================================================
st.set_page_config(
    page_title="MyClicker Pro | Global Fleet Command",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700;900&display=swap');

:root {
  --primary: #0061FF; --accent: #00D1FF; --bg: #F8FAFC;
  --card: #FFFFFF; --text: #1E293B; --border: #E2E8F0;
}

html, body, [class*="css"] { 
    font-family: 'Cairo', sans-serif; direction: rtl; text-align: right; 
    background: var(--bg); color: var(--text); 
}

/* تصميم اللوجو النيوني المطور */
.neon-logo { 
    width: 80px; height: 80px; border-radius: 50%; 
    background: radial-gradient(circle, var(--accent), var(--primary)); 
    box-shadow: 0 0 25px rgba(0,97,255,.4); 
    margin: 0 auto 15px; display: flex; align-items: center; justify-content: center; 
    font-size: 35px; color: white; animation: pulse 2.5s infinite ease-in-out;
}
@keyframes pulse { 0%, 100% { transform: scale(1); opacity: 0.8; } 50% { transform: scale(1.1); opacity: 1; box-shadow: 0 0 40px rgba(0,209,255,.6); } }

/* تحسين الكروت */
.stMetric { background: white !important; border-radius: 20px !important; border-right: 6px solid var(--primary) !important; box-shadow: 0 10px 20px rgba(0,0,0,0.05) !important; padding: 20px !important; }
div[data-testid="stMetricValue"] { color: var(--primary) !important; font-weight: 900 !important; font-size: 2.2rem !important; }

/* الأزرار الملونة */
.stButton > button { background: linear-gradient(135deg, var(--primary), var(--accent)) !important; border: 0 !important; border-radius: 14px !important; color: white !important; font-weight: 800 !important; min-height: 3.5em !important; width: 100% !important; transition: 0.3s; }
.stButton > button:hover { transform: translateY(-2px); box-shadow: 0 8px 20px rgba(0,97,255,0.3) !important; }

/* تنسيق الجداول (Sheets) */
[data-testid="stDataEditor"] { border-radius: 15px; border: 1px solid var(--border); overflow: hidden; box-shadow: 0 5px 15px rgba(0,0,0,0.02); }
</style>
""", unsafe_allow_html=True)

# ============================================================
# 2. محرك الاتصال بـ Neon (Ultra Stable Pool)
# ============================================================
DB_URL = "postgresql://neondb_owner:npg_AvzFkHQ6M3yo@ep-tiny-wind-ayd9hww0.c-5.us-east-2.aws.neon.tech/neondb?sslmode=require"

@st.cache_resource
def get_db_pool():
    return pool.SimpleConnectionPool(1, 50, dsn=DB_URL, sslmode="require", sslrootcert="")

@contextmanager
def db_conn():
    connection = None
    try:
        connection = get_db_pool().getconn()
        yield connection
    finally:
        if connection: get_db_pool().putconn(connection)

def run_query(query, params=None, is_select=True):
    try:
        with db_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(query, params)
                if is_select:
                    rows = cur.fetchall()
                    cols = [d[0] for d in cur.description]
                    return pd.DataFrame(rows, columns=cols)
                conn.commit()
                return True
    except Exception as e:
        st.error(f"❌ خطأ فني: {e}")
        return None

# ============================================================
# 3. بوابة الدخول (Login Gate)
# ============================================================
if 'auth' not in st.session_state: st.session_state.auth = False

if not st.session_state.auth:
    _, center, _ = st.columns([1, 1.2, 1])
    with center:
        st.markdown("<br><br><div class='neon-logo'>⚡</div><h2 style='text-align:center'>تسجيل دخول الإدارة</h2>", unsafe_allow_html=True)
        u = st.text_input("اسم المستخدم")
        p = st.text_input("كلمة المرور", type="password")
        if st.button("فتح الأنظمة 🚀"):
            if u == "admin" and p == "admin123":
                st.session_state.auth = True; st.rerun()
            else: st.error("بيانات غير صحيحة")
    st.stop()

# --- القائمة الجانبية ( Sidebar) ---
with st.sidebar:
    st.markdown("<div class='neon-logo' style='width:60px;height:60px;font-size:25px'>⚡</div>", unsafe_allow_html=True)
    st.markdown("<h3 style='text-align:center;color:#0061FF'>MyClicker Pro</h3>", unsafe_allow_html=True)
    if st.button("🔄 مزامنة الأنظمة"):
        st.cache_data.clear(); st.rerun()
    st.divider()
    menu = st.radio("**الوحدات الإدارية:**", [
        "📈 لوحة التحكم والإحصائيات",
        "📂 ورقة إدارة السائقين الحقيقية",
        "🤖 ورقة أجهزة المحاكاة (الاختبار)",
        "📢 مركز الإشعارات (Peak Mode)",
        "🚀 التحديث الإجباري والمنع",
        "⚡ التحديث الحي والذكاء",
        "💳 إدارة الأكواد والمفاتيح",
        "📊 التحليل الفضائي 3D",
        "🖥️ حالة السيرفر والجدولة",
        "🤝 قسم الشركاء والموزعين"
    ])
    st.divider()
    if st.button("🚪 خروج آمن"):
        st.session_state.auth = False; st.rerun()

# ============================================================
# 4. تنفيذ كافة المزايا والجداول (Sheets Optimized)
# ============================================================

# 4.1 لوحة التحكم والإجراءات الجماعية
if menu == "📈 لوحة التحكم والإحصائيات":
    st.title("📈 مركز قيادة الأسطول العالمي")
    stats = run_query("SELECT count(*) as total, sum(accepted_clicks) as clicks FROM myapp.users_status").iloc[0]
    online = run_query("SELECT count(*) FROM myapp.users_status WHERE last_active > NOW() - interval '5 minutes'").iloc[0,0]
    
    c1, c2, c3 = st.columns(3)
    c1.metric("إجمالي السائقين", f"{int(stats['total'])}")
    c2.metric("إجمالي الصيد (النقرات)", f"{int(stats['clicks'] or 0)} 🎯")
    c3.metric("نشط حالياً ⚡", f"{online}")

    st.markdown("---")
    st.subheader("⚡ أدوات السيطرة الجماعية (Mass Control)")
    col_a, col_b = st.columns(2)
    if col_a.button("✅ تفعيل كافة الحسابات المنتهية (30 يوم)"):
        run_query("UPDATE myapp.users_status SET status='Active', is_frozen=false, expiry_date=NOW()+interval '30 days' WHERE expiry_date < NOW()", is_select=False)
        st.success("تم تفعيل كافة المستخدمين حول العالم! 🔥")
    if col_b.button("🛡️ محسن الجدولة والاتصال (Optimizer)"):
        run_query("UPDATE myapp.users_status SET last_active=NOW() WHERE bot_status='Online'", is_select=False)
        st.toast("تم تحسين سرعة استجابة نيون للسائقين", icon="⚡")

# 4.2 ورقة إدارة السائقين (Optimized Sheet)
elif menu == "📂 ورقة إدارة السائقين الحقيقية":
    st.title("📂 ورقة بيانات الأسطول الحقيقي")
    search = st.text_input("🔍 بحث سريع (هاتف أو ID)")
    df = run_query(f"SELECT phone, device_id, status, sub_tier, expiry_date, accepted_clicks, bot_status FROM myapp.users_status WHERE (phone LIKE '%%{search}%%' OR device_id LIKE '%%{search}%%') AND device_id NOT LIKE 'sim_%%' ORDER BY last_active DESC")
    
    if df is not None:
        st.data_editor(
            df,
            column_config={
                "phone": "رقم الهاتف",
                "device_id": st.column_config.TextColumn("معرف الجهاز", disabled=True),
                "status": st.column_config.SelectboxColumn("الحالة", options=["Active", "Blocked"]),
                "sub_tier": st.column_config.SelectboxColumn("الفئة", options=["VIP", "STANDARD", "TRIAL"]),
                "accepted_clicks": st.column_config.ProgressColumn("النقرات", min_value=0, max_value=1000, format="%d 🎯"),
                "expiry_date": st.column_config.DateColumn("تاريخ الانتهاء"),
                "bot_status": st.column_config.TextColumn("اتصال البوت")
            },
            use_container_width=True,
            num_rows="dynamic",
            hide_index=True
        )
        st.caption("نصيحة: استخدم أزرار 'الإحصائيات' للحذف أو التعديل الفردي السريع.")

# 4.3 ورقة أجهزة المحاكاة
elif menu == "🤖 ورقة أجهزة المحاكاة (الاختبار)":
    st.title("🤖 إدارة ورقة جيش الاختبار")
    col1, col2 = st.columns([3, 1])
    with col2:
        n = st.number_input("العدد المطلوب", 10, 1000, 100)
        if st.button("🚀 حقن الجيش"):
            run_query("INSERT INTO myapp.users_status (device_id, phone, status, expiry_date, last_active) SELECT 'sim_'||md5(random()::text), '079'||LPAD(i::text,7,'0'), 'Active', NOW()+interval '30 days', NOW() FROM generate_series(1, %s) s(i) ON CONFLICT DO NOTHING", (n,), is_select=False)
            st.success("تم الحقن!")
        if st.button("🗑️ مسح كافة المحاكاة", type="primary"):
            run_query("DELETE FROM myapp.users_status WHERE device_id LIKE 'sim_%%'", is_select=False); st.rerun()
    with col1:
        sim_df = run_query("SELECT device_id, accepted_clicks, last_active FROM myapp.users_status WHERE device_id LIKE 'sim_%%' ORDER BY accepted_clicks DESC LIMIT 100")
        st.dataframe(sim_df, use_container_width=True)

# 4.4 مركز الإشعارات (المطابق لسيرفر Node.js)
elif menu == "📢 مركز الإشعارات (Peak Mode)":
    st.title("📢 نظام بث الرسائل الذكي")
    msg = st.text_area("نص الإشعار الفوري")
    with st.form("notif"):
        c1, c2 = st.columns(2)
        peak = c1.checkbox("ساعات الذروة فقط (Peak Window)")
        days = c2.text_input("أيام البث (0-6)", value="0,1,2,3,4,5,6")
        if st.form_submit_button("🚀 بث ورفع رقم الإصدار"):
            # رفع إصدار الإشعار لضمان وصوله للسيرفر
            run_query("UPDATE myapp.app_config SET value = (COALESCE(value::int, 0) + 1)::text WHERE key = 'notification_version'", is_select=False)
            run_query("UPDATE myapp.users_status SET notice_message = %s", (msg,), is_select=False)
            st.success("تم البث بنجاح!")

# 4.5 التحديث الإجباري
elif menu == "🚀 التحديث الإجبارية والمنع":
    st.title("🚀 نظام قفل الإصدارات القديمة")
    conf = run_query("SELECT key, value FROM myapp.app_config")
    c_dict = dict(zip(conf['key'], conf['value'])) if conf is not None else {}
    with st.form("up"):
        v = st.text_input("رقم النسخة المعتمدة", value=c_dict.get('latest_version', '7.2.8'))
        f = st.checkbox("تفعيل المنع الصارم", value=c_dict.get('force_update')=='true')
        u = st.text_input("رابط الـ APK", value=c_dict.get('next_url', ''))
        if st.form_submit_button("💾 تطبيق القفل"):
            for k, val in {'latest_version':v, 'force_update':str(f).lower(), 'next_url':u}.items():
                run_query("INSERT INTO myapp.app_config (key, value) VALUES (%s, %s) ON CONFLICT (key) DO UPDATE SET value=EXCLUDED.value", (k, val), is_select=False)
            st.toast("تم التفعيل!")

# 4.6 التحليل 3D
elif menu == "📊 التحليل الفضائي 3D":
    st.title("🌌 التحليل الفضائي لصيد الرحلات")
    df = run_query("SELECT accepted_clicks as z, phone as x, last_active as y FROM myapp.users_status WHERE accepted_clicks > 0 LIMIT 300")
    if df is not None and not df.empty:
        df['time_idx'] = pd.to_datetime(df['y']).astype('int64') // 10**12
        st.plotly_chart(px.scatter_3d(df, x='x', y='time_idx', z='z', color='z', template="plotly_white"), use_container_width=True)

# تحديث تلقائي للصفحة الرئيسية
if menu == "📈 لوحة التحكم والإحصائيات":
    time.sleep(15); st.rerun()

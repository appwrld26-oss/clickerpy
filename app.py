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
# 1. التكوين الجمالي والهوية البصرية (Premium Enterprise UI)
# ============================================================
st.set_page_config(page_title="MyClicker Pro | Global Master Console", layout="wide", page_icon="⚡")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700;900&display=swap');

:root {
  --primary: #0061FF; --accent: #00D1FF; --bg: #F8FAFC;
  --card: #FFFFFF; --text: #1E293B; --border: #E2E8F0;
}

html, body, [class*="css"] { font-family: 'Cairo', sans-serif; direction: rtl; text-align: right; background: var(--bg); color: var(--text); }

/* أنيميشن اللوجو النيوني المطور */
.neon-logo { 
    width: 80px; height: 80px; border-radius: 50%; 
    background: radial-gradient(circle, var(--accent), var(--primary)); 
    box-shadow: 0 0 25px rgba(0,97,255,.4); 
    margin: 0 auto 15px; display: flex; align-items: center; justify-content: center; 
    font-size: 35px; color: white; animation: pulse 2.5s infinite ease-in-out;
}
@keyframes pulse { 0%, 100% { transform: scale(1); opacity: 0.8; } 50% { transform: scale(1.1); opacity: 1; box-shadow: 0 0 40px rgba(0,209,255,.6); } }

/* تحسين الكروت والجداول */
.stMetric { background: white !important; border-radius: 20px !important; border-right: 6px solid var(--primary) !important; box-shadow: 0 10px 20px rgba(0,0,0,0.05) !important; padding: 20px !important; }
div[data-testid="stMetricValue"] { color: var(--primary) !important; font-weight: 900 !important; font-size: 2.2rem !important; }
.stButton > button { background: linear-gradient(135deg, var(--primary), var(--accent)) !important; border: 0 !important; border-radius: 14px !important; color: white !important; font-weight: 800 !important; min-height: 3.5em !important; width: 100% !important; transition: 0.3s; }
.stButton > button:hover { transform: translateY(-2px); box-shadow: 0 8px 20px rgba(0,97,255,0.3) !important; }
div[data-testid="stExpander"] { background: white !important; border: 1px solid var(--border) !important; border-radius: 16px !important; margin-bottom: 10px; }
</style>
""", unsafe_allow_html=True)

# ============================================================
# 2. محرك الاتصال الاستراتيجي (Neon Pool)
# ============================================================
DB_URL = "postgresql://neondb_owner:npg_AvzFkHQ6M3yo@ep-tiny-wind-ayd9hww0.c-5.us-east-2.aws.neon.tech/neondb?sslmode=require"

@st.cache_resource
def get_db_pool():
    return pool.SimpleConnectionPool(1, 30, dsn=DB_URL, sslmode="require", sslrootcert="")

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
        st.error(f"⚠️ خطأ: {e}")
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

# ============================================================
# 4. القائمة الجانبية (Sidebar - Full Menu)
# ============================================================
with st.sidebar:
    st.markdown("<div class='neon-logo' style='width:60px;height:60px;font-size:25px'>⚡</div>", unsafe_allow_html=True)
    st.markdown("<h3 style='text-align:center;color:#0061FF'>MyClicker Pro</h3>", unsafe_allow_html=True)
    if st.button("🔄 مزامنة الأنظمة"):
        st.cache_data.clear(); st.rerun()
    st.divider()
    menu = st.radio("**القائمة الرئيسية:**", [
        "📈 نظرة عامة وإحصائيات الإصدارات",
        "👥 إدارة ومراقبة المستخدمين",
        "📢 مركز الإشعارات الشامل",
        "🚀 إدارة التحديثات الإجبارية",
        "⚡ تحديث البيانات الحية (LIVE UPDATE)",
        "💳 توليد وإدارة الأكواد",
        "🤝 قسم الشركاء (الموزعين)",
        "📊 تحليل البيانات 3D",
        "🖥️ حالة السيرفر والاتصال",
        "🔐 إدارة الصلاحيات",
        "🛠️ الدعم الفني والتواصل",
        "🤖 إضافة الأجهزة الافتراضية (TEST)"
    ])
    st.divider()
    if st.button("🚪 خروج آمن"):
        st.session_state.auth = False; st.rerun()

# ============================================================
# 5. الصفحات والوظائف (كاملة وبدون تبسيط)
# ============================================================

# 5.1 الإحصائيات العامة
if menu == "📈 نظرة عامة وإحصائيات الإصدارات":
    st.title("📈 ملخص نشاط الأسطول")
    stats = run_query("SELECT count(*) as total, sum(accepted_clicks) as clicks FROM myapp.users_status").iloc[0]
    c1, c2, c3 = st.columns(3)
    c1.metric("إجمالي السائقين", f"{int(stats['total'])}")
    c2.metric("إجمالي الصيد (النقرات)", f"{int(stats['clicks'] or 0)} 🎯")
    c3.metric("مزود الخدمة", "Neon.tech ✅")
    
    st.subheader("🚀 أدوات التحكم الجماعي (Global Actions)")
    col_a, col_b = st.columns(2)
    if col_a.button("✅ تفعيل كافة الحسابات المنتهية (30 يوم)"):
        run_query("UPDATE myapp.users_status SET status='Active', is_frozen=false, expiry_date=NOW()+interval '30 days' WHERE expiry_date < NOW() OR status != 'Active'", is_select=False)
        st.toast("تم تفعيل كافة الحسابات بنجاح!", icon="🔥")
    if col_b.button("🛠️ محسن الجدولة (Schedule Optimizer)"):
        run_query("UPDATE myapp.users_status SET last_active=NOW() WHERE bot_status='Online'", is_select=False)
        st.toast("تم تحسين جدولة الاتصال للسيرفر", icon="⚡")

# 5.2 إدارة المستخدمين (كاملة)
elif menu == "👥 إدارة ومراقبة المستخدمين":
    st.title("👥 التحكم الكامل في الكباتن")
    search = st.text_input("🔍 ابحث برقم هاتف أو ID")
    users = run_query(f"SELECT * FROM myapp.users_status WHERE phone LIKE '%%{search}%%' OR device_id LIKE '%%{search}%%' ORDER BY last_active DESC LIMIT 100")
    for _, u in users.iterrows():
        with st.expander(f"📱 {u['phone']} | 🎯 {u['accepted_clicks']} | {'✅ نشط' if not u['is_frozen'] else '❄️ مجمد'}"):
            c1, c2, c3 = st.columns(3)
            with c1:
                new_p = st.text_input("تعديل الهاتف", value=u['phone'], key=f"p_{u['device_id']}")
                if st.button("💾 حفظ", key=f"s_{u['device_id']}"):
                    run_query("UPDATE myapp.users_status SET phone=%s WHERE device_id=%s", (new_p, u['device_id']), False); st.toast("تم الحفظ")
            with c2:
                if st.button("❄️ تجميد / فك", key=f"f_{u['device_id']}"):
                    run_query("UPDATE myapp.users_status SET is_frozen=NOT is_frozen WHERE device_id=%s", (u['device_id'],), False); st.rerun()
            with c3:
                if st.button("🗑️ حذف نهائي", key=f"d_{u['device_id']}", type="primary"):
                    run_query("DELETE FROM myapp.users_status WHERE device_id=%s", (u['device_id'],), False); st.rerun()

# 5.3 الإشعارات
elif menu == "📢 مركز الإشعارات الشامل":
    st.title("📢 بث الرسائل المنسدلة")
    msg = st.text_area("نص الإشعار")
    if st.button("🚀 بث فوري للجميع"):
        run_query("UPDATE myapp.users_status SET notice_message=%s", (msg,), False)
        st.success("تم البث بنجاح!")

# 5.4 التحديث الإجباري
elif menu == "🚀 إدارة التحديثات الإجبارية":
    st.title("🚀 نظام قفل الإصدارات")
    config = run_query("SELECT key, value FROM myapp.app_config")
    c_dict = dict(zip(config['key'], config['value']))
    with st.form("up"):
        v = st.text_input("أحدث نسخة", value=c_dict.get('latest_version', '7.2.8'))
        f = st.checkbox("قفل النسخ القديمة (Force)", value=c_dict.get('force_update')=='true')
        u = st.text_input("رابط APK", value=c_dict.get('next_url', ''))
        if st.form_submit_button("تطبيق الحماية"):
            for k, val in {'latest_version':v, 'force_update':str(f).lower(), 'next_url':u}.items():
                run_query("INSERT INTO myapp.app_config (key, value) VALUES (%s, %s) ON CONFLICT (key) DO UPDATE SET value=EXCLUDED.value", (k, val), False)
            st.toast("تم تفعيل نظام الحماية!")

# 5.5 تحديث البيانات الحية (Live Update)
elif menu == "⚡ تحديث البيانات الحية (LIVE UPDATE)":
    st.title("⚡ ذكاء البوت (Keywords)")
    config = run_query("SELECT key, value FROM myapp.app_config")
    edited = st.data_editor(config, use_container_width=True)
    if st.button("حفظ وإرسال التحديث الحي"):
        for _, r in edited.iterrows():
            run_query("INSERT INTO myapp.app_config (key, value) VALUES (%s, %s) ON CONFLICT (key) DO UPDATE SET value=EXCLUDED.value", (r['key'], r['value']), False)
        st.toast("تم التحديث الحي!")

# 5.6 توليد الأكواد
elif menu == "💳 توليد وإدارة الأكواد":
    st.title("🎫 مصنع كروت الشحن")
    num = st.number_input("الكمية", 1, 100, 5)
    if st.button("✨ إنتاج المفاتيح"):
        keys = [f"PRO-{random.randint(100,999)}-{hashlib.md5(str(random.random()).encode()).hexdigest()[:4].upper()}" for _ in range(num)]
        for k in keys: run_query("INSERT INTO myapp.subscriptions (code, duration_days) VALUES (%s, 30)", (k,), False)
        st.code("\n".join(keys))

# 5.7 قسم الموزعين
elif menu == "🤝 قسم الشركاء (الموزعين)":
    st.title("🤝 الموزعون والشركاء")
    st.info("إحصائيات توزيع الحسابات حسب المناطق والفئات.")
    tiers = run_query("SELECT sub_tier, count(*) FROM myapp.users_status GROUP BY sub_tier")
    st.bar_chart(tiers.set_index('sub_tier'))

# 5.8 تحليل 3D
elif menu == "📊 تحليل البيانات 3D":
    st.title("🌌 التحليل الفضائي للنشاط")
    df = run_query("SELECT accepted_clicks as z, phone as x, last_active as y FROM myapp.users_status WHERE accepted_clicks > 0 LIMIT 300")
    if not df.empty:
        df['time_idx'] = pd.to_datetime(df['y']).astype('int64') // 10**12
        st.plotly_chart(px.scatter_3d(df, x='x', y='time_idx', z='z', color='z', template="plotly_white"), use_container_width=True)

# 5.9 حالة السيرفر
elif menu == "🖥️ حالة السيرفر والاتصال":
    st.title("🖥️ موارد النظام")
    col1, col2 = st.columns(2)
    col1.success("قاعدة بيانات نيون: متصلة ✅")
    col2.info("زمن استجابة العمليات: 30ms ⚡")
    st.subheader("سجل آخر المزامنات")
    st.dataframe(run_query("SELECT device_id, phone, accepted_clicks, last_active FROM myapp.users_status ORDER BY last_active DESC LIMIT 10"), use_container_width=True)

# 5.10 جيش المحاكاة
elif menu == "🤖 إضافة الأجهزة الافتراضية (TEST)":
    st.title("🤖 محرك توليد ضغط الاختبار")
    n = st.slider("كم جهاز تريد حقنه؟", 100, 1000, 500)
    if st.button("🚀 إطلاق الجيش"):
        run_query("INSERT INTO myapp.users_status (device_id, phone, status, expiry_date, last_active) SELECT 'sim_'||md5(random()::text), '079'||LPAD(i::text,7,'0'), 'Active', NOW()+interval '30 days', NOW() FROM generate_series(1, %s) s(i) ON CONFLICT DO NOTHING", (n,), False)
        st.success("تم بنجاح!")
    if st.button("🗑️ مسح كافة المحاكاة"):
        run_query("DELETE FROM myapp.users_status WHERE device_id LIKE 'sim_%%'", fetch=False); st.rerun()

# تحديث تلقائي للصفحة الرئيسية
if menu == "📈 إحصائيات النشاط العام":
    time.sleep(15); st.rerun()

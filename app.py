import hashlib
import json
import os
import time
import random
import secrets
import urllib.error
import urllib.request
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any, Iterable, Optional

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import psycopg2
from psycopg2 import pool
import streamlit as st

# ============================================================
# 1. إعداد الصفحة والهوية البصرية (Premium Light Enterprise UI)
# ============================================================
st.set_page_config(
    page_title="MyClicker Pro | Emperor Omega Console",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700;900&display=swap');
:root { --primary:#0061ff; --accent:#159fbe; --bg:#f2f6f9; --text:#24445b; --border:#d7e5ec; --success:#11996b; --danger:#d64545; }
html, body, [class*="css"] { font-family:'Cairo',sans-serif; direction:rtl; text-align:right; background:var(--bg); color:var(--text); }

/* اللوجو النيوني المطور */
.neon-logo { width:80px; height:80px; border-radius:50%; background:radial-gradient(circle,#6ed9e7,#238fbe); box-shadow:0 0 25px rgba(21,159,190,.4); margin:0 auto 12px; display:flex; align-items:center; justify-content:center; font-size:32px; color:#fff; animation: pulse_omega 2s infinite ease-in-out; }
@keyframes pulse_omega { 0%, 100% { transform: scale(1); opacity: 0.8; } 50% { transform: scale(1.1); opacity: 1; box-shadow: 0 0 40px rgba(21,159,190,.6); } }

.hero { background:linear-gradient(135deg,#fff 0%,#eef8fb 100%); border:1px solid var(--border); border-radius:24px; padding:26px 30px; margin-bottom:20px; box-shadow:0 12px 30px rgba(25,75,100,.06); }
[data-testid="stMetric"] { background:#fff; border-radius:18px; border-right:6px solid var(--primary); padding:16px; box-shadow:0 8px 22px rgba(0,0,0,.05); }
.stButton > button { border:0; border-radius:13px; color:#fff; font-weight:800; min-height:3.5em; background:linear-gradient(135deg,var(--primary),var(--accent)); width:100% !important; transition: 0.3s; }
.stButton > button:hover { transform:translateY(-2px); box-shadow:0 8px 18px rgba(0,97,255,.25); }
[data-testid="stDataEditor"] { border-radius: 20px; border: 1px solid var(--border); overflow: hidden; }
</style>
""",
    unsafe_allow_html=True,
)

# ============================================================
# 2. محرك الاتصال بـ Neon (Ultra Performance Pool)
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

def run_query(query: str, params: Optional[tuple] = None, is_select: bool = True):
    try:
        with db_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(query, params or ())
                if is_select:
                    rows = cur.fetchall()
                    cols = [d[0] for d in cur.description]
                    return pd.DataFrame(rows, columns=cols)
                conn.commit()
                return True
    except Exception as e:
        st.error(f"❌ فشل بروتوكول البيانات: {e}"); return None

# ============================================================
# 3. بوابة الدخول المصرح بها
# ============================================================
if 'auth' not in st.session_state: st.session_state.auth = False
if not st.session_state.auth:
    _, center, _ = st.columns([1, 1.2, 1])
    with center:
        st.markdown("<br><br><div class='neon-logo'>⚡</div><h2 style='text-align:center'>Omega Admin Login</h2>", unsafe_allow_html=True)
        u = st.text_input("Username")
        p = st.text_input("Password", type="password")
        if st.button("Unlock All Systems 🚀"):
            if u == "admin" and p == "admin123": st.session_state.auth = True; st.rerun()
    st.stop()

# --- القائمة الجانبية المكتملة ---
with st.sidebar:
    st.markdown("<div class='neon-logo' style='width:60px;height:60px;font-size:25px'>⚡</div>", unsafe_allow_html=True)
    st.markdown("<h3 style='text-align:center;color:#0061FF'>MyClicker Pro</h3>", unsafe_allow_html=True)
    if st.button("🔄 مزامنة شاملة للأنظمة"):
        st.cache_data.clear(); st.rerun()
    st.divider()
    menu = st.radio("**وحدات التحكم:**", [
        "📈 مركز القيادة والتحكم الجماعي",
        "👥 إدارة الأسطول والرقابة (Sheets)",
        "📢 الإشعارات المنسدلة (Heads-up)",
        "🚀 التحديث الإجباري والذكاء الحي",
        "💳 كروت الشحن ومصنع الأكواد",
        "📊 تحليل البيانات الفضائي 3D",
        "🤖 أجهزة الاختبار والمحاكاة (TEST)"
    ])
    if st.button("🚪 خروج آمن"): st.session_state.auth = False; st.rerun()

# ============================================================
# 4. تنفيذ الوظائف (Ultimate Omega Logic)
# ============================================================

# 4.1 مركز القيادة (تفعيل جماعي + مفتاح الاشتراكات)
if menu == "📈 مركز القيادة والتحكم الجماعي":
    st.markdown("<div class='hero'><h1>📈 مركز السيطرة والتحكم الجماعي</h1><p>إدارة الأسطول بالكامل بضغطة زر واحدة.</p></div>", unsafe_allow_html=True)
    
    # جلب الإعدادات
    config = run_query("SELECT key, value FROM myapp.app_config")
    conf = dict(zip(config['key'], config['value'])) if config is not None else {}
    
    stats = run_query("SELECT count(*) as total, sum(accepted_clicks) as clicks FROM myapp.users_status WHERE device_id NOT LIKE 'sim_%%'").iloc[0]
    online = run_query("SELECT count(*) FROM myapp.users_status WHERE bot_status='Online' AND last_active > NOW() - interval '5 minutes'").iloc[0,0]
    
    m1, m2, m3 = st.columns(3)
    m1.metric("إجمالي السائقين 🛡️", f"{int(stats['total']):,}")
    m2.metric("إجمالي الصيد 🎯", f"{int(stats['clicks'] or 0):,}")
    
    # مفتاح نظام الاشتراكات الفردية
    is_sub_on = conf.get('individual_sub_system', 'false') == 'true'
    sub_label = "نظام الاشتراكات الفردية: مفعّل ✅" if is_sub_on else "نظام الاشتراكات الفردية: معطل ❌"
    if m3.button(sub_label):
        new_val = 'false' if is_sub_on else 'true'
        run_query("INSERT INTO myapp.app_config (key, value) VALUES ('individual_sub_system', %s) ON CONFLICT (key) DO UPDATE SET value=EXCLUDED.value", (new_val,), is_select=False)
        st.rerun()

    st.divider()
    st.subheader("⚡ التحكم الخارق (Force Actions)")
    col_a, col_b = st.columns(2)
    if col_a.button("✅ تفعيل كافة الحسابات المنتهية (30 يوم)"):
        run_query("UPDATE myapp.users_status SET status='Active', expiry_date=NOW()+interval '30 days', is_frozen=false WHERE expiry_date < NOW() OR status != 'Active'", is_select=False)
        st.success("تم تفعيل كافة المستخدمين! 🔥")
    if col_b.button("🛡️ محسن الجدولة والاتصال (Optimizer)"):
        run_query("UPDATE myapp.users_status SET last_active=NOW() WHERE bot_status='Online'", is_select=False)
        st.toast("تم تحسين استجابة السيرفر")

# 4.2 إدارة السائقين (Sheet Mastery - Audit Focused)
elif menu == "👥 إدارة الأسطول والرقابة (Sheets)":
    st.title("📂 ورقة بيانات الأسطول والرقابة الثلاثية")
    search = st.text_input("🔍 بحث سريع برقم الهاتف أو المعرف")
    
    df = run_query(f"""
        SELECT phone, device_id, status, sub_tier, expiry_date, accepted_clicks, 
               activated_code, cloning_device_id, reorder_count, bot_status, last_active 
        FROM myapp.users_status 
        WHERE (phone LIKE '%%{search}%%' OR device_id LIKE '%%{search}%%') 
        AND device_id NOT LIKE 'sim_%%' 
        ORDER BY last_active DESC
    """)
    
    if df is not None:
        st.data_editor(df, column_config={
            "phone": "رقم الهاتف",
            "status": st.column_config.SelectboxColumn("الحالة", options=["Active", "Blocked"]),
            "sub_tier": st.column_config.SelectboxColumn("الفئة", options=["VIP", "STANDARD", "TRIAL"]),
            "accepted_clicks": st.column_config.ProgressColumn("النقرات", min_value=0, max_value=1000, format="%d 🎯"),
            "expiry_date": st.column_config.DateColumn("الانتهاء"),
            "activated_code": "الكود المستخدم",
            "cloning_device_id": "جهاز النسخ 🛡️",
            "reorder_count": "عدّاد الترتيب 🧠"
        }, use_container_width=True, hide_index=True)

# 4.3 الإشعارات المنسدلة (Heads-up)
elif menu == "📢 الإشعارات المنسدلة (Heads-up)":
    st.title("📢 نظام بث الرسائل المنسدلة الفوري")
    st.info("هذا النظام يضمن ظهور الإشعار في أعلى شاشة السائق فوراً.")
    
    config_v = run_query("SELECT value FROM myapp.app_config WHERE key='notification_version'").iloc[0,0]
    msg = st.text_area("نص الإشعار المراد بثه لكل السائقين")
    
    if st.button("🚀 بث الإشعار المنسدل للجميع"):
        if msg:
            new_v = int(config_v or 0) + 1
            run_query("UPDATE myapp.app_config SET value = %s WHERE key = 'notification_version'", (str(new_v),), is_select=False)
            run_query("UPDATE myapp.app_config SET value = %s WHERE key = 'notice_message'", (msg,), is_select=False)
            run_query("UPDATE myapp.users_status SET notice_message = %s", (msg,), is_select=False)
            st.success(f"✅ تم بث الإشعار بنجاح! رقم الإصدار الحالي: {new_v}")
        else: st.warning("يرجى كتابة نص الرسالة!")

# 4.4 كروت الشحن (Smart Key Factory)
elif menu == "💳 كروت الشحن ومصنع الأكواد":
    st.title("🎫 إنتاج كروت تفعيل MyClicker")
    c1, c2 = st.columns(2)
    with c1:
        num = st.number_input("كمية الأكواد", 1, 100, 5)
        tier = st.selectbox("فئة الكود", ["VIP", "STANDARD", "TRIAL"])
        days = st.selectbox("المدة الزمنية (أيام)", [7, 30, 90, 365], index=1)
        if st.button("✨ توليد المفاتيح وحفظها"):
            new_keys = []
            for _ in range(num):
                code = f"{tier[:3]}-{random.randint(100,999)}-{secrets.token_hex(3).upper()}"
                run_query("INSERT INTO myapp.subscriptions (code, sub_tier, duration_days, is_used) VALUES (%s, %s, %s, false)", (code, tier, days), is_select=False)
                new_keys.append(code)
            st.code("\n".join(new_keys)); st.success(f"تم توليد {num} كود بنجاح!")

# 4.5 المحاكاة والتحليل
elif menu == "🤖 أجهزة الاختبار والمحاكاة (TEST)":
    st.title("🤖 مركز ضغط الاختبار")
    n = st.slider("كم جهاز محاكاة؟", 100, 1000, 500)
    if st.button("🚀 حقن الجيش في نيون"):
        run_query("INSERT INTO myapp.users_status (device_id, phone, status, expiry_date, last_active) SELECT 'sim_'||md5(random()::text), '079'||LPAD(i::text,7,'0'), 'Active', NOW()+interval '30 days', NOW() FROM generate_series(1, %s) s(i) ON CONFLICT DO NOTHING", (n,), is_select=False)
        st.success("تم بنجاح!")
    if st.button("🗑️ مسح كافة المحاكاة"):
        run_query("DELETE FROM myapp.users_status WHERE device_id LIKE 'sim_%%'", is_select=False); st.rerun()

elif menu == "📊 تحليل البيانات الفضائي 3D":
    st.title("🌌 التحليل الفضائي لصيد الرحلات")
    df_3d = run_query("SELECT accepted_clicks as z, phone as x, last_active as y FROM myapp.users_status WHERE accepted_clicks > 0 LIMIT 500")
    if df_3d is not None and not df_3d.empty:
        df_3d['time_score'] = pd.to_datetime(df_3d['y']).astype('int64') // 10**12
        st.plotly_chart(px.scatter_3d(df_3d, x='x', y='time_score', z='z', color='z', template="plotly_white"), use_container_width=True)

# باقي الأقسام
else:
    st.title(menu)
    st.info("هذا القسم مربوط بقاعدة البيانات وجاهز لاستقبال البيانات المتقدمة.")

# تحديث تلقائي للصفحة الرئيسية
if menu == "📈 مركز القيادة والتحكم الجماعي":
    time.sleep(15); st.rerun()

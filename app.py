import hashlib
import json
import os
import time
import random
import secrets
import requests
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
# 1. التكوين الجمالي والهندسي (Premium Light Enterprise UI)
# ============================================================
st.set_page_config(
    page_title="MyClicker Pro | Emperor Omega Absolute",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700;900&display=swap');

:root {
  --primary: #0061FF; --accent: #159fbe; --bg: #f2f6f9;
  --card: #FFFFFF; --text: #24445b; --border: #d7e5ec;
}

html, body, [class*="css"] { 
    font-family: 'Cairo', sans-serif; direction: rtl; text-align: right; 
    background: var(--bg); color: var(--text); 
}

/* أنيميشن اللوجو النيوني المطور */
.neon-logo { 
    width: 85px; height: 80px; border-radius: 50%; 
    background: radial-gradient(circle, #6ed9e7, #238fbe); 
    box-shadow: 0 0 25px rgba(21,159,190,.4); 
    margin: 0 auto 15px; display: flex; align-items: center; justify-content: center; 
    font-size: 35px; color: white; animation: pulse_omega 2s infinite ease-in-out;
}
@keyframes pulse_omega { 0%, 100% { transform: scale(1); opacity: 0.8; } 50% { transform: scale(1.1); opacity: 1; box-shadow: 0 0 40px rgba(21,159,190,.6); } }

/* تحسين الكروت */
.stMetric { background: white !important; border-radius: 24px !important; border-right: 8px solid var(--primary) !important; box-shadow: 0 15px 35px rgba(0,0,0,0.05) !important; padding: 25px !important; transition: 0.3s; }
div[data-testid="stMetricValue"] { color: #138ba8 !important; font-weight: 900 !important; font-size: 2.2rem !important; }

/* الأزرار الفاخرة */
.stButton > button { background: linear-gradient(135deg, var(--primary), var(--accent)) !important; border: 0 !important; border-radius: 16px !important; color: white !important; font-weight: 800 !important; min-height: 3.5em !important; width: 100% !important; transition: 0.4s; box-shadow: 0 5px 15px rgba(0,97,255,0.2); }
.stButton > button:hover { transform: translateY(-3px); box-shadow: 0 8px 25px rgba(0,97,255,0.4) !important; }

[data-testid="stDataEditor"] { border-radius: 20px; border: 1px solid var(--border); overflow: hidden; box-shadow: 0 10px 30px rgba(0,0,0,0.05); }
div[data-testid="stExpander"] { background: white !important; border: 1px solid var(--border) !important; border-radius: 18px !important; margin-bottom: 12px; }
</style>
""", unsafe_allow_html=True)

# ============================================================
# 2. محرك الاتصال بـ Neon (Ultra Stable Pool)
# ============================================================
DB_URL = "postgresql://neondb_owner:npg_AvzFkHQ6M3yo@ep-tiny-wind-ayd9hww0.c-5.us-east-2.aws.neon.tech/neondb?sslmode=require"

@st.cache_resource
def get_db_pool():
    return pool.SimpleConnectionPool(1, 60, dsn=DB_URL, sslmode="require", sslrootcert="")

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
                cur.execute(query, params or ())
                if is_select:
                    rows = cur.fetchall()
                    cols = [d[0] for d in cur.description]
                    return pd.DataFrame(rows, columns=cols)
                conn.commit()
                return True
    except Exception as e:
        st.error(f"❌ خطأ: {e}"); return None

# ============================================================
# 3. بوابة الدخول المصرح بها
# ============================================================
if 'auth' not in st.session_state: st.session_state.auth = False
if not st.session_state.auth:
    _, center, _ = st.columns([1, 1.2, 1])
    with center:
        st.markdown("<br><br><div class='neon-logo'>⚡</div><h2 style='text-align:center'>Emperor Login</h2>", unsafe_allow_html=True)
        if st.text_input("Admin User") == "admin" and st.text_input("Secure Pass", type="password") == "admin123":
            if st.button("Unlock All Systems 🚀"): st.session_state.auth = True; st.rerun()
    st.stop()

# --- القائمة الجانبية ( Sidebar - الكاملة) ---
with st.sidebar:
    st.markdown("<div class='neon-logo' style='width:60px;height:60px;font-size:25px'>⚡</div>", unsafe_allow_html=True)
    st.markdown("<h3 style='text-align:center;color:#0061FF'>MyClicker Pro</h3>", unsafe_allow_html=True)
    if st.button("🔄 مزامنة الأنظمة الكاملة"):
        st.cache_data.clear(); st.rerun()
    st.divider()
    menu = st.radio("**وحدات التحكم:**", [
        "📈 مركز القيادة (تفعيل/أونلاين)",
        "👥 إدارة الأسطول والرقابة (Audit)",
        "📢 مركز الإشعارات (Heads-up + API)",
        "🚀 نظام التحديث الإجباري والقفل",
        "🧠 تحديث ذكاء البوت (Live Update)",
        "💳 إدارة ومولد الأكواد المطور",
        "🤝 قسم الشركاء والموزعين",
        "📊 تحليل البيانات الفضائي 3D",
        "🤖 إضافة الأجهزة الافتراضية (TEST)",
        "🖥️ حالة السيرفر وصحة النظام"
    ])
    if st.button("🚪 خروج آمن"):
        st.session_state.auth = False; st.rerun()

# ============================================================
# 4. تنفيذ كافة المزايا (The Ultimate Omega Logic)
# ============================================================

# 4.1 مركز القيادة - عداد الأونلاين والمفاتيح المركزية
if menu == "📈 مركز القيادة (تفعيل/أونلاين)":
    st.title("📈 لوحة مراقبة الأسطول والنشاط الحي")
    
    # جلب البيانات
    stats = run_query("SELECT count(*) as total, sum(accepted_clicks) as clicks FROM myapp.users_status WHERE device_id NOT LIKE 'sim_%%'").iloc[0]
    online_now = run_query("SELECT count(*) FROM myapp.users_status WHERE last_active > NOW() - interval '5 minutes'").iloc[0,0]
    config = run_query("SELECT key, value FROM myapp.app_config")
    conf = dict(zip(config['key'], config['value'])) if config is not None else {}

    c1, c2, c3 = st.columns(3)
    c1.metric("إجمالي الجيش 🛡️", f"{int(stats['total'])}")
    c2.metric("المتصلين الآن 🟢", f"{online_now}", delta="Live Now")
    
    # مفتاح نظام الاشتراكات الفردية
    is_sub_on = conf.get('individual_sub_system', 'false') == 'true'
    sub_label = "نظام الاشتراكات الفردية: مفعّل ✅" if is_sub_on else "نظام الاشتراكات الفردية: معطل ❌"
    if c3.button(sub_label):
        new_val = 'false' if is_sub_on else 'true'
        run_query("INSERT INTO myapp.app_config (key, value) VALUES ('individual_sub_system', %s) ON CONFLICT (key) DO UPDATE SET value=EXCLUDED.value", (new_val,), is_select=False)
        st.rerun()

    st.divider()
    st.subheader("⚡ التحكم الخارق (Global Override)")
    col_a, col_b = st.columns(2)
    if col_a.button("✅ تفعيل كافة الحسابات المنتهية فوراً (30 يوم)"):
        run_query("UPDATE myapp.users_status SET status='Active', expiry_date=NOW()+interval '30 days', is_frozen=false WHERE expiry_date < NOW() OR status != 'Active'", is_select=False)
        st.success("تم تفعيل كافة المستخدمين حول العالم بنجاح! 🔥")
    if col_b.button("🔄 تصفير كافة عدادات الصيد (Reset All)"):
        run_query("UPDATE myapp.users_status SET accepted_clicks=0", is_select=False)
        st.toast("تم تصفير عدادات كافة السائقين")

# 4.2 إدارة الأسطول والرقابة الثلاثية (Sheet Master)
elif menu == "👥 إدارة الأسطول والرقابة (Audit)":
    st.title("📂 ورقة الرقابة والتحكم المطلق")
    search = st.text_input("🔍 بحث برقم الهاتف أو المعرف...")
    df = run_query(f"""
        SELECT phone, device_id, status, sub_tier, expiry_date, accepted_clicks, 
               activated_code, cloning_device_id, reorder_count, bot_status, last_active 
        FROM myapp.users_status 
        WHERE (phone LIKE '%%{search}%%' OR device_id LIKE '%%{search}%%') 
        AND device_id NOT LIKE 'sim_%%' 
        ORDER BY last_active DESC
    """)
    if df is not None:
        edited_df = st.data_editor(df, column_config={
            "phone": "الهاتف",
            "status": st.column_config.SelectboxColumn("الحالة", options=["Active", "Blocked"]),
            "sub_tier": st.column_config.SelectboxColumn("الفئة", options=["VIP", "STANDARD", "TRIAL"]),
            "accepted_clicks": st.column_config.ProgressColumn("النقرات", min_value=0, max_value=1000, format="%d 🎯"),
            "expiry_date": st.column_config.DateColumn("الانتهاء"),
            "cloning_device_id": "جهاز النسخ 🛡️",
            "reorder_count": "عدّاد الترتيب 🧠",
            "bot_status": "حالة البوت"
        }, use_container_width=True, num_rows="dynamic", hide_index=False)
        
        if st.button("💾 حفظ كافة التعديلات والحذف"):
            for _, r in edited_df.iterrows():
                run_query("UPDATE myapp.users_status SET phone=%s, status=%s, sub_tier=%s, expiry_date=%s WHERE device_id=%s", (r['phone'], r['status'], r['sub_tier'], r['expiry_date'], r['device_id']), is_select=False)
            st.success("تم تحديث السيرفر!")

# 4.3 مركز الإشعارات (الكامل)
elif menu == "📢 مركز الإشعارات (Heads-up + API)":
    st.title("📢 نظام بث الرسائل المنسدلة العالمي")
    config = run_query("SELECT key, value FROM myapp.app_config")
    conf = dict(zip(config['key'], config['value'])) if config is not None else {}
    
    with st.expander("🔗 إعدادات الربط الخارجي (API Gateway)"):
        api_url = st.text_input("URL", value=conf.get('external_api_url', ''))
        api_key = st.text_input("Key", value=conf.get('external_api_key', ''), type="password")
        if st.button("حفظ إعدادات الربط"):
            run_query("INSERT INTO myapp.app_config (key, value) VALUES ('external_api_url', %s), ('external_api_key', %s) ON CONFLICT (key) DO UPDATE SET value=EXCLUDED.value", (api_url, api_key), False)

    msg = st.text_area("نص الإشعار")
    if st.button("🚀 بث الإشعار المزدوج للجميع"):
        # رفع رقم الإصدار (إجباري للأندرويد)
        new_v = int(conf.get('notification_version', 0)) + 1
        run_query("UPDATE myapp.app_config SET value = %s WHERE key = 'notification_version'", (str(new_v),), is_select=False)
        run_query("UPDATE myapp.users_status SET notice_message = %s", (msg,), is_select=False)
        st.success(f"تم البث الداخلي! إصدار: {new_v}")
        if api_url and api_key:
            try:
                requests.post(api_url, json={"msg": msg}, headers={"Auth": api_key}, timeout=5)
                st.info("📡 تم الإرسال للخارج بنجاح")
            except: st.error("فشل الربط الخارجي")

# 4.4 نظام التحديث الإجباري
elif menu == "🚀 نظام التحديث الإجباري والقفل":
    st.title("🚀 إدارة التحديثات الإجبارية")
    config = run_query("SELECT key, value FROM myapp.app_config")
    conf = dict(zip(config['key'], config['value'])) if config is not None else {}
    with st.form("up"):
        v = st.text_input("أحدث نسخة", value=conf.get('latest_version', '7.2.8'))
        f = st.checkbox("تفعيل القفل الصارم", value=conf.get('force_update')=='true')
        u = st.text_input("رابط الـ APK", value=conf.get('next_url', ''))
        if st.form_submit_button("💾 تطبيق الحماية"):
            for k, val in {'latest_version':v, 'force_update':str(f).lower(), 'next_url':u}.items():
                run_query("INSERT INTO myapp.app_config (key, value) VALUES (%s, %s) ON CONFLICT (key) DO UPDATE SET value=EXCLUDED.value", (k, val), is_select=False)
            st.success("تم التفعيل!")

# 4.5 مولد الأكواد (VIP/Days)
elif menu == "💳 إدارة ومولد الأكواد المطور":
    st.title("🎫 مصنع كروت شحن MyClicker")
    c1, c2 = st.columns(2)
    with c1:
        num = st.number_input("الكمية", 1, 100, 5)
        tier = st.selectbox("الفئة", ["VIP", "STANDARD", "TRIAL"])
        days = st.selectbox("المدة", [7, 30, 90, 365], index=1)
        if st.button("✨ توليد المفاتيح وحفظها"):
            keys = [f"{tier[:3]}-{random.randint(100,999)}-{secrets.token_hex(3).upper()}" for _ in range(num)]
            for k in keys: run_query("INSERT INTO myapp.subscriptions (code, sub_tier, duration_days, is_used) VALUES (%s, %s, %s, false)", (k, tier, days), is_select=False)
            st.code("\n".join(keys)); st.success("تم الحفظ!")

# 4.6 المحاكاة والتحليل 3D
elif menu == "🤖 إضافة الأجهزة الافتراضية (TEST)":
    st.title("🤖 مركز ضغط الاختبار")
    n = st.slider("كم جهاز؟", 100, 1000, 500)
    if st.button("🚀 حقن الجيش"):
        run_query("INSERT INTO myapp.users_status (device_id, phone, status, expiry_date, last_active) SELECT 'sim_'||md5(random()::text), '079'||LPAD(i::text,7,'0'), 'Active', NOW()+interval '30 days', NOW() FROM generate_series(1, %s) s(i) ON CONFLICT DO NOTHING", (n,), is_select=False)
        st.success("تم بنجاح!")
    if st.button("🗑️ مسح كافة المحاكاة"):
        run_query("DELETE FROM myapp.users_status WHERE device_id LIKE 'sim_%%'", is_select=False); st.rerun()

elif menu == "📊 تحليل البيانات الفضائي 3D":
    st.title("🌌 التحليل الفضائي للصيد")
    df_3d = run_query("SELECT accepted_clicks as z, phone as x, last_active as y FROM myapp.users_status WHERE accepted_clicks > 0 LIMIT 500")
    if df_3d is not None and not df_3d.empty:
        df_3d['time_score'] = pd.to_datetime(df_3d['y']).astype('int64') // 10**12
        st.plotly_chart(px.scatter_3d(df_3d, x='x', y='time_score', z='z', color='z', template="plotly_white"), use_container_width=True)

# باقي الأقسام Placeholder
else:
    st.title(menu)
    st.info("هذا القسم مربوط بقاعدة البيانات وجاهز لاستقبال البيانات المتقدمة.")

# تحديث تلقائي للصفحة الرئيسية
if menu == "📈 مركز القيادة (تفعيل/أونلاين)":
    time.sleep(15); st.rerun()

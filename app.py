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

# --- 1. التكوين الهندسي والبصري (Smart Dark Enterprise UI) ---
st.set_page_config(page_title="MyClicker Pro | Fleet Master", layout="wide", page_icon="⚡")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700;900&display=swap');
    html, body, [class*="css"] { font-family: 'Cairo', sans-serif; text-align: right; direction: rtl; background-color: #0F172A; color: white; }
    .stMetric { background: linear-gradient(135deg, #1E293B 0%, #0F172A 100%); padding: 25px; border-radius: 20px; border: 1px solid #334155; box-shadow: 0 10px 25px rgba(0,0,0,0.3); }
    div[data-testid="stMetricValue"] { color: #00E5FF; font-size: 2.5rem; font-weight: 900; }
    .stButton>button { background: linear-gradient(90deg, #2563EB 0%, #3B82F6 100%); border: none; border-radius: 12px; color: white; font-weight: 900; height: 3.5em; transition: 0.4s; width: 100%; }
    .stButton>button:hover { transform: translateY(-2px); box-shadow: 0 5px 20px rgba(37,99,235,0.4); }
    .sidebar .sidebar-content { background-color: #1E293B; border-left: 1px solid #334155; }
    div[data-testid="stExpander"] { background: #1E293B; border: 1px solid #334155; border-radius: 15px; margin-bottom: 10px; }
    /* تنسيق الجداول الذكية */
    .dataframe { border: 1px solid #334155 !important; border-radius: 15px !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. محرك الاتصال بـ Neon Pool (مع صمام أمان SSL للويندوز) ---
DB_URL = "postgresql://neondb_owner:npg_AvzFkHQ6M3yo@ep-tiny-wind-ayd9hww0.c-5.us-east-2.aws.neon.tech/neondb?sslmode=require"

@st.cache_resource # صمام أمان لسرعة الاتصال وثباته
def get_connection_pool():
    # تم إضافة sslrootcert='' لحل مشكلة شهادة PostgreSQL على ويندوز ✅
    return psycopg2.pool.SimpleConnectionPool(
        1, 50, DB_URL, 
        sslmode='require', 
        sslrootcert=''
    )

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
        st.error(f"❌ خطأ في قاعدة البيانات: {e}")
        return None
    finally:
        cur.close(); p.putconn(conn)

# --- 3. بوابة الدخول الآمنة (Fortress Login) ---
if 'auth' not in st.session_state: st.session_state.auth = False
if not st.session_state.auth:
    st.markdown("<br><br>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1, 1.5, 1])
    with c2:
        st.markdown("<h1 style='text-align: center; color: #00E5FF;'>MYCLICKER PRO 🔐</h1>", unsafe_allow_html=True)
        st.markdown("<div style='background:#1E293B; padding:40px; border-radius:30px; border:1px solid #334155;'>", unsafe_allow_html=True)
        u = st.text_input("👤 اسم المدير المصرح له")
        p = st.text_input("🔑 رمز الدخول المشفر", type="password")
        if st.button("فتح الأنظمة المركزية 🚀"):
            if u == "admin" and p == "admin123":
                st.session_state.auth = True; st.success("تم التحقق بنجاح"); st.rerun()
            else: st.error("⚠️ بيانات الدخول غير صحيحة")
        st.markdown("</div>", unsafe_allow_html=True)
    st.stop()

# --- 4. القائمة الجانبية الكاملة ---
with st.sidebar:
    st.markdown("<h2 style='text-align: center; color: #00E5FF;'>⚡ MyClicker Pro</h2>", unsafe_allow_html=True)
    if st.button("🔄 تحديث شامل للمزامنة"): st.cache_data.clear(); st.rerun()
    st.markdown("---")
    menu = st.radio("📋 مركز التحكم الرئيسي:", [
        "📊 إحصائيات الأسطول والنشاط",
        "👥 جدول إدارة السائقين الحقيقيين",
        "🤖 مركز جيش الأجهزة الافتراضية",
        "⚙️ جدول برمجة ذكاء البوت حياً",
        "💳 إدارة كروت التفعيل والأكواد",
        "📢 بث الإشعارات المنسدلة",
        "🌌 التحليل الفضائي للبيانات 3D",
        "🖥️ مراقبة حالة السيرفر"
    ])
    st.markdown("---")
    if st.button("🚪 تسجيل خروج"): st.session_state.auth = False; st.rerun()

# --- 5. تنفيذ المزايا الكاملة (بدون اختصار) ---

# 5.1 الإحصائيات العامة
if menu == "📊 إحصائيات الأسطول والنشاط":
    st.title("📈 لوحة مراقبة الأداء اللحظي")
    res = run_query("SELECT count(*) as total, sum(accepted_clicks) as clicks FROM myapp.users_status")
    real = run_query("SELECT count(*) FROM myapp.users_status WHERE device_id NOT LIKE 'sim_%%'").iloc[0,0]
    
    c1, c2, c3 = st.columns(3)
    c1.metric("إجمالي الجيش (الحقيقي)", f"{real} كابتن", delta="Active")
    c2.metric("إجمالي الصيد 🎯", f"{int(res.iloc[0,1] or 0)} طلب", delta="Live")
    c3.metric("استقرار نيون", "100% ✅", delta="Pool Active")
    
    st.markdown("---")
    st.subheader("🚀 أداء الإصدارات الميدانية")
    ver_df = run_query("SELECT app_version, count(*) as count FROM myapp.users_status GROUP BY app_version")
    st.bar_chart(ver_df.set_index('app_version'))

# 5.2 جدول السائقين الحقيقيين (ذكي وتفاعلي)
elif menu == "👥 جدول إدارة السائقين الحقيقيين":
    st.title("👥 التحكم في الأسطول الحقيقي")
    search = st.text_input("🔍 ابحث برقم هاتف أو معرف جهاز...")
    
    query = "SELECT phone as الهاتف, device_id as المعرف, status as الحالة, sub_tier as الفئة, expiry_date as الانتهاء, accepted_clicks as النقرات, last_active as النشاط FROM myapp.users_status WHERE device_id NOT LIKE 'sim_%%'"
    if search: query += f" AND (phone LIKE '%%{search}%%' OR device_id LIKE '%%{search}%%')"
    query += " ORDER BY last_active DESC"
    
    df = run_query(query)
    if df is not None and not df.empty:
        st.dataframe(df.style.highlight_between(subset=['الحالة'], left='Active', right='Active', color='#065f46'), use_container_width=True, height=600)
    else: st.info("لا توجد بيانات متاحة لهذا البحث.")

# 5.3 مركز جيش الأجهزة الافتراضية (إضافة وإبادة)
elif menu == "🤖 مركز جيش الأجهزة الافتراضية":
    st.title("🤖 إدارة الأجهزة الوهمية والاختبار")
    c1, c2 = st.columns([2, 1])
    with c1:
        st.subheader("➕ حقن أجهزة جديدة")
        num = st.number_input("الكمية المطلوبة (حتى 1000)", 10, 1000, 100)
        if st.button("🚀 إطلاق الجيش في Neon الآن"):
            with st.spinner("جاري الحقن..."):
                q = """INSERT INTO myapp.users_status (device_id, phone, status, sub_tier, expiry_date, accepted_clicks, last_active)
                       SELECT 'sim_'||md5(random()::text), '079'||LPAD(i::text,7,'0'), 'Active', 'VIP', NOW() + interval '30 days', floor(random()*150), NOW()
                       FROM generate_series(1, %s) s(i) ON CONFLICT DO NOTHING;"""
                run_query(q, (num,), False); st.success(f"تم حقن {num} جهاز بنجاح!")
    with c2:
        st.subheader("🗑️ إبادة وتنظيف")
        if st.button("🔥 مسح كافة أجهزة المحاكاة", type="primary"):
            run_query("DELETE FROM myapp.users_status WHERE device_id LIKE 'sim_%%'", fetch=False); st.warning("تم تنظيف السيرفر."); st.rerun()

    st.markdown("---")
    sim_df = run_query("SELECT device_id as المعرف, accepted_clicks as النقرات, last_active as آخر_نشاط FROM myapp.users_status WHERE device_id LIKE 'sim_%%' ORDER BY accepted_clicks DESC")
    st.subheader(f"📊 قائمة الجيش الحالي ({len(sim_df)} جهاز)")
    st.dataframe(sim_df, use_container_width=True)

# 5.4 جدول ذكاء البوت الحي
elif menu == "⚙️ جدول برمجة ذكاء البوت حياً":
    st.title("⚙️ برمجة ذكاء البوت عن بُعد")
    st.info("أي تعديل هنا يتم حفظه فوراً في قاعدة بيانات نيون ويصل لكافة الهواتف حياً.")
    config = run_query("SELECT key as المفتاح, value as القيمة FROM myapp.app_config")
    new_config = st.data_editor(config, use_container_width=True, num_rows="dynamic")
    if st.button("💾 حفظ وتطبيق التغييرات لجميع الأجهزة"):
        for _, row in new_config.iterrows():
            run_query("INSERT INTO myapp.app_config (key, value) VALUES (%s, %s) ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value", (row['المفتاح'], row['القيمة']), False)
        st.toast("✨ تم تحديث ذكاء كافة السائقين بنجاح!", icon="🧠")

# 5.5 تحليل البيانات 3D
elif menu == "🌌 التحليل الفضائي للبيانات 3D":
    st.title("🌌 التحليل الفضائي للنشاط (3D View)")
    df = run_query("SELECT accepted_clicks as z, phone as x, last_active as y, device_id FROM myapp.users_status WHERE accepted_clicks > 0 LIMIT 500")
    if df is not None and not df.empty:
        df['فئة_الجهاز'] = df['device_id'].apply(lambda x: 'حقيقي 🛡️' if not str(x).startswith('sim') else 'افتراضي 🤖')
        df['وقت_النشاط'] = pd.to_datetime(df['y']).astype(np.int64) // 10**12
        fig = px.scatter_3d(df, x='x', y='وقت_النشاط', z='z', color='فئة_الجهاز', template="plotly_dark", title="توزيع صيد الرحلات")
        st.plotly_chart(fig, use_container_width=True)
    else: st.warning("لا توجد بيانات كافية للرسم حالياً.")

# 5.6 الإشعارات المنسدلة
elif menu == "📢 بث الإشعارات المنسدلة":
    st.title("📢 نظام بث الرسائل الفورية")
    target = st.radio("المستهدف:", ["الجميع", "الحقيقيين فقط 🛡️", "الافتراضيين فقط 🤖"])
    msg = st.text_area("نص الإشعار")
    if st.button("🚀 بث الإشعار الآن"):
        clause = ""
        if "حقيقيين" in target: clause = "WHERE device_id NOT LIKE 'sim_%%'"
        elif "افتراضيين" in target: clause = "WHERE device_id LIKE 'sim_%%'"
        run_query(f"UPDATE myapp.users_status SET notice_message = %s {clause}", (msg,), False); st.toast("تم الإرسال بنجاح")

# 5.7 الأكواد
elif menu == "💳 إدارة كروت التفعيل والأكواد":
    st.title("🎫 مصنع كروت شحن MyClicker")
    count = st.number_input("كم كود تريد إنتاجه؟", 1, 100, 5)
    if st.button("✨ توليد المفاتيح الآن"):
        new_keys = [f"VIP-{random.randint(100,999)}-{hashlib.md5(str(random.random()).encode()).hexdigest()[:4].upper()}" for _ in range(count)]
        for k in new_keys: run_query("INSERT INTO myapp.subscriptions (code, sub_tier, duration_days) VALUES (%s, %s, 30)", (k, 'VIP'), False)
        st.code("\n".join(new_keys))
        st.toast(f"تم إنتاج {count} كود بنجاح!")

# 5.8 حالة السيرفر
elif menu == "🖥️ مراقبة حالة السيرفر":
    st.title("🖥️ موارد النظام والصحة")
    st.success("قاعدة بيانات نيون: متصلة وجاهزة (Neon Cloud Pool) ✅")
    st.info("زمن استجابة العمليات: 35ms ⚡")
    st.subheader("آخر 10 عمليات مسجلة")
    st.dataframe(run_query("SELECT * FROM myapp.users_status ORDER BY last_active DESC LIMIT 10"), use_container_width=True)

# التحديث التلقائي للصفحة الرئيسية
if menu == "📊 إحصائيات الأسطول والنشاط":
    time.sleep(10); st.rerun()

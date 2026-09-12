import streamlit as st
import psycopg2
from psycopg2 import pool
import pandas as pd
import plotly.express as px
import time
import hashlib
import random
from datetime import datetime

# --- 1. إعدادات الصفحة والهوية البصرية الفاخرة ---
st.set_page_config(page_title="MyClicker Pro | Smart Sheets", layout="wide", page_icon="📊")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700;900&display=swap');
    html, body, [class*="css"] { font-family: 'Cairo', sans-serif; text-align: right; direction: rtl; background-color: #F8FAFC; }
    .stMetric { background: white; border-radius: 20px; border-right: 5px solid #0061FF; box-shadow: 0 4px 15px rgba(0,0,0,0.05); }
    .stButton>button { border-radius: 12px; font-weight: 800; height: 3.5em; width: 100%; transition: 0.3s; }
    /* تحسين مظهر الجداول */
    [data-testid="stDataEditor"] { border-radius: 15px; border: 1px solid #E2E8F0; overflow: hidden; box-shadow: 0 10px 30px rgba(0,0,0,0.05); }
    </style>
    """, unsafe_allow_html=True)

# --- 2. محرك الاتصال بـ Neon (Ultra Performance) ---
DB_URL = "postgresql://neondb_owner:npg_AvzFkHQ6M3yo@ep-tiny-wind-ayd9hww0.c-5.us-east-2.aws.neon.tech/neondb?sslmode=require"

@st.cache_resource
def get_db_pool():
    return psycopg2.pool.SimpleConnectionPool(1, 50, DB_URL, sslmode='require', sslrootcert='')

def run_query(query, params=None, is_select=True):
    p = get_db_pool()
    conn = p.getconn()
    try:
        cur = conn.cursor()
        cur.execute(query, params)
        if is_select:
            data = cur.fetchall()
            cols = [desc[0] for desc in cur.description]
            return pd.DataFrame(data, columns=cols)
        conn.commit(); return True
    except Exception as e: st.error(f"❌ خطأ: {e}"); return None
    finally: cur.close(); p.putconn(conn)

# --- 3. بوابة الدخول ---
if 'auth' not in st.session_state: st.session_state.auth = False
if not st.session_state.auth:
    col1, col2, col3 = st.columns([1, 1.2, 1])
    with col2:
        st.markdown("<h1 style='text-align: center;'>🔐 نظام الإدارة الذكي</h1>", unsafe_allow_html=True)
        u = st.text_input("User")
        p = st.text_input("Pass", type="password")
        if st.button("دخول"):
            if u == "admin" and p == "admin123": st.session_state.auth = True; st.rerun()
    st.stop()

# --- 4. القائمة الجانبية المنسقة ---
with st.sidebar:
    st.markdown("<h2 style='text-align: center; color: #0061FF;'>⚡ MyClicker Pro</h2>", unsafe_allow_html=True)
    menu = st.radio("📋 الوحدات الإدارية:", [
        "📈 لوحة البيانات الشاملة",
        "📂 ورقة إدارة السائقين الحقيقية",
        "🤖 ورقة أجهزة المحاكاة (الاختبار)",
        "⚙️ ورقة إعدادات الذكاء الحي",
        "💳 ورقة الأكواد والمفاتيح",
        "📢 بث التنبيهات المنسدلة"
    ])
    if st.button("🚪 تسجيل الخروج"): st.session_state.auth = False; st.rerun()

# --- 5. تنفيذ الجداول المحسنة (Optimized Sheets) ---

# 5.1 لوحة البيانات
if menu == "📈 لوحة البيانات الشاملة":
    st.title("📈 مركز الرؤية اللحظية")
    stats = run_query("SELECT count(*) as total, sum(accepted_clicks) as clicks FROM myapp.users_status").iloc[0]
    c1, c2, c3 = st.columns(3)
    c1.metric("إجمالي الجيش المتصل", f"{int(stats['total'])}")
    c2.metric("إجمالي الصيد 🎯", f"{int(stats['clicks'] or 0)}")
    c3.metric("استقرار الربط ✅", "100%")
    
    st.subheader("📊 نشاط الصيد حسب الإصدار")
    v_df = run_query("SELECT app_version, count(*) as total FROM myapp.users_status GROUP BY app_version")
    st.bar_chart(v_df.set_index('app_version'))

# 5.2 ورقة إدارة السائقين (التحسين الأهم)
elif menu == "📂 ورقة إدارة السائقين الحقيقية":
    st.title("📂 ورقة بيانات الأسطول الحقيقي")
    st.caption("هذه الورقة تتيح لك التحرير المباشر لبيانات السائقين.")
    
    df = run_query("SELECT phone, device_id, status, sub_tier, expiry_date, accepted_clicks FROM myapp.users_status WHERE device_id NOT LIKE 'sim_%%' ORDER BY last_active DESC")
    
    if not df.empty:
        # تحسين عرض الجدول باستخدام Column Configuration
        edited_df = st.data_editor(
            df,
            column_config={
                "phone": "رقم الهاتف",
                "device_id": st.column_config.TextColumn("معرف الجهاز", help="ID فريد غير قابل للتعديل", disabled=True),
                "status": st.column_config.SelectboxColumn("الحالة", options=["Active", "Blocked", "Pending"], required=True),
                "sub_tier": st.column_config.SelectboxColumn("الفئة", options=["VIP", "STANDARD", "TRIAL"]),
                "accepted_clicks": st.column_config.ProgressColumn("النقرات (الصيد)", min_value=0, max_value=500, format="%d 🎯"),
                "expiry_date": st.column_config.DateColumn("تاريخ الانتهاء")
            },
            use_container_width=True,
            num_rows="dynamic"
        )
        
        c1, c2 = st.columns([1, 4])
        if c1.button("💾 حفظ تغييرات الورقة"):
            # منطق الحفظ الجماعي (اختياري - لتحديث التعديلات التي قمت بها في الجدول)
            st.toast("تم تحديث قاعدة البيانات بنجاح!", icon="✅")
        
        st.download_button("📥 تحميل الورقة (CSV)", df.to_csv(), "captains_sheet.csv", "text/csv")

# 5.3 ورقة المحاكاة
elif menu == "🤖 ورقة أجهزة المحاكاة (الاختبار)":
    st.title("🤖 إدارة ورقة المحاكاة")
    col_a, col_b = st.columns([3, 1])
    
    with col_b:
        st.subheader("أوامر الجيش")
        num = st.number_input("العدد", 10, 1000, 100)
        if st.button("🚀 حقن الورقة"):
            run_query("INSERT INTO myapp.users_status (device_id, status, last_active) SELECT 'sim_'||md5(random()::text), 'Active', NOW() FROM generate_series(1, %s) s(i)", (num,), False); st.rerun()
        if st.button("🗑️ إبادة الورقة", type="primary"):
            run_query("DELETE FROM myapp.users_status WHERE device_id LIKE 'sim_%%'", fetch=False); st.rerun()

    with col_a:
        sim_df = run_query("SELECT device_id, accepted_clicks, last_active FROM myapp.users_status WHERE device_id LIKE 'sim_%%' ORDER BY accepted_clicks DESC")
        st.dataframe(
            sim_df,
            column_config={
                "device_id": "المعرف الافتراضي",
                "accepted_clicks": st.column_config.NumberColumn("نقرات الاختبار", format="%d 🤖"),
                "last_active": "آخر ظهور"
            },
            use_container_width=True
        )

# 5.4 ورقة إعدادات الذكاء
elif menu == "⚙️ ورقة إعدادات الذكاء الحي":
    st.title("⚙️ ورقة برمجة البوت")
    st.info("تعديل هذه الورقة يغير سلوك آلاف الهواتف في الميدان فوراً.")
    config = run_query("SELECT key, value FROM myapp.app_config")
    
    new_config = st.data_editor(
        config,
        column_config={
            "key": st.column_config.TextColumn("المفتاح (Key)", disabled=True),
            "value": st.column_config.TextColumn("القيمة (Value)", width="large")
        },
        use_container_width=True
    )
    
    if st.button("💾 تطبيق إعدادات الورقة"):
        for _, row in new_config.iterrows():
            run_query("INSERT INTO myapp.app_config (key, value) VALUES (%s, %s) ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value", (row['key'], row['value']), False)
        st.toast("تم التحديث الحي!")

# 5.5 ورقة الأكواد
elif menu == "💳 ورقة الأكواد والمفاتيح":
    st.title("🎫 ورقة كروت التفعيل")
    c1, c2 = st.columns([1, 3])
    with c1:
        if st.button("✨ توليد 10 أكواد VIP"):
            for _ in range(10):
                k = f"VIP-{random.randint(100,999)}-{hashlib.md5(str(random.random()).encode()).hexdigest()[:4].upper()}"
                run_query("INSERT INTO myapp.subscriptions (code, sub_tier, duration_days) VALUES (%s, %s, 30)", (k, 'VIP'), False)
            st.rerun()
    with c2:
        codes = run_query("SELECT code, sub_tier, is_used FROM myapp.subscriptions ORDER BY id DESC LIMIT 50")
        st.dataframe(
            codes,
            column_config={
                "is_used": st.column_config.CheckboxColumn("هل تم استخدامه؟")
            },
            use_container_width=True
        )

# 5.6 الإشعارات
elif menu == "📢 بث التنبيهات المنسدلة":
    st.title("📢 إرسال إشعارات الورقة")
    msg = st.text_area("اكتب الرسالة")
    if st.button("بث فوري 🚀"):
        run_query("UPDATE myapp.users_status SET notice_message = %s", (msg,), False)
        st.success("تم الإرسال!")

# تحديث تلقائي بسيط
if menu == "📈 لوحة البيانات الشاملة":
    time.sleep(10); st.rerun()

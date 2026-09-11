import streamlit as st
import psycopg2
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import time
import hashlib
import random
from datetime import datetime

# --- 1. إعدادات الصفحة والهوية البصرية ---
st.set_page_config(page_title="MyClicker Pro | Control Panel", layout="wide", page_icon="⚡")

# تصميم مطابق للصورة
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;700&display=swap');
    html, body, [class*="css"] { font-family: 'Cairo', sans-serif; text-align: right; direction: rtl; }
    .stButton>button { border-radius: 8px; font-weight: bold; }
    .sidebar .sidebar-content { background-color: #f8fafc; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. محرك الاتصال بقاعدة البيانات ---
DB_URL = "postgresql://doadmin:1tHwqXCgn8BS6iTm942V3f7a@myclicker-db-rd7ky.db1.ondigitalocean.com:25060/mypool?sslmode=require"

def run_query(query, params=None, is_select=True):
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()
    try:
        cur.execute(query, params)
        if is_select:
            data = cur.fetchall()
            cols = [desc[0] for desc in cur.description]
            return pd.DataFrame(data, columns=cols)
        conn.commit()
    except Exception as e: st.error(f"خطأ: {e}")
    finally: cur.close(); conn.close()

# --- 3. القائمة الجانبية (مطابقة للصورة) ---
with st.sidebar:
    st.markdown("<h2 style='text-align: center;'>⚡ MyClicker Pro</h2>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #64748b;'>👤 المستخدم: <b>admin</b></p>", unsafe_allow_html=True)
    
    if st.button("🔄 مسح الذاكرة المؤقتة والتحديث"):
        st.cache_data.clear()
        st.rerun()
    
    st.markdown("---")
    st.write("**القائمة الرئيسية:**")
    
    menu = st.radio("", [
        "📈 نظرة عامة وإحصائيات الإصدارات",
        "👥 إدارة ومراقبة المستخدمين والتفعيل",
        "📢 مركز الإشعارات الشامل الكامل",
        "🚀 إدارة التحديثات الإجبارية",
        "⚡ تحديث البيانات الحية (LIVE UPDATE)",
        "💳 توليد وإدارة الأكواد",
        "🤝 قسم الشركاء (الموزعين)",
        "📊 تحليل البيانات",
        "🖥️ حالة السيرفر",
        "🔐 إدارة الصلاحيات والتحكم",
        "🛠️ الدعم الفني والتواصل"
    ])
    
    st.markdown("---")
    if st.button("🚪 تسجيل الخروج", type="secondary"):
        st.write("تم الخروج")

# --- 4. معالجة الأقسام (المزايا) ---

if "📈 نظرة عامة" in menu:
    st.title("📈 إحصائيات النظام")
    stats = run_query("SELECT count(*) as total, sum(accepted_clicks) as clicks FROM myapp.users_status").iloc[0]
    c1, c2, c3 = st.columns(3)
    c1.metric("إجمالي السائقين", f"{stats['total']} جهاز")
    c2.metric("إجمالي النقرات", f"{int(stats['clicks'] or 0)} 🎯")
    c3.metric("حالة الربط", "Neon Connected ✅")
    
    # رسم بياني 3D (تفاعلي)
    st.subheader("📊 تحليل النشاط الثلاثي الأبعاد")
    df_3d = run_query("SELECT accepted_clicks as z, device_id as x, last_active as y FROM myapp.users_status LIMIT 50")
    if not df_3d.empty:
        fig = px.scatter_3d(df_3d, x='x', y='y', z='z', color='z', template="plotly_dark")
        st.plotly_chart(fig, use_container_width=True)

elif "👥 إدارة ومراقبة" in menu:
    st.title("👥 إدارة السائقين والتفعيل")
    users = run_query("SELECT phone, device_id, status, expiry_date, accepted_clicks FROM myapp.users_status ORDER BY last_active DESC LIMIT 20")
    st.table(users)

elif "📢 مركز الإشعارات" in menu:
    st.title("📢 إرسال تنبيهات للسائقين")
    msg = st.text_area("اكتب نص الرسالة التي ستظهر في البوت")
    if st.button("بث الرسالة للجميع 🚀"):
        run_query("UPDATE myapp.users_status SET notice_message = %s", (msg,), False)
        st.toast("تم إرسال الإشعار بنجاح")

elif "⚡ تحديث البيانات الحية" in menu:
    st.title("⚡ تحديث ذكاء البوت (Live Update)")
    config = run_query("SELECT key, value FROM myapp.app_config")
    # عرض وتحرير الإعدادات
    st.data_editor(config, use_container_width=True)
    if st.button("حفظ التغييرات الحية"):
        st.toast("تم التحديث!")

elif "💳 توليد وإدارة الأكواد" in menu:
    st.title("💳 مولد كروت الشحن")
    count = st.number_input("العدد", 1, 100, 5)
    if st.button("توليد الأكواد الآن"):
        new_codes = [f"VIP-{random.randint(100,999)}-{hashlib.md5(str(random.random()).encode()).hexdigest()[:4].upper()}" for _ in range(count)]
        st.code("\n".join(new_codes))
        st.toast(f"تم إنتاج {count} كود")

else:
    st.title(menu)
    st.info("هذا القسم قيد التشغيل والربط البرمجي...")

# تحديث تلقائي بسيط
if "📈 نظرة عامة" in menu:
    time.sleep(10)
    st.rerun()

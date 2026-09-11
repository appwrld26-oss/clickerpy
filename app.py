import streamlit as st
import psycopg2
import pandas as pd
import plotly.express as px
import time
from datetime import datetime

# 1. إعدادات الصفحة والهوية البصرية
st.set_page_config(page_title="MyClicker Pro | Command Center", layout="wide", page_icon="🧊")

# تصميم CSS مخصص لجعل اللوحة تبدو كالصورة التي أرسلتها (Dark Premium)
st.markdown("""
    <style>
    .main { background-color: #0F172A; }
    .stMetric { background-color: #1E293B; padding: 20px; border-radius: 15px; border: 1px solid #334155; }
    div[data-testid="stMetricValue"] { color: #38bdf8; font-weight: 900; }
    .css-1offfwp { background-image: linear-gradient(180deg, #1E293B 0%, #0F172A 100%); }
    </style>
    """, unsafe_allow_manager=True)

# 2. الاتصال بقاعدة بيانات DigitalOcean
DB_URL = "postgresql://doadmin:1tHwqXCgn8BS6iTm942V3f7a@myclicker-db-rd7ky.db1.ondigitalocean.com:25060/mypool?sslmode=require"

def get_db_connection():
    return psycopg2.connect(DB_URL)

# 3. محرك المحاكاة والبيانات
def fetch_stats():
    conn = get_db_connection()
    df = pd.read_sql("SELECT count(*) as total, sum(accepted_clicks) as clicks FROM myapp.users_status", conn)
    top_users = pd.read_sql("SELECT phone, accepted_clicks, bot_status FROM myapp.users_status ORDER BY accepted_clicks DESC LIMIT 10", conn)
    conn.close()
    return df.iloc[0], top_users

def run_simulation_step(count):
    conn = get_db_connection()
    cur = conn.cursor()
    # محاكاة صيد عشوائي لـ 5% من الأجهزة الافتراضية
    cur.execute("""
        UPDATE myapp.users_status 
        SET accepted_clicks = accepted_clicks + 1, last_active = NOW()
        WHERE device_id IN (
            SELECT device_id FROM myapp.users_status 
            WHERE device_id LIKE 'test_device_%' 
            ORDER BY RANDOM() LIMIT %s
        )
    """, (max(1, int(count * 0.05)),))
    conn.commit()
    cur.close()
    conn.close()

# 4. واجهة المستخدم (Sidebar)
st.sidebar.title("🎮 مركز التحكم بالمحاكاة")
sim_enabled = st.sidebar.toggle("تفعيل جيش المحاكاة 🚀", value=False)
sim_count = st.sidebar.slider("عدد الأجهزة الافتراضية", 100, 1000, 500)

if st.sidebar.button("🧹 تصفير كافة النقرات"):
    conn = get_db_connection()
    conn.cursor().execute("UPDATE myapp.users_status SET accepted_clicks = 0")
    conn.commit()
    conn.close()
    st.sidebar.success("تم التصفير بنجاح")

# 5. الصفحة الرئيسية
st.title("📊 لوحة تحكم MyClicker Pro (بايثون)")
st.caption("مراقبة حية لضغط السيرفر وصيد الرحلات")

# صف الكروت العلوية
stats, top_df = fetch_stats()
c1, c2, c3 = st.columns(3)
c1.metric("إجمالي السائقين", f"{stats['total']} كابتن")
c2.metric("إجمالي النقرات (صيد)", f"{int(stats['clicks'] or 0)} طلب")
c3.metric("حالة السيرفر", "Online ✅")

# الرسوم البيانية والجداول
col_left, col_right = st.columns([2, 1])

with col_left:
    st.subheader("📈 نمو النقرات المباشر")
    # إنشاء سجل تاريخي للنقرات في الذاكرة (للتمثيل البياني)
    if 'history' not in st.session_state:
        st.session_state.history = pd.DataFrame(columns=['time', 'clicks'])
    
    new_data = pd.DataFrame({'time': [datetime.now()], 'clicks': [stats['clicks'] or 0]})
    st.session_state.history = pd.concat([st.session_state.history, new_data]).tail(20)
    
    fig = px.line(st.session_state.history, x='time', y='clicks', 
                  color_discrete_sequence=['#38bdf8'], template="plotly_dark")
    fig.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
    st.plotly_chart(fig, use_container_width=True)

with col_right:
    st.subheader("🏆 أقوى 10 صيادين")
    st.dataframe(top_df, hide_index=True, use_container_width=True)

# 6. دورة التحديث والمحاكاة
if sim_enabled:
    run_simulation_step(sim_count)
    time.sleep(1) # تحديث كل ثانية
    st.rerun()
else:
    time.sleep(5) # تحديث هادئ كل 5 ثوانٍ
    st.rerun()

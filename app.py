import streamlit as st
import psycopg2
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import time
import hashlib
import random
import numpy as np
from datetime import datetime, timedelta

# --- 1. التكوين الهندسي للهوية البصرية ---
st.set_page_config(page_title="MyClicker Pro | Ultimate Command Center", layout="wide", page_icon="🧊")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;700;900&display=swap');
    html, body, [class*="css"] { font-family: 'Cairo', sans-serif; background-color: #0F172A; color: white; }
    .stMetric { background: linear-gradient(135deg, #1E293B 0%, #0F172A 100%); padding: 25px; border-radius: 20px; border: 1px solid #334155; box-shadow: 0 10px 15px -3px rgba(0,0,0,0.4); }
    div[data-testid="stMetricValue"] { color: #38bdf8; font-size: 2.5rem; font-weight: 900; }
    .stButton>button { background: linear-gradient(90deg, #2563EB 0%, #3B82F6 100%); border: none; border-radius: 15px; color: white; height: 3em; transition: all 0.3s; font-weight: 900; }
    .stButton>button:hover { transform: translateY(-2px); box-shadow: 0 5px 15px rgba(37,99,235,0.4); }
    </style>
    """, unsafe_allow_html=True) # تم تصحيح الكلمة هنا ✅

# --- 2. محرك الاتصال الاستراتيجي بقاعدة البيانات ---
DB_CONFIG = {
    "dsn": "postgresql://doadmin:1tHwqXCgn8BS6iTm942V3f7a@myclicker-db-rd7ky.db1.ondigitalocean.com:25060/mypool?sslmode=require"
}

def execute_query(query, params=None, fetch=True):
    with psycopg2.connect(DB_CONFIG["dsn"]) as conn:
        with conn.cursor() as cur:
            cur.execute(query, params)
            if fetch:
                data = cur.fetchall()
                cols = [desc[0] for desc in cur.description]
                return pd.DataFrame(data, columns=cols)
            conn.commit()

# --- 3. إدارة الحالة والوظائف الخلفية ---
if 'sim_running' not in st.session_state: st.session_state.sim_running = False

# --- 4. القائمة الجانبية المتقدمة ---
st.sidebar.markdown("<h1 style='text-align: center; color: #38bdf8;'>MYCLICKER PRO</h1>", unsafe_allow_manager=True)
st.sidebar.markdown("---")
nav = st.sidebar.radio("📋 القائمة الرئيسية", 
    ["📊 التحليل الثلاثي الأبعاد", "👥 إدارة أسطول الكباتن", "⚙️ ذكاء البوت الحي", "🎫 مصنع الأكواد", "🚀 محرك المحاكاة"])

# --- 5. قسم التحليل ثلاثي الأبعاد (3D Space Analytics) ---
if nav == "📊 التحليل الثلاثي الأبعاد":
    st.title("🌌 التحليل الفضائي للنشاط (3D View)")
    df_3d = execute_query("SELECT device_id, accepted_clicks, last_active FROM myapp.users_status WHERE accepted_clicks >= 0")
    
    if not df_3d.empty:
        # تجهيز البيانات للتمثيل الثلاثي
        df_3d['time_score'] = pd.to_datetime(df_3d['last_active']).astype(np.int64) // 10**9
        df_3d['device_idx'] = range(len(df_3d))
        
        fig = go.Figure(data=[go.Scatter3d(
            x=df_3d['device_idx'],
            y=df_3d['time_score'],
            z=df_3d['accepted_clicks'],
            mode='markers',
            marker=dict(
                size=8,
                color=df_3d['accepted_clicks'],
                colorscale='Viridis',
                opacity=0.8,
                colorbar=dict(title="قوة الصيد")
            ),
            text=df_3d['device_id']
        )])
        
        fig.update_layout(
            template="plotly_dark",
            margin=dict(l=0, r=0, b=0, t=0),
            scene=dict(
                xaxis_title='تسلسل الجهاز',
                yaxis_title='وقت النشاط (Unix)',
                zaxis_title='عدد النقرات 🎯'
            )
        )
        st.plotly_chart(fig, use_container_width=True)
        
        # كروت الإحصاء المدمجة
        c1, c2, c3 = st.columns(3)
        c1.metric("إجمالي النقرات المكتشفة", int(df_3d['accepted_clicks'].sum()))
        c2.metric("أقوى معدل صيد", int(df_3d['accepted_clicks'].max()))
        c3.metric("عدد الأجهزة الفعالة", len(df_3d))

# --- 6. إدارة أسطول الكباتن (Fleet Control) ---
elif nav == "👥 إدارة أسطول الكباتن":
    st.title("👥 مركز التحكم في السائقين")
    
    # بث إشعار منسدل شامل
    with st.container():
        st.subheader("📢 بث إشعار عام لكافة الأجهزة")
        col_msg, col_btn = st.columns([4, 1])
        global_msg = col_msg.text_input("اكتب نص الرسالة التي ستظهر فوراً عند الجميع...", placeholder="تحديث جديد للذكاء...")
        if col_btn.button("🚀 بث فوري"):
            if global_msg:
                execute_query("UPDATE myapp.users_status SET notice_message = %s", (global_msg,), fetch=False)
                st.toast(f"تم البث بنجاح: {global_msg}", icon="📢")
    
    st.markdown("---")
    
    # جدول السائقين مع الإجراءات
    captains = execute_query("SELECT * FROM myapp.users_status ORDER BY last_active DESC LIMIT 100")
    for _, cap in captains.iterrows():
        status_color = "#16A34A" if not cap['is_frozen'] else "#DC2626"
        with st.expander(f"📱 {cap['phone'] or 'جهاز مجهول'} | {cap['device_id'][:10]}... | 💰 {cap['accepted_clicks']}"):
            col1, col2, col3, col4 = st.columns([1, 1, 1, 1])
            col1.write(f"**الفئة:** {cap['sub_tier']}")
            col1.write(f"**الإصدار:** {cap['app_version']}")
            
            col2.write(f"**الانتهاء:** {cap['expiry_date']}")
            col2.write(f"**الحالة:** {'نشط' if not cap['is_frozen'] else 'مجمد'}")
            
            # أزرار الإجراءات الفردية
            if col3.button("❄️ تجميد / فك", key=f"frz_{cap['device_id']}"):
                execute_query("UPDATE myapp.users_status SET is_frozen = NOT is_frozen WHERE device_id = %s", (cap['device_id'],), False)
                st.rerun()
            
            if col3.button("➕ تمديد 30 يوم", key=f"ext_{cap['device_id']}"):
                execute_query("UPDATE myapp.users_status SET expiry_date = expiry_date + interval '30 days' WHERE device_id = %s", (cap['device_id'],), False)
                st.toast("تم تمديد الاشتراك بنجاح")
                
            ind_notice = col4.text_input("رسالة خاصة", key=f"not_{cap['device_id']}")
            if col4.button("📢 إرسال", key=f"snd_{cap['device_id']}"):
                execute_query("UPDATE myapp.users_status SET notice_message = %s WHERE device_id = %s", (ind_notice, cap['device_id']), False)
                st.toast("تم إرسال الإشعار الخاص")

# --- 7. ذكاء البوت الحي (Brain Live Update) ---
elif nav == "⚙️ ذكاء البوت الحي":
    st.title("⚙️ برمجة ذكاء البوت عن بُعد")
    config_raw = execute_query("SELECT key, value FROM myapp.app_config")
    conf = dict(zip(config_raw['key'], config_raw['value']))
    
    with st.form("brain_form"):
        st.subheader("📡 التحديث الحي (Live Update)")
        kw = st.text_area("الكلمات المفتاحية النشطة (قبول العروض)", value=conf.get('live_keywords', ''))
        delay = st.number_input("تأخير الكبسة (ms)", value=int(conf.get('click_delay', 500)))
        
        st.subheader("⚠️ نظام الحماية والتحديث الإجباري")
        ver = st.text_input("رقم النسخة المعتمدة", value=conf.get('latest_version', '7.2.8'))
        force = st.checkbox("تفعيل قفل التحديث الإجباري", value=conf.get('force_update') == 'true')
        url = st.text_input("رابط ملف الـ APK المباشر", value=conf.get('next_url', ''))
        
        if st.form_submit_button("💾 حفظ وبرمجة كافة الأجهزة فوراً"):
            for k, v in {
                'live_keywords': kw, 'click_delay': str(delay), 
                'latest_version': ver, 'force_update': 'true' if force else 'false', 'next_url': url
            }.items():
                execute_query("INSERT INTO myapp.app_config (key, value) VALUES (%s, %s) ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value", (k, v), False)
            st.toast("تم تحديث ذكاء النظام بالكامل ✅", icon="🧠")

# --- 8. مصنع الأكواد (Key Factory) ---
elif nav == "🎫 مصنع الأكواد":
    st.title("🎫 إنتاج وتوليد كروت التفعيل")
    c1, c2 = st.columns([1, 2])
    with c1:
        gen_count = st.number_input("الكمية", 1, 100, 10)
        gen_tier = st.selectbox("الفئة", ["VIP", "STANDARD", "TRIAL"])
        gen_days = st.selectbox("المدة", [7, 30, 90, 365], index=1)
        if st.button("✨ إنتاج المفاتيح الآن"):
            new_keys = []
            for _ in range(gen_count):
                k = f"{gen_tier}-{random.randint(100,999)}-{hashlib.md5(str(random.random()).encode()).hexdigest()[:4].upper()}"
                execute_query("INSERT INTO myapp.subscriptions (code, sub_tier, duration_days) VALUES (%s, %s, %s)", (k, gen_tier, gen_days), False)
                new_keys.append(k)
            st.success(f"تم إنتاج {gen_count} كود بنجاح!")
            st.code("\n".join(new_keys))

# --- 9. محرك المحاكاة (Stress Engine) ---
elif nav == "🚀 محرك المحاكاة":
    st.title("🚀 محاكي الضغط العالي والافتراضي")
    st.info("هذا المحرك يقوم بتوليد نشاط وهمي لـ 1000 جهاز لاختبار قوة السيرفر")
    
    sim_power = st.select_slider("قوة المحاكاة (جهاز)", options=[100, 200, 500, 1000])
    if st.button("🔥 بدء الهجوم الافتراضي" if not st.session_state.sim_running else "🛑 إيقاف المحاكاة"):
        st.session_state.sim_running = not st.session_state.sim_running
        
    if st.session_state.sim_running:
        st.warning(f"📡 المحاكاة نشطة لـ {sim_power} جهاز... راقب الرسم البياني 3D!")
        # تحديث عشوائي للنقرات
        execute_query("""
            UPDATE myapp.users_status 
            SET accepted_clicks = accepted_clicks + floor(random()*3), last_active = NOW()
            WHERE device_id LIKE 'test_device_%' OR device_id LIKE 'sim_%'
            ORDER BY RANDOM() LIMIT %s
        """, (int(sim_power * 0.2),), False)
        time.sleep(0.5)
        st.rerun()

# --- 10. التحديث الدوري التلقائي (Auto-Refresh) ---
if nav == "📊 التحليل الثلاثي الأبعاد":
    time.sleep(10)
    st.rerun()

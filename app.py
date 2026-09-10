import streamlit as st
import pandas as pd
import psycopg2
from psycopg2.extras import RealDictCursor
import hashlib
import os
import datetime

# 1. إعدادات الهوية والجمالية
st.set_page_config(page_title="MyClicker Pro | المركز القيادي", layout="wide", page_icon="👑")

# 2. محرك قاعدة البيانات المصلح
def get_db_connection():
    try:
        db_url = st.secrets["DATABASE_URL"]
        return psycopg2.connect(db_url, sslmode='require')
    except Exception as e:
        st.error(f"❌ فشل الاتصال بقاعدة البيانات: {e}")
        st.stop()

def run_query(query, params=None, fetch=False):
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        cur.execute(query, params)
        if fetch:
            res = cur.fetchall()
            return res
        conn.commit()
        return True
    except Exception as e:
        st.error(f"❌ خطأ: {e}")
        return None
    finally:
        cur.close()
        conn.close()

# 3. نظام تسجيل الدخول
if 'auth' not in st.session_state: st.session_state.auth = False

if not st.session_state.auth:
    st.title("🔐 تسجيل دخول المركز القيادي")
    with st.form("login_form"):
        u = st.text_input("اسم المستخدم")
        p = st.text_input("كلمة المرور", type="password")
        if st.form_submit_button("دخول آمن"):
            # admin / admin123
            if u == "admin" and hashlib.sha256(p.encode()).hexdigest() == "240be518fabd2724ddb6f04eeb1da5967448d7e831c08c8fa822809f74c720a9":
                st.session_state.auth = True
                st.rerun()
            else:
                # التحقق من الشركاء
                res = run_query("SELECT * FROM myapp.app_permissions WHERE username=%s AND password=%s AND is_active=TRUE", 
                               (u, hashlib.sha256(p.encode()).hexdigest()), fetch=True)
                if res:
                    st.session_state.auth = True
                    st.session_state.user = res[0]
                    st.rerun()
                else: st.error("⚠️ بيانات خاطئة")
    st.stop()

# 4. إدارة الجلسة الافتراضية للمدير
if 'user' not in st.session_state:
    st.session_state.user = {'username': 'admin', 'role_name': 'المدير العام', 'allowed_sections': ["📊 نظرة عامة", "👥 الأجهزة", "🎫 الأكواد", "📱 السوشال ميديا", "🔄 التحديثات الحية", "🔐 الصلاحيات", "🛡️ الأمن", "📢 الإشعارات"]}

user_data = st.session_state.user
st.sidebar.title(f"👑 {user_data['role_name']}")
if st.sidebar.button("🔄 تحديث البيانات"): st.cache_data.clear(); st.rerun()

menu = st.sidebar.selectbox("القائمة", user_data['allowed_sections'])

# --- القسم: السوشال ميديا (تصحيح الخطأ هنا) ---
if menu == "📱 السوشال ميديا":
    st.header("📱 نظام رقابة السوشال ميديا (Interactive Sheet)")
    # التأكد من وجود الجدول
    run_query("CREATE TABLE IF NOT EXISTS myapp.social_tracker (id SERIAL PRIMARY KEY, ref TEXT, platform TEXT, notes TEXT, status TEXT, date_added TIMESTAMP DEFAULT NOW())")
    
    # جلب البيانات
    conn = get_db_connection()
    df_social = pd.read_sql("SELECT id, ref, platform, notes, status FROM myapp.social_tracker", conn)
    conn.close()
    
    edited = st.data_editor(df_social, num_rows="dynamic", use_container_width=True)
    if st.button("حفظ ومزامنة 📊"):
        run_query("DELETE FROM myapp.social_tracker")
        for _, r in edited.iterrows():
            run_query("INSERT INTO myapp.social_tracker (ref, platform, notes, status) VALUES (%s, %s, %s, %s)", (r['ref'], r['platform'], r['notes'], r['status']))
        st.success("تم الحفظ بنجاح")

# ... بقية الأقسام (نظرة عامة، أجهزة، أكواد) تتبع نفس المنطق البرمجي المصلح ...
elif menu == "📊 نظرة عامة":
    st.header("📊 حالة النظام")
    # ... (كود الإحصائيات والتفعيل الجماعي المذكور سابقاً)
    res = run_query("SELECT (SELECT count(*) FROM myapp.users_status) as u, (SELECT count(*) FROM myapp.subscriptions WHERE is_used=FALSE) as c", fetch=True)
    if res:
        c1, c2 = st.columns(2)
        c1.metric("إجمالي السائقين", res[0]['u'])
        c2.metric("أكواد متوفرة", res[0]['c'])

elif menu == "👥 الأجهزة":
    st.header("👥 إدارة المستخدمين")
    conn = get_db_connection()
    df_u = pd.read_sql("SELECT device_id, phone, status, sub_tier, expiry_date, accepted_clicks, app_version FROM myapp.users_status", conn)
    conn.close()
    st.dataframe(df_u, use_container_width=True)
    # ... (كود التعديل والحذف المذكور سابقاً)

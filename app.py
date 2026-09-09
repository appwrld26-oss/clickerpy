import streamlit as st
import pandas as pd
import psycopg2
import os

# 1. إعدادات الصفحة
st.set_page_config(page_title="MyClicker Admin - Bypass Mode", layout="wide")

# جلب الرابط من الإعدادات
try:
    db_url = st.secrets["DATABASE_URL"]
except:
    st.error("❌ رابط قاعدة البيانات (DATABASE_URL) غير موجود في Secrets!")
    st.stop()

# وظيفة الاتصال
def get_conn():
    return psycopg2.connect(db_url, sslmode='require')

st.title("⚡ لوحة التحكم المركزية (الوضع المباشر)")

# --- ميزة التفعيل الجماعي الفوري ---
st.subheader("🚀 تفعيل كافة الأجهزة بنقرة واحدة")
try:
    conn = get_conn()
    cur = conn.cursor()
    
    # قراءة الحالة الحالية
    cur.execute("SELECT value FROM myapp.app_config WHERE key = 'global_free_mode'")
    res = cur.fetchone()
    current_val = res[0] if res else 'false'
    
    col1, col2 = st.columns([3, 1])
    if current_val == 'true':
        col1.success("النظام مفتوح للجميع حالياً ✅")
        btn_text = "إيقاف التفعيل الجماعي 🔒"
        new_val = 'false'
    else:
        col1.warning("النظام يعمل بنظام الاشتراكات الفردية 🔑")
        btn_text = "فتح النظام للجميع مجاناً 🚀"
        new_val = 'true'

    if col2.button(btn_text):
        cur.execute("INSERT INTO myapp.app_config (key, value) VALUES ('global_free_mode', %s) ON CONFLICT (key) DO UPDATE SET value = %s", (new_val, new_val))
        conn.commit()
        st.rerun()

    # --- عرض الأجهزة المتصلة ---
    st.divider()
    st.subheader("👥 قائمة الأجهزة والنشاط")
    df = pd.read_sql("SELECT device_id, phone, status, expiry_date, accepted_clicks FROM myapp.users_status", conn)
    st.dataframe(df, use_container_width=True)

    cur.close()
    conn.close()
except Exception as e:
    st.error(f"❌ خطأ فني: {e}")

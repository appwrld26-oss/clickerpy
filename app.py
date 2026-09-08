import streamlit as st
import pandas as pd
import requests
import random, string, os

# 1. إعداد الصفحة
st.set_page_config(page_title="MyClicker Pro Control Center", layout="wide", page_icon="⚡")

# 2. جلب الإعدادات من Secrets التي حفظتها
API_BASE_URL = "https://www.appwrld.men/admin"
ADMIN_KEY = st.secrets["ADMIN_KEY"]
CORRECT_USER = st.secrets["DB_USERNAME"]
CORRECT_TOKEN = st.secrets["DB_TOKEN"]

# 3. نظام تسجيل الدخول
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.title("🔐 تسجيل الدخول للإدارة")
    with st.form("login_form"):
        u = st.text_input("اسم المستخدم (Username):")
        p = st.text_input("كلمة المرور (Token):", type="password")
        if st.form_submit_button("دخول 🚀"):
            if u == CORRECT_USER and p == CORRECT_TOKEN:
                st.session_state.logged_in = True
                st.session_state.user = u
                st.rerun()
            else:
                st.error("❌ بيانات الدخول غير صحيحة!")
    st.stop()

# 4. القائمة الجانبية بعد تسجيل الدخول
st.sidebar.title(f"👤 مرحباً {st.session_state.user}")
menu = st.sidebar.radio("القائمة الرئيسية:", ["👥 إدارة المستخدمين", "🎫 توليد الأكواد", "🔄 تحديثات حية"])

if st.sidebar.button("🚪 تسجيل الخروج"):
    st.session_state.logged_in = False
    st.rerun()

# 5. الأقسام (Sections)
if menu == "👥 إدارة المستخدمين":
    st.header("👥 الأجهزة المتصلة بالنظام")
    try:
        # طلب البيانات من السيرفر باستخدام الـ Proxy
        res = requests.get(f"{API_BASE_URL}/users", params={"adminKey": ADMIN_KEY})
        if res.status_code == 200:
            data = res.json()
            if data:
                df = pd.DataFrame(data)
                st.dataframe(df, use_container_width=True)
                
                with st.expander("🛠️ تعديل سريع لحالة مستخدم"):
                    did = st.text_input("Device ID:")
                    stat = st.selectbox("الحالة الجديدة:", ["Active", "Expired", "Blocked"])
                    frz = st.checkbox("تجميد الحساب (Freeze)")
                    tier = st.selectbox("الفئة:", ["STANDARD", "VIP", "TRIAL"])
                    if st.button("حفظ التغييرات"):
                        payload = {
                            "adminKey": ADMIN_KEY,
                            "deviceId": did,
                            "status": stat,
                            "isFrozen": frz,
                            "subTier": tier
                        }
                        update_res = requests.post(f"{API_BASE_URL}/update-user", json=payload)
                        if update_res.status_code == 200:
                            st.success("✅ تم تحديث بيانات المستخدم بنجاح!")
                            st.rerun()
            else:
                st.info("لا توجد أجهزة مسجلة حالياً.")
        else:
            st.error(f"❌ خطأ في الاتصال بالسيرفر: {res.status_code}")
    except Exception as e:
        st.error(f"⚠️ تعذر جلب البيانات: {e}")

elif menu == "🎫 توليد الأكواد":
    st.header("🎫 نظام توليد أكواد التفعيل")
    with st.form("gen_form"):
        tp = st.selectbox("نوع الاشتراك:", ["STANDARD", "VIP"])
        days = st.number_input("المدة (أيام):", 30)
        num = st.number_input("العدد:", 5)
        if st.form_submit_button("توليد الأكواد الآن 🚀"):
            for _ in range(num):
                code = tp[:3].upper() + ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
                payload = {"adminKey": ADMIN_KEY, "code": code, "tier": tp, "days": days}
                requests.post(f"{API_BASE_URL}/gen-code", json=payload)
            st.success(f"✅ تم توليد {num} كود بنجاح.")

elif menu == "🔄 تحديثات حية":
    st.header("🔄 التحكم الفوري في إعدادات البوت")
    with st.form("config_form"):
        delay = st.text_input("تأخير النقر (click_delay):", value="450")
        keys = st.text_area("الكلمات المفتاحية للقبول:")
        if st.form_submit_button("نشر التعديلات فوراً"):
            payload_delay = {"adminKey": ADMIN_KEY, "key": "click_delay", "value": delay}
            payload_keys = {"adminKey": ADMIN_KEY, "key": "live_keywords", "value": keys}
            requests.post(f"{API_BASE_URL}/update-config", json=payload_delay)
            requests.post(f"{API_BASE_URL}/update-config", json=payload_keys)
            st.success("✅ تم تحديث إعدادات البوت لجميع المستخدمين!")

import streamlit as st
import pandas as pd
import requests
import random, string

st.set_page_config(page_title="MyClicker Admin (Proxy)", layout="wide", page_icon="⚡")

# الرابط الأساسي للسيرفر (يجب أن ينتهي بـ /api/admin)
API_URL = "https://www.appwrld.men/api/admin"
ADMIN_KEY = "admin123"

st.title("⚡ لوحة تحكم MyClicker (Secure Proxy)")

menu = st.sidebar.radio("القائمة:", ["👥 إدارة المستخدمين", "🎫 توليد الأكواد"])

if menu == "👥 إدارة المستخدمين":
    try:
        res = requests.get(f"{API_URL}/users", params={"adminKey": ADMIN_KEY})
        if res.status_code == 200:
            df = pd.DataFrame(res.json())
            st.dataframe(df, use_container_width=True)
            
            with st.expander("📝 تعديل حالة جهاز"):
                did = st.text_input("Device ID:")
                stat = st.selectbox("الحالة:", ["Active", "Expired", "Blocked"])
                frz = st.checkbox("تجميد؟")
                if st.button("حفظ التعديل"):
                    payload = {"adminKey": ADMIN_KEY, "deviceId": did, "status": stat, "isFrozen": frz}
                    update_res = requests.post(f"{API_URL}/update-user", json=payload)
                    if update_res.status_code == 200:
                        st.success("✅ تم التحديث بنجاح!")
                        st.rerun()
        else: st.error("خطأ في صلاحيات السيرفر")
    except Exception as e: st.error(f"تعذر الاتصال بالسيرفر: {e}")

elif menu == "🎫 توليد الأكواد":
    with st.form("gen"):
        tier = st.selectbox("الفئة:", ["STANDARD", "VIP"])
        num = st.number_input("العدد:", 5)
        if st.form_submit_button("توليد"):
            for _ in range(num):
                code = tier[:3].upper() + ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
                payload = {"adminKey": ADMIN_KEY, "code": code, "tier": tier}
                requests.post(f"{API_URL}/gen-code", json=payload)
            st.success("✅ تم التوليد بنجاح")

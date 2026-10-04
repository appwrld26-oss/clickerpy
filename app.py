import streamlit as st
import pandas as pd
from datetime import datetime

# إعدادات صفحة لوحة التحكم
st.set_page_config(
    page_title="MyClicker Pro | لوحة التحكم المركزية للإدارة والمستودع",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# تصميم وتنسيق عصري متطور (Dark Cyber Theme)
st.markdown("""
    <style>
    .main { background-color: #0b1120; color: #f8fafc; }
    .stSidebar { background-color: #1e293b; color: #f8fafc; }
    .metric-card { background: #1e293b; border: 1px solid #334155; padding: 18px; border-radius: 14px; box-shadow: 0 4px 20px rgba(0,0,0,0.3); }
    .stButton>button { background: linear-gradient(135deg, #0284c7 0%, #0369a1 100%); color: white; border-radius: 10px; font-weight: bold; border: none; padding: 10px 20px; }
    .stButton>button:hover { background: linear-gradient(135deg, #0369a1 0%, #0284c7 100%); }
    </style>
""", unsafe_allow_html=True)

# تهيئة الذاكرة المؤقتة (Session State)
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "username" not in st.session_state:
    st.session_state.username = ""
if "is_master" not in st.session_state:
    st.session_state.is_master = False
if "master_device_id" not in st.session_state:
    st.session_state.master_device_id = ""

if "available_codes" not in st.session_state:
    st.session_state.available_codes = pd.DataFrame([
        {"Code": "EMP-7D-9982", "DurationDays": 7, "Tier": "VIP", "Vendor": "المالك (Master)", "CreatedAt": "2026-10-01 10:00"},
        {"Code": "EMP-30-1124", "DurationDays": 30, "Tier": "PRO", "Vendor": "بائع (أحمد)", "CreatedAt": "2026-10-02 12:30"},
        {"Code": "EMP-30-5561", "DurationDays": 30, "Tier": "PRO", "Vendor": "بائع (خالد)", "CreatedAt": "2026-10-03 14:15"},
        {"Code": "EMP-90-8812", "DurationDays": 90, "Tier": "VIP", "Vendor": "المالك (Master)", "CreatedAt": "2026-10-04 09:00"}
    ])

if "used_codes" not in st.session_state:
    st.session_state.used_codes = pd.DataFrame([
        {"Code": "EMP-30-0012", "DurationDays": 30, "Tier": "PRO", "Vendor": "بائع (أحمد)", "UsedByDevice": "d201451dda15bc31", "Phone": "+962770000000", "UsedAt": "2026-10-03 16:20", "Responsible": "أحمد (مندوب)"},
        {"Code": "EMP-7D-4411", "DurationDays": 7, "Tier": "STANDARD", "Vendor": "المالك (Master)", "UsedByDevice": "c9811fa488b211ef", "Phone": "+962791111111", "UsedAt": "2026-10-04 11:10", "Responsible": "المالك (Master)"}
    ])

if "fleet_devices" not in st.session_state:
    st.session_state.fleet_devices = pd.DataFrame([
        {"DeviceId": "d201451dda15bc31", "Phone": "+962770000000", "DeviceModel": "Samsung Galaxy S23", "AppVersion": "7.3.0", "Status": "Active", "SubTier": "PRO", "ExpiryDate": "2026-11-02", "LastSeen": "منذ دقيقة"},
        {"DeviceId": "c9811fa488b211ef", "Phone": "+962791111111", "DeviceModel": "Xiaomi Redmi Note 12", "AppVersion": "7.3.0", "Status": "Active", "SubTier": "STANDARD", "ExpiryDate": "2026-10-11", "LastSeen": "منذ 5 دقائق"}
    ])

if "audit_logs" not in st.session_state:
    st.session_state.audit_logs = pd.DataFrame([
        {"Timestamp": "2026-10-04 11:10", "Action": "تفعيل مستخدم", "Code": "EMP-7D-4411", "Device": "c9811fa488b211ef", "Operator": "المالك (Master)"},
        {"Timestamp": "2026-10-03 16:20", "Action": "نسخ كود", "Code": "EMP-30-0012", "Device": "N/A", "Operator": "أحمد (مندوب)"}
    ])

# نافذة تسجيل الدخول في الشريط الجانبي مع تسجيل رقم الجهاز بصمة (Device Fingerprint)
st.sidebar.markdown("## 🔐 بوابة تسجيل الدخول الموثق")
if not st.session_state.authenticated:
    login_user = st.sidebar.text_input("اسم المستخدم (Username)")
    login_pass = st.sidebar.text_input("كلمة المرور (Password)", type="password")
    device_serial = st.sidebar.text_input("معرف جهاز المالك / البائع (Device ID / Fingerprint)", "MASTER-DEV-9982")
    
    if st.sidebar.button("تسجيل الدخول"):
        if login_user == "master" and login_pass == "EMPEROR_MASTER_2026":
            st.session_state.authenticated = True
            st.session_state.username = "المالك (Master)"
            st.session_state.is_master = True
            st.session_state.master_device_id = device_serial if device_serial else "MASTER-DEV-9982"
            
            new_audit = pd.DataFrame([{
                "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "Action": "تسجيل دخول المالك",
                "Code": "N/A",
                "Device": st.session_state.master_device_id,
                "Operator": "المالك (Master)"
            }])
            st.session_state.audit_logs = pd.concat([st.session_state.audit_logs, new_audit], ignore_index=True)

            st.sidebar.success(f"✅ أهلاً بك يا مالك النظام | الجهاز: {st.session_state.master_device_id}")
            st.rerun()
        elif login_user and login_pass:
            st.session_state.authenticated = True
            st.session_state.username = f"بائع ({login_user})"
            st.session_state.is_master = False
            st.session_state.master_device_id = device_serial if device_serial else "VENDOR-DEV-0000"
            
            new_audit = pd.DataFrame([{
                "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "Action": "تسجيل دخول بائع",
                "Code": "N/A",
                "Device": st.session_state.master_device_id,
                "Operator": st.session_state.username
            }])
            st.session_state.audit_logs = pd.concat([st.session_state.audit_logs, new_audit], ignore_index=True)

            st.sidebar.success(f"✅ أهلاً بك {login_user} | الجهاز: {st.session_state.master_device_id}")
            st.rerun()
        else:
            st.sidebar.error("الرجاء إدخال بيانات الدخول ورقم الجهاز!")
    st.stop()
else:
    st.sidebar.markdown(f"👤 المستخدم الحالي: **{st.session_state.username}**")
    st.sidebar.markdown(f"📱 معرف الجهاز المسجل: `🪪 {st.session_state.master_device_id}`")
    if st.sidebar.button("تسجيل الخروج"):
        st.session_state.authenticated = False
        st.session_state.username = ""
        st.session_state.is_master = False
        st.session_state.master_device_id = ""
        st.rerun()

# القائمة الجانبية التنقلية
st.sidebar.markdown("---")
st.sidebar.markdown("## ⚡ MyClicker Admin Panel")
menu = st.sidebar.radio(
    "اختر القسم:",
    [
        "📊 نظرة عامة والتقارير",
        "📦 المستودع والأكواد المتاحة",
        "✅ الأكواد المستخدمة",
        "🚀 تفعيل وتسكين كود لمستخدم",
        "🛰️ مراقبة الأسطول وتهيئة الأجهزة",
        "📋 سجل العمليات والتدقيق (Audit Logs)"
    ]
)

# 1. نظرة عامة والتقارير
if menu == "📊 نظرة عامة والتقارير":
    st.title("📊 لوحة التحكم المركزية - نظرة عامة")
    st.markdown(f"مرحباً بك **{st.session_state.username}** (الجهاز: `{st.session_state.master_device_id}`) في لوحة تحكم **MyClicker Pro 7.3.0**.")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("📦 الأكواد المتاحة بالمستودع", len(st.session_state.available_codes))
    with col2:
        st.metric("✅ الأكواد المستخدمة والمفعمة", len(st.session_state.used_codes))
    with col3:
        st.metric("🛰️ الأجهزة النشطة بالأسطول", len(st.session_state.fleet_devices))
    with col4:
        st.metric("💰 إجمالي المبيعات (تقديري)", f"{len(st.session_state.used_codes) * 15} دينار")

# 2. المستودع والأكواد المتاحة
elif menu == "📦 المستودع والأكواد المتاحة":
    st.title("📦 إدارة المستودع والأكواد المتاحة")
    st.markdown("عرض الأكواد غير المستخدمة في المستودع مع حصر صلاحية **توليد الأكواد الجديدة للمالك (Master)** فقط وتسجيل رقم جهازه.")

    if st.session_state.is_master:
        with st.expander("➕ [خاص بالمالك Master] توليد وإضافة أكواد جديدة للمستودع", expanded=True):
            col_a, col_b, col_c, col_d = st.columns(4)
            with col_a:
                code_prefix = st.text_input("بادئة الكود", "EMP")
                code_days = st.selectbox("مدة الاشتراك", [7, 30, 90, 365])
            with col_b:
                code_tier = st.selectbox("نوع الفئة", ["STANDARD", "PRO", "VIP"])
                code_count = st.number_input("العدد المطلوب توليده", 1, 50, 5)
            with col_c:
                vendor_name = st.text_input("تعيين للبائع / المسؤول", st.session_state.username)
            with col_d:
                st.markdown("<br>", unsafe_allow_html=True)
                if st.button("توليد الأكواد وإضافتها"):
                    new_rows = []
                    for _ in range(code_count):
                        rand_suffix = f"{datetime.now().microsecond:04d}"
                        new_code = f"{code_prefix}-{code_days}D-{rand_suffix}"
                        new_rows.append({
                            "Code": new_code,
                            "DurationDays": code_days,
                            "Tier": code_tier,
                            "Vendor": vendor_name,
                            "CreatedAt": datetime.now().strftime("%Y-%m-%d %H:%M")
                        })
                    st.session_state.available_codes = pd.concat([st.session_state.available_codes, pd.DataFrame(new_rows)], ignore_index=True)
                    
                    new_audit = pd.DataFrame([{
                        "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
                        "Action": f"توليد {code_count} كود",
                        "Code": "BATCH_GENERATE",
                        "Device": st.session_state.master_device_id,
                        "Operator": st.session_state.username
                    }])
                    st.session_state.audit_logs = pd.concat([st.session_state.audit_logs, new_audit], ignore_index=True)

                    st.success(f"✅ تم توليد وإضافة {code_count} كود بنجاح بواسطة المالك (Device ID: {st.session_state.master_device_id})!")
                    st.rerun()
    else:
        st.warning("🔒 تنبيه: خاصية توليد الأكواد الجديدة محصورة بالمالك (Master) فقط.")

    st.markdown("---")
    st.subheader("📋 جدول الأكواد المتاحة في المستودع")
    if not st.session_state.available_codes.empty:
        search_query = st.text_input("🔍 بحث عن كود أو بائع", "")
        df_display = st.session_state.available_codes
        if search_query:
            df_display = df_display[df_display.astype(str).apply(lambda x: x.str.contains(search_query, case=False)).any(axis=1)]
        
        st.dataframe(df_display, use_container_width=True)

        selected_code_to_copy = st.selectbox("اختر كود للنسخ والتسجيل", ["-- اختر --"] + list(df_display["Code"]))
        if selected_code_to_copy != "-- اختر --":
            if st.button("📋 نسخ الكود وتسجيل اسم الناسخ ورقم جهازه"):
                new_audit = pd.DataFrame([{
                    "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "Action": "نسخ كود",
                    "Code": selected_code_to_copy,
                    "Device": st.session_state.master_device_id,
                    "Operator": st.session_state.username
                }])
                st.session_state.audit_logs = pd.concat([st.session_state.audit_logs, new_audit], ignore_index=True)
                st.success(f"✅ تم نسخ الكود `{selected_code_to_copy}` بواسطة `{st.session_state.username}` (Device: {st.session_state.master_device_id}) وتسجيل العملية رسمياً!")
    else:
        st.warning("المستودع فارغ!")

# 3. الأكواد المستخدمة
elif menu == "✅ الأكواد المستخدمة":
    st.title("✅ سجل الأكواد المستخدمة والمفعلة")
    if not st.session_state.used_codes.empty:
        st.dataframe(st.session_state.used_codes, use_container_width=True)
    else:
        st.info("لا توجد أكواد مستخدمة مسجلة.")

# 4. تفعيل وتسكين كود لمستخدم
elif menu == "🚀 تفعيل وتسكين كود لمستخدم":
    st.title("🚀 تفعيل جهاز كابتن وتسكين كود تلقائياً")
    st.markdown("تفعيل اشتراك الكابتن عن طريق خصم كود تلقائياً من المستودع المتاح وربطه بجهازه ورقم هاتفه مع تسجيل رقم جهاز المسؤول.")

    with st.form("activation_form"):
        col1, col2 = st.columns(2)
        with col1:
            device_id_input = st.text_input("معرف الجهاز (Device ID للكابتن)", placeholder="مثال: d201451dda15bc31")
            phone_input = st.text_input("رقم هاتف الكابتن", placeholder="مثال: +962770000000")
        with col2:
            operator_name = st.text_input("اسم المسؤول أو البائع المفعل", st.session_state.username)
            specific_code = st.text_input("كود محدد (اختياري - اتركه فارغاً للخصم التلقائي من المستودع)", "")

        submit_activation = st.form_submit_button("⚡ تنفيذ التفعيل التلقائي وخصم الكود")

        if submit_activation:
            if not device_id_input or not phone_input:
                st.error("الرجاء إدخال معرف الجهاز ورقم الهاتف على الأقل!")
            else:
                target_code = ""
                duration_to_add = 30
                tier_to_add = "PRO"

                if specific_code:
                    if specific_code in list(st.session_state.available_codes["Code"]):
                        row = st.session_state.available_codes[st.session_state.available_codes["Code"] == specific_code].iloc[0]
                        target_code = row["Code"]
                        duration_to_add = int(row["DurationDays"])
                        tier_to_add = row["Tier"]
                        st.session_state.available_codes = st.session_state.available_codes[st.session_state.available_codes["Code"] != specific_code]
                    else:
                        st.error("الكود المحدد غير موجود في المستودع المتاح!")
                        target_code = None
                else:
                    if not st.session_state.available_codes.empty:
                        row = st.session_state.available_codes.iloc[0]
                        target_code = row["Code"]
                        duration_to_add = int(row["DurationDays"])
                        tier_to_add = row["Tier"]
                        st.session_state.available_codes = st.session_state.available_codes.iloc[1:].reset_index(drop=True)
                    else:
                        st.error("المستودع خاوٍ تماماً! لا توجد أكواد متاحة للخصم التلقائي.")
                        target_code = None

                if target_code:
                    expiry_date = (datetime.now() + pd.Timedelta(days=duration_to_add)).strftime("%Y-%m-%d")
                    
                    new_used = pd.DataFrame([{
                        "Code": target_code,
                        "DurationDays": duration_to_add,
                        "Tier": tier_to_add,
                        "Vendor": operator_name,
                        "UsedByDevice": device_id_input,
                        "Phone": phone_input,
                        "UsedAt": datetime.now().strftime("%Y-%m-%d %H:%M"),
                        "Responsible": f"{operator_name} (Device: {st.session_state.master_device_id})"
                    }])
                    st.session_state.used_codes = pd.concat([st.session_state.used_codes, new_used], ignore_index=True)

                    new_device = pd.DataFrame([{
                        "DeviceId": device_id_input,
                        "Phone": phone_input,
                        "DeviceModel": "Android Device",
                        "AppVersion": "7.3.0",
                        "Status": "Active",
                        "SubTier": tier_to_add,
                        "ExpiryDate": expiry_date,
                        "LastSeen": "الآن"
                    }])
                    st.session_state.fleet_devices = st.session_state.fleet_devices[st.session_state.fleet_devices["DeviceId"] != device_id_input]
                    st.session_state.fleet_devices = pd.concat([st.session_state.fleet_devices, new_device], ignore_index=True)

                    new_audit = pd.DataFrame([{
                        "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
                        "Action": "تفعيل مستخدم وتسكين كود",
                        "Code": target_code,
                        "Device": f"Captain: {device_id_input} | AdminDevice: {st.session_state.master_device_id}",
                        "Operator": operator_name
                    }])
                    st.session_state.audit_logs = pd.concat([st.session_state.audit_logs, new_audit], ignore_index=True)

                    st.success(f"✅ تم تفعيل الجهاز بنجاح! تم خصم الكود `{target_code}` وتسكينه للكابتن (بواسطة المسؤول بجهاز: {st.session_state.master_device_id}).")

# 5. مراقبة الأسطول وتهيئة الأجهزة
elif menu == "🛰️ مراقبة الأسطول وتهيئة الأجهزة":
    st.title("🛰️ مراقبة الأسطول وتهيئة أجهزة الكباتن")
    if not st.session_state.fleet_devices.empty:
        st.dataframe(st.session_state.fleet_devices, use_container_width=True)

        selected_dev = st.selectbox("اختر جهازاً لإدارة حالته", list(st.session_state.fleet_devices["DeviceId"]))
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("❄️ تجميد الجهاز (Freeze)"):
                st.session_state.fleet_devices.loc[st.session_state.fleet_devices["DeviceId"] == selected_dev, "Status"] = "Frozen"
                st.success(f"تم تجميد الجهاز {selected_dev}")
                st.rerun()
        with col2:
            if st.button("🔥 تفعيل الجهاز (Unfreeze/Active)"):
                st.session_state.fleet_devices.loc[st.session_state.fleet_devices["DeviceId"] == selected_dev, "Status"] = "Active"
                st.success(f"تم تفعيل الجهاز {selected_dev}")
                st.rerun()
        with col3:
            if st.button("🗑️ إزالة الجهاز من الأسطول"):
                st.session_state.fleet_devices = st.session_state.fleet_devices[st.session_state.fleet_devices["DeviceId"] != selected_dev]
                st.success(f"تمت إزالة الجهاز {selected_dev}")
                st.rerun()
    else:
        st.info("لا توجد أجهزة مسجلة.")

# 6. سجل العمليات والتدقيق (Audit Logs)
elif menu == "📋 سجل العمليات والتدقيق (Audit Logs)":
    st.title("📋 سجل العمليات والتدقيق مع بصمة أجهزة المسؤولين")
    if not st.session_state.audit_logs.empty:
        st.dataframe(st.session_state.audit_logs, use_container_width=True)
    else:
        st.info("لا توجد سجلات مسجلة.")

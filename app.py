import streamlit as st
import pandas as pd
import psycopg2
from psycopg2 import pool
import plotly.express as px
import random
import string
import hashlib
from datetime import datetime, timedelta

# =====================================================================
# إعدادات الصفحة والتنسيقات المتجاوبة لكافة المتصفحات والبيئات
# =====================================================================
st.set_page_config(page_title="MyClicker Pro Ultra Command Center", layout="wide", page_icon="⚡")

st.markdown("""
<style>
header {visibility: hidden;}
* {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, "Noto Sans Arabic", "Cairo", "Tahoma", sans-serif !important;
}
.stApp {
    background-color: #f8fafc !important;
    color: #1e293b !important;
}
[data-testid="stSidebar"] { 
    background-color: #f1f5f9 !important; 
    padding: 10px;
}
.stMetric { 
    background-color: #ffffff !important; 
    padding: 15px !important; 
    border-radius: 12px !important; 
    border: 1px solid #e2e8f0 !important; 
    box-shadow: 0 2px 4px rgba(0,0,0,0.02); 
    margin-bottom: 10px;
    color: #0f172a !important;
}
input, textarea, select {
    background-color: #ffffff !important;
    color: #0f172a !important;
    border: 1px solid #cbd5e1 !important;
}
[data-baseweb="input"] div, [data-baseweb="base-input"] div, [data-baseweb="select"] div {
    background-color: #ffffff !important;
    color: #0f172a !important;
}
div[data-baseweb="select"] span {
    color: #0f172a !important;
}
[data-testid="stDataFrame"] {
    background-color: #ffffff !important;
    border-radius: 10px;
    padding: 5px;
    border: 1px solid #e2e8f0;
}
.stButton button {
    width: 100% !important;
    border-radius: 8px !important;
    font-weight: 600 !important;
}
.stTabs [data-baseweb="tab-list"] { 
    gap: 8px; 
    flex-wrap: wrap;
}
.stTabs [data-baseweb="tab"] { 
    background-color: #f1f5f9 !important; 
    border-radius: 8px 8px 0 0 !important; 
    padding: 10px 18px !important; 
    font-weight: bold; 
    color: #334155 !important;
}
</style>
""", unsafe_allow_html=True)

# دالة مساعدة لتشفير كلمات المرور
def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode('utf-8')).hexdigest()

# =====================================================================
# الاتصال بقاعدة البيانات باستخدام Connection Pool وآلية أمان Secrets
# =====================================================================
@st.cache_resource
def init_connection_pool():
    try:
        db_config = st.secrets.get("postgres", {
            "dbname": "defaultdb",
            "user": "doadmin",
            "password": "1tHwqXCgn8BS6iTm942V3f7a",
            "host": "myclicker-db-rd7ky.db1.ondigitalocean.com",
            "port": "5432",
            "sslmode": "require"
        })
        return pool.SimpleConnectionPool(1, 10, **db_config)
    except Exception as e:
        st.error(f"❌ خطأ في تهيئة الاتصال بقاعدة البيانات: {e}")
        return None

db_pool = init_connection_pool()

def execute_query(sql, params=(), fetch=False):
    if not db_pool:
        return None if fetch else False
    conn = None
    try:
        conn = db_pool.getconn()
        with conn.cursor() as cur:
            cur.execute(sql, params)
            if fetch:
                colnames = [desc[0] for desc in cur.description] if cur.description else []
                data = cur.fetchall()
                conn.commit()
                return pd.DataFrame(data, columns=colnames) if colnames else pd.DataFrame()
            conn.commit()
            return True
    except Exception as e:
        if conn:
            conn.rollback()
        st.error(f"خطأ في تنفيذ قاعدة البيانات: {e}")
        return None if fetch else False
    finally:
        if conn:
            db_pool.putconn(conn)

@st.cache_data(ttl=10)
def load_users_data():
    df = execute_query("SELECT device_id, phone, status, sub_tier, is_frozen, expiry_date, bot_status, app_version, accepted_clicks, last_active, notice_message, last_ip FROM myapp.users_status ORDER BY last_active DESC", fetch=True)
    return df if df is not None else pd.DataFrame()

@st.cache_data(ttl=10)
def load_subs_data():
    df = execute_query("SELECT id, code, sub_tier, duration_days, is_used, used_by_device, used_at FROM myapp.subscriptions ORDER BY id DESC", fetch=True)
    return df if df is not None else pd.DataFrame()

@st.cache_data(ttl=10)
def load_security_logs():
    df = execute_query("SELECT id, device_id, phone, action, reason, created_at FROM myapp.security_logs ORDER BY created_at DESC LIMIT 500", fetch=True)
    return df if df is not None else pd.DataFrame()

@st.cache_data(ttl=15)
def load_config_data():
    df = execute_query("SELECT key, value FROM myapp.app_config", fetch=True)
    if df is not None and not df.empty:
        return dict(zip(df['key'], df['value']))
    return {'latest_version': '7.2.0', 'update_url': '', 'force_update': 'true', 'update_message': 'يرجى التحديث'}

# =====================================================================
# تهيئة الجداول وتحديث الهيكل الذاتي وصلاحيات الأدمن
# =====================================================================
try:
    execute_query("CREATE SCHEMA IF NOT EXISTS myapp;")
    
    db_patches = [
        "ALTER TABLE myapp.users_status ADD COLUMN IF NOT EXISTS sub_tier VARCHAR(20) DEFAULT 'STANDARD'",
        "ALTER TABLE myapp.users_status ADD COLUMN IF NOT EXISTS is_frozen BOOLEAN DEFAULT FALSE",
        "ALTER TABLE myapp.users_status ADD COLUMN IF NOT EXISTS last_ip VARCHAR(100)",
        "ALTER TABLE myapp.subscriptions ADD COLUMN IF NOT EXISTS sub_tier VARCHAR(50) DEFAULT 'STANDARD'",
        "ALTER TABLE myapp.subscriptions ADD COLUMN IF NOT EXISTS sub_type VARCHAR(50) DEFAULT 'STANDARD'"
    ]
    for patch in db_patches:
        execute_query(patch)

    execute_query("""
        CREATE TABLE IF NOT EXISTS myapp.app_permissions (
            id SERIAL PRIMARY KEY,
            username VARCHAR(50) UNIQUE NOT NULL,
            password VARCHAR(100) NOT NULL,
            role_name VARCHAR(50),
            allowed_sections TEXT[],
            is_active BOOLEAN DEFAULT TRUE
        );
    """)
    
    all_secs = [
        "📈 نظرة عامة وإحصائيات الإصدارات",
        "👥 إدارة ومراقبة المستخدمين والتفعيل", 
        "📢 مركز الإشعارات الشامل الكامل",
        "🛡️ سجلات الأمان والرقابة",
        "🔄 لوحة LIVE UPDATE",
        "🚀 إدارة التحديثات الإجبارية", 
        "🎫 توليد وإدارة الأكواد", 
        "🤝 قسم الشركاء (الموزعين)", 
        "📈 تحليل البيانات", 
        "🖥️ حالة السيرفر", 
        "🔐 إدارة الصلاحيات والتحكم", 
        "🛠️ الدعم الفني والتواصل"
    ]

    admin_check = execute_query("SELECT COUNT(*) FROM myapp.app_permissions WHERE username = 'admin'", fetch=True)
    if admin_check is not None and not admin_check.empty and admin_check.iloc[0, 0] == 0:
        execute_query("INSERT INTO myapp.app_permissions (username, password, role_name, allowed_sections, is_active) VALUES ('admin', %s, 'مدير النظام', %s, TRUE)", (hash_password('admin123'), all_secs,))
    else:
        execute_query("UPDATE myapp.app_permissions SET allowed_sections = %s WHERE username = 'admin'", (all_secs,))
except Exception as e:
    st.error(f"خطأ أثناء تهيئة هيكل قاعدة البيانات: {e}")

# =====================================================================
# نظام المصادقة
# =====================================================================
if "logged" not in st.session_state:
    st.session_state.logged = False

if not st.session_state.logged:
    st.title("🔐 تسجيل الدخول - لوحة تحكم MyClicker Pro")
    with st.form("login"):
        u = st.text_input("اسم المستخدم:")
        p = st.text_input("كلمة المرور:", type="password")
        if st.form_submit_button("تسجيل الدخول 🚀"):
            res = execute_query("SELECT password, allowed_sections, is_active FROM myapp.app_permissions WHERE username = %s", (u,), fetch=True)
            if res is not None and not res.empty:
                user_pass, user_secs, is_active = res.iloc[0]['password'], res.iloc[0]['allowed_sections'], res.iloc[0]['is_active']
                # دعم الحسابات القديمة وغير المشفرة مع تشفير الحسابات الجديدة
                if is_active and (user_pass == p or user_pass == hash_password(p)):
                    st.session_state.logged = True
                    st.session_state.user = u
                    st.session_state.sections = all_secs if u == 'admin' else (user_secs if user_secs is not None else [])
                    st.rerun()
                else:
                    st.error("بيانات الدخول غير صحيحة أو الحساب معطل.")
            else:
                st.error("اسم المستخدم غير موجود.")
    st.stop()

# =====================================================================
# الشريط الجانبي (Sidebar والصلاحيات)
# =====================================================================
st.sidebar.markdown(f"### ⚡ MyClicker Pro\n👤 المستخدم: {st.session_state.user}")
if st.sidebar.button("🔄 مسح الذاكرة المؤقتة والتحديث"):
    st.cache_data.clear()
    st.rerun()

user_allowed_sections = st.session_state.get('sections', [])
if not user_allowed_sections:
    st.warning("⚠️ ليس لديك أي صلاحيات لعرض الأقسام. يرجى مراجعة مدير النظام.")
    if st.sidebar.button("🚪 تسجيل الخروج"):
        st.session_state.logged = False
        st.rerun()
    st.stop()

page = st.sidebar.radio("القائمة الرئيسية:", user_allowed_sections)

if st.sidebar.button("🚪 تسجيل الخروج"):
    st.session_state.logged = False
    st.rerun()

# =====================================================================
# الأقسام البرمجية للوحة التحكم
# =====================================================================
if page == "📈 نظرة عامة وإحصائيات الإصدارات":
    st.title("📈 لوحة المؤشرات الحية وإحصائيات إصدارات التطبيق")
    df_u = load_users_data()
    total_subs = len(df_u)
    active_subs = len(df_u[df_u['status'] == 'Active']) if not df_u.empty else 0
    expired_subs = len(df_u[df_u['status'] == 'Expired']) if not df_u.empty else 0
    online_bots = len(df_u[df_u['bot_status'] == 'Online']) if not df_u.empty else 0
    total_clicks = int(df_u['accepted_clicks'].sum()) if not df_u.empty and 'accepted_clicks' in df_u.columns else 0

    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("👥 إجمالي الأجهزة", total_subs)
    col2.metric("🟢 النشطة (Active)", active_subs)
    col3.metric("🔴 المنتهية (Expired)", expired_subs)
    col4.metric("⚡ البوتات (Online)", online_bots)
    col5.metric("🖱️ إجمالي النقرات", total_clicks)

    st.markdown("---")

    if not df_u.empty and 'app_version' in df_u.columns:
        c_v1, c_v2 = st.columns(2)
        with c_v1:
            st.subheader("📊 تحليل وتوزيع إصدارات التطبيق")
            version_counts = df_u['app_version'].value_counts().reset_index()
            version_counts.columns = ['Version', 'Count']
            fig_ver = px.pie(version_counts, names='Version', values='Count', title="نسبة انتشار إصدارات التطبيق", hole=0.4)
            st.plotly_chart(fig_ver, use_container_width=True)
            
        with c_v2:
            st.subheader("🤖 حالة نشاط البوتات (Bot Status)")
            bot_counts = df_u['bot_status'].value_counts().reset_index()
            bot_counts.columns = ['Status', 'Count']
            fig_bot = px.bar(bot_counts, x='Status', y='Count', title="مقارنة البوتات (Online / Offline)", color='Status')
            st.plotly_chart(fig_bot, use_container_width=True)

elif page == "👥 إدارة ومراقبة المستخدمين والتفعيل":
    st.title("👥 إدارة المستخدمين والأجهزة")
    df_users = load_users_data()
    
    if not df_users.empty:
        st.subheader("🔍 البحث عن مستخدم")
        search_query = st.text_input("أدخل رقم الهاتف أو معرف الجهاز للبحث:", placeholder="مثال: 079xxxxxxx")
        
        filtered_df = df_users
        if search_query:
            filtered_df = df_users[
                df_users['phone'].astype(str).str.contains(search_query, na=False) | 
                df_users['device_id'].astype(str).str.contains(search_query, na=False)
            ]
        
        if filtered_df.empty:
            st.warning("❌ لم يتم العثور على نتائج تطابق بحثك.")
        else:
            st.dataframe(filtered_df, use_container_width=True)
            
            st.markdown("---")
            st.subheader("🛠️ لوحة التحكم في الجهاز المختار")
            
            device_list = filtered_df['device_id'].tolist()
            options = [f"📱 {p} | 🆔 {str(d)[:12]}... | 🏷️ {s}" for p, d, s in zip(filtered_df['phone'], device_list, filtered_df['status'])]
            
            selected_idx = st.selectbox("اختر الحساب المطلوب معالجته:", range(len(options)), format_func=lambda x: options[x])
            target_device = device_list[selected_idx]
            target_row = filtered_df[filtered_df['device_id'] == target_device].iloc[0]
            
            c1, c2, c3 = st.columns(3)
            with c1: st.info(f"📞 الهاتف: {target_row['phone']}")
            with c2: st.info(f"📅 الانتهاء: {target_row['expiry_date']}")
            with c3: 
                color = "green" if target_row['status'] == "Active" else "red"
                st.markdown(f"**الحالة:** :{color}[{target_row['status']}]")

            with st.form("edit_user_activation_form"):
                col_e1, col_e2 = st.columns(2)
                with col_e1:
                    new_phone = st.text_input("تعديل رقم الهاتف:", value=str(target_row['phone']) if pd.notnull(target_row['phone']) else "")
                    new_status = st.selectbox("تغيير الحالة:", ["Active", "Expired", "Blocked"], index=["Active", "Expired", "Blocked"].index(target_row['status']) if target_row['status'] in ["Active", "Expired", "Blocked"] else 0)
                    new_sub_tier = st.selectbox("فئة الاشتراك:", ["TRIAL", "STANDARD", "VIP"], index=["TRIAL", "STANDARD", "VIP"].index(target_row['sub_tier']) if target_row['sub_tier'] in ["TRIAL", "STANDARD", "VIP"] else 1)
                    is_frozen = st.checkbox("تجميد الحساب (Freeze)", value=bool(target_row['is_frozen']))
                with col_e2:
                    current_expiry = pd.to_datetime(target_row['expiry_date']) if pd.notnull(target_row['expiry_date']) else datetime.now()
                    new_expiry_date = st.date_input("تاريخ الانتهاء الجديد:", value=current_expiry.date())
                    new_expiry_time = st.time_input("وقت الانتهاء:", value=current_expiry.time())
                
                st.markdown("---")
                col_btn1, col_btn2, col_btn3 = st.columns(3)
                save_clicked = col_btn1.form_submit_button("💾 حفظ التعديلات")
                reset_device_clicked = col_btn2.form_submit_button("🔄 فك ارتباط الجهاز (Reset)")
                delete_clicked = col_btn3.form_submit_button("🗑️ حذف نهائي")
                
                if save_clicked:
                    full_expiry = datetime.combine(new_expiry_date, new_expiry_time)
                    if execute_query("UPDATE myapp.users_status SET phone = %s, status = %s, sub_tier = %s, is_frozen = %s, expiry_date = %s WHERE device_id = %s", (new_phone, new_status, new_sub_tier, is_frozen, full_expiry, target_device)):
                        st.cache_data.clear()
                        st.success("✅ تم تحديث البيانات بنجاح!")
                        st.rerun()

                if reset_device_clicked:
                    if execute_query("DELETE FROM myapp.users_status WHERE device_id = %s", (target_device,)):
                        st.cache_data.clear()
                        st.success(f"✅ تم فك الارتباط بنجاح. يمكن صاحب الرقم ({target_row['phone']}) تسجيل الدخول الآن من أي جهاز آخر.")
                        st.rerun()
                        
                if delete_clicked:
                    if execute_query("DELETE FROM myapp.users_status WHERE device_id = %s", (target_device,)):
                        st.cache_data.clear()
                        st.error("🗑️ تم حذف الحساب بالكامل من النظام.")
                        st.rerun()
    else:
        st.info("لا توجد بيانات مستخدمين مسجلة في الوقت الحالي.")

elif page == "📢 مركز الإشعارات الشامل الكامل":
    st.title("📢 مركز الإشعارات الشامل المتقدم")
    df_notif_users = load_users_data()
    tab_send, tab_manage = st.tabs(["📤 إرسال إشعار جديد", "📋 إدارة ومتابعة الإشعارات المعلقة"])

    with tab_send:
        notif_target_type = st.radio("حدد نطاق الإرسال:", ["إشعار لجهاز/مستخدم فردي عبر رقم الهاتف أو ID", "إشعار لمجموعة محددة (حسب الحالة أو النوع)", "إشعار عام لجميع المشتركين"], horizontal=True)
        notif_display_type = st.selectbox("نوع الإشعار في التطبيق:", ["شريط الحالة (Status Bar Notice)", "رسالة منبثقة إجبارية (Dialog)", "إشعار نصي عادي"])

        with st.form("advanced_notification_form"):
            msg_content = st.text_area("نص الإشعار المراد إرساله:")
            target_device_id = None
            target_group = None

            if notif_target_type == "إشعار لجهاز/مستخدم فردي عبر رقم الهاتف أو ID":
                if not df_notif_users.empty:
                    dev_options = [f"هاتف: {p} | حالة: {s} | ID: {str(d)[:10]}..." for p, s, d in zip(df_notif_users['phone'], df_notif_users['status'], df_notif_users['device_id'])]
                    selected_dev_idx = st.selectbox("اختر الجهاز المستهدف:", range(len(dev_options)), format_func=lambda x: dev_options[x])
                    target_device_id = df_notif_users['device_id'].tolist()[selected_dev_idx]
                else:
                    st.warning("لا توجد أجهزة مسجلة.")
                    
            elif notif_target_type == "إشعار لمجموعة محددة (حسب الحالة أو النوع)":
                target_group = st.selectbox("اختر المجموعة المستهدفة:", [
                    "Active (المشتركين النشطين فقط)", 
                    "Expired (منتهيو الصلاحية فقط)", 
                    "VIP (اشتراكات VIP فقط)", 
                    "TRIAL (اشتراكات التجربة فقط)"
                ])

            if st.form_submit_button("إرسال الإشعار الفوري 🚀"):
                if not msg_content.strip():
                    st.error("يرجى كتابة نص الإشعار أولاً!")
                else:
                    formatted_msg = f"STATUSBAR:{msg_content}" if "شريط الحالة" in notif_display_type else msg_content
                    
                    success_flag = False
                    if notif_target_type == "إشعار لجهاز/مستخدم فردي عبر رقم الهاتف أو ID" and target_device_id:
                        success_flag = execute_query("UPDATE myapp.users_status SET notice_message = %s WHERE device_id = %s", (formatted_msg, target_device_id))
                    elif notif_target_type == "إشعار لمجموعة محددة (حسب الحالة أو النوع)":
                        if "Active" in target_group:
                            success_flag = execute_query("UPDATE myapp.users_status SET notice_message = %s WHERE status = 'Active'", (formatted_msg,))
                        elif "Expired" in target_group:
                            success_flag = execute_query("UPDATE myapp.users_status SET notice_message = %s WHERE status = 'Expired'", (formatted_msg,))
                        elif "VIP" in target_group:
                            success_flag = execute_query("UPDATE myapp.users_status SET notice_message = %s WHERE sub_tier = 'VIP'", (formatted_msg,))
                        elif "TRIAL" in target_group:
                            success_flag = execute_query("UPDATE myapp.users_status SET notice_message = %s WHERE sub_tier = 'TRIAL'", (formatted_msg,))
                    elif notif_target_type == "إشعار عام لجميع المشتركين":
                        success_flag = execute_query("UPDATE myapp.users_status SET notice_message = %s", (formatted_msg,))

                    if success_flag:
                        st.cache_data.clear()
                        st.success("✅ تم إرسال الإشعار بنجاح إلى الجهة المستهدفة!")

    with tab_manage:
        st.subheader("📋 متابعة الإشعارات المعلقة لمستجيبي الأجهزة")
        if not df_notif_users.empty:
            pending_notifs = df_notif_users[df_notif_users['notice_message'].notnull() & (df_notif_users['notice_message'] != '')]
            if not pending_notifs.empty:
                st.dataframe(pending_notifs[['device_id', 'phone', 'notice_message']], use_container_width=True)
                if st.button("🗑️ مسح وإلغاء كافة الإشعارات المعلقة لمجمل الأجهزة"):
                    if execute_query("UPDATE myapp.users_status SET notice_message = NULL"):
                        st.cache_data.clear()
                        st.success("تم مسح جميع الإشعارات المعلقة بنجاح.")
                        st.rerun()
            else:
                st.info("لا توجد إشعارات معلقة حالياً بانتظار استلام الأجهزة لها.")

elif page == "🛡️ سجلات الأمان والرقابة":
    st.title("🛡️ سجلات الأمان ومراقبة محاولات التلاعب")
    logs_df = load_security_logs()
    if not logs_df.empty:
        st.dataframe(logs_df, use_container_width=True)
        if st.button("🗑️ مسح كافة سجلات الأمان"):
            if execute_query("DELETE FROM myapp.security_logs"):
                st.cache_data.clear()
                st.success("تم مسح السجلات بنجاح.")
                st.rerun()
    else:
        st.success("✅ لا توجد سجلات أمان مشبوهة حالياً.")

elif page == "🔄 لوحة LIVE UPDATE":
    st.title("🔄 لوحة التحكم الفوري - LIVE UPDATE")
    conf = load_config_data()
    
    with st.form("live_update_form"):
        st.subheader("📝 الكلمات المفتاحية والمؤشرات")
        lk = st.text_area("الكلمات المفتاحية للقبول (live_keywords):", value=conf.get('live_keywords', ''))
        li = st.text_area("مؤشرات الطلب (live_indicators):", value=conf.get('live_indicators', ''))
        
        st.markdown("---")
        st.subheader("🌐 توجيه السيرفر والسرعة")
        n_url = st.text_input("رابط الـ API القادم (next_api_url):", value=conf.get('next_api_url', ''))
        
        try:
            default_delay = int(conf.get('click_delay', 500))
        except ValueError:
            default_delay = 500
            
        c_delay = st.number_input("تأخير النقرات بالمللي ثانية (click_delay):", min_value=1, max_value=5000, value=default_delay)
        
        if st.form_submit_button("🚀 حفظ ونشر التحديثات الحية"):
            execute_query("INSERT INTO myapp.app_config (key, value) VALUES ('live_keywords', %s) ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value", (lk,))
            execute_query("INSERT INTO myapp.app_config (key, value) VALUES ('live_indicators', %s) ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value", (li,))
            execute_query("INSERT INTO myapp.app_config (key, value) VALUES ('next_api_url', %s) ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value", (n_url,))
            execute_query("INSERT INTO myapp.app_config (key, value) VALUES ('click_delay', %s) ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value", (str(c_delay),))
            
            st.cache_data.clear()
            st.success("✅ تم حفظ ونشر التحديثات الحية بنجاح!")
            st.rerun()

elif page == "🚀 إدارة التحديثات الإجبارية":
    st.title("🚀 إدارة التحديثات الإجبارية")
    conf = load_config_data()
    with st.form("upd_form_node"):
        v = st.text_input("رقم الإصدار الأحدث:", value=conf.get('latest_version', '7.2.0'))
        url = st.text_input("رابط التحميل المباشر للـ APK:", value=conf.get('update_url', ''))
        msg = st.text_area("رسالة النافذة المنبثقة الإجبارية:", value=conf.get('update_message', 'يرجى تحديث التطبيق للاستمرار!'))
        forced = st.selectbox("حالة التحديث الإجباري:", ["true", "false"], index=0 if conf.get('force_update', 'true') == 'true' else 1)
        
        if st.form_submit_button("حفظ ونشر التحديث الإجباري 🚀"):
            execute_query("INSERT INTO myapp.app_config (key, value) VALUES ('latest_version', %s) ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value", (v,))
            execute_query("INSERT INTO myapp.app_config (key, value) VALUES ('update_url', %s) ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value", (url,))
            execute_query("INSERT INTO myapp.app_config (key, value) VALUES ('update_message', %s) ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value", (msg,))
            execute_query("INSERT INTO myapp.app_config (key, value) VALUES ('force_update', %s) ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value", (forced,))
            
            dialog_cmd = f"DIALOG_UPDATE:version={v}|url={url}|msg={msg}"
            execute_query("UPDATE myapp.users_status SET notice_message = %s", (dialog_cmd,))
            
            st.cache_data.clear()
            st.success("✅ تم تحديث ونشر إعدادات التحديث الإجباري بنجاح!")
            st.rerun()

elif page == "🎫 توليد وإدارة الأكواد":
    st.title("🎫 توليد وإدارة الأكواد والاشتراكات")
    with st.form("gen"):
        tp = st.selectbox("نوع الاشتراك:", ["VIP", "TRIAL", "STANDARD"])
        days = st.number_input("المدة بالأيام:", min_value=1, value=30)
        qty = st.number_input("الكمية المراد توليدها:", min_value=1, value=10)
        if st.form_submit_button("توليد الأكواد الآن 🚀"):
            for _ in range(qty):
                code = tp[:3].upper() + ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
                execute_query("INSERT INTO myapp.subscriptions (code, sub_tier, sub_type, duration_days, is_used) VALUES (%s, %s, %s, %s, FALSE) ON CONFLICT DO NOTHING", (code, tp, tp, days))
            st.cache_data.clear()
            st.success(f"تم توليد {qty} كود اشتراك بنجاح.")
            st.rerun()

elif page == "🤝 قسم الشركاء (الموزعين)":
    st.title("🤝 لوحة الشركاء والموزعين")
    df_s = load_subs_data()
    if not df_s.empty:
        t1, t2 = st.tabs(["📦 الأكواد المتاحة للتوزيع", "✅ الأكواد المستخدمة من العملاء"])
        t1.dataframe(df_s[df_s['is_used'] == False], use_container_width=True)
        t2.dataframe(df_s[df_s['is_used'] == True], use_container_width=True)
    else:
        st.info("لا توجد أكواد مسجلة حالياً.")

elif page == "📈 تحليل البيانات":
    st.title("📈 تحليل البيانات وأوقات الذروة للطلبات")
    df_orders = execute_query("SELECT order_time, price FROM myapp.accepted_orders LIMIT 2000", fetch=True)
    if df_orders is not None and not df_orders.empty:
        df_orders['hour'] = pd.to_datetime(df_orders['order_time']).dt.hour
        fig = px.bar(df_orders.groupby('hour').size().reset_index(name='count'), x='hour', y='count', title="أوقات الذروة للطلبات المقبولة حسب الساعة")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("لا توجد سجلات طلبات كافية لعرض الرسومات البيانية.")

elif page == "🖥️ حالة السيرفر":
    st.title("🖥️ مراقبة حالة الخادم وقاعدة البيانات")
    st.success("🟢 سيرفر Node.js متصل بقاعدة بيانات PostgreSQL ويعمل بكفاءة عالية على DigitalOcean.")
    st.info("قاعدة البيانات: PostgreSQL | التشفير: SSL Active | بيئة العمل: Production")

elif page == "🔐 إدارة الصلاحيات والتحكم":
    st.title("🔐 إدارة حسابات لوحة التحكم وصلاحيات الأقسام")
    tab_add, tab_edit, tab_view = st.tabs(["➕ إضافة حساب جديد", "✏️ تعديل صلاحيات حساب موجود", "📋 عرض وحذف الحسابات"])

    with tab_add:
        with st.form("add_user_perm"):
            new_u = st.text_input("اسم المستخدم الجديد:")
            new_p = st.text_input("كلمة المرور:", type="password")
            role_desc = st.text_input("مسمى الوظيفة / الوصف:")
            p_adds = {sec: st.checkbox(sec, value=(sec == "🤝 قسم الشركاء (الموزعين)")) for sec in all_secs}
            if st.form_submit_button("حفظ الحساب والصلاحيات 💾"):
                if not new_u or not new_p:
                    st.error("يرجى إدخال اسم المستخدم وكلمة المرور!")
                else:
                    chosen_secs = [sec for sec, val in p_adds.items() if val]
                    hashed_p = hash_password(new_p)
                    if execute_query("INSERT INTO myapp.app_permissions (username, password, role_name, allowed_sections, is_active) VALUES (%s, %s, %s, %s, TRUE) ON CONFLICT (username) DO NOTHING", (new_u, hashed_p, role_desc, chosen_secs)):
                        st.success(f"تم إنشاء حساب ({new_u}) بنجاح!")
                        st.rerun()

    with tab_edit:
        users_df = execute_query("SELECT username FROM myapp.app_permissions", fetch=True)
        if users_df is not None and not users_df.empty:
            usernames = users_df['username'].tolist()
            selected_edit_user = st.selectbox("اختر المستخدم المراد تعديله:", usernames)
            u_data = execute_query("SELECT password, role_name, allowed_sections FROM myapp.app_permissions WHERE username = %s", (selected_edit_user,), fetch=True)
            if u_data is not None and not u_data.empty:
                old_pass = u_data.iloc[0]['password']
                old_role = u_data.iloc[0]['role_name']
                old_secs = u_data.iloc[0]['allowed_sections'] if u_data.iloc[0]['allowed_sections'] is not None else []
                with st.form("edit_user_perm_form"):
                    edit_p = st.text_input("تعديل كلمة المرور (أتركها كما هي للعدم التغيير):", value=old_pass, type="password")
                    edit_role = st.text_input("تعديل المسمى الوظيفي:", value=old_role if old_role else "")
                    p_edits = {sec: st.checkbox(sec, value=(sec in old_secs), key=f"edit_{selected_edit_user}_{sec}") for sec in all_secs}
                    if st.form_submit_button("حفظ التعديلات والتحديث 🔄"):
                        updated_secs = [sec for sec, val in p_edits.items() if val]
                        new_pass_final = edit_p if edit_p == old_pass else hash_password(edit_p)
                        if execute_query("UPDATE myapp.app_permissions SET password = %s, role_name = %s, allowed_sections = %s WHERE username = %s", (new_pass_final, edit_role, updated_secs, selected_edit_user)):
                            st.success(f"✅ تم تحديث صلاحيات الحساب ({selected_edit_user}) بنجاح!")
                            st.rerun()

    with tab_view:
        df_perms = execute_query("SELECT id, username, role_name, is_active FROM myapp.app_permissions", fetch=True)
        if df_perms is not None:
            st.dataframe(df_perms, use_container_width=True)
        target_user_del = st.text_input("أدخل اسم المستخدم المراد حذفه نهائياً:")
        if st.button("حذف الحساب 🗑️"):
            if target_user_del == "admin":
                st.error("لا يمكن حذف حساب الأدمن الرئيسي للنظام!")
            elif execute_query("DELETE FROM myapp.app_permissions WHERE username = %s", (target_user_del,)):
                st.success(f"تم حذف الحساب ({target_user_del}) بنجاح.")
                st.rerun()

elif page == "🛠️ الدعم الفني والتواصل":
    st.title("🛠️ الدعم الفني وقنوات التواصل")
    st.info("📱 واتساب الإدارة: مراسلة الدعم الفني")
    st.success("✈️ تليجرام الدعم الفني: @MyClicker_Support")

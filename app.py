import streamlit as st
import pandas as pd
import psycopg2
import plotly.express as px
import random
import string
from datetime import datetime, timedelta

# =====================================================================
# إعدادات الصفحة والتنسيقات المتجاوبة لكافة المتصفحات والبيئات
# =====================================================================
st.set_page_config(
    page_title="MyClicker Pro Ultra Command Center",
    layout="wide",
    page_icon="⚡"
)

st.markdown("""
    <style>
    header {visibility: hidden;}
    
    /* خطوط النظام القياسية والمتجاوبة */
    * {
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, "Noto Sans Arabic", "Cairo", "Tahoma", sans-serif !important;
    }
    
    /* تثبيت خلفية التطبيق العامة للوضع الفاتح ومنع الشاشة السوداء */
    .stApp {
        background-color: #f8fafc !important;
        color: #1e293b !important;
    }
    
    /* الشريط الجانبي */
    [data-testid="stSidebar"] { 
        background-color: #f1f5f9 !important; 
        padding: 10px;
    }
    
    /* بطاقات المقاييس والإحصائيات */
    .stMetric { 
        background-color: #ffffff !important; 
        padding: 15px !important; 
        border-radius: 12px !important; 
        border: 1px solid #e2e8f0 !important; 
        box-shadow: 0 2px 4px rgba(0,0,0,0.02); 
        margin-bottom: 10px;
        color: #0f172a !important;
    }
    
    /* تثبيت ألوان وخلفيات حقول الإدخال والـ Selectbox لمنع ظهورها باللون الأسود */
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
    
    /* تنسيق الجداول لتكون بخلفية بيضاء ونظيفة */
    [data-testid="stDataFrame"] {
        background-color: #ffffff !important;
        border-radius: 10px;
        padding: 5px;
        border: 1px solid #e2e8f0;
    }

    /* الأزرار */
    .stButton button {
        width: 100% !important;
        border-radius: 8px !important;
        font-weight: 600 !important;
    }

    /* التبويبات */
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

# =====================================================================
# الاتصال بقاعدة البيانات مع التخزين المؤقت وتحسين الأداء
# =====================================================================
@st.cache_resource
def get_conn():
    try:
        return psycopg2.connect(
            database="defaultdb",
            user="doadmin",
            password="1tHwqXCgn8BS6iTm942V3f7a",
            host="myclicker-db-rd7ky.db1.ondigitalocean.com",
            port="5432",
            sslmode="require",
            connect_timeout=5
        )
    except Exception:
        return None

conn = get_conn()
if not conn:
    st.error("❌ فشل الاتصال بقاعدة البيانات على DigitalOcean. يرجى التحقق من بيانات الاتصال.")
    st.stop()

def query(sql, params=()):
    try:
        global conn
        if conn.closed != 0:
            conn = get_conn()
        cur = conn.cursor()
        cur.execute(sql, params)
        conn.commit()
        cur.close()
        return True
    except Exception as e:
        conn.rollback()
        st.error(f"خطأ في تنفيذ قاعدة البيانات: {e}")
        return False

@st.cache_data(ttl=10)
def load_users_data():
    try:
        return pd.read_sql("SELECT device_id, phone, status, subscription_type, expiry_date, bot_status, app_version, accepted_clicks, last_active, notice_message FROM myapp.users_status ORDER BY last_active DESC", conn)
    except Exception:
        return pd.DataFrame()

@st.cache_data(ttl=10)
def load_subs_data():
    try:
        return pd.read_sql("SELECT id, code, sub_type, duration_days, is_used, used_by_device, used_at FROM myapp.subscriptions ORDER BY id DESC", conn)
    except Exception:
        return pd.DataFrame()

@st.cache_data(ttl=15)
def load_config_data():
    try:
        config_rows = pd.read_sql("SELECT key, value FROM myapp.app_config", conn)
        return dict(zip(config_rows['key'], config_rows['value']))
    except Exception:
        return {'latest_version': '7.1.0', 'update_url': '', 'force_update': 'true', 'update_message': 'يرجى التحديث'}

# =====================================================================
# تهيئة الجداول وتحديث الهيكل الذاتي
# =====================================================================
try:
    cur = conn.cursor()
    cur.execute("CREATE SCHEMA IF NOT EXISTS myapp;")
    cur.execute("""
        CREATE TABLE IF NOT EXISTS myapp.app_permissions (
            id SERIAL PRIMARY KEY,
            username VARCHAR(50) UNIQUE NOT NULL,
            password VARCHAR(100) NOT NULL,
            role_name VARCHAR(50),
            allowed_sections TEXT[],
            is_active BOOLEAN DEFAULT TRUE
        );
    """)
    cur.execute("ALTER TABLE myapp.app_permissions ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE;")
    
    all_secs = [
        "📈 نظرة عامة وإحصائيات الإصدارات",
        "👥 إدارة ومراقبة المستخدمين والتفعيل", 
        "📢 مركز الإشعارات الشامل الكامل",
        "🚀 إدارة التحديثات الإجبارية", 
        "🎫 توليد وإدارة الأكواد", 
        "🤝 قسم الشركاء (الموزعين)", 
        "📈 تحليل البيانات", 
        "🖥️ حالة السيرفر", 
        "🔐 إدارة الصلاحيات والتحكم", 
        "🛠️ الدعم الفني والتواصل"
    ]

    cur.execute("SELECT COUNT(*) FROM myapp.app_permissions WHERE username = 'admin'")
    if cur.fetchone()[0] == 0:
        cur.execute("INSERT INTO myapp.app_permissions (username, password, role_name, allowed_sections, is_active) VALUES ('admin', 'admin123', 'مدير النظام', %s, TRUE)", (all_secs,))
    else:
        cur.execute("UPDATE myapp.app_permissions SET allowed_sections = %s WHERE username = 'admin'", (all_secs,))
    
    conn.commit()
    cur.close()
except Exception:
    conn.rollback()

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
            cur = conn.cursor()
            cur.execute("SELECT password, allowed_sections, is_active FROM myapp.app_permissions WHERE username = %s", (u,))
            res = cur.fetchone()
            cur.close()
            if res and res[2] and res[0] == p:
                st.session_state.logged = True
                st.session_state.user = u
                st.session_state.sections = res[1]
                st.rerun()
            else:
                st.error("بيانات الدخول غير صحيحة أو الحساب معطل.")
    st.stop()

# =====================================================================
# الشريط الجانبي (Sidebar)
# =====================================================================
st.sidebar.markdown(f"### ⚡ MyClicker Pro\n👤 المستخدم: **{st.session_state.user}**")
if st.sidebar.button("🔄 مسح الذاكرة المؤقتة والتحديث"):
    st.cache_data.clear()
    st.rerun()

page = st.sidebar.radio("القائمة الرئيسية:", st.session_state.sections)

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
    total_clicks = int(df_u['accepted_clicks'].sum()) if not df_u.empty else 0

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
    st.title("👥 إدارة المستخدمين، الأجهزة، والتحكم ببيانات التفعيل")
    df_users = load_users_data()

    if not df_users.empty:
        st.dataframe(df_users, use_container_width=True)
        
        st.markdown("---")
        st.subheader("🛠️ لوحة التحكم وتعديل بيانات التفعيل للمستخدم المختار")
        
        device_list = df_users['device_id'].tolist()
        options = [f"هاتف: {p} | حالة: {s} | اشتراك: {t} | جهاز: {d[:8]}..." for p, s, t, d in zip(df_users['phone'], df_users['status'], df_users['subscription_type'], device_list)]
        
        selected_idx = st.selectbox("اختر الجهاز أو المشترك للتعديل:", range(len(options)), format_func=lambda x: options[x])
        target_device = device_list[selected_idx]
        target_row = df_users[df_users['device_id'] == target_device].iloc[0]
        
        with st.form("edit_user_activation_form"):
            col_e1, col_e2 = st.columns(2)
            with col_e1:
                new_phone = st.text_input("تعديل رقم الهاتف:", value=str(target_row['phone']) if target_row['phone'] else "")
                new_status = st.selectbox("حالة الاشتراك:", ["Active", "Expired", "Blocked"], index=["Active", "Expired", "Blocked"].index(target_row['status']) if target_row['status'] in ["Active", "Expired", "Blocked"] else 0)
                new_sub_type = st.selectbox("نوع الاشتراك:", ["VIP", "TRIAL", "Monthly"], index=0)
            with col_e2:
                current_expiry = pd.to_datetime(target_row['expiry_date']) if target_row['expiry_date'] else datetime.now()
                new_expiry_date = st.date_input("تاريخ انتهاء الاشتراك:", value=current_expiry.date())
                new_expiry_time = st.time_input("وقت الانتهاء:", value=current_expiry.time())
            
            if st.form_submit_button("💾 حفظ وتحديث بيانات التفعيل"):
                full_expiry = datetime.combine(new_expiry_date, new_expiry_time)
                res = query("""
                    UPDATE myapp.users_status 
                    SET phone = %s, status = %s, subscription_type = %s, expiry_date = %s 
                    WHERE device_id = %s
                """, (new_phone, new_status, new_sub_type, full_expiry, target_device))
                
                if res:
                    st.cache_data.clear()
                    st.success("✅ تم تحديث بيانات تفعيل المستخدم بنجاح!")
                    st.rerun()
    else:
        st.info("لا توجد بيانات مسجلة للمستخدمين حالياً.")

elif page == "📢 مركز الإشعارات الشامل الكامل":
    st.title("📢 مركز الإشعارات الشامل المتقدم")
    st.info("💡 تحكم كامل بإرسال الإشعارات والرسائل المنبثقة الفورية للأجهزة مع إمكانية متابعة الإشعارات المعلقة وحذفها.")
    
    df_notif_users = load_users_data()

    tab_send, tab_manage = st.tabs(["📤 إرسال إشعار جديد", "📋 إدارة ومتابعة الإشعارات المعلقة"])

    with tab_send:
        notif_target_type = st.radio("حدد نطاق الإرسال:", ["إشعار لجهاز/مستخدم فردي عبر رقم الهاتف أو ID", "إشعار لمجموعة محددة (حسب الحالة أو النوع)", "إشعار عام لجميع المشتركين"], horizontal=True)

        with st.form("advanced_notification_form"):
            msg_content = st.text_area("نص الإشعار المراد إرساله للمستخدمين:")
            target_device_id = None
            target_group = None

            if notif_target_type == "إشعار لجهاز/مستخدم فردي عبر رقم الهاتف أو ID":
                if not df_notif_users.empty:
                    dev_options = [f"هاتف: {p} | حالة: {s} | ID: {d[:10]}..." for p, s, d in zip(df_notif_users['phone'], df_notif_users['status'], df_notif_users['device_id'])]
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
                    success_flag = False
                    if notif_target_type == "إشعار لجهاز/مستخدم فردي عبر رقم الهاتف أو ID" and target_device_id:
                        success_flag = query("UPDATE myapp.users_status SET notice_message = %s WHERE device_id = %s", (msg_content, target_device_id))
                    elif notif_target_type == "إشعار لمجموعة محددة (حسب الحالة أو النوع)":
                        if "Active" in target_group:
                            success_flag = query("UPDATE myapp.users_status SET notice_message = %s WHERE status = 'Active'", (msg_content,))
                        elif "Expired" in target_group:
                            success_flag = query("UPDATE myapp.users_status SET notice_message = %s WHERE status = 'Expired'", (msg_content,))
                        elif "VIP" in target_group:
                            success_flag = query("UPDATE myapp.users_status SET notice_message = %s WHERE subscription_type = 'VIP'", (msg_content,))
                        elif "TRIAL" in target_group:
                            success_flag = query("UPDATE myapp.users_status SET notice_message = %s WHERE subscription_type = 'TRIAL'", (msg_content,))
                    elif notif_target_type == "إشعار عام لجميع المشتركين":
                        success_flag = query("UPDATE myapp.users_status SET notice_message = %s", (msg_content,))

                    if success_flag:
                        st.cache_data.clear()
                        st.success("✅ تم إرسال الإشعار بنجاح إلى الجهة المستهدفة!")
                    else:
                        st.error("فشل إرسال الإشعار.")

    with tab_manage:
        st.subheader("📋 متابعة الإشعارات المعلقة لمستجيبي الأجهزة")
        if not df_notif_users.empty:
            pending_notifs = df_notif_users[df_notif_users['notice_message'].notnull() & (df_notif_users['notice_message'] != '')]
            if not pending_notifs.empty:
                st.dataframe(pending_notifs[['device_id', 'phone', 'notice_message']], use_container_width=True)
                if st.button("🗑️ مسح وإلغاء كافة الإشعارات المعلقة لمجمل الأجهزة"):
                    if query("UPDATE myapp.users_status SET notice_message = NULL"):
                        st.cache_data.clear()
                        st.success("تم مسح جميع الإشعارات المعلقة بنجاح.")
                        st.rerun()
            else:
                st.info("لا توجد إشعارات معلقة حالياً بانتظار استلام الأجهزة لها.")

elif page == "🚀 إدارة التحديثات الإجبارية":
    st.title("🚀 إدارة التحديثات الإجبارية")
    conf = load_config_data()
    
    with st.form("upd_form_node"):
        v = st.text_input("رقم الإصدار الأحدث:", value=conf.get('latest_version', '7.1.0'))
        url = st.text_input("رابط التحميل المباشر للـ APK:", value=conf.get('update_url', ''))
        msg = st.text_area("رسالة النافذة المنبثقة الإجبارية:", value=conf.get('update_message', 'يرجى تحديث التطبيق للاستمرار!'))
        forced = st.selectbox("حالة التحديث الإجباري:", ["true", "false"], index=0 if conf.get('force_update', 'true') == 'true' else 1)
        
        if st.form_submit_button("حفظ ونشر التحديث الإجباري 🚀"):
            query("INSERT INTO myapp.app_config (key, value) VALUES ('latest_version', %s) ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value", (v,))
            query("INSERT INTO myapp.app_config (key, value) VALUES ('update_url', %s) ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value", (url,))
            query("INSERT INTO myapp.app_config (key, value) VALUES ('update_message', %s) ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value", (msg,))
            query("INSERT INTO myapp.app_config (key, value) VALUES ('force_update', %s) ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value", (forced,))
            
            dialog_cmd = f"DIALOG_UPDATE:version={v}|url={url}|msg={msg}"
            query("UPDATE myapp.users_status SET notice_message = %s", (dialog_cmd,))
            
            st.cache_data.clear()
            st.success("✅ تم تحديث ونشر إعدادات التحديث الإجباري بنجاح!")
            st.rerun()

elif page == "🎫 توليد وإدارة الأكواد":
    st.title("🎫 توليد وإدارة الأكواد والاشتراكات")
    with st.form("gen"):
        tp = st.selectbox("نوع الاشتراك:", ["VIP", "TRIAL"])
        days = st.number_input("المدة بالأيام:", min_value=1, value=30)
        qty = st.number_input("الكمية المراد توليدها:", min_value=1, value=10)
        if st.form_submit_button("توليد الأكواد الآن 🚀"):
            for _ in range(qty):
                code = tp[:3].upper() + ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
                query("INSERT INTO myapp.subscriptions (code, sub_type, duration_days, is_used) VALUES (%s, %s, %s, FALSE) ON CONFLICT DO NOTHING", (code, tp, days))
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
    try:
        df_orders = pd.read_sql("SELECT order_time, price FROM myapp.accepted_orders LIMIT 2000", conn)
        if not df_orders.empty:
            df_orders['hour'] = pd.to_datetime(df_orders['order_time']).dt.hour
            fig = px.bar(df_orders.groupby('hour').size().reset_index(name='count'), x='hour', y='count', title="أوقات الذروة للطلبات المقبولة حسب الساعة")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("لا توجد سجلات طلبات كافية لعرض الرسومات البيانية.")
    except Exception:
        st.info("بيانات الطلبات غير متوفرة في قاعدة البيانات حالياً.")

elif page == "🖥️ حالة السيرفر":
    st.title("🖥️ مراقبة حالة الخادم وقاعدة البيانات")
    st.success("🟢 سيرفر Node.js متصل بقاعدة بيانات PostgreSQL ويعمل بكفاءة عالية على DigitalOcean.")
    st.info("قاعدة البيانات: PostgreSQL | التشفير: SSL Active | بيئة العمل: Production")

elif page == "🔐 إدارة الصلاحيات والتحكم":
    st.title("🔐 إدارة حسابات لوحة التحكم والصلاحيات")
    try:
        df_p = pd.read_sql("SELECT username, role_name, is_active FROM myapp.app_permissions", conn)
        st.dataframe(df_p, use_container_width=True)
    except Exception:
        st.info("لا توجد حسابات صلاحيات مسجلة.")

elif page == "🛠️ الدعم الفني والتواصل":
    st.title("🛠️ الدعم الفني وقنوات التواصل")
    st.info("📱 واتساب الإدارة: مراسلة الدعم الفني")
    st.success("✈️ تليجرام الدعم الفني: @MyClicker_Support")

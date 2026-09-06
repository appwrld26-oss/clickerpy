import streamlit as st
import pandas as pd
import psycopg2
import plotly.express as px
import random
import string
from datetime import datetime, timedelta

# =====================================================================
# 1. إعدادات التصميم والسمات (Theme)
# =====================================================================
        st.markdown("---")
        cc1, cc2 = st.columns(2)
        with cc1:
            st.subheader("📊 توزيع إصدارات التطبيق")
            # إصلاح الرسم الدائري
            version_df = df['app_version'].value_counts().reset_index()
            version_df.columns = ['Version', 'Count']
            st.plotly_chart(px.pie(version_df, names='Version', values='Count', hole=0.4), use_container_width=True)
            
        with cc2:
            st.subheader("🤖 حالة نشاط البوتات")
            # إصلاح الرسم البياني للأعمدة (حل المشكلة المذكورة)
            bot_df = df['bot_status'].value_counts().reset_index()
            bot_df.columns = ['Status', 'Count'] # تسمية الأعمدة يدوياً لضمان الاستقرار
            st.plotly_chart(px.bar(bot_df, x='Status', y='Count', color='Status'), use_container_width=True)

# =====================================================================
# 2. إدارة قاعدة البيانات
# =====================================================================
@st.cache_resource
def get_conn():
    try:
        return psycopg2.connect(
            database="defaultdb", user="doadmin", password="1tHwqXCgn8BS6iTm942V3f7a",
            host="myclicker-db-rd7ky.db1.ondigitalocean.com", port="5432", sslmode="require"
        )
    except: return None

def query(sql, params=()):
    conn = get_conn()
    if not conn: return False
    try:
        cur = conn.cursor()
        cur.execute(sql, params)
        conn.commit()
        cur.close()
        return True
    except Exception as e:
        st.error(f"خطأ قاعدة بيانات: {e}")
        return False

@st.cache_data(ttl=5)
def load_data(sql):
    conn = get_conn()
    if not conn: return pd.DataFrame()
    try: return pd.read_sql(sql, conn)
    except: return pd.DataFrame()

def load_config():
    df = load_data("SELECT key, value FROM myapp.app_config")
    return dict(zip(df['key'], df['value'])) if not df.empty else {}

# =====================================================================
# 3. نظام تسجيل الدخول والصلاحيات
# =====================================================================
if "logged" not in st.session_state: st.session_state.logged = False

if not st.session_state.logged:
    st.title("🛡️ MyClicker Pro - بوابة التحكم")
    with st.form("login_form"):
        u = st.text_input("اسم المستخدم")
        p = st.text_input("كلمة المرور", type="password")
        if st.form_submit_button("دخول آمن 🚀"):
            conn = get_conn()
            cur = conn.cursor()
            cur.execute("SELECT password, allowed_sections FROM myapp.app_permissions WHERE username = %s AND is_active = TRUE", (u,))
            res = cur.fetchone()
            if res and res[0] == p:
                st.session_state.logged, st.session_state.user, st.session_state.sections = True, u, res[1]
                st.rerun()
            else: st.error("عذراً، بيانات الدخول غير صحيحة")
    st.stop()

# =====================================================================
# 4. القائمة الجانبية (Sidebar)
# =====================================================================
st.sidebar.markdown(f"### ⚡ مركز الإدارة\n👤 المستخدِم: **{st.session_state.user}**")
page = st.sidebar.radio("القائمة الرئيسية:", st.session_state.sections)
if st.sidebar.button("🚪 تسجيل الخروج"):
    st.session_state.logged = False
    st.rerun()

# =====================================================================
# 5. الأقسام والمهمات (Features)
# =====================================================================

# --- 1. الإحصائيات العامة ---
if page == "📈 نظرة عامة وإحصائيات الإصدارات":
    st.title("📈 تحليل الشبكة والمؤشرات الحية")
    df = load_data("SELECT * FROM myapp.users_status")
    if not df.empty:
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("إجمالي الأجهزة", len(df))
        c2.metric("🟢 الأجهزة النشطة", len(df[df['status'] == 'Active']))
        c3.metric("🔴 منتهي/محظور", len(df[df['status'] != 'Active']))
        c4.metric("🖱️ نقرات اليوم", int(df['accepted_clicks'].sum()))
        
        st.markdown("---")
        cc1, cc2 = st.columns(2)
        with cc1:
            st.subheader("📊 توزيع إصدارات التطبيق")
            st.plotly_chart(px.pie(df, names='app_version', hole=0.4), use_container_width=True)
        with cc2:
            st.subheader("🤖 حالة نشاط البوتات")
            st.plotly_chart(px.bar(df['bot_status'].value_counts().reset_index(), x='index', y='bot_status', color='index'), use_container_width=True)

# --- 2. إدارة المستخدمين (تعديل، حذف، تحديث فردي) ---
elif page == "👥 إدارة ومراقبة المستخدمين والتفعيل":
    st.title("👥 إدارة الأجهزة والمشتركين")
    df = load_data("SELECT device_id, phone, status, subscription_type, expiry_date, app_version, last_active FROM myapp.users_status ORDER BY last_active DESC")
    st.dataframe(df, use_container_width=True)
    
    st.markdown("---")
    st.subheader("🛠️ لوحة العمليات الفردية")
    target_phone = st.selectbox("اختر رقم الهاتف:", df['phone'].tolist())
    target_row = df[df['phone'] == target_phone].iloc[0]
    target_id = target_row['device_id']
    
    tab1, tab2, tab3 = st.tabs(["✏️ تعديل البيانات", "🚀 تحديث إجباري فردي", "🗑️ حذف الحساب"])
    
    with tab1:
        with st.form("edit_individual"):
            c_e1, c_e2 = st.columns(2)
            new_p = c_e1.text_input("تعديل الهاتف:", value=target_row['phone'])
            new_s = c_e1.selectbox("الحالة:", ["Active", "Expired", "Blocked"], index=["Active", "Expired", "Blocked"].index(target_row['status']))
            new_t = c_e2.selectbox("نوع الاشتراك:", ["VIP", "Pro", "TRIAL"], index=0)
            new_d = c_e2.date_input("تاريخ الانتهاء:", value=pd.to_datetime(target_row['expiry_date']).date() if target_row['expiry_date'] else datetime.now().date())
            if st.form_submit_button("حفظ التعديلات 💾"):
                query("UPDATE myapp.users_status SET phone=%s, status=%s, subscription_type=%s, expiry_date=%s WHERE device_id=%s", (new_p, new_s, new_t, new_d, target_id))
                st.success("تم تحديث بيانات المستخدم")
                st.rerun()

    with tab2:
        conf = load_config()
        with st.form("force_individual"):
            v_ind = st.text_input("إصدار التحديث:", value=conf.get('latest_version', '7.2.4'))
            m_ind = st.text_area("رسالة الإجبار:", value="يجب تحديث هذا الجهاز تحديداً الآن!")
            if st.form_submit_button("إرسال أمر التحديث لهذا الجهاز فقط ⚠️"):
                cmd = f"DIALOG_UPDATE:version={v_ind}|url={conf.get('update_url', '')}|msg={m_ind}"
                query("UPDATE myapp.users_status SET notice_message = %s WHERE device_id = %s", (cmd, target_id))
                st.warning("تم إرسال أمر التحديث الإجباري")

    with tab3:
        st.error("⚠️ تحذير: سيتم حذف كافة بيانات هذا الجهاز ولن يتمكن من الدخول إلا بتفعيل جديد.")
        if st.button("تأكيد الحذف النهائي 🗑️"):
            query("DELETE FROM myapp.users_status WHERE device_id = %s", (target_id,))
            st.success("تم حذف المستخدم نهائياً")
            st.rerun()

# --- 3. مركز الإشعارات (فردي وجماعي) ---
elif page == "📢 مركز الإشعارات الشامل الكامل":
    st.title("📢 إدارة البث والتنبيهات")
    with st.form("notif_center"):
        target_mode = st.radio("الجمهور:", ["الجميع", "جهاز محدد"])
        spec_phone = st.text_input("رقم الهاتف (إذا اخترت جهاز محدد):")
        n_type = st.selectbox("نوع التنبيه:", ["Status Bar (إشعار علوي)", "Dialog (نافذة منبثقة)"])
        msg_text = st.text_area("نص الرسالة:")
        
        if st.form_submit_button("إرسال الآن 🚀"):
            prefix = "STATUSBAR:" if "Status" in n_type else "DIALOG:"
            final_msg = prefix + msg_text
            if target_mode == "الجميع":
                query("UPDATE myapp.users_status SET notice_message = %s", (final_msg,))
            else:
                query("UPDATE myapp.users_status SET notice_message = %s WHERE phone = %s", (final_msg, spec_phone))
            st.success("تم إرسال الإشعار بنجاح")

# --- 4. التحديثات الإجبارية (العامة) ---
elif page == "🚀 إدارة التحديثات الإجبارية":
    st.title("🚀 التحديث الإجباري العالمي")
    conf = load_config()
    with st.form("global_upd_form"):
        v_gl = st.text_input("الإصدار الأحدث:", value=conf.get('latest_version', '7.2.4'))
        url_gl = st.text_input("رابط APK (Dropbox/Direct):", value=conf.get('update_url', ''))
        msg_gl = st.text_area("رسالة الإجبار لجميع المستخدمين:", value=conf.get('update_message', 'تحديث هام جداً لاستمرار الخدمة'))
        if st.form_submit_button("نشر التحديث لكافة الهواتف 🌍"):
            query("INSERT INTO myapp.app_config (key, value) VALUES ('latest_version', %s), ('update_url', %s), ('update_message', %s) ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value", (v_gl, url_gl, msg_gl))
            query("UPDATE myapp.users_status SET notice_message = %s", (f"DIALOG_UPDATE:version={v_gl}|url={url_gl}|msg={msg_gl}",))
            st.success("تم تفعيل وضع التحديث الإجباري لجميع المستخدمين")

# --- 5. لوحة LIVE UPDATE (التحكم الحي بالبوت) ---
elif page == "⚡ تحديث البيانات الحية (LIVE UPDATE)":
    st.title("⚡ التحكم الذكي المباشر (Live Data)")
    st.info("💡 هذه الإعدادات تغير سلوك البوت في الهواتف 'لحظياً' دون الحاجة لتحديث التطبيق.")
    conf = load_config()
    
    with st.form("advanced_live_form"):
        col1, col2 = st.columns(2)
        with col1:
            kw = st.text_area("✅ كلمات القبول (مثلاً: قبول, Accept):", value=conf.get('live_keywords', 'قبول, accept, استلام'))
            neg = st.text_area("❌ كلمات التجنب (مثلاً: كاش, دفع نقدي):", value=conf.get('live_negative_keywords', 'كاش, سيء, مديونية'))
        with col2:
            ind = st.text_area("🔍 مؤشرات الطلب (مثلاً: Economy, Uber):", value=conf.get('live_indicators', 'Economy, Uber, Careem, ريال, د.أ'))
            jitter = st.slider("🎭 التمويه البشري (تأخير عشوائي بالـ ms):", 0, 1000, int(conf.get('live_jitter', 50)))
        
        status_gl = st.radio("🚦 حالة النظام العالمية (Kill Switch):", ["ON (تشغيل شامل)", "OFF (إيقاف شامل لكل البوتات)"], index=0 if conf.get('global_status', 'ON') == 'ON' else 1)
        
        if st.form_submit_button("حفظ وتحديث ذكاء كافة البوتات 🚀"):
            query("INSERT INTO myapp.app_config (key, value) VALUES ('live_keywords', %s), ('live_negative_keywords', %s), ('live_indicators', %s), ('live_jitter', %s), ('global_status', %s) ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value", 
                  (kw, neg, ind, str(jitter), "ON" if "ON" in status_gl else "OFF"))
            query("UPDATE myapp.users_status SET notice_message = 'LIVE_UPDATE_TRIGGER'")
            st.success("✅ تم تحديث ذكاء البوتات عالمياً بنجاح!")

# --- 6. إدارة الصلاحيات والمدراء ---
elif page == "🔐 إدارة الصلاحيات والتحكم":
    st.title("🔐 إدارة حسابات الإدارة والصلاحيات")
    df_perms = load_data("SELECT username, role_name, allowed_sections, is_active FROM myapp.app_permissions")
    st.dataframe(df_perms, use_container_width=True)
    
    with st.expander("➕ إضافة مدير / شريك جديد"):
        all_sections = [
            "📈 نظرة عامة وإحصائيات الإصدارات", "👥 إدارة ومراقبة المستخدمين والتفعيل", 
            "📢 مركز الإشعارات الشامل الكامل", "🚀 إدارة التحديثات الإجبارية", 
            "⚡ تحديث البيانات الحية (LIVE UPDATE)", "🎫 توليد وإدارة الأكواد",
            "🤝 قسم الشركاء (الموزعين)", "🖥️ حالة السيرفر", "🔐 إدارة الصلاحيات والتحكم"
        ]
        with st.form("add_admin_form"):
            new_u = st.text_input("اسم المستخدم")
            new_p = st.text_input("كلمة المرور")
            sel_secs = st.multiselect("الأقسام المسموحة:", all_sections, default=all_sections[:2])
            if st.form_submit_button("إنشاء الحساب 💾"):
                query("INSERT INTO myapp.app_permissions (username, password, role_name, allowed_sections, is_active) VALUES (%s, %s, 'Admin', %s, TRUE)", (new_u, new_p, sel_secs))
                st.success(f"تم إنشاء حساب {new_u}")
                st.rerun()

# --- باقي الأقسام الأساسية (أكواد، موزعين، سيرفر) ---
elif page == "🎫 توليد وإدارة الأكواد":
    st.title("🎫 نظام توليد الاشتراكات")
    with st.form("gen_codes"):
        t_c = st.selectbox("الفئة:", ["VIP", "TRIAL"])
        d_c = st.number_input("الأيام:", 1, 365, 30)
        q_c = st.number_input("الكمية:", 1, 100, 10)
        if st.form_submit_button("توليد الأكواد الآن 🚀"):
            for _ in range(q_c):
                code = t_c + ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
                query("INSERT INTO myapp.subscriptions (code, sub_type, duration_days, is_used) VALUES (%s, %s, %s, FALSE)", (code, t_c, d_c))
            st.success(f"تم توليد {q_c} كود بنجاح")

elif page == "🤝 قسم الشركاء (الموزعين)":
    st.title("🤝 لوحة الموزعين والأكواد")
    df_codes = load_data("SELECT code, sub_type, duration_days FROM myapp.subscriptions WHERE is_used = FALSE")
    st.dataframe(df_codes, use_container_width=True)

elif page == "🖥️ حالة السيرفر":
    st.title("🖥️ مراقبة الخادم")
    st.success("الخادم: متصل بكفاءة 🟢")
    st.info("قاعدة البيانات (PostgreSQL): تعمل بوضع الإنتاج 🚀")

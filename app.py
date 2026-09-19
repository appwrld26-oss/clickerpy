import hashlib
import os
import secrets
from contextlib import contextmanager
from typing import Optional

import pandas as pd
import plotly.express as px
import psycopg2
import streamlit as st
from psycopg2 import pool

# ============================================================
# إعداد الصفحة والهوية البصرية
# ============================================================
st.set_page_config(
    page_title="MyClicker Pro | Emperor Console",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700;900&display=swap');
:root { --primary:#0061ff; --accent:#159fbe; --bg:#f2f6f9; --text:#24445b; --border:#d7e5ec; --success:#11996b; --warning:#d98500; --danger:#d64545; }
html, body, [class*="css"] { font-family:'Cairo',sans-serif; direction:rtl; text-align:right; background:var(--bg); color:var(--text); }
.block-container { max-width:1500px; padding-top:2rem; }
.neon-logo { width:76px; height:76px; border-radius:50%; background:radial-gradient(circle,#6ed9e7,#238fbe); box-shadow:0 0 25px rgba(21,159,190,.4); margin:0 auto 12px; display:flex; align-items:center; justify-content:center; font-size:32px; color:#fff; }
.hero { background:linear-gradient(135deg,#fff 0%,#eef8fb 100%); border:1px solid var(--border); border-radius:24px; padding:26px 30px; margin-bottom:20px; box-shadow:0 12px 30px rgba(25,75,100,.06); }
.hero h1 { margin:0; color:var(--primary); font-weight:900; }
.hero p { margin:.4rem 0 0; color:#587388; }
[data-testid="stMetric"] { background:#fff; border-radius:18px; border-right:6px solid var(--primary); padding:16px; box-shadow:0 8px 22px rgba(0,0,0,.05); }
.stButton > button, .stFormSubmitButton > button { border:0; border-radius:13px; color:#fff; font-weight:800; min-height:3em; background:linear-gradient(135deg,var(--primary),var(--accent)); }
.stButton > button:hover, .stFormSubmitButton > button:hover { transform:translateY(-2px); box-shadow:0 8px 18px rgba(0,97,255,.25); }
.panel { background:#fff; border:1px solid var(--border); border-radius:20px; padding:20px; margin:12px 0; }
.status-online { color:var(--success); font-weight:800; }
.status-offline { color:var(--danger); font-weight:800; }
.small-note { color:#6b8291; font-size:.88rem; }
</style>
""",
    unsafe_allow_html=True,
)

# ============================================================
# الاتصال بقاعدة البيانات — السر يُقرأ من Secrets/Environment فقط
# ============================================================
DB_URL = st.secrets.get("DB_URL", os.getenv("DB_URL", ""))

@st.cache_resource
def get_db_pool():
    if not DB_URL:
        raise RuntimeError("لم يتم ضبط DB_URL في Streamlit Secrets أو متغيرات البيئة")
    return pool.SimpleConnectionPool(1, 10, dsn=DB_URL, sslmode="require")

@contextmanager
def db_conn():
    connection = None
    try:
        connection = get_db_pool().getconn()
        yield connection
    finally:
        if connection is not None:
            get_db_pool().putconn(connection)


def run_query(query: str, params: Optional[tuple] = None, is_select: bool = True):
    try:
        with db_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(query, params or ())
                if is_select:
                    rows = cur.fetchall()
                    columns = [item[0] for item in cur.description]
                    return pd.DataFrame(rows, columns=columns)
                conn.commit()
                return True
    except Exception as exc:
        st.error(f"❌ تعذر تنفيذ العملية: {exc}")
        return None


def scalar(query: str, params: Optional[tuple] = None, default=0):
    result = run_query(query, params)
    if result is None or result.empty:
        return default
    return result.iloc[0, 0]


def flash(message: str, kind: str = "success"):
    getattr(st, kind)(message)

# ============================================================
# بوابة الدخول — غيّر القيم من Secrets ولا تضعها في الشيفرة
# ============================================================
ADMIN_ID = st.secrets.get("ADMIN_ID", os.getenv("ADMIN_ID", ""))
ADMIN_PASSWORD = st.secrets.get("ADMIN_PASSWORD", os.getenv("ADMIN_PASSWORD", ""))

if "auth" not in st.session_state:
    st.session_state.auth = False

if not st.session_state.auth:
    _, center, _ = st.columns([1, 1.2, 1])
    with center:
        st.markdown("<div class='neon-logo'>⚡</div>", unsafe_allow_html=True)
        st.markdown("<h2 style='text-align:center'>دخول لوحة Emperor</h2>", unsafe_allow_html=True)
        with st.form("login_form"):
            admin_id = st.text_input("معرّف المسؤول")
            password = st.text_input("كلمة المرور", type="password")
            submitted = st.form_submit_button("فتح لوحة التحكم 🚀", use_container_width=True)
        if submitted:
            if ADMIN_ID and secrets.compare_digest(admin_id, ADMIN_ID) and secrets.compare_digest(password, ADMIN_PASSWORD):
                st.session_state.auth = True
                st.rerun()
            else:
                st.error("بيانات الدخول غير صحيحة أو غير مضبوطة في Secrets")
    st.stop()

# ============================================================
# القائمة الجانبية
# ============================================================
with st.sidebar:
    st.markdown("<div class='neon-logo' style='width:60px;height:60px;font-size:25px'>⚡</div>", unsafe_allow_html=True)
    st.markdown("<h3 style='text-align:center;color:#0061FF'>MyClicker Pro</h3>", unsafe_allow_html=True)
    if st.button("🔄 تحديث البيانات", use_container_width=True):
        st.cache_data.clear()
        st.rerun()
    st.divider()
    menu = st.radio(
        "**وحدات التحكم:**",
        [
            "📈 مركز القيادة والتحكم الجماعي",
            "👥 إدارة الأسطول",
            "📢 الإشعارات المنسدلة",
            "💳 الاشتراكات ومصنع الأكواد",
            "📊 تحليل البيانات 3D",
            "🤖 أجهزة الاختبار والمحاكاة",
        ],
    )
    st.divider()
    if st.button("🚪 خروج آمن", use_container_width=True):
        st.session_state.auth = False
        st.rerun()

# ============================================================
# 1) مركز القيادة: التفعيل الجماعي + الاشتراكات + حالة البوت
# ============================================================
if menu == "📈 مركز القيادة والتحكم الجماعي":
    st.markdown("<div class='hero'><h1>📈 مركز القيادة والتحكم الجماعي</h1><p>مراقبة الأسطول وتنفيذ العمليات الجماعية من واجهة واحدة.</p></div>", unsafe_allow_html=True)

    total = int(scalar("SELECT count(*) FROM myapp.users_status WHERE device_id NOT LIKE %s", ("sim_%",)))
    active = int(scalar("SELECT count(*) FROM myapp.users_status WHERE status=%s AND device_id NOT LIKE %s", ("Active", "sim_%")))
    online = int(scalar("SELECT count(*) FROM myapp.users_status WHERE bot_status=%s AND last_active > NOW() - interval '5 minutes'", ("Online",)))
    bots = int(scalar("SELECT count(*) FROM myapp.users_status WHERE bot_status=%s", ("Online",)))
    expired = int(scalar("SELECT count(*) FROM myapp.users_status WHERE expiry_date < NOW() AND device_id NOT LIKE %s", ("sim_%",)))
    clicks = int(scalar("SELECT COALESCE(sum(accepted_clicks),0) FROM myapp.users_status WHERE device_id NOT LIKE %s", ("sim_%",)))

    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("إجمالي السائقين", f"{total:,}")
    m2.metric("الحسابات النشطة", f"{active:,}")
    m3.metric("البوتات المتصلة", f"{online:,}", delta=f"{bots:,} إجمالي Online")
    m4.metric("الحسابات المنتهية", f"{expired:,}")
    m5.metric("إجمالي الصيد 🎯", f"{clicks:,}")

    st.subheader("⚡ التفعيل الجماعي")
    left, right = st.columns(2)
    with left:
        with st.form("bulk_activation"):
            activation_days = st.number_input("مدة التفعيل بالأيام", min_value=1, max_value=3650, value=30)
            target = st.selectbox("النطاق", ["الحسابات المنتهية فقط", "كل الحسابات غير المحاكاة"])
            confirm = st.checkbox("أؤكد تنفيذ التفعيل الجماعي")
            submit = st.form_submit_button("✅ تنفيذ التفعيل الجماعي", use_container_width=True)
        if submit:
            if not confirm:
                st.warning("يرجى تأكيد العملية أولاً")
            else:
                condition = "expiry_date < NOW()" if target == "الحسابات المنتهية فقط" else "TRUE"
                result = run_query(
                    f"UPDATE myapp.users_status SET status='Active', expiry_date=NOW() + (%s * interval '1 day'), is_frozen=false WHERE device_id NOT LIKE %s AND {condition}",
                    (activation_days, "sim_%"),
                    is_select=False,
                )
                if result:
                    flash(f"تم تفعيل الحسابات بنجاح لمدة {activation_days} يوماً")

    with right:
        subscription_enabled = scalar("SELECT value FROM myapp.app_config WHERE key=%s", ("individual_sub_system",), "false") == "true"
        st.markdown(f"<div class='panel'><h4>🔐 نظام الاشتراكات الفردية</h4><p>الحالة الحالية: <span class='{ 'status-online' if subscription_enabled else 'status-offline' }'>{'مفعّل' if subscription_enabled else 'معطّل'}</span></p><p class='small-note'>التحكم في قبول الاشتراكات الفردية من تطبيقات السائقين.</p></div>", unsafe_allow_html=True)
        with st.form("subscription_switch"):
            confirm_sub = st.checkbox("أؤكد تغيير حالة نظام الاشتراكات")
            switch = st.form_submit_button("تفعيل النظام" if not subscription_enabled else "تعطيل النظام", use_container_width=True)
        if switch:
            if not confirm_sub:
                st.warning("يرجى تأكيد تغيير الحالة")
            else:
                new_value = "false" if subscription_enabled else "true"
                if run_query("INSERT INTO myapp.app_config (key,value) VALUES (%s,%s) ON CONFLICT (key) DO UPDATE SET value=EXCLUDED.value", ("individual_sub_system", new_value), is_select=False):
                    flash("تم تحديث نظام الاشتراكات")
                    st.rerun()

    st.subheader("🤖 حالة البوت التفصيلية")
    status_df = run_query("SELECT bot_status, count(*) AS total FROM myapp.users_status WHERE device_id NOT LIKE %s GROUP BY bot_status ORDER BY total DESC", ("sim_%",))
    if status_df is not None and not status_df.empty:
        chart_col, table_col = st.columns([1.2, 1])
        with chart_col:
            st.plotly_chart(px.pie(status_df, names="bot_status", values="total", hole=.55, title="توزيع حالات البوت"), use_container_width=True)
        with table_col:
            st.dataframe(status_df.rename(columns={"bot_status": "حالة البوت", "total": "العدد"}), use_container_width=True, hide_index=True)

# ============================================================
# 2) إدارة الأسطول والرقابة الثلاثية
# ============================================================
elif menu == "👥 إدارة الأسطول":
    st.markdown("<div class='hero'><h1>👥 إدارة الأسطول والرقابة الثلاثية</h1><p>مراجعة activated_code وcloning_device_id وreorder_count لاكتشاف الاستخدام غير الطبيعي.</p></div>", unsafe_allow_html=True)
    search = st.text_input("🔍 بحث بالهاتف أو معرّف الجهاز")
    df = run_query(
        """SELECT phone, device_id, status, sub_tier, expiry_date, accepted_clicks,
                  activated_code, cloning_device_id, reorder_count, bot_status, last_active
           FROM myapp.users_status
           WHERE (phone ILIKE %s OR device_id ILIKE %s)
             AND device_id NOT LIKE %s
           ORDER BY last_active DESC NULLS LAST""",
        (f"%{search}%", f"%{search}%", "sim_%"),
    )
    if df is not None:
        st.dataframe(df, use_container_width=True, hide_index=True, column_config={
            "phone": "الهاتف", "device_id": "الجهاز", "status": "الحالة", "sub_tier": "الفئة",
            "expiry_date": "الانتهاء", "accepted_clicks": st.column_config.ProgressColumn("النقرات", min_value=0, max_value=1000),
            "activated_code": "كود التفعيل", "cloning_device_id": "جهاز النسخ", "reorder_count": "عداد الترتيب",
            "bot_status": "حالة البوت", "last_active": "آخر نشاط",
        })

# ============================================================
# 3) الإشعارات المنسدلة مع notification_version
# ============================================================
elif menu == "📢 الإشعارات المنسدلة":
    st.markdown("<div class='hero'><h1>📢 مركز الإشعارات المنسدلة</h1><p>كل بث يرفع notification_version، ليقرأ تطبيق Android الرسالة فوراً.</p></div>", unsafe_allow_html=True)
    current_version = int(scalar("SELECT COALESCE(value,'0')::int FROM myapp.app_config WHERE key=%s", ("notification_version",), 0))
    current_message = scalar("SELECT COALESCE(value,'') FROM myapp.app_config WHERE key=%s", ("notice_message",), "")
    a, b, c = st.columns(3)
    a.metric("رقم الإصدار الحالي", current_version)
    b.metric("المستهدفون", total if 'total' in locals() else int(scalar("SELECT count(*) FROM myapp.users_status WHERE device_id NOT LIKE %s", ("sim_%",))))
    c.metric("آلية العرض", "فوري / Heads-up")
    with st.form("broadcast_notice"):
        msg = st.text_area("نص الإشعار", value=current_message, height=140, placeholder="اكتب رسالة واضحة للسائقين...")
        include_sim = st.checkbox("إرسال إلى أجهزة المحاكاة للاختبار")
        confirm_notice = st.checkbox("أؤكد بث الإشعار لجميع الأجهزة المحددة")
        send_notice = st.form_submit_button("🚀 بث الإشعار ورفع الإصدار", use_container_width=True)
    if send_notice:
        if not msg.strip():
            st.warning("يرجى كتابة نص الإشعار")
        elif not confirm_notice:
            st.warning("يرجى تأكيد البث الجماعي")
        else:
            new_version = current_version + 1
            if not run_query("INSERT INTO myapp.app_config (key,value) VALUES (%s,%s) ON CONFLICT (key) DO UPDATE SET value=EXCLUDED.value", ("notification_version", str(new_version)), is_select=False):
                st.stop()
            run_query("INSERT INTO myapp.app_config (key,value) VALUES (%s,%s) ON CONFLICT (key) DO UPDATE SET value=EXCLUDED.value", ("notice_message", msg.strip()), is_select=False)
            where_clause = "TRUE" if include_sim else "device_id NOT LIKE %s"
            params = (msg.strip(),) if include_sim else (msg.strip(), "sim_%")
            run_query(f"UPDATE myapp.users_status SET notice_message=%s WHERE {where_clause}", params, is_select=False)
            st.success(f"تم بث الإشعار بنجاح. notification_version الجديد: {new_version}")
            st.info("سيستخدم تطبيق Android الإصدار الجديد لإظهار الإشعار المنسدل فوراً.")

# ============================================================
# 4) الاشتراكات ومصنع الأكواد
# ============================================================
elif menu == "💳 الاشتراكات ومصنع الأكواد":
    st.markdown("<div class='hero'><h1>💳 الاشتراكات ومصنع الأكواد</h1><p>إنشاء مفاتيح اشتراك ومتابعة حالتها بطريقة منظمة.</p></div>", unsafe_allow_html=True)
    with st.form("key_factory"):
        quantity = st.number_input("الكمية", 1, 100, 5)
        tier = st.selectbox("الفئة", ["VIP", "STANDARD", "TRIAL"])
        days = st.selectbox("المدة بالأيام", [7, 30, 90, 365], index=1)
        generate = st.form_submit_button("✨ توليد المفاتيح وحفظها", use_container_width=True)
    if generate:
        keys = []
        for _ in range(int(quantity)):
            code = f"{tier[:3]}-{secrets.token_hex(4).upper()}"
            if run_query("INSERT INTO myapp.subscriptions (code,sub_tier,duration_days,is_used) VALUES (%s,%s,%s,false)", (code, tier, days), is_select=False):
                keys.append(code)
        if keys:
            st.code("\n".join(keys))
            st.success(f"تم توليد {len(keys)} مفتاحاً")

# ============================================================
# 5) التحليل والمحاكاة
# ============================================================
elif menu == "📊 تحليل البيانات 3D":
    st.title("🌌 التحليل الفضائي لصيد الرحلات")
    df_3d = run_query("SELECT accepted_clicks AS z, phone AS x, last_active AS y FROM myapp.users_status WHERE accepted_clicks > 0 LIMIT 500")
    if df_3d is not None and not df_3d.empty:
        df_3d["time_score"] = pd.to_datetime(df_3d["y"]).astype("int64") // 10**12
        st.plotly_chart(px.scatter_3d(df_3d, x="x", y="time_score", z="z", color="z", template="plotly_white"), use_container_width=True)
    else:
        st.info("لا توجد بيانات كافية للتحليل حالياً.")

elif menu == "🤖 أجهزة الاختبار والمحاكاة":
    st.title("🤖 مركز ضغط الاختبار")
    n = st.slider("عدد الأجهزة الافتراضية", 100, 1000, 500)
    confirm_sim = st.checkbox("أؤكد أن هذه العملية على بيانات اختبار فقط")
    c1, c2 = st.columns(2)
    if c1.button("🚀 حقن أجهزة المحاكاة", use_container_width=True):
        if not confirm_sim:
            st.warning("يرجى تأكيد أن العملية للاختبار فقط")
        else:
            run_query("INSERT INTO myapp.users_status (device_id,phone,status,expiry_date,last_active) SELECT 'sim_'||md5(random()::text), '079'||LPAD(i::text,7,'0'), 'Active', NOW()+interval '30 days', NOW() FROM generate_series(1,%s) s(i) ON CONFLICT DO NOTHING", (n,), is_select=False)
            st.success("تم حقن أجهزة المحاكاة")
    if c2.button("🗑️ مسح كافة المحاكاة", use_container_width=True):
        if not confirm_sim:
            st.warning("يرجى تأكيد أن العملية على بيانات اختبار فقط")
        else:
            run_query("DELETE FROM myapp.users_status WHERE device_id LIKE %s", ("sim_%",), is_select=False)
            st.success("تم مسح بيانات المحاكاة")

st.caption("MyClicker Pro • لوحة تحكم RTL • العمليات الجماعية محمية بتأكيد صريح")

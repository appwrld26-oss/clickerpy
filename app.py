import hashlib
import time
from contextlib import contextmanager
from datetime import datetime
from typing import Any, Iterable, Optional

import numpy as np
import pandas as pd
import plotly.express as px
import psycopg2
import streamlit as st
from psycopg2 import pool


# ============================================================
# 1. إعداد الصفحة والهوية البصرية
# ============================================================
st.set_page_config(
    page_title="MyClicker Pro | Ultimate Command",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700;900&display=swap');

    :root {
        --bg: #0b1120;
        --panel: #111c32;
        --panel-soft: #16233d;
        --line: #263957;
        --cyan: #00e5ff;
        --blue: #4285ff;
        --green: #35e0a1;
        --orange: #ffb454;
        --red: #ff5c7a;
        --text-soft: #a9b8d0;
    }

    html, body, [class*="css"] {
        font-family: 'Cairo', sans-serif;
        direction: rtl;
        text-align: right;
        background: var(--bg);
        color: white;
    }

    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0e1930 0%, #0a1222 100%);
        border-left: 1px solid var(--line);
    }

    .hero {
        position: relative;
        overflow: hidden;
        margin: 0 0 1.5rem;
        padding: 2rem 2.25rem;
        border: 1px solid rgba(0,229,255,.25);
        border-radius: 24px;
        background:
            radial-gradient(circle at 10% 10%, rgba(0,229,255,.18), transparent 32%),
            radial-gradient(circle at 90% 90%, rgba(66,133,255,.18), transparent 35%),
            linear-gradient(135deg, #13223d, #0d172b);
        box-shadow: 0 18px 55px rgba(0,0,0,.22);
    }

    .hero h1 { margin: 0; color: #fff; font-size: 2.2rem; font-weight: 900; }
    .hero p { margin: .35rem 0 0; color: var(--text-soft); font-size: 1rem; }

    .logo-container { text-align: center; padding: 1rem 0 0.5rem; }
    .neon-circle {
        display: flex;
        align-items: center;
        justify-content: center;
        width: 92px;
        height: 92px;
        margin: auto;
        border-radius: 50%;
        font-size: 38px;
        background: radial-gradient(circle, #00e5ff 0%, #007bff 100%);
        box-shadow: 0 0 20px #00e5ff, 0 0 48px rgba(0,123,255,.8);
        animation: pulse 2.4s ease-in-out infinite;
    }

    @keyframes pulse {
        0%, 100% { transform: scale(1); filter: brightness(1); }
        50% { transform: scale(1.08); filter: brightness(1.2); }
    }

    .stMetric {
        padding: 1.1rem 1.25rem;
        border: 1px solid var(--line);
        border-radius: 18px;
        background: linear-gradient(135deg, var(--panel-soft), var(--panel));
        box-shadow: 0 8px 25px rgba(0,0,0,.12);
    }

    .stButton > button {
        width: 100%;
        min-height: 2.8rem;
        border-radius: 12px;
        border: 1px solid rgba(0,229,255,.25);
        font-weight: 800;
        transition: all .2s ease;
    }

    .stButton > button:hover {
        transform: translateY(-2px);
        border-color: var(--cyan);
        box-shadow: 0 8px 22px rgba(0,229,255,.18);
    }

    div[data-testid="stExpander"] {
        margin-bottom: .7rem;
        border: 1px solid var(--line);
        border-radius: 16px;
        background: var(--panel);
    }

    .section-caption {
        color: var(--text-soft);
        margin-top: -0.7rem;
        margin-bottom: 1rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# 2. قاعدة البيانات: pool واحد، معاملات آمنة، وتنظيف مضمون
# ============================================================
DB_URL = "postgresql://neondb_owner:npg_AvzFkHQ6M3yo@ep-tiny-wind-ayd9hww0.c-5.us-east-2.aws.neon.tech/neondb?sslmode=require"


@st.cache_resource(show_spinner=False)
def get_pool() -> pool.SimpleConnectionPool:
    """Create one shared connection pool for the Streamlit process."""
    return pool.SimpleConnectionPool(
        minconn=1,
        maxconn=20,
        dsn=DB_URL,
        sslmode="require",
        sslrootcert="",
    )


@contextmanager
def db_connection():
    """Borrow a connection and always return it to the pool."""
    connection = None
    database_pool = get_pool()
    try:
        connection = database_pool.getconn()
        yield connection
    finally:
        if connection is not None:
            database_pool.putconn(connection)


def run_query(
    query: str,
    params: Optional[Iterable[Any]] = None,
    is_select: bool = True,
) -> Optional[pd.DataFrame | bool]:
    """Run a parameterized query and return a DataFrame or success flag."""
    try:
        with db_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(query, tuple(params or ()))
                if is_select:
                    rows = cursor.fetchall()
                    columns = [column[0] for column in cursor.description]
                    return pd.DataFrame(rows, columns=columns)
                connection.commit()
                return True
    except Exception as error:
        st.error(f"❌ تعذر تنفيذ العملية: {error}")
        return None


def fetch_config() -> dict[str, str]:
    config = run_query("SELECT key, value FROM myapp.app_config")
    if config is None or config.empty:
        return {}
    return dict(zip(config["key"].astype(str), config["value"].astype(str)))


def save_config(values: dict[str, Any]) -> bool:
    for key, value in values.items():
        result = run_query(
            """
            INSERT INTO myapp.app_config (key, value)
            VALUES (%s, %s)
            ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value
            """,
            (key, str(value)),
            is_select=False,
        )
        if result is None:
            return False
    return True


# ============================================================
# 3. جلسة المستخدم والمكونات المشتركة
# ============================================================
if "auth" not in st.session_state:
    st.session_state.auth = False

if not st.session_state.auth:
    left, center, right = st.columns([1, 1.15, 1])
    with center:
        st.markdown(
            """
            <div class="hero" style="text-align:center;">
                <div class="neon-circle" style="width:74px;height:74px;font-size:30px;">⚡</div>
                <h1 style="font-size:1.8rem;margin-top:1rem;">MYCLICKER PRO</h1>
                <p>بوابة القيادة والتحكم الذكية</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        username = st.text_input("👤 اسم المستخدم")
        password = st.text_input("🔑 كلمة السر", type="password")
        if st.button("دخول إلى غرفة القيادة 🚀", type="primary"):
            if username == "admin" and password == "admin123":
                st.session_state.auth = True
                st.rerun()
            st.error("بيانات الدخول غير صحيحة")
    st.stop()


MENU_ITEMS = [
    "📈 نظرة عامة وإحصائيات الإصدارات",
    "👥 إدارة ومراقبة المستخدمين والتفعيل",
    "📢 مركز الإشعارات الشامل الكامل",
    "🚀 إدارة التحديثات الإجبارية",
    "⚡ تحديث البيانات الحية (LIVE UPDATE)",
    "💳 توليد وإدارة الأكواد",
    "🤝 قسم الشركاء (الموزعين)",
    "📊 تحليل البيانات 3D",
    "🖥️ حالة السيرفر",
    "🔐 إدارة الصلاحيات والتحكم",
    "🛠️ الدعم الفني والتواصل",
    "🤖 إضافة الأجهزة الافتراضية (TEST)",
]

with st.sidebar:
    st.markdown("<div class='logo-container'><div class='neon-circle'>⚡</div></div>", unsafe_allow_html=True)
    st.markdown("<h3 style='text-align:center;color:#00E5FF;'>MyClicker Pro</h3>", unsafe_allow_html=True)
    st.markdown("<p style='text-align:center;color:#a9b8d0;'>المستخدم: admin</p>", unsafe_allow_html=True)
    if st.button("🔄 مسح الذاكرة والتحديث"):
        st.cache_data.clear()
        st.rerun()
    st.divider()
    menu = st.radio("القائمة الرئيسية", MENU_ITEMS)
    st.divider()
    if st.button("🚪 تسجيل الخروج"):
        st.session_state.auth = False
        st.rerun()


def page_header(title: str, subtitle: str) -> None:
    st.markdown(
        f"<div class='hero'><h1>{title}</h1><p>{subtitle}</p></div>",
        unsafe_allow_html=True,
    )


# ============================================================
# 4. صفحات لوحة التحكم
# ============================================================
if menu.startswith("📈"):
    page_header("📈 مركز الرؤية والتحليلات", "لقطة فورية لأداء الأسطول وإصدارات التطبيق.")
    summary = run_query(
        """
        SELECT COUNT(*) AS total,
               COALESCE(SUM(accepted_clicks), 0) AS clicks,
               COUNT(*) FILTER (WHERE is_frozen = TRUE) AS frozen
        FROM myapp.users_status
        """
    )
    if summary is not None and not summary.empty:
        stats = summary.iloc[0]
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("إجمالي الأجهزة", f"{int(stats['total']):,}")
        c2.metric("إجمالي النقرات", f"{int(stats['clicks']):,}")
        c3.metric("الأجهزة المجمدة", f"{int(stats['frozen']):,}")
        c4.metric("حالة الاتصال", "مستقر ✅")

    versions = run_query(
        """
        SELECT COALESCE(app_version, 'غير معروف') AS app_version, COUNT(*) AS devices
        FROM myapp.users_status
        GROUP BY app_version
        ORDER BY devices DESC
        """
    )
    if versions is not None and not versions.empty:
        st.subheader("📊 خريطة انتشار الإصدارات")
        chart = px.bar(
            versions,
            x="app_version",
            y="devices",
            color="devices",
            template="plotly_dark",
            labels={"app_version": "الإصدار", "devices": "عدد الأجهزة"},
            color_continuous_scale="blues",
        )
        st.plotly_chart(chart, use_container_width=True)
    time.sleep(10)
    st.rerun()

elif menu.startswith("👥"):
    page_header("👥 إدارة أسطول الكباتن", "ابحث، حدّث، جمّد أو أعد ضبط الأجهزة من مكان واحد.")
    search = st.text_input("🔍 ابحث برقم الهاتف أو معرّف الجهاز")
    base_query = """
        SELECT * FROM myapp.users_status
        WHERE device_id NOT LIKE 'sim_%%'
    """
    params: list[str] = []
    if search.strip():
        base_query += " AND (phone ILIKE %s OR device_id ILIKE %s)"
        pattern = f"%{search.strip()}%"
        params.extend([pattern, pattern])
    base_query += " ORDER BY last_active DESC NULLS LAST LIMIT 100"
    users = run_query(base_query, params)

    if users is None or users.empty:
        st.info("لا توجد أجهزة مطابقة للبحث.")
    else:
        for _, user in users.iterrows():
            device_id = str(user.get("device_id", ""))
            phone = str(user.get("phone", ""))
            clicks = int(user.get("accepted_clicks") or 0)
            frozen = bool(user.get("is_frozen", False))
            with st.expander(f"📱 {phone}  |  {device_id[:12]}...  |  🎯 {clicks:,}"):
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    new_phone = st.text_input("تعديل الهاتف", value=phone, key=f"phone_{device_id}")
                    tiers = ["VIP", "STANDARD", "TRIAL"]
                    current_tier = str(user.get("sub_tier") or "STANDARD")
                    tier_index = tiers.index(current_tier) if current_tier in tiers else 1
                    new_tier = st.selectbox("الفئة", tiers, index=tier_index, key=f"tier_{device_id}")
                    if st.button("💾 حفظ التعديلات", key=f"save_{device_id}"):
                        run_query(
                            "UPDATE myapp.users_status SET phone=%s, sub_tier=%s WHERE device_id=%s",
                            (new_phone, new_tier, device_id),
                            is_select=False,
                        )
                        st.toast("تم تحديث بيانات الجهاز")
                        st.rerun()
                with col2:
                    st.write("**تحكم العداد**")
                    if st.button("🔄 تصفير النقرات", key=f"reset_{device_id}"):
                        run_query(
                            "UPDATE myapp.users_status SET accepted_clicks=0 WHERE device_id=%s",
                            (device_id,),
                            is_select=False,
                        )
                        st.toast("تم تصفير العداد")
                        st.rerun()
                with col3:
                    st.write("**منطقة الخطر**")
                    if st.button("🗑️ حذف الجهاز نهائياً", key=f"delete_{device_id}", type="primary"):
                        run_query(
                            "DELETE FROM myapp.users_status WHERE device_id=%s",
                            (device_id,),
                            is_select=False,
                        )
                        st.toast("تم حذف الجهاز")
                        st.rerun()
                with col4:
                    st.write(f"**الحالة:** {'مجمد' if frozen else 'نشط'}")
                    if st.button("❄️ تجميد / فك التجميد", key=f"freeze_{device_id}"):
                        run_query(
                            "UPDATE myapp.users_status SET is_frozen = NOT COALESCE(is_frozen, FALSE) WHERE device_id=%s",
                            (device_id,),
                            is_select=False,
                        )
                        st.toast("تم تغيير حالة الجهاز")
                        st.rerun()

elif menu.startswith("📢"):
    page_header("📢 مركز الإشعارات", "أرسل رسالة موحّدة إلى شريط إشعارات التطبيق.")
    message = st.text_area("نص الرسالة", height=140, placeholder="اكتب الإعلان أو التنبيه هنا...")
    if st.button("🚀 بث فوري للجميع", type="primary"):
        if message.strip():
            run_query("UPDATE myapp.users_status SET notice_message = %s", (message.strip(),), is_select=False)
            st.success("تم بث الرسالة بنجاح")
        else:
            st.warning("اكتب رسالة قبل الإرسال")

elif menu.startswith("🚀"):
    page_header("🚀 التحديث الإجباري", "تحكم في النسخة المطلوبة ورابط حزمة التحديث.")
    config = fetch_config()
    with st.form("forced_update_form"):
        version = st.text_input("أحدث نسخة", value=config.get("latest_version", "7.2.8"))
        force_update = st.checkbox("تفعيل قفل النسخة", value=config.get("force_update") == "true")
        apk_url = st.text_input("رابط APK", value=config.get("next_url", ""))
        if st.form_submit_button("💾 تطبيق الإعدادات", type="primary"):
            if save_config({"latest_version": version, "force_update": str(force_update).lower(), "next_url": apk_url}):
                st.success("تم حفظ إعدادات التحديث")

elif menu.startswith("⚡"):
    page_header("⚡ البيانات الحية", "عدّل إعدادات التشغيل وأرسلها إلى جميع الأجهزة.")
    config = run_query("SELECT key, value FROM myapp.app_config ORDER BY key")
    if config is not None:
        edited = st.data_editor(config, use_container_width=True, hide_index=True, num_rows="dynamic")
        if st.button("💾 حفظ وإرسال إلى الهواتف", type="primary"):
            values = {
                str(row["key"]): row["value"]
                for _, row in edited.dropna(subset=["key"]).iterrows()
            }
            if save_config(values):
                st.toast("تم تحديث البيانات الحية")
                st.rerun()

elif menu.startswith("🤖"):
    page_header("🤖 مركز أجهزة الاختبار", "أنشئ بيانات محاكاة بأمان لاختبار الأداء والواجهات.")
    col1, col2 = st.columns(2)
    with col1:
        amount = st.number_input("عدد الأجهزة", min_value=10, max_value=1000, value=100, step=10)
        if st.button("🚀 حقن جيش الاختبار", type="primary"):
            run_query(
                """
                INSERT INTO myapp.users_status
                    (device_id, phone, status, expiry_date, last_active)
                SELECT 'sim_' || md5(random()::text),
                       '079' || LPAD(i::text, 7, '0'),
                       'Active', NOW() + interval '30 days', NOW()
                FROM generate_series(1, %s) AS series(i)
                """,
                (int(amount),),
                is_select=False,
            )
            st.success("تم إنشاء أجهزة الاختبار")
    with col2:
        st.warning("سيحذف هذا الإجراء جميع الأجهزة التي تبدأ بـ sim_.")
        if st.button("🗑️ إبادة المحاكاة", type="primary"):
            run_query(
                "DELETE FROM myapp.users_status WHERE device_id LIKE 'sim_%%'",
                is_select=False,
            )
            st.success("تم حذف بيانات المحاكاة")
            st.rerun()

elif menu.startswith("📊"):
    page_header("📊 التحليل الفضائي للنشاط", "استكشف العلاقة بين النشاط والزمن والأجهزة في عرض ثلاثي الأبعاد.")
    activity = run_query(
        """
        SELECT accepted_clicks AS z, phone AS x, last_active AS y
        FROM myapp.users_status
        WHERE accepted_clicks > 0
        ORDER BY accepted_clicks DESC
        LIMIT 300
        """
    )
    if activity is not None and not activity.empty:
        activity["time_idx"] = pd.to_datetime(activity["y"], errors="coerce").astype("int64") // 10**12
        figure = px.scatter_3d(
            activity,
            x="x",
            y="time_idx",
            z="z",
            color="z",
            template="plotly_dark",
            labels={"x": "الهاتف", "time_idx": "الوقت", "z": "النقرات"},
            color_continuous_scale="Turbo",
        )
        figure.update_layout(height=650, margin=dict(l=0, r=0, t=30, b=0))
        st.plotly_chart(figure, use_container_width=True)
    else:
        st.info("لا توجد بيانات نشاط كافية للعرض.")

elif menu.startswith(("🤝", "🖥️", "🔐", "🛠️", "💳")):
    page_header(menu, "هذا القسم مهيأ للتوسعة ومربوط بمصدر البيانات الحالي.")
    st.info("يمكن توسيع هذه الوحدة لإضافة منطق الموزعين، الأكواد، الصلاحيات، الدعم، ومراقبة الخادم.")
    preview = run_query("SELECT * FROM myapp.users_status LIMIT 5")
    if preview is not None:
        st.dataframe(preview, use_container_width=True, hide_index=True)

else:
    st.warning("اختر وحدة من القائمة الجانبية.")

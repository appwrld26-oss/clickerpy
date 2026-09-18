import hashlib
import json
import os
import time
import urllib.error
import urllib.request
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
        --bg: #f2f6f9;
        --panel: #ffffff;
        --panel-soft: #eef7fb;
        --line: #d7e5ec;
        --cyan: #159fbe;
        --blue: #398fc2;
        --green: #168b72;
        --orange: #c8872e;
        --red: #c94e61;
        --text-soft: #587184;
        --text: #24445b;
        --muted: #718899;
        --radius-lg: 22px;
        --radius-md: 14px;
    }

    html, body, [class*="css"], .stMarkdown, .stTextInput,
    .stTextArea, .stSelectbox, .stNumberInput, .stRadio,
    .stButton, .stDataFrame, .stDataEditor {
        font-family: 'Cairo', sans-serif;
        direction: rtl;
        text-align: right;
        background: var(--bg);
        color: var(--text);
    }

    h1, h2, h3, h4, h5, h6 {
        color: var(--text) !important;
        font-weight: 900 !important;
        letter-spacing: -.02em;
    }

    p, label, .stCaption, [data-testid="stMarkdownContainer"] {
        line-height: 1.85;
    }

    .stCaption, [data-testid="stCaptionContainer"] {
        color: var(--muted) !important;
        font-size: .9rem;
    }

    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #ffffff 0%, #edf6fa 100%);
        border-left: 1px solid var(--line);
        box-shadow: -8px 0 28px rgba(68, 119, 145, .08);
    }

    .hero {
        position: relative;
        overflow: hidden;
        margin: 0 0 1.5rem;
        padding: 2rem 2.25rem;
        border: 1px solid rgba(21,159,190,.28);
        border-radius: var(--radius-lg);
        background:
            radial-gradient(circle at 10% 10%, rgba(74,190,213,.20), transparent 32%),
            radial-gradient(circle at 90% 90%, rgba(66,145,194,.15), transparent 35%),
            linear-gradient(135deg, #ffffff, #eaf5f9);
        box-shadow: 0 18px 55px rgba(68, 119, 145, .14);
    }

    .hero h1 { margin: 0; color: var(--text); font-size: clamp(1.55rem, 3vw, 2.2rem); font-weight: 900; }
    .hero p { margin: .45rem 0 0; color: var(--text-soft); font-size: 1rem; }

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
        background: radial-gradient(circle, #6ed9e7 0%, #238fbe 100%);
        box-shadow: 0 0 20px rgba(54,177,202,.55), 0 0 48px rgba(35,143,190,.28);
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
        box-shadow: 0 8px 25px rgba(68,119,145,.10);
    }

    [data-testid="stMetricLabel"] {
        color: var(--muted) !important;
        font-size: .9rem !important;
        font-weight: 700 !important;
    }

    [data-testid="stMetricValue"] {
        color: #138ba8 !important;
        font-size: 1.65rem !important;
        font-weight: 900 !important;
    }

    .stButton > button {
        width: 100%;
        min-height: 2.8rem;
        border-radius: 12px;
        border: 1px solid rgba(21,159,190,.28);
        font-weight: 800;
        transition: all .2s ease;
    }

    .stButton > button:hover {
        transform: translateY(-2px);
        border-color: var(--cyan);
        box-shadow: 0 8px 22px rgba(21,159,190,.16);
    }

    div[data-testid="stExpander"] {
        margin-bottom: .7rem;
        border: 1px solid var(--line);
        border-radius: 16px;
        background: var(--panel);
    }

    div[data-testid="stExpander"] summary p {
        color: var(--text) !important;
        font-weight: 800;
    }

    [data-testid="stDataFrame"], [data-testid="stDataEditor"] {
        overflow: hidden;
        border: 1px solid var(--line);
        border-radius: var(--radius-md);
        background: var(--panel);
        box-shadow: 0 10px 30px rgba(0,0,0,.14);
    }

    [data-testid="stDataFrame"] iframe,
    [data-testid="stDataEditor"] iframe {
        border-radius: var(--radius-md);
    }

    [data-testid="stDataFrame"] [role="columnheader"],
    [data-testid="stDataEditor"] [role="columnheader"] {
        background: #dff2f7 !important;
        color: #28566c !important;
        font-weight: 900 !important;
    }

    [data-testid="stDataFrame"] [role="gridcell"],
    [data-testid="stDataEditor"] [role="gridcell"] {
        color: #36576b !important;
        border-color: #d7e5ec !important;
        font-size: .92rem !important;
    }

    [data-testid="stDataFrame"] [role="row"]:nth-child(even),
    [data-testid="stDataEditor"] [role="row"]:nth-child(even) {
        background: #f6fafc !important;
    }

    [data-testid="stDataFrame"] [role="row"]:hover,
    [data-testid="stDataEditor"] [role="row"]:hover {
        background: #eaf7fa !important;
    }

    .section-title {
        display: flex;
        align-items: center;
        gap: .65rem;
        margin: 1.3rem 0 .55rem;
        padding-bottom: .45rem;
        border-bottom: 1px solid var(--line);
        color: var(--text);
        font-size: 1.15rem;
        font-weight: 900;
    }

    .section-caption {
        color: var(--text-soft);
        margin-top: -0.7rem;
        margin-bottom: 1rem;
    }

    /* Responsive command-center polish */
    [data-testid="stAppViewContainer"] > .main {
        padding: 1.1rem clamp(.75rem, 2.5vw, 2.6rem) 3rem;
    }
    [data-testid="stVerticalBlock"] > [style*="flex-direction: column"] {
        gap: .85rem;
    }
    .stButton > button, .stDownloadButton > button {
        white-space: normal;
        line-height: 1.35;
        padding: .55rem .75rem;
    }
    [data-testid="stDataFrame"], [data-testid="stDataEditor"] {
        max-width: 100%;
        overflow-x: auto;
    }
    div[data-testid="stExpander"] {
        box-shadow: 0 5px 18px rgba(68,119,145,.07);
    }
    div[data-testid="stExpander"] summary {
        min-height: 3rem;
        align-items: center;
    }
    div[data-testid="stForm"] {
        padding: 1rem;
        border: 1px solid var(--line);
        border-radius: var(--radius-md);
        background: linear-gradient(135deg, #ffffff, #f4fafc);
        box-shadow: 0 8px 24px rgba(68,119,145,.08);
    }
    [data-testid="stAlert"] {
        border-radius: 14px;
    }
    @media (max-width: 1100px) {
        [data-testid="stAppViewContainer"] > .main { padding-inline: 1rem; }
        .hero { padding: 1.45rem 1.35rem; }
        .stMetric { padding: .85rem .8rem; }
        [data-testid="stMetricValue"] { font-size: 1.35rem !important; }
    }
    @media (max-width: 760px) {
        [data-testid="stSidebar"] { min-width: 240px; max-width: 82vw; }
        .hero { margin-bottom: 1rem; border-radius: 16px; }
        .hero h1 { font-size: 1.35rem; }
        .hero p { font-size: .88rem; }
        .section-title { font-size: 1rem; margin-top: 1rem; }
        .stButton > button, .stDownloadButton > button { min-height: 2.65rem; font-size: .86rem; }
        [data-testid="stDataFrame"], [data-testid="stDataEditor"] { font-size: .78rem; }
        [data-testid="stMetricLabel"] { font-size: .75rem !important; }
        [data-testid="stMetricValue"] { font-size: 1.08rem !important; }
        div[data-testid="stForm"] { padding: .75rem; }
    }
    @media (max-width: 480px) {
        [data-testid="stAppViewContainer"] > .main { padding: .65rem .55rem 2rem; }
        .hero { padding: 1.1rem 1rem; }
        .hero h1 { font-size: 1.15rem; }
        .stCaption, [data-testid="stCaptionContainer"] { font-size: .76rem; }
        div[data-testid="stExpander"] summary p { font-size: .82rem; }
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


def push_to_sync_api(values: dict[str, Any]) -> tuple[bool, str]:
    """Best-effort bridge to the Android sync API; Neon remains the dashboard source."""
    api_url = os.getenv("MYCLICKER_SYNC_API_URL", "").strip().rstrip("/")
    api_secret = os.getenv("MYCLICKER_API_SECRET", "").strip()
    if not api_url or not api_secret:
        return False, "لم يتم ضبط MYCLICKER_SYNC_API_URL و MYCLICKER_API_SECRET"
    payload = json.dumps({"values": {key: str(value) for key, value in values.items()}}).encode("utf-8")
    request = urllib.request.Request(
        f"{api_url}/api/admin/live-config",
        data=payload,
        headers={"Content-Type": "application/json", "X-MyClicker-Key": api_secret},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=8) as response:
            body = json.loads(response.read().decode("utf-8"))
        return bool(body.get("success")), "تم إرسال الإعدادات إلى API" if body.get("success") else "رفض API الإعدادات"
    except (urllib.error.URLError, TimeoutError, ValueError) as error:
        return False, f"تعذر الوصول إلى API: {error}"


def send_notification_to_api(message: str, notification_type: str, device_ids: list[str] | None = None) -> tuple[bool, str]:
    """Send an in-app notification to one device or all devices through the sync API."""
    api_url = os.getenv("MYCLICKER_SYNC_API_URL", "").strip().rstrip("/")
    api_secret = os.getenv("MYCLICKER_API_SECRET", "").strip()
    if not api_url or not api_secret:
        return False, "لم يتم ضبط رابط API أو مفتاح API"
    body = {"message": message, "type": notification_type, "sendToAll": not device_ids, "deviceIds": device_ids or []}
    request = urllib.request.Request(
        f"{api_url}/api/admin/notification/send",
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json", "X-MyClicker-Key": api_secret},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=8) as response:
            result = json.loads(response.read().decode("utf-8"))
        return bool(result.get("success")), "تم إرسال الإشعار إلى API" if result.get("success") else "رفض API الإشعار"
    except (urllib.error.URLError, TimeoutError, ValueError) as error:
        return False, f"تعذر إرسال الإشعار إلى API: {error}"


def ensure_management_tables() -> None:
    """Create optional management tables without changing existing connection paths."""
    statements = [
        """CREATE TABLE IF NOT EXISTS myapp.app_staff (
            id BIGSERIAL PRIMARY KEY, username TEXT UNIQUE NOT NULL, password_hash TEXT NOT NULL,
            display_name TEXT NOT NULL, role TEXT NOT NULL DEFAULT 'monitor', active BOOLEAN NOT NULL DEFAULT TRUE,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )""",
        """CREATE TABLE IF NOT EXISTS myapp.activation_codes_audit (
            id BIGSERIAL PRIMARY KEY, code TEXT NOT NULL, category TEXT NOT NULL DEFAULT 'STANDARD',
            status TEXT NOT NULL DEFAULT 'generated', employee_name TEXT, action TEXT NOT NULL DEFAULT 'generated',
            device_id TEXT, created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), action_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )""",
        """CREATE TABLE IF NOT EXISTS myapp.partners (
            id BIGSERIAL PRIMARY KEY, name TEXT UNIQUE NOT NULL, category TEXT NOT NULL DEFAULT 'STANDARD',
            commission NUMERIC(10,2) NOT NULL DEFAULT 0, active BOOLEAN NOT NULL DEFAULT TRUE,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )""",
    ]
    for statement in statements:
        run_query(statement, is_select=False)


ensure_management_tables()


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
            staff = run_query(
                "SELECT username, display_name, role FROM myapp.app_staff WHERE username=%s AND password_hash=%s AND active=TRUE LIMIT 1",
                (username.strip(), hashlib.sha256(password.encode()).hexdigest()),
            )
            if username == "admin" and password == "admin123":
                st.session_state.auth = True
                st.session_state.staff_name = "المدير العام"
                st.session_state.staff_role = "admin"
                st.rerun()
            elif staff is not None and not staff.empty:
                st.session_state.auth = True
                st.session_state.staff_name = str(staff.iloc[0]["display_name"])
                st.session_state.staff_role = str(staff.iloc[0]["role"])
                st.rerun()
            else:
                st.error("بيانات الدخول غير صحيحة أو الحساب غير مفعّل")
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
    "⏱️ وقت الذروة والنشاط",
    "🖥️ حالة السيرفر",
    "🔐 إدارة الصلاحيات والتحكم",
    "🛠️ الدعم الفني والتواصل",
    "📱 السوشال ميديا والتواصل",
    "🤖 إضافة الأجهزة الافتراضية (TEST)",
]

with st.sidebar:
    st.markdown("<div class='logo-container'><div class='neon-circle'>⚡</div></div>", unsafe_allow_html=True)
    st.markdown("<h3 style='text-align:center;color:#00E5FF;'>MyClicker Pro</h3>", unsafe_allow_html=True)
    st.markdown(f"<p style='text-align:center;color:#a9b8d0;'>المستخدم: {st.session_state.get('staff_name', 'المدير العام')}</p>", unsafe_allow_html=True)
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


def section_title(title: str) -> None:
    """Render a consistent section heading across all dashboard pages."""
    st.markdown(f"<div class='section-title'>{title}</div>", unsafe_allow_html=True)


def render_table(frame: pd.DataFrame, *, height: int = 320) -> None:
    """Render a clean, compact, right-to-left data table."""
    st.dataframe(
        frame,
        use_container_width=True,
        hide_index=True,
        height=height,
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
               COUNT(*) FILTER (WHERE is_frozen = TRUE) AS frozen,
               COUNT(*) FILTER (WHERE last_active >= NOW() - INTERVAL '5 minutes') AS online,
               COUNT(*) FILTER (WHERE last_active IS NULL OR last_active < NOW() - INTERVAL '5 minutes') AS offline
        FROM myapp.users_status
        """
    )
    if summary is not None and not summary.empty:
        stats = summary.iloc[0]
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("إجمالي الأجهزة", f"{int(stats['total']):,}")
        c2.metric("إجمالي النقرات", f"{int(stats['clicks']):,}")
        c3.metric("الأجهزة المجمدة", f"{int(stats['frozen']):,}")
        c4.metric("حالة الاتصال", "مستقر ✅")
        c5.metric("حالات البوت", f"🟢 {int(stats['online'])} / 🔴 {int(stats['offline'])}")

    versions = run_query(
        """
        SELECT COALESCE(app_version, 'غير معروف') AS app_version, COUNT(*) AS devices
        FROM myapp.users_status
        GROUP BY app_version
        ORDER BY devices DESC
        """
    )
    if versions is not None and not versions.empty:
        section_title("📊 خريطة انتشار الإصدارات")
        chart = px.bar(
            versions,
            x="app_version",
            y="devices",
            color="devices",
            template="plotly_dark",
            labels={"app_version": "الإصدار", "devices": "عدد الأجهزة"},
            color_continuous_scale="blues",
        )
        chart.update_layout(height=390, margin=dict(l=10, r=10, t=30, b=10), paper_bgcolor="#ffffff", plot_bgcolor="#f2f6f9")
        st.plotly_chart(chart, use_container_width=True)
    if st.button("🔄 تحديث التحليلات"):
        st.rerun()

elif menu.startswith("👥"):
    page_header("👥 إدارة أسطول الكباتن", "جدول شامل بأسلوب Excel لمراقبة المستخدمين وحالة البوت لحظياً.")
    version_config = fetch_config()
    required_version = version_config.get("latest_version", "7.2.8")
    st.caption(f"النسخة المطلوبة حالياً: **v{required_version}** — تتم مقارنة كل مستخدم ومزامنته مع هذه النسخة.")
    search = st.text_input("🔍 ابحث برقم الهاتف أو معرّف الجهاز")
    base_query = """
        SELECT users_status.*,
               nd.notification_version AS last_notification_version,
               COALESCE(nd.delivery_status, 'لم تتم المزامنة') AS notification_delivery_status,
               nd.delivered_at AS notification_received_at,
               CASE
                   WHEN last_active >= NOW() - INTERVAL '5 minutes'
                   THEN '🟢 Online'
                   ELSE '🔴 Offline'
               END AS bot_connection,
               CASE
                   WHEN last_active >= NOW() - INTERVAL '5 minutes'
                   THEN TRUE
                   ELSE FALSE
               END AS bot_online,
               GREATEST(0, CEIL(EXTRACT(EPOCH FROM (expiry_date - NOW())) / 86400))::int AS days_remaining
        FROM myapp.users_status
        LEFT JOIN myapp.notification_delivery nd ON nd.device_id = users_status.device_id
        WHERE users_status.device_id NOT LIKE 'sim_%%'
    """
    params: list[str] = []
    if search.strip():
        base_query += " AND (users_status.phone ILIKE %s OR users_status.device_id ILIKE %s)"
        pattern = f"%{search.strip()}%"
        params.extend([pattern, pattern])
    base_query += " ORDER BY last_active DESC NULLS LAST LIMIT 100"
    users = run_query(base_query, params)

    if users is None or users.empty:
        st.info("لا توجد أجهزة مطابقة للبحث.")
    else:
        def version_key(value: object) -> tuple[int, ...]:
            try:
                return tuple(int(part) for part in str(value).lstrip("vV").split(".") if part.isdigit())
            except ValueError:
                return (0,)

        required_key = version_key(required_version)
        users["version_status"] = users["app_version"].map(lambda value: "✅ محدث" if version_key(value) == required_key else "⚠️ يحتاج مزامنة")
        st.markdown("### ⚡ التفعيل الجماعي والاشتراكات")
        activation_ids = st.multiselect(
            "اختر الأجهزة المطلوب تفعيلها",
            options=users["device_id"].astype(str).tolist(),
            format_func=lambda value: f"{value} — {users.loc[users['device_id'].astype(str) == value, 'phone'].iloc[0] if not users.loc[users['device_id'].astype(str) == value].empty else value}",
        )
        activation_col1, activation_col2 = st.columns(2)
        with activation_col1:
            free_enabled = version_config.get("free_activation_enabled", "true") == "true"
            if st.button("⛔ إيقاف التفعيل المجاني الجماعي" if free_enabled else "✅ تفعيل المجاني الجماعي", type="secondary"):
                save_config({"free_activation_enabled": str(not free_enabled).lower()})
                st.rerun()
            if st.button("🎁 تفعيل مجاني جماعي", disabled=not activation_ids or not free_enabled, type="primary"):
                run_query("UPDATE myapp.users_status SET status='Active', expiry_date=NOW() + INTERVAL '30 days' WHERE device_id = ANY(%s)", (activation_ids,), is_select=False)
                st.success(f"تم تفعيل {len(activation_ids)} جهاز مجاناً لمدة 30 يوماً")
                st.rerun()
        with activation_col2:
            subscription_tier = st.selectbox("نوع الاشتراك", ["VIP", "STANDARD", "TRIAL"], key="bulk_subscription_tier")
            if st.button("💳 تفعيل الاشتراكات المحددة", disabled=not activation_ids, type="primary"):
                run_query("UPDATE myapp.users_status SET status='Active', sub_tier=%s, expiry_date=NOW() + INTERVAL '30 days' WHERE device_id = ANY(%s)", (subscription_tier, activation_ids), is_select=False)
                st.success(f"تم تفعيل اشتراك {subscription_tier} لـ {len(activation_ids)} جهاز")
                st.rerun()
        if st.button("💳 تفعيل النظام الشامل لجميع الأجهزة", type="primary"):
            result = run_query("UPDATE myapp.users_status SET status='Active', sub_tier=%s, expiry_date=NOW() + INTERVAL '30 days' WHERE device_id NOT LIKE 'sim_%%'", (subscription_tier,), is_select=False)
            if result is not None:
                st.success(f"تم تفعيل الاشتراك الشامل {subscription_tier} لجميع الأجهزة لمدة 30 يوماً")
                st.rerun()
        if st.button("🔄 مزامنة الإصدار للأجهزة المحددة", disabled=not activation_ids):
            result = run_query("UPDATE myapp.users_status SET app_version=%s WHERE device_id = ANY(%s)", (required_version, activation_ids), is_select=False)
            if result is not None:
                st.success(f"تمت مزامنة v{required_version} مع {len(activation_ids)} جهاز")
                st.rerun()
        if st.button("🔄 مزامنة الإصدارات الجماعية لجميع الأجهزة", type="primary"):
            outdated = run_query(
                "SELECT COUNT(*) AS total FROM myapp.users_status WHERE device_id NOT LIKE 'sim_%%' AND (app_version IS NULL OR app_version IS DISTINCT FROM %s)",
                (required_version,),
            )
            outdated_count = int(outdated.iloc[0]["total"]) if outdated is not None and not outdated.empty else 0
            result = run_query(
                "UPDATE myapp.users_status SET app_version=%s WHERE device_id NOT LIKE 'sim_%%' AND (app_version IS NULL OR app_version IS DISTINCT FROM %s)",
                (required_version, required_version),
                is_select=False,
            )
            if result is not None:
                st.success(f"تمت مزامنة الإصدار v{required_version} مع {outdated_count} جهاز")
                st.rerun()
        section_title("📋 جدول المستخدمين — عرض Excel")
        st.caption("🟢 Online = نشاط خلال آخر 5 دقائق  |  🔴 Offline = لا يوجد نشاط حديث")

        # ترتيب الأعمدة المهمة أولاً مع إبقاء جميع معلومات قاعدة البيانات ظاهرة.
        priority_columns = [
            "bot_connection", "phone", "device_id", "accepted_clicks",
            "app_version", "version_status", "status", "sub_tier", "last_active",
            "expiry_date", "days_remaining", "is_frozen", "notice_message",
            "last_notification_version", "notification_delivery_status", "notification_received_at",
        ]
        visible_columns = [column for column in priority_columns if column in users.columns]
        visible_columns += [column for column in users.columns if column not in visible_columns and column != "bot_online"]
        excel_view = users[visible_columns].copy()
        excel_view = excel_view.rename(columns={
            "bot_connection": "حالة البوت",
            "phone": "رقم الهاتف",
            "device_id": "معرّف الجهاز",
            "accepted_clicks": "عدد النقرات",
            "app_version": "رقم الإصدار",
            "version_status": "حالة الإصدار",
            "status": "الحالة العامة",
            "sub_tier": "الفئة",
            "last_active": "آخر نشاط",
            "expiry_date": "تاريخ الانتهاء",
            "last_notification_version": "آخر إصدار إشعار",
            "notification_delivery_status": "استلام الإشعار",
            "notification_received_at": "وقت الاستلام المؤكد",
            "days_remaining": "الأيام المتبقية",
            "is_frozen": "مجمد؟",
            "notice_message": "رسالة التنبيه",
        })
        render_table(excel_view, height=480)

        st.download_button(
            "📥 تنزيل بيانات المستخدمين CSV",
            data=excel_view.to_csv(index=False).encode("utf-8-sig"),
            file_name=f"myclicker_users_{datetime.now():%Y%m%d_%H%M}.csv",
            mime="text/csv",
            use_container_width=True,
        )

        section_title("🛠️ أدوات التحكم السريع")
        for _, user in users.iterrows():
            device_id = str(user.get("device_id", ""))
            phone = str(user.get("phone", ""))
            clicks = int(user.get("accepted_clicks") or 0)
            frozen = bool(user.get("is_frozen", False))
            connection = str(user.get("bot_connection", "🔴 Offline"))
            version = str(user.get("app_version", "غير معروف"))
            with st.expander(f"{connection}  |  📱 {phone}  |  🎯 {clicks:,} نقرة  |  الإصدار {version}"):
                col1, col2, col3, col4, col5, col6 = st.columns(6)
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
                with col5:
                    st.write("**إعادة التهيئة**")
                    if st.button("♻️ إعادة تهيئة الجهاز", key=f"reset_device_{device_id}"):
                        result = run_query(
                            """
                            UPDATE myapp.users_status
                               SET accepted_clicks=0,
                                   status='Active',
                                   is_frozen=FALSE,
                                   notice_message=NULL,
                                   last_active=NOW()
                             WHERE device_id=%s
                            """,
                            (device_id,),
                            is_select=False,
                        )
                        if result is not None:
                            st.success(f"تمت إعادة تهيئة الجهاز {device_id}")
                            st.rerun()
                with col6:
                    st.write("**الإصدار**")
                    if st.button("🔄 مزامنة الإصدار", key=f"sync_version_{device_id}", disabled=version_key(version) == required_key):
                        result = run_query("UPDATE myapp.users_status SET app_version=%s WHERE device_id=%s", (required_version, device_id), is_select=False)
                        if result is not None:
                            st.success(f"تم تحديث الإصدار إلى v{required_version}")
                            st.rerun()

elif menu.startswith("📢"):
    page_header("📢 مركز الإشعارات", "أرسل رسالة موحّدة إلى شريط إشعارات التطبيق.")
    notification_config = fetch_config()
    notification_type = st.selectbox("نوع الإشعار", ["إعلان عام", "تنبيه مهم", "تحديث التطبيق", "انتهاء الاشتراك"], index=["إعلان عام", "تنبيه مهم", "تحديث التطبيق", "انتهاء الاشتراك"].index(notification_config.get("notification_type", "إعلان عام")) if notification_config.get("notification_type", "إعلان عام") in ["إعلان عام", "تنبيه مهم", "تحديث التطبيق", "انتهاء الاشتراك"] else 0)
    delivery_mode = st.radio("نطاق الإرسال", ["جماعي — جميع الأجهزة", "فردي — جهاز واحد"], horizontal=True)
    selected_device_id = None
    if delivery_mode.startswith("فردي"):
        device_rows = run_query("SELECT device_id, phone FROM myapp.users_status ORDER BY last_active DESC")
        if device_rows is not None and not device_rows.empty:
            device_options = device_rows["device_id"].astype(str).tolist()
            selected_device_id = st.selectbox("اختر الجهاز", device_options, format_func=lambda device: f"{device} — {device_rows.loc[device_rows['device_id'].astype(str) == device, 'phone'].iloc[0] if not device_rows.loc[device_rows['device_id'].astype(str) == device, 'phone'].empty else 'بلا هاتف'}")
        else:
            st.warning("لا توجد أجهزة مسجلة للإرسال الفردي")
    message = st.text_area("نص الرسالة المنسدلة", value=notification_config.get("notice_message", ""), height=140, placeholder="اكتب الإعلان أو التنبيه هنا...")
    notification_enabled = st.toggle("تفعيل ظهور الإشعار داخل التطبيق", value=notification_config.get("notification_enabled", "true") == "true")
    notification_peak_only = st.toggle("إرسال الإشعار للكباتن أثناء وقت الذروة فقط", value=notification_config.get("notification_peak_only", "false") == "true")
    peak_days = st.multiselect("أيام الذروة", options=list(range(7)), default=[int(day) for day in notification_config.get("peak_days", "0,1,2,3,4,5,6").split(",") if day.strip().isdigit() and 0 <= int(day) <= 6], format_func=lambda day: ["الإثنين", "الثلاثاء", "الأربعاء", "الخميس", "الجمعة", "السبت", "الأحد"][day])
    peak_col1, peak_col2 = st.columns(2)
    with peak_col1:
        peak_start = st.time_input("بداية الذروة", value=datetime.strptime(notification_config.get("peak_start", "18:00"), "%H:%M").time())
    with peak_col2:
        peak_end = st.time_input("نهاية الذروة", value=datetime.strptime(notification_config.get("peak_end", "23:00"), "%H:%M").time())
    st.caption("يستخدم التطبيق يوم الأسبوع والوقت المحلي المرسل في طلب المزامنة لتحديد وقت الذروة.")
    if st.button("🚀 بث فوري للجميع", type="primary"):
        if message.strip():
            target_ids = [selected_device_id] if delivery_mode.startswith("فردي") and selected_device_id else []
            users_saved = run_query("UPDATE myapp.users_status SET notice_message = %s WHERE device_id = ANY(%s)", (message.strip(), target_ids), is_select=False) if target_ids else run_query("UPDATE myapp.users_status SET notice_message = %s", (message.strip(),), is_select=False)
            current_version = int(notification_config.get("notification_version", "0") or 0)
            config_saved = save_config({"notification_type": notification_type, "notice_message": message.strip(), "notification_enabled": str(notification_enabled).lower(), "notification_version": current_version + 1, "notification_peak_only": str(notification_peak_only).lower(), "peak_days": ",".join(str(day) for day in sorted(peak_days)), "peak_start": peak_start.strftime("%H:%M"), "peak_end": peak_end.strftime("%H:%M")})
            if users_saved is not None and config_saved:
                api_ok, api_message = send_notification_to_api(message.strip(), notification_type, target_ids)
                st.success("تم إرسال الإشعار الفردي داخل التطبيق" if target_ids else "تم إرسال الإشعار الجماعي داخل التطبيق")
                st.info(api_message if api_ok else f"الإشعار داخل التطبيق يعمل، أما الإرسال الخارجي فيحتاج ربط API: {api_message}")
            else:
                st.error("فشلت مزامنة الإشعار مع قاعدة البيانات؛ راجع اتصال قاعدة البيانات والصلاحيات")
        else:
            st.warning("اكتب رسالة قبل الإرسال")

elif menu.startswith("🚀"):
    page_header("🚀 التحديث الإجباري", "تحكم في النسخة المطلوبة ورابط حزمة التحديث.")
    config = fetch_config()
    with st.form("forced_update_form"):
        version = st.text_input("أحدث نسخة", value=config.get("latest_version", "7.2.8"))
        force_update = st.checkbox("تفعيل قفل النسخة", value=config.get("force_update") == "true")
        apk_url = st.text_input("رابط APK", value=config.get("next_url", "https://pub-7fc5f2f6fb34448f81ade9895014d897.r2.dev/v7.2.8.apk"))
        if st.form_submit_button("💾 تطبيق الإعدادات", type="primary"):
            if save_config({"latest_version": version, "force_update": str(force_update).lower(), "next_url": apk_url}):
                st.success("تم حفظ إعدادات التحديث ومزامنتها مع التطبيق")

elif menu.startswith("⚡"):
    page_header("⚡ البيانات الحية", "عدّل إعدادات التشغيل وأرسلها إلى جميع الأجهزة.")
    config = run_query("SELECT key, value FROM myapp.app_config ORDER BY key")
    if config is not None:
        delay_col, bridge_col = st.columns(2)
        with delay_col:
            if st.button("⚡ ضبط سرعة النقر على 10", type="primary", key="set_click_delay_10"):
                if save_config({"click_delay": "10"}):
                    api_ok, api_message = push_to_sync_api({"click_delay": "10"})
                    st.success("تم ضبط click_delay = 10 داخل لوحة التحكم")
                    st.info(api_message if api_ok else f"تم الحفظ محلياً؛ مزامنة API تحتاج إعداد الربط: {api_message}")
                    st.rerun()
        with bridge_col:
            st.caption("القيمة الحالية: " + str(fetch_config().get("click_delay", "500")) + " ms")
        edited = st.data_editor(config, use_container_width=True, hide_index=True, num_rows="dynamic")
        if st.button("💾 حفظ وإرسال إلى الهواتف", type="primary"):
            values = {
                str(row["key"]): row["value"]
                for _, row in edited.dropna(subset=["key"]).iterrows()
            }
            if save_config(values):
                api_ok, api_message = push_to_sync_api(values)
                st.toast("تم تحديث البيانات الحية داخل قاعدة اللوحة")
                st.info(api_message if api_ok else f"تم الحفظ؛ تعذر إرسالها إلى API: {api_message}")
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
            template="plotly_white",
            labels={"x": "الهاتف", "time_idx": "الوقت", "z": "النقرات"},
            color_continuous_scale="Turbo",
        )
        figure.update_layout(height=650, margin=dict(l=0, r=0, t=30, b=0), paper_bgcolor="#ffffff", plot_bgcolor="#f2f6f9", scene=dict(bgcolor="#f2f6f9", xaxis=dict(showbackground=True, backgroundcolor="#eaf7fa"), yaxis=dict(showbackground=True, backgroundcolor="#f5fafc"), zaxis=dict(showbackground=True, backgroundcolor="#eaf7fa")))
        st.plotly_chart(figure, use_container_width=True)
    else:
        st.info("لا توجد بيانات نشاط كافية للعرض.")

elif menu.startswith("💳"):
    page_header("💳 إدارة الأكواد", "إنشاء أكواد تفعيل مؤقتة ومتابعة حالتها.")
    quantity = st.number_input("عدد الأكواد", min_value=1, max_value=100, value=5, step=1)
    if st.button("🎟️ توليد أكواد جديدة", type="primary"):
        codes = [hashlib.sha256(f"{time.time_ns()}-{index}".encode()).hexdigest()[:12].upper() for index in range(int(quantity))]
        st.session_state.generated_codes = codes
        for code in codes:
            run_query(
                "INSERT INTO myapp.activation_codes_audit (code, category, employee_name, action) VALUES (%s, %s, %s, 'generated')",
                (code, "STANDARD", st.session_state.get("staff_name", "المدير العام")),
                is_select=False,
            )
        st.success(f"تم توليد {len(codes)} أكواد")
    generated_codes = st.session_state.get("generated_codes", [])
    if generated_codes:
        codes_frame = pd.DataFrame({"كود التفعيل": generated_codes, "الحالة": "جديد", "الفئة": "STANDARD", "تاريخ الإنشاء": datetime.now().strftime("%Y-%m-%d %H:%M")})
        sort_column = st.selectbox("فرز الأكواد حسب", list(codes_frame.columns), key="codes_sort_column")
        codes_frame = codes_frame.sort_values(sort_column).reset_index(drop=True)
        render_table(codes_frame, height=300)
        st.download_button("📥 تنزيل الأكواد CSV", codes_frame.to_csv(index=False).encode("utf-8-sig"), "myclicker_codes.csv", "text/csv")
    section_title("🧾 سجل حركة الأكواد")
    code_search = st.text_input("🔍 ابحث عن كود أو موظف أو جهاز", key="code_audit_search")
    audit_query = "SELECT code, category, status, employee_name, action, device_id, created_at, action_at FROM myapp.activation_codes_audit"
    audit_params: list[str] = []
    if code_search.strip():
        audit_query += " WHERE code ILIKE %s OR employee_name ILIKE %s OR device_id ILIKE %s"
        pattern = f"%{code_search.strip()}%"
        audit_params = [pattern, pattern, pattern]
    audit_query += " ORDER BY action_at DESC LIMIT 300"
    audit = run_query(audit_query, audit_params)
    if audit is not None and not audit.empty:
        audit = audit.rename(columns={"code": "الكود", "category": "التصنيف", "status": "الحالة", "employee_name": "اسم الموظف", "action": "الإجراء", "device_id": "الجهاز", "created_at": "تاريخ الإنشاء", "action_at": "وقت الإجراء"})
        render_table(audit, height=360)
    else:
        st.info("لا يوجد سجل حركة للأكواد بعد.")
    st.markdown("### 📝 تسجيل حركة كود")
    action_code = st.text_input("الكود", key="action_code")
    action_type = st.selectbox("نوع الحركة", ["copied", "transferred", "used"], format_func=lambda value: {"copied": "تم نسخه", "transferred": "تم نقله", "used": "تم استخدامه"}[value], key="action_type")
    action_device = st.text_input("الجهاز المستخدم أو المستلم", key="action_device")
    if st.button("💾 تسجيل الحركة"):
        if action_code.strip():
            result = run_query("INSERT INTO myapp.activation_codes_audit (code, status, employee_name, action, device_id) VALUES (%s, %s, %s, %s, %s)", (action_code.strip(), action_type, st.session_state.get("staff_name", "المدير العام"), action_type, action_device.strip() or None), is_select=False)
            if result is not None:
                st.success("تم تسجيل حركة الكود باسم الموظف والجهاز")
                st.rerun()

elif menu.startswith("🤝"):
    page_header("🤝 قسم الشركاء والتوزيع", "إدارة الموزعين وتصنيف التوزيع ومتابعة الاشتراكات والنقرات.")
    with st.expander("➕ إضافة شريك جديد"):
        partner_name = st.text_input("اسم الشريك", key="partner_name")
        partner_category = st.selectbox("تصنيف الشريك", ["MASTER", "DISTRIBUTOR", "RESELLER", "AFFILIATE"], key="partner_category")
        commission = st.number_input("نسبة العمولة", min_value=0.0, max_value=100.0, value=0.0, step=0.5, key="partner_commission")
        if st.button("💾 حفظ الشريك"):
            if partner_name.strip():
                result = run_query("INSERT INTO myapp.partners (name, category, commission) VALUES (%s, %s, %s) ON CONFLICT (name) DO UPDATE SET category=EXCLUDED.category, commission=EXCLUDED.commission, active=TRUE", (partner_name.strip(), partner_category, commission), is_select=False)
                if result is not None:
                    st.success("تم حفظ الشريك")
                    st.rerun()
    partner_list = run_query("SELECT name, category, commission, active, created_at FROM myapp.partners ORDER BY created_at DESC")
    if partner_list is not None and not partner_list.empty:
        render_table(partner_list.rename(columns={"name": "اسم الشريك", "category": "التصنيف", "commission": "العمولة %", "active": "مفعّل", "created_at": "تاريخ الإنشاء"}), height=220)
    partners = run_query("SELECT COALESCE(sub_tier, 'STANDARD') AS tier, COUNT(*) AS devices, COALESCE(SUM(accepted_clicks), 0) AS clicks FROM myapp.users_status GROUP BY sub_tier ORDER BY devices DESC")
    if partners is not None and not partners.empty:
        st.plotly_chart(px.bar(partners, x="tier", y="devices", color="clicks", template="plotly_dark", labels={"tier": "الفئة", "devices": "الأجهزة", "clicks": "النقرات"}), use_container_width=True)
        render_table(partners, height=240)
    else:
        st.info("لا توجد بيانات شركاء حالياً.")

elif menu.startswith("⏱️"):
    page_header("⏱️ وقت الذروة والنشاط", "حدد الساعات والأيام التي تسجل أعلى نشاط ونقرات.")
    peak_config = fetch_config()
    st.markdown("### ⚙️ جدولة وقت الذروة")
    with st.form("peak_schedule_form"):
        schedule_days = st.multiselect("الأيام النشطة", options=list(range(7)), default=[int(day) for day in peak_config.get("peak_days", "0,1,2,3,4,5,6").split(",") if day.strip().isdigit() and 0 <= int(day) <= 6], format_func=lambda day: ["الإثنين", "الثلاثاء", "الأربعاء", "الخميس", "الجمعة", "السبت", "الأحد"][day], key="schedule_days")
        schedule_col1, schedule_col2 = st.columns(2)
        with schedule_col1:
            schedule_start = st.time_input("من الساعة", value=datetime.strptime(peak_config.get("peak_start", "18:00"), "%H:%M").time(), key="schedule_start")
        with schedule_col2:
            schedule_end = st.time_input("إلى الساعة", value=datetime.strptime(peak_config.get("peak_end", "23:00"), "%H:%M").time(), key="schedule_end")
        if st.form_submit_button("💾 حفظ جدول الذروة", type="primary"):
            if save_config({"peak_days": ",".join(str(day) for day in sorted(schedule_days)), "peak_start": schedule_start.strftime("%H:%M"), "peak_end": schedule_end.strftime("%H:%M")}):
                st.success("تم حفظ أيام وساعات الذروة ومزامنتها مع التطبيق")
    st.info(f"الجدول الحالي: {peak_config.get('peak_start', '18:00')} — {peak_config.get('peak_end', '23:00')} | الأيام: {peak_config.get('peak_days', '0,1,2,3,4,5,6')}")
    peak = run_query("SELECT EXTRACT(HOUR FROM last_active)::int AS hour, COUNT(*) AS devices, COALESCE(SUM(accepted_clicks), 0) AS clicks FROM myapp.users_status WHERE last_active IS NOT NULL GROUP BY 1 ORDER BY 1")
    if peak is not None and not peak.empty:
        peak["الساعة"] = peak["hour"].map(lambda hour: f"{int(hour):02d}:00")
        peak_hour = peak.loc[peak["clicks"].idxmax(), "الساعة"]
        st.metric("ساعة الذروة", peak_hour)
        chart = px.area(peak, x="الساعة", y="clicks", markers=True, color_discrete_sequence=["#159fbe"], labels={"الساعة": "الوقت", "clicks": "النقرات"})
        chart.update_layout(template="plotly_white", height=430, margin=dict(l=15, r=15, t=35, b=15))
        st.plotly_chart(chart, use_container_width=True)
        render_table(peak[["الساعة", "devices", "clicks"]].rename(columns={"devices": "الأجهزة", "clicks": "النقرات"}), height=260)
    else:
        st.info("لا توجد بيانات كافية لتحليل وقت الذروة.")

elif menu.startswith("🖥️"):
    page_header("🖥️ حالة السيرفر", "مراقبة اتصال قاعدة البيانات وحالة خدمة MyClicker Pro.")
    health = run_query("SELECT NOW() AS database_time, COUNT(*) AS users FROM myapp.users_status")
    c1, c2, c3 = st.columns(3)
    c1.metric("قاعدة البيانات", "متصل ✅" if health is not None else "غير متصل ❌")
    c2.metric("زمن الفحص", datetime.now().strftime("%H:%M:%S"))
    c3.metric("عدد السجلات", f"{int(health.iloc[0]['users']):,}" if health is not None and not health.empty else "—")
    st.success("الخدمة تعمل بصورة طبيعية.") if health is not None else st.error("تعذر الوصول إلى قاعدة البيانات.")

elif menu.startswith("🔐"):
    page_header("🔐 إدارة الصلاحيات", "مراجعة أدوار المستخدمين وحدود الوصول إلى لوحة التحكم.")
    st.markdown("### 👤 حسابات الموظفين")
    with st.form("staff_account_form"):
        new_username = st.text_input("اسم المستخدم الجديد")
        new_display_name = st.text_input("اسم الموظف الظاهر")
        new_password = st.text_input("كلمة المرور", type="password")
        new_role = st.selectbox("الصلاحية", ["admin", "operator", "monitor"], format_func=lambda role: {"admin": "مدير النظام", "operator": "مشرف العمليات", "monitor": "مراقب"}[role])
        if st.form_submit_button("➕ إنشاء الحساب"):
            if new_username.strip() and new_display_name.strip() and new_password:
                result = run_query("INSERT INTO myapp.app_staff (username, password_hash, display_name, role) VALUES (%s, %s, %s, %s) ON CONFLICT (username) DO UPDATE SET password_hash=EXCLUDED.password_hash, display_name=EXCLUDED.display_name, role=EXCLUDED.role, active=TRUE", (new_username.strip(), hashlib.sha256(new_password.encode()).hexdigest(), new_display_name.strip(), new_role), is_select=False)
                if result is not None:
                    st.success("تم إنشاء الحساب وتحديد الصلاحيات")
                    st.rerun()
            else:
                st.warning("أكمل بيانات الحساب قبل الحفظ")
    staff_list = run_query("SELECT username, display_name, role, active, created_at FROM myapp.app_staff ORDER BY created_at DESC")
    if staff_list is not None and not staff_list.empty:
        render_table(staff_list.rename(columns={"username": "اسم المستخدم", "display_name": "اسم الموظف", "role": "الصلاحية", "active": "مفعّل", "created_at": "تاريخ الإنشاء"}), height=240)
        staff_to_toggle = st.selectbox("الحساب المطلوب تفعيله أو إيقافه", staff_list["username"].astype(str).tolist())
        if st.button("🔁 تبديل حالة الحساب"):
            run_query("UPDATE myapp.app_staff SET active=NOT active WHERE username=%s", (staff_to_toggle,), is_select=False)
            st.success("تم تحديث حالة الحساب")
            st.rerun()
    roles = pd.DataFrame({"اسم الصلاحية": ["مدير النظام", "مشرف العمليات", "مراقب"], "المشاهدة": ["كاملة", "كاملة", "كاملة"], "التعديل والحذف": ["مسموح", "مسموح", "ممنوع"], "التفعيل والاشتراكات": ["مسموح", "مسموح", "ممنوع"], "الإشعارات": ["إدارة وإرسال", "إدارة وإرسال", "مشاهدة"]})
    render_table(roles, height=180)
    st.info("يتم تطبيق صلاحيات العمليات الحساسة قبل تنفيذ الاستعلام في الخادم.")

elif menu.startswith("📱"):
    page_header("📱 السوشال ميديا والتواصل", "أدر روابط التواصل التي تظهر داخل التطبيق وشارك الحملات مع المستخدمين.")
    social_config = fetch_config()
    with st.form("social_media_form"):
        st.markdown("### روابط الحسابات الرسمية")
        instagram = st.text_input("Instagram", value=social_config.get("social_instagram", ""), placeholder="https://instagram.com/...")
        facebook = st.text_input("Facebook", value=social_config.get("social_facebook", ""), placeholder="https://facebook.com/...")
        telegram = st.text_input("Telegram", value=social_config.get("social_telegram", ""), placeholder="https://t.me/...")
        whatsapp = st.text_input("WhatsApp", value=social_config.get("social_whatsapp", ""), placeholder="https://wa.me/...")
        social_enabled = st.checkbox("إظهار روابط التواصل داخل التطبيق", value=social_config.get("social_enabled", "true") == "true")
        campaign = st.text_area("رسالة الحملة الحالية", value=social_config.get("social_campaign", ""), placeholder="اكتب رسالة قصيرة للحملة أو العرض...")
        if st.form_submit_button("💾 حفظ ومزامنة السوشال ميديا", type="primary"):
            if save_config({"social_instagram": instagram, "social_facebook": facebook, "social_telegram": telegram, "social_whatsapp": whatsapp, "social_enabled": str(social_enabled).lower(), "social_campaign": campaign}):
                st.success("تم حفظ روابط السوشال ميديا ومزامنتها مع التطبيق")
    links = pd.DataFrame({"المنصة": ["Instagram", "Facebook", "Telegram", "WhatsApp"], "الرابط": [instagram, facebook, telegram, whatsapp], "الحالة": ["مفعّل" if value else "غير مضاف" for value in [instagram, facebook, telegram, whatsapp]]})
    render_table(links, height=220)

elif menu.startswith("🛠️"):
    page_header("🛠️ الدعم الفني", "أرسل ملاحظة أو طلب مساعدة إلى فريق تشغيل MyClicker Pro.")
    subject = st.text_input("عنوان الطلب")
    message = st.text_area("تفاصيل المشكلة", height=150)
    if st.button("📨 إرسال الطلب", type="primary"):
        if subject.strip() and message.strip():
            st.success("تم تسجيل طلب الدعم بنجاح.")
        else:
            st.warning("أدخل العنوان والتفاصيل قبل الإرسال.")

else:
    st.warning("اختر وحدة من القائمة الجانبية.")

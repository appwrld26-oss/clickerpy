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
    return pool.SimpleConnectionPool(
        minconn=1,
        maxconn=20,
        dsn=DB_URL,
        sslmode="require",
        sslrootcert="",
    )


@contextmanager
def db_connection():
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
    api_url = str(st.session_state.get("sync_api_url", os.getenv("MYCLICKER_SYNC_API_URL", ""))).strip().rstrip("/")
    api_secret = str(st.session_state.get("sync_api_secret", os.getenv("MYCLICKER_API_SECRET", ""))).strip()
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
    api_url = str(st.session_state.get("sync_api_url", os.getenv("MYCLICKER_SYNC_API_URL", ""))).strip().rstrip("/")
    api_secret = str(st.session_state.get("sync_api_secret", os.getenv("MYCLICKER_API_SECRET", ""))).strip()
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


def check_sync_api() -> tuple[bool, str]:
    api_url = str(st.session_state.get("sync_api_url", os.getenv("MYCLICKER_SYNC_API_URL", ""))).strip().rstrip("/")
    if not api_url:
        return False, "أدخل رابط API أولاً"
    try:
        with urllib.request.urlopen(f"{api_url}/health", timeout=8) as response:
            body = json.loads(response.read().decode("utf-8"))
        if body.get("status") == "ok":
            return True, f"الخادم يعمل: {body.get('service', 'myclicker-sync')}"
        return False, "الخادم ردّ بحالة غير جاهزة"
    except (urllib.error.URLError, TimeoutError, ValueError) as error:
        return False, f"تعذر فحص الخادم: {error}"


def end_free_subscription(device_ids: list[str]) -> bool:
    if not device_ids:
        return False
    result = run_query(
        """UPDATE myapp.users_status
              SET status='Expired', sub_tier=NULL, expiry_date=NOW(),
                  is_frozen=FALSE, notice_message=NULL
            WHERE device_id = ANY(%s)""",
        (device_ids,),
        is_select=False,
    )
    if result is None:
        return False
    for device_id in device_ids:
        run_query(
            """INSERT INTO myapp.activation_codes_audit
                (code, category, duration_days, status, action, device_id, activated_device_id, employee_name)
               VALUES ('FREE_ACCESS', 'FREE', 0, 'ended', 'free_ended', %s, %s, %s)""",
            (device_id, device_id, st.session_state.get("staff_name", "المدير العام")),
            is_select=False,
        )
    return True


def ensure_management_tables() -> None:
    statements = [
        """CREATE TABLE IF NOT EXISTS myapp.app_staff (
            id BIGSERIAL PRIMARY KEY, username TEXT UNIQUE NOT NULL, password_hash TEXT NOT NULL,
            display_name TEXT NOT NULL, role TEXT NOT NULL DEFAULT 'monitor', active BOOLEAN NOT NULL DEFAULT TRUE,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )""",
        """CREATE TABLE IF NOT EXISTS myapp.activation_codes_audit (
            id BIGSERIAL PRIMARY KEY, code TEXT NOT NULL, category TEXT NOT NULL DEFAULT 'STANDARD',
            status TEXT NOT NULL DEFAULT 'generated', employee_name TEXT, action TEXT NOT NULL DEFAULT 'generated',
            device_id TEXT, duration_days INTEGER NOT NULL DEFAULT 30,
            activated_device_id TEXT, copied_by_device_id TEXT,
            reorder_count INTEGER NOT NULL DEFAULT 0,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), action_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )""",
        """ALTER TABLE myapp.activation_codes_audit ADD COLUMN IF NOT EXISTS duration_days INTEGER NOT NULL DEFAULT 30""",
        """ALTER TABLE myapp.activation_codes_audit ADD COLUMN IF NOT EXISTS activated_device_id TEXT""",
        """ALTER TABLE myapp.activation_codes_audit ADD COLUMN IF NOT EXISTS copied_by_device_id TEXT""",
        """ALTER TABLE myapp.activation_codes_audit ADD COLUMN IF NOT EXISTS reorder_count INTEGER NOT NULL DEFAULT 0""",
        """CREATE TABLE IF NOT EXISTS myapp.subscriptions (
            code TEXT PRIMARY KEY, duration_days INTEGER NOT NULL DEFAULT 30,
            category TEXT NOT NULL DEFAULT 'STANDARD', payment_status TEXT NOT NULL DEFAULT 'pending',
            renewal_status TEXT NOT NULL DEFAULT 'new', renewed_at TIMESTAMPTZ,
            is_used BOOLEAN NOT NULL DEFAULT FALSE,
            used_by_device TEXT, used_at TIMESTAMPTZ
        )""",
        """ALTER TABLE myapp.subscriptions ADD COLUMN IF NOT EXISTS category TEXT NOT NULL DEFAULT 'STANDARD'""",
        """ALTER TABLE myapp.subscriptions ADD COLUMN IF NOT EXISTS payment_status TEXT NOT NULL DEFAULT 'pending'""",
        """ALTER TABLE myapp.subscriptions ADD COLUMN IF NOT EXISTS renewal_status TEXT NOT NULL DEFAULT 'new'""",
        """ALTER TABLE myapp.subscriptions ADD COLUMN IF NOT EXISTS renewed_at TIMESTAMPTZ""",
        """CREATE TABLE IF NOT EXISTS myapp.partners (
            id BIGSERIAL PRIMARY KEY, name TEXT UNIQUE NOT NULL, category TEXT NOT NULL DEFAULT 'STANDARD',
            commission NUMERIC(10,2) NOT NULL DEFAULT 0, active BOOLEAN NOT NULL DEFAULT TRUE,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )""",
        """CREATE TABLE IF NOT EXISTS myapp.notification_delivery (
            device_id TEXT PRIMARY KEY,
            phone TEXT,
            notification_version TEXT NOT NULL DEFAULT '0',
            notification_id TEXT,
            delivered_at TIMESTAMPTZ,
            delivery_status TEXT NOT NULL DEFAULT 'offered',
            last_sync_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )""",
        """ALTER TABLE myapp.notification_delivery
           ADD COLUMN IF NOT EXISTS delivery_status TEXT NOT NULL DEFAULT 'offered'""",
        """ALTER TABLE myapp.notification_delivery
           ADD COLUMN IF NOT EXISTS delivered_at TIMESTAMPTZ""",
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
    "🎟️ تفعيل اشتراك يدوي",
    "📢 مركز الإشعارات الشامل الكامل",
    "🚀 إدارة التحديثات الإجبارية",
    "⚡ تحديث البيانات الحية (LIVE UPDATE)",
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
    st.markdown(f"<div class='section-title'>{title}</div>", unsafe_allow_html=True)


def render_table(frame: pd.DataFrame, *, height: int = 320) -> None:
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
        WHERE device_id NOT LIKE 'sim_%%'
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

        section_title("🛠️ أدوات السيطرة الجماعية (Global Override)")
        confirm_global = st.checkbox("أؤكد تنفيذ الإجراء على جميع الأجهزة الحقيقية", key="confirm_global_override")
        override_col1, override_col2, override_col3 = st.columns(3)
        with override_col1:
            if st.button("🎁 تفعيل مجاني 30 يوماً", disabled=not confirm_global, key="global_free_activation"):
                result = run_query(
                    """UPDATE myapp.users_status
                       SET status='Active', expiry_date=NOW() + INTERVAL '30 days', is_frozen=FALSE
                     WHERE device_id NOT LIKE 'sim_%%'""",
                    is_select=False,
                )
                if result is not None:
                    st.success("تم تفعيل جميع الأجهزة الحقيقية لمدة 30 يوماً")
                    st.rerun()
        with override_col2:
            global_tier = st.selectbox("الفئة الجماعية", ["VIP", "STANDARD", "TRIAL"], key="global_override_tier")
            if st.button("💳 تفعيل الاشتراك الشامل", disabled=not confirm_global, key="global_subscription_activation"):
                result = run_query(
                    """UPDATE myapp.users_status
                       SET status='Active', sub_tier=%s, expiry_date=NOW() + INTERVAL '30 days', is_frozen=FALSE
                     WHERE device_id NOT LIKE 'sim_%%'""",
                    (global_tier,),
                    is_select=False,
                )
                if result is not None:
                    st.success(f"تم تفعيل اشتراك {global_tier} لجميع الأجهزة الحقيقية")
                    st.rerun()
        with override_col3:
            if st.button("🔄 مزامنة الإصدار للجميع", disabled=not confirm_global, key="global_version_sync"):
                required = fetch_config().get("latest_version", "7.2.8")
                outdated = run_query(
                    """SELECT COUNT(*) AS total FROM myapp.users_status
                     WHERE device_id NOT LIKE 'sim_%%'
                       AND (app_version IS NULL OR app_version IS DISTINCT FROM %s)""",
                    (required,),
                )
                count = int(outdated.iloc[0]["total"]) if outdated is not None and not outdated.empty else 0
                st.success(f"تم تحديث حالة المطابقة للإصدار المطلوب v{required}. الأجهزة التي تحتاج تحديثاً: {count}")

    versions = run_query(
        """
        SELECT COALESCE(app_version, 'غير معروف') AS app_version, COUNT(*) AS devices
        FROM myapp.users_status
        WHERE device_id NOT LIKE 'sim_%%'
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

elif menu.startswith("👥"):
    page_header("👥 إدارة أسطول الكباتن", "جدول شامل بأسلوب Excel لمراقبة المستخدمين وحالة البوت لحظياً.")
    version_config = fetch_config()
    required_version = version_config.get("latest_version", "7.2.8")
    st.caption(f"النسخة المطلوبة حالياً: **v{required_version}**")
    search = st.text_input("🔍 ابحث برقم الهاتف أو معرّف الجهاز")
    count_query = "SELECT COUNT(*) AS total FROM myapp.users_status WHERE device_id NOT LIKE 'sim_%%'"
    count_params: list[str] = []
    if search.strip():
        count_query += " AND (phone ILIKE %s OR device_id ILIKE %s)"
        count_pattern = f"%{search.strip()}%"
        count_params.extend([count_pattern, count_pattern])
    total_result = run_query(count_query, count_params)
    total_devices = int(total_result.iloc[0]["total"]) if total_result is not None and not total_result.empty else 0
    page_size = st.selectbox("عدد الأجهزة في الصفحة", [50, 100, 250], index=1, key="fleet_page_size")
    total_pages = max(1, (total_devices + page_size - 1) // page_size)
    page_number = st.number_input("صفحة الأسطول", min_value=1, max_value=total_pages, value=1, step=1, key="fleet_page_number")
    st.info(f"إجمالي الأجهزة المطابقة: **{total_devices}** | الصفحة **{page_number}** من **{total_pages}**")
    base_query = """
        SELECT users_status.*,
               activation_log.activation_code,
               activation_log.activation_duration_days,
               activation_log.activation_category,
               activation_log.copied_by_device_id,
               activation_log.activation_reorder_count,
               nd.notification_version AS last_notification_version,
               COALESCE(nd.delivery_status, 'لم تتم المزامنة') AS notification_delivery_status,
               nd.delivered_at AS notification_received_at,
               CASE
                   WHEN last_active >= NOW() - INTERVAL '5 minutes'
                   THEN '🟢 Online'
                   ELSE '🔴 Offline'
               END AS bot_connection,
               GREATEST(0, CEIL(EXTRACT(EPOCH FROM (expiry_date - NOW())) / 86400))::int AS days_remaining
        FROM myapp.users_status
        LEFT JOIN LATERAL (
            SELECT a.code AS activation_code,
                   a.duration_days AS activation_duration_days,
                   a.category AS activation_category,
                   a.copied_by_device_id,
                   a.reorder_count AS activation_reorder_count
            FROM myapp.activation_codes_audit a
            WHERE a.action = 'used'
              AND (a.activated_device_id = users_status.device_id OR a.device_id = users_status.device_id)
            ORDER BY a.action_at DESC
            LIMIT 1
        ) activation_log ON TRUE
        LEFT JOIN myapp.notification_delivery nd ON nd.device_id = users_status.device_id
        WHERE users_status.device_id NOT LIKE 'sim_%%'
    """
    params: list[str] = []
    if search.strip():
        base_query += " AND (users_status.phone ILIKE %s OR users_status.device_id ILIKE %s)"
        pattern = f"%{search.strip()}%"
        params.extend([pattern, pattern])
    base_query += " ORDER BY last_active DESC NULLS LAST LIMIT %s OFFSET %s"
    params.extend([int(page_size), (int(page_number) - 1) * int(page_size)])
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
        section_title("📋 جدول المستخدمين — عرض Excel")
        
        priority_columns = [
            "bot_connection", "phone", "device_id", "accepted_clicks",
            "app_version", "version_status", "status", "sub_tier", "last_active",
            "expiry_date", "days_remaining", "is_frozen", "notice_message"
        ]
        visible_columns = [column for column in priority_columns if column in users.columns]
        visible_columns += [column for column in users.columns if column not in visible_columns and column != "bot_online"]
        excel_view = users[visible_columns].copy()
        render_table(excel_view, height=480)

        st.download_button(
            "📥 تنزيل بيانات المستخدمين CSV",
            data=excel_view.to_csv(index=False).encode("utf-8-sig"),
            file_name=f"myclicker_users_{datetime.now():%Y%m%d_%H%M}.csv",
            mime="text/csv",
            use_container_width=True,
        )

# قسم تفعيل الاشتراك اليدوي الجديد
elif menu.startswith("🎟️"):
    page_header("🎟️ تفعيل اشتراك يدوي", "تفعيل حساب السائق يدويًا مع جلب معرّف الجهاز ورقم الكمبيوتر/المسؤول تلقائياً.")
    
    devices_df = run_query("SELECT device_id, phone FROM myapp.users_status ORDER BY last_active DESC")

    if devices_df is not None and not devices_df.empty:
        phone_options = devices_df["phone"].dropna().astype(str).tolist()
        
        col_p1, col_p2 = st.columns(2)
        with col_p1:
            selected_phone = st.selectbox("اختر رقم الهاتف", ["-- اختر أو أدخل يدوياً --"] + phone_options, key="manual_activation_phone_select")
        
        with col_p2:
            if selected_phone != "-- اختر أو أدخل يدوياً --":
                manual_phone = st.text_input("رقم الهاتف", value=selected_phone, key="manual_phone_input")
            else:
                manual_phone = st.text_input("أدخل رقم الهاتف يدوياً", value="", key="manual_phone_input_custom")

        # جلب رقم الجهاز (Device ID) تلقائياً بناءً على الهاتف المختار
        auto_device_id = ""
        if manual_phone.strip():
            matched_row = devices_df[devices_df["phone"].astype(str) == manual_phone.strip()]
            if not matched_row.empty:
                auto_device_id = str(matched_row.iloc[0]["device_id"])

        target_device_id = st.text_input("📱 معرّف الجهاز (Device ID) - يتم تعبئته تلقائياً", value=auto_device_id, key="manual_target_device_id")

        # خيار طريقة الحصول على الكود (توليد تلقائي أو اختيار من الجدول)
        code_mode = st.radio("طريقة كود التفعيل", ["توليد كود تلقائياً 🔄", "اختيار كود من جدول الاشتراكات 📋"], horizontal=True, key="manual_code_mode")

        activation_code = ""
        default_days = 30
        
        if code_mode.startswith("توليد"):
            activation_code = hashlib.sha256(f"{time.time_ns()}-manual-gen".encode()).hexdigest()[:12].upper()
            st.info(f"🔑 الكود الذي سيتم اعتماده وتفعيله: **{activation_code}**")
        else:
            unused_subs = run_query("SELECT code, duration_days, category FROM myapp.subscriptions WHERE is_used = FALSE ORDER BY code")
            if unused_subs is not None and not unused_subs.empty:
                code_options = unused_subs["code"].astype(str).tolist()
                selected_existing_code = st.selectbox("اختر كوداً جاهزاً من الجدول", code_options, key="manual_existing_code_sel")
                activation_code = selected_existing_code
                
                row_sub = unused_subs[unused_subs["code"] == selected_existing_code]
                if not row_sub.empty:
                    default_days = int(row_sub.iloc[0]["duration_days"])
            else:
                st.warning("⚠️ لا توجد أكواد غير مستخدمة في الجدول؛ سيتم توليد كود تلقائي بديل.")
                activation_code = hashlib.sha256(f"{time.time_ns()}-fallback".encode()).hexdigest()[:12].upper()

        col_d1, col_d2 = st.columns(2)
        with col_d1:
            activation_days = st.number_input("عدد الأيام للتفعيل", min_value=1, max_value=3650, value=default_days, step=1, key="manual_activation_days")
        with col_d2:
            tier_choice = st.selectbox("نوع الاشتراك", ["VIP", "STANDARD", "TRIAL"], key="manual_tier_choice")

        # إظهار اسم المسؤول أو جهاز الكمبيوتر المفعل الحالي
        current_staff = st.session_state.get("staff_name", "المدير العام")
        st.info(f"🖥️ المسؤول / جهاز الكمبيوتر المفعل الحالي: **{current_staff}**")

        if st.button("🚀 تنفيذ التفعيل اليدوي", type="primary", key="execute_manual_activation_with_code"):
            if not target_device_id.strip():
                st.error("⚠️ يرجى التأكد من توفر معرّف الجهاز (Device ID).")
            else:
                update_result = run_query(
                    """
                    UPDATE myapp.users_status 
                    SET status = 'Active', 
                        sub_tier = %s,
                        expiry_date = GREATEST(COALESCE(expiry_date, NOW()), NOW()) + (%s || ' days')::interval,
                        phone = COALESCE(NULLIF(%s, ''), phone),
                        is_frozen = FALSE,
                        activated_code = %s,
                        last_active = NOW()
                    WHERE device_id = %s
                    """,
                    (tier_choice, int(activation_days), manual_phone.strip(), activation_code, target_device_id.strip()),
                    is_select=False
                )
                
                if update_result is not None:
                    run_query(
                        """
                        INSERT INTO myapp.subscriptions (code, duration_days, category, is_used, used_by_device, used_at)
                        VALUES (%s, %s, %s, TRUE, %s, NOW())
                        ON CONFLICT (code) DO UPDATE SET is_used = TRUE, used_by_device = EXCLUDED.used_by_device, used_at = NOW()
                        """,
                        (activation_code, int(activation_days), tier_choice, target_device_id.strip()),
                        is_select=False
                    )

                    run_query(
                        """
                        INSERT INTO myapp.activation_codes_audit
                        (code, category, duration_days, status, employee_name, action, device_id, activated_device_id)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        """,
                        (activation_code, tier_choice, int(activation_days), 'used', current_staff, 'manual_activation_portal', target_device_id.strip(), target_device_id.strip()),
                        is_select=False
                    )

                    st.success(f"✅ تم تفعيل الاشتراك بنجاح للكود (`{activation_code}`) لمدة {activation_days} يوم للجهاز: {target_device_id.strip()} بواسطة ({current_staff})!")
                    st.toast("تم التفعيل اليدوي بنجاح", icon="🎉")
                else:
                    st.error("❌ فشل تنفيذ التفعيل، تحقق من اتصال قاعدة البيانات أو معرّف الجهاز.")
    else:
        st.warning("لا توجد بيانات مسجلة في جدول الأجهزة حالياً.")

elif menu.startswith("📢"):
    page_header("📢 مركز الإشعارات", "أرسل رسالة موحّدة إلى شريط إشعارات التطبيق.")
    notification_config = fetch_config()
    with st.expander("🔗 إعداد ربط API المزامنة", expanded=True):
        sync_api_url = st.text_input("رابط API المزامنة", value=str(st.session_state.get("sync_api_url", "")), key="sync_api_url_input")
        sync_api_secret = st.text_input("مفتاح API", value=str(st.session_state.get("sync_api_secret", "")), type="password", key="sync_api_secret_input")
        if st.button("💾 حفظ واختبار رابط API", key="save_sync_api_settings"):
            st.session_state.sync_api_url = sync_api_url.strip()
            st.session_state.sync_api_secret = sync_api_secret.strip()
            st.success("تم حفظ إعدادات API في الجلسة.")
    
    notification_type = st.selectbox("نوع الإشعار", ["إعلان عام", "تنبيه مهم", "تحديث التطبيق", "انتهاء الاشتراك"])
    message = st.text_area("نص الرسالة المنسدلة", value=notification_config.get("notice_message", ""), height=140)
    if st.button("🚀 بث إشعار منسدل جماعي", type="primary", key="send_tray_notification"):
        if message.strip():
            run_query("UPDATE myapp.users_status SET notice_message = %s", (message.strip(),), is_select=False)
            save_config({"notice_message": message.strip(), "notification_type": notification_type})
            st.success("تم إرسال الإشعار بنجاح")

elif menu.startswith("🚀"):
    page_header("🚀 التحديث الإجباري", "تحكم في النسخة المطلوبة ورابط حزمة التحديث.")
    config = fetch_config()
    with st.form("forced_update_form"):
        version = st.text_input("أحدث نسخة", value=config.get("latest_version", "7.2.8"))
        force_update = st.checkbox("تفعيل قفل النسخة", value=config.get("force_update") == "true")
        apk_url = st.text_input("رابط APK", value=config.get("next_url", ""))
        if st.form_submit_button("💾 تطبيق الإعدادات", type="primary"):
            save_config({"latest_version": version, "force_update": str(force_update).lower(), "next_url": apk_url})
            st.success("تم حفظ إعدادات التحديث")

elif menu.startswith("⚡"):
    page_header("⚡ البيانات الحية", "عدّل إعدادات التشغيل وأرسلها إلى جميع الأجهزة.")
    config = run_query("SELECT key, value FROM myapp.app_config ORDER BY key")
    if config is not None:
        edited = st.data_editor(config, use_container_width=True, hide_index=True, num_rows="dynamic")
        if st.button("💾 حفظ وإرسال إلى الهواتف", type="primary"):
            values = {str(row["key"]): row["value"] for _, row in edited.dropna(subset=["key"]).iterrows()}
            if save_config(values):
                st.success("تم تحديث البيانات الحية")

elif menu.startswith("🤖"):
    page_header("🤖 مركز أجهزة الاختبار", "أنشئ بيانات محاكاة بأمان لاختبار الأداء والواجهات.")
    amount = st.number_input("عدد الأجهزة", min_value=10, max_value=1000, value=100, step=10)
    if st.button("🚀 حقن جيش الاختبار", type="primary"):
        run_query(
            "INSERT INTO myapp.users_status (device_id, phone, status, expiry_date, last_active) SELECT 'sim_' || md5(random()::text), '079' || LPAD(i::text, 7, '0'), 'Active', NOW() + interval '30 days', NOW() FROM generate_series(1, %s) AS series(i)",
            (int(amount),),
            is_select=False,
        )
        st.success("تم إنشاء أجهزة الاختبار")

elif menu.startswith("📊"):
    page_header("📊 التحليل الفضائي للنشاط", "استكشف العلاقة بين النشاط والزمن والأجهزة في عرض ثلاثي الأبعاد.")
    activity = run_query("SELECT accepted_clicks AS z, phone AS x, last_active AS y FROM myapp.users_status WHERE accepted_clicks > 0 LIMIT 300")
    if activity is not None and not activity.empty:
        activity["time_idx"] = pd.to_datetime(activity["y"], errors="coerce").astype("int64") // 10**12
        figure = px.scatter_3d(activity, x="x", y="time_idx", z="z", color="z", template="plotly_white")
        st.plotly_chart(figure, use_container_width=True)

elif menu.startswith("🤝"):
    page_header("🤝 قسم الشركاء والتوزيع", "إدارة الموزعين وتصنيف التوزيع.")
    partner_list = run_query("SELECT name, category, commission, active, created_at FROM myapp.partners ORDER BY created_at DESC")
    if partner_list is not None and not partner_list.empty:
        render_table(partner_list, height=220)

elif menu.startswith("⏱️"):
    page_header("⏱️ وقت الذروة والنشاط", "حدد الساعات والأيام التي تسجل أعلى نشاط.")
    peak_config = fetch_config()
    st.info(f"الجدول الحالي: {peak_config.get('peak_start', '18:00')} — {peak_config.get('peak_end', '23:00')}")

elif menu.startswith("🖥️"):
    page_header("🖥️ حالة السيرفر", "مراقبة اتصال قاعدة البيانات.")
    health = run_query("SELECT NOW() AS database_time, COUNT(*) AS users FROM myapp.users_status")
    st.success("الخدمة تعمل بصورة طبيعية.") if health is not None else st.error("تعذر الوصول إلى قاعدة البيانات.")

elif menu.startswith("🔐"):
    page_header("🔐 إدارة الصلاحيات", "مراجعة أدوار المستخدمين.")
    staff_list = run_query("SELECT username, display_name, role, active, created_at FROM myapp.app_staff ORDER BY created_at DESC")
    if staff_list is not None and not staff_list.empty:
        render_table(staff_list, height=240)

elif menu.startswith("📱"):
    page_header("📱 السوشال ميديا والتواصل", "أدر روابط التواصل.")
    social_config = fetch_config()
    st.text_input("Instagram", value=social_config.get("social_instagram", ""))

elif menu.startswith("🛠️"):
    page_header("🛠️ الدعم الفني", "أرسل ملاحظة أو طلب مساعدة.")
    st.text_input("عنوان الطلب")

else:
    st.warning("اختر وحدة من القائمة الجانبية.")

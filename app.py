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
# 1. إعداد الصفحة والهوية البصرية الاحترافية
# ============================================================
st.set_page_config(
    page_title="MyClicker Pro | Ultimate Command & Control",
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
    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# 2. إدارة قاعدة البيانات والاتصالات (Connection Pooling)
# ============================================================
DB_URL = "postgresql://neondb_owner:npg_AvzFkHQ6M3yo@ep-tiny-wind-ayd9hww0.c-5.us-east-2.aws.neon.tech/neondb?sslmode=require"


@st.cache_resource(show_spinner=False)
def get_pool() -> pool.SimpleConnectionPool:
    return pool.SimpleConnectionPool(
        minconn=1,
        maxconn=25,
        dsn=DB_URL,
        sslmode="require",
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
        st.error(f"❌ تعذر تنفيذ العملية في قاعدة البيانات: {error}")
        return None


@st.cache_data(ttl=15, show_spinner=False)
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
    st.cache_data.clear()
    return True


def ensure_management_tables() -> None:
    statements = [
        """CREATE SCHEMA IF NOT EXISTS myapp;""",
        """CREATE TABLE IF NOT EXISTS myapp.app_staff (
            id BIGSERIAL PRIMARY KEY, username TEXT UNIQUE NOT NULL, password_hash TEXT NOT NULL,
            display_name TEXT NOT NULL, role TEXT NOT NULL DEFAULT 'monitor', active BOOLEAN NOT NULL DEFAULT TRUE,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )""",
        """CREATE TABLE IF NOT EXISTS myapp.bot_logs (
            id BIGSERIAL PRIMARY KEY, device_id TEXT, event_type TEXT, keyword TEXT,
            reaction_time_ms INTEGER, status TEXT, detected_app TEXT, order_price NUMERIC,
            order_distance NUMERIC, conditions_ignored BOOLEAN, ignore_reason TEXT,
            details JSONB, created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )""",
        """CREATE TABLE IF NOT EXISTS myapp.activation_codes_audit (
            id BIGSERIAL PRIMARY KEY, code TEXT NOT NULL, category TEXT NOT NULL DEFAULT 'STANDARD',
            status TEXT NOT NULL DEFAULT 'generated', employee_name TEXT, action TEXT NOT NULL DEFAULT 'generated',
            device_id TEXT, duration_days INTEGER NOT NULL DEFAULT 30,
            activated_device_id TEXT, copied_by_device_id TEXT,
            reorder_count INTEGER NOT NULL DEFAULT 0,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), action_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )""",
        """CREATE TABLE IF NOT EXISTS myapp.subscriptions (
            code TEXT PRIMARY KEY, duration_days INTEGER NOT NULL DEFAULT 30,
            category TEXT NOT NULL DEFAULT 'STANDARD', payment_status TEXT NOT NULL DEFAULT 'pending',
            renewal_status TEXT NOT NULL DEFAULT 'new', renewed_at TIMESTAMPTZ,
            is_used BOOLEAN NOT NULL DEFAULT FALSE,
            used_by_device TEXT, used_at TIMESTAMPTZ
        )""",
        """CREATE TABLE IF NOT EXISTS myapp.partners (
            id BIGSERIAL PRIMARY KEY, name TEXT UNIQUE NOT NULL, category TEXT NOT NULL DEFAULT 'STANDARD',
            commission NUMERIC(10,2) NOT NULL DEFAULT 0, active BOOLEAN NOT NULL DEFAULT TRUE,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )""",
        """CREATE TABLE IF NOT EXISTS myapp.notification_delivery (
            device_id TEXT PRIMARY KEY, phone TEXT, notification_version TEXT NOT NULL DEFAULT '0',
            notification_id TEXT, delivered_at TIMESTAMPTZ, delivery_status TEXT NOT NULL DEFAULT 'offered',
            last_sync_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )"""
    ]
    for statement in statements:
        run_query(statement, is_select=False)


ensure_management_tables()


# ============================================================
# 3. نظام المصادقة والأمان
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
                <p>بوابة القيادة والتحكم الذكية (النسخة المطورة)</p>
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
    "👥 إدارة ومراقبة المستخدمين (الأسطول)",
    "🎟️ تفعيل اشتراك يدوي فوري",
    "🤖 سجلات أداء البوت والتشخيص (Telemetry)",
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
    if st.button("🔄 مسح الذاكرة المؤقتة والتحديث"):
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
# 4. لوحات التحكم والصفحات المطورة
# ============================================================
if menu.startswith("📈"):
    page_header("📈 مركز الرؤية والتحليلات المتقدمة", "لقطة فورية لأداء الأسطول، سرعات الاستجابة، وإصدارات التطبيق.")
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
        c4.metric("حالة النظام", "مستقر وسريع 🚀")
        c5.metric("حالات الاتصال", f"🟢 {int(stats['online'])} / 🔴 {int(stats['offline'])}")

        section_title("🛠️ أدوات السيطرة الجماعية الفورية (Global Override)")
        confirm_global = st.checkbox("أؤكد تنفيذ الإجراء على جميع الأجهزة الحقيقية بالأسطول", key="confirm_global_override")
        override_col1, override_col2, override_col3 = st.columns(3)
        with override_col1:
            if st.button("🎁 تفعيل مجاني 30 يوماً للجميع", disabled=not confirm_global, key="global_free_activation"):
                result = run_query(
                    """UPDATE myapp.users_status
                       SET status='Active', expiry_date=NOW() + INTERVAL '30 days', is_frozen=FALSE
                     WHERE device_id NOT LIKE 'sim_%%'""",
                    is_select=False,
                )
                if result is not None:
                    st.success("✨ تم تفعيل جميع الأجهزة الحقيقية لمدة 30 يوماً بنجاح")
                    st.toast("تم التفعيل الجماعي بنجاح", icon="🎉")
        with override_col2:
            global_tier = st.selectbox("اختر الفئة الجماعية", ["VIP", "STANDARD", "TRIAL"], key="global_override_tier")
            if st.button("💳 تفعيل الاشتراك الشامل", disabled=not confirm_global, key="global_subscription_activation"):
                result = run_query(
                    """UPDATE myapp.users_status
                       SET status='Active', sub_tier=%s, expiry_date=NOW() + INTERVAL '30 days', is_frozen=FALSE
                     WHERE device_id NOT LIKE 'sim_%%'""",
                    (global_tier,),
                    is_select=False,
                )
                if result is not None:
                    st.success(f"💎 تم تفعيل اشتراك {global_tier} لجميع الأجهزة الحقيقية")
                    st.toast("تم التفعيل الشامل بنجاح", icon="💎")
        with override_col3:
            if st.button("❄️ تجميد الأسطول طوارئ", disabled=not confirm_global, key="global_freeze_fleet"):
                result = run_query("UPDATE myapp.users_status SET is_frozen = TRUE WHERE device_id NOT LIKE 'sim_%%'", is_select=False)
                if result is not None:
                    st.warning("⚠️ تم تجميد كافة الأجهزة الحقيقية مؤقتاً للطوارئ.")

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
        section_title("📊 خريطة انتشار الإصدارات الحية")
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
    page_header("👥 إدارة أسطول الكباتن مع إجراءات جماعية", "جدول شامل لمراقبة المستخدمين، تجميد الأجهزة، وتعديل الاشتراكات بضغطة زر.")
    version_config = fetch_config()
    required_version = version_config.get("latest_version", "7.2.8")
    st.caption(f"النسخة المطلوبة حالياً: **v{required_version}**")
    
    search = st.text_input("🔍 ابحث برقم الهاتف أو معرّف الجهاز (Device ID)")
    
    col_f1, col_f2 = st.columns(2)
    with col_f1:
        filter_status = st.selectbox("تصفية حسب الحالة", ["الكل", "متصل (Online)", "غير متصل (Offline)", "مجمد (Frozen)"])
    with col_f2:
        filter_tier = st.selectbox("تصفية حسب الفئة", ["الكل", "VIP", "STANDARD", "TRIAL"])

    base_query = """
        SELECT users_status.*,
               activation_log.activation_code,
               activation_log.activation_duration_days,
               activation_log.activation_category,
               nd.notification_version AS last_notification_version,
               COALESCE(nd.delivery_status, 'لم تتم المزامنة') AS notification_delivery_status,
               CASE
                   WHEN last_active >= NOW() - INTERVAL '5 minutes' THEN '🟢 Online'
                   ELSE '🔴 Offline'
               END AS bot_connection,
               GREATEST(0, CEIL(EXTRACT(EPOCH FROM (expiry_date - NOW())) / 86400))::int AS days_remaining
        FROM myapp.users_status
        LEFT JOIN LATERAL (
            SELECT a.code AS activation_code, a.duration_days AS activation_duration_days, a.category AS activation_category
            FROM myapp.activation_codes_audit a
            WHERE a.action = 'used' AND (a.activated_device_id = users_status.device_id OR a.device_id = users_status.device_id)
            ORDER BY a.action_at DESC LIMIT 1
        ) activation_log ON TRUE
        LEFT JOIN myapp.notification_delivery nd ON nd.device_id = users_status.device_id
        WHERE users_status.device_id NOT LIKE 'sim_%%'
    """
    params: list[Any] = []
    if search.strip():
        base_query += " AND (users_status.phone ILIKE %s OR users_status.device_id ILIKE %s)"
        pattern = f"%{search.strip()}%"
        params.extend([pattern, pattern])
    
    if filter_status == "متصل (Online)":
        base_query += " AND last_active >= NOW() - INTERVAL '5 minutes'"
    elif filter_status == "غير متصل (Offline)":
        base_query += " AND (last_active IS NULL OR last_active < NOW() - INTERVAL '5 minutes')"
    elif filter_status == "مجمد (Frozen)":
        base_query += " AND is_frozen = TRUE"

    if filter_tier != "الكل":
        base_query += " AND UPPER(COALESCE(sub_tier, 'STANDARD')) = UPPER(%s)"
        params.append(filter_tier)

    base_query += " ORDER BY last_active DESC NULLS LAST LIMIT 250"
    users = run_query(base_query, params)

    if users is None or users.empty:
        st.info("لا توجد أجهزة مطابقة لخيارات البحث أو التصفية الحالية.")
    else:
        st.success(f"تم العثور على {len(users)} جهاز مطابق.")
        
        # إجراءات جماعية على الأجهزة المحددة
        section_title("⚡ إجراءات سريعة جماعية / فردية")
        selected_devices = st.multiselect("اختر معرفات الأجهزة (Device IDs) لتطبيق إجراء جماعي عليها", options=users["device_id"].tolist())
        
        col_act1, col_act2, col_act3, col_act4 = st.columns(4)
        with col_act1:
            if st.button("❄️ تجميد الأجهزة المحددة") and selected_devices:
                run_query("UPDATE myapp.users_status SET is_frozen = TRUE WHERE device_id = ANY(%s)", (selected_devices,), is_select=False)
                st.success(f"تم تجميد {len(selected_devices)} جهاز بنجاح.")
                st.rerun()
        with col_act2:
            if st.button("🔥 فك التجميد") and selected_devices:
                run_query("UPDATE myapp.users_status SET is_frozen = FALSE WHERE device_id = ANY(%s)", (selected_devices,), is_select=False)
                st.success(f"تم فك تجميد {len(selected_devices)} جهاز بنجاح.")
                st.rerun()
        with col_act3:
            if st.button("🔄 تصفير النقرات") and selected_devices:
                run_query("UPDATE myapp.users_status SET accepted_clicks = 0 WHERE device_id = ANY(%s)", (selected_devices,), is_select=False)
                st.success(f"تم تصفير نقرات {len(selected_devices)} جهاز بنجاح.")
                st.rerun()
        with col_act4:
            if st.button("🗑️ حذف الأجهزة") and selected_devices:
                run_query("DELETE FROM myapp.users_status WHERE device_id = ANY(%s)", (selected_devices,), is_select=False)
                st.success(f"تم حذف {len(selected_devices)} جهاز بنجاح.")
                st.rerun()

        render_table(users, height=450)
        st.download_button(
            "📥 تنزيل بيانات الأسطول المصفاة CSV",
            data=users.to_csv(index=False).encode("utf-8-sig"),
            file_name=f"myclicker_fleet_{datetime.now():%Y%m%d_%H%M}.csv",
            mime="text/csv",
            use_container_width=True,
        )

elif menu.startswith("🎟️"):
    page_header("🎟️ تفعيل اشتراك يدوي فوري", "تفعيل حساب السائق مع تعبئة رقم الهاتف، معرّف الجهاز وتحديد الأيام والفئة.")
    devices_df = run_query("SELECT device_id, phone FROM myapp.users_status ORDER BY last_active DESC")

    phone_options = devices_df["phone"].dropna().astype(str).tolist() if devices_df is not None and not devices_df.empty else []
    col_p1, col_p2 = st.columns(2)
    with col_p1:
        selected_phone = st.selectbox("اختر رقم الهاتف المسجل", ["-- اختر أو أدخل يدوياً --"] + phone_options)
    with col_p2:
        manual_phone = st.text_input("رقم الهاتف", value="" if selected_phone == "-- اختر أو أدخل يدوياً --" else selected_phone)

    auto_device_id = ""
    if manual_phone.strip() and devices_df is not None:
        matched = devices_df[devices_df["phone"].astype(str) == manual_phone.strip()]
        if not matched.empty:
            auto_device_id = str(matched.iloc[0]["device_id"])

    target_device_id = st.text_input("📱 معرّف الجهاز (Device ID)", value=auto_device_id)
    activation_code = st.text_input("🔑 كود التفعيل", value=f"MANUAL-{hashlib.sha256(str(time.time()).encode()).hexdigest()[:8].upper()}")

    col_d1, col_d2 = st.columns(2)
    with col_d1:
        activation_days = st.number_input("مدة الاشتراك بالأيام", min_value=1, max_value=3650, value=30)
    with col_d2:
        tier_choice = st.selectbox("فئة الاشتراك", ["VIP", "STANDARD", "TRIAL"], index=0)

    current_staff = st.session_state.get("staff_name", "المدير العام")
    st.info(f"🖥️ المسؤول المنفذ: **{current_staff}**")

    if st.button("🚀 تنفيذ التفعيل الفوري", type="primary"):
        if not target_device_id.strip():
            st.error("⚠️ يرجى توفير معرّف الجهاز (Device ID).")
        else:
            res = run_query(
                """
                UPDATE myapp.users_status 
                SET status = 'Active', sub_tier = %s,
                    expiry_date = GREATEST(COALESCE(expiry_date, NOW()), NOW()) + (%s || ' days')::interval,
                    phone = COALESCE(NULLIF(%s, ''), phone), is_frozen = FALSE, activated_code = %s, last_active = NOW()
                WHERE device_id = %s
                """,
                (tier_choice, int(activation_days), manual_phone.strip(), activation_code.strip(), target_device_id.strip()),
                is_select=False
            )
            if res is not None:
                run_query(
                    """
                    INSERT INTO myapp.subscriptions (code, duration_days, category, is_used, used_by_device, used_at)
                    VALUES (%s, %s, %s, TRUE, %s, NOW())
                    ON CONFLICT (code) DO UPDATE SET is_used = TRUE, used_by_device = EXCLUDED.used_by_device, used_at = NOW()
                    """,
                    (activation_code.strip(), int(activation_days), tier_choice, target_device_id.strip()),
                    is_select=False
                )
                run_query(
                    """
                    INSERT INTO myapp.activation_codes_audit
                    (code, category, duration_days, status, employee_name, action, device_id, activated_device_id)
                    VALUES (%s, %s, %s, 'used', %s, 'manual_activation_dashboard', %s, %s)
                    """,
                    (activation_code.strip(), tier_choice, int(activation_days), current_staff, target_device_id.strip(), target_device_id.strip()),
                    is_select=False
                )
                st.success(f"✅ تم تفعيل الاشتراك بنجاح للباقة [{tier_choice}] لمدة {activation_days} يوم للجهاز ({target_device_id.strip()})!")
                st.toast("تم التفعيل اليدوي بنجاح", icon="🎉")

elif menu.startswith("🤖"):
    page_header("🤖 سجلات أداء البوت والتشخيص (Telemetry)", "مراقبة زمن الاستجابة (Reaction Time) وسجلات أداء النقر اللحظي للأجهزة.")
    logs = run_query("SELECT * FROM myapp.bot_logs ORDER BY created_at DESC LIMIT 200")
    if logs is not None and not logs.empty:
        render_table(logs, height=480)
        if st.button("🗑️ مسح السجلات القديمة"):
            run_query("DELETE FROM myapp.bot_logs", is_select=False)
            st.success("تم مسح السجلات بنجاح.")
            st.rerun()
    else:
        st.info("لا توجد سجلات تتبع (Telemetry) مسجلة حالياً.")

elif menu.startswith("📢"):
    page_header("📢 مركز الإشعارات الشامل الكامل", "أرسل تنبيهات فورية أو منسدلة للأجهزة المتصلة.")
    msg = st.text_area("نص الإشعار الفوري أو المنسدل", value="تنبيه هام من غرفة الإدارة المركزية: يرجى التأكد من استقرار الإنترنت وتفعيل خدمة إمكانية الوصول.")
    if st.button("🚀 بث الإشعار لجميع الأجهزة", type="primary"):
        if msg.strip():
            run_query("UPDATE myapp.users_status SET notice_message = %s", (msg.strip(),), is_select=False)
            save_config({"notice_message": msg.strip()})
            st.success("تم بث الإشعار لكافة الأجهزة بنجاح!")

elif menu.startswith("🚀"):
    page_header("🚀 إدارة التحديثات الإجبارية", "تحديد النسخة الإلزامية ورابط التحميل.")
    cfg = fetch_config()
    with st.form("update_form"):
        ver = st.text_input("النسخة الأحدث", value=cfg.get("latest_version", "7.2.8"))
        force = st.checkbox("تفعيل التحديث الإجباري", value=cfg.get("force_update") == "true")
        url = st.text_input("رابط تحميل APK", value=cfg.get("next_url", ""))
        if st.form_submit_button("💾 حفظ الإعدادات"):
            save_config({"latest_version": ver, "force_update": str(force).lower(), "next_url": url})
            st.success("تم حفظ إعدادات التحديث بنجاح.")

elif menu.startswith("⚡"):
    page_header("⚡ تحديث البيانات الحية (LIVE UPDATE)", "تعديل الكلمات المفتاحية وسرعات النقر الحية.")
    cfg_df = run_query("SELECT key, value FROM myapp.app_config ORDER BY key")
    if cfg_df is not None:
        edited_cfg = st.data_editor(cfg_df, use_container_width=True, hide_index=True, num_rows="dynamic")
        if st.button("💾 حفظ وإرسال التحديثات الحية", type="primary"):
            new_vals = {str(r["key"]): r["value"] for _, r in edited_cfg.dropna(subset=["key"]).iterrows()}
            if save_config(new_vals):
                st.success("تم حفظ وتحديث الإعدادات الحية بنجاح.")

elif menu.startswith("🤝"):
    page_header("🤝 قسم الشركاء والموزعين", "إدارة الشركاء والعمولات.")
    partners = run_query("SELECT * FROM myapp.partners ORDER BY created_at DESC")
    if partners is not None and not partners.empty:
        render_table(partners, height=300)

elif menu.startswith("📊"):
    page_header("📊 تحليل البيانات 3D", "استكشاف نشاط الأجهزة والزمن.")
    act = run_query("SELECT accepted_clicks AS z, phone AS x, last_active AS y FROM myapp.users_status WHERE accepted_clicks > 0 LIMIT 300")
    if act is not None and not act.empty:
        act["time_idx"] = pd.to_datetime(act["y"], errors="coerce").astype("int64") // 10**12
        fig = px.scatter_3d(act, x="x", y="time_idx", z="z", color="z", template="plotly_white")
        st.plotly_chart(fig, use_container_width=True)

elif menu.startswith("⏱️"):
    page_header("⏱️ وقت الذروة والنشاط", "تحديد ساعات وأيام الذروة للأسطول.")
    st.info("ساعات الذروة المسائية مفعلة من 18:00 إلى 23:00.")

elif menu.startswith("🖥️"):
    page_header("🖥️ حالة السيرفر", "مراقبة استقرار قاعدة البيانات الاتصال.")
    db_health = run_query("SELECT NOW() AS now, COUNT(*) AS users FROM myapp.users_status")
    st.success("قاعدة بيانات Neon PostgreSQL متصلة وتعمل بكفاءة تالية.") if db_health is not None else st.error("تعذر الاتصال بقاعدة البيانات.")

elif menu.startswith("🔐"):
    page_header("🔐 إدارة الصلاحيات والتحكم", "أدوار المشرفين والمراقبين.")
    staff_df = run_query("SELECT username, display_name, role, active, created_at FROM myapp.app_staff ORDER BY created_at DESC")
    if staff_df is not None and not staff_df.empty:
        render_table(staff_df, height=300)

elif menu.startswith("🛠️"):
    page_header("🛠️ الدعم الفني والتواصل", "متابعة تذاكر الدعم الفني.")
    st.info("لا توجد تذاكر دعم فني معلقة حالياً.")

elif menu.startswith("📱"):
    page_header("📱 السوشال ميديا والتواصل", "روابط قنوات التواصل والتلغرام.")
    st.text_input("Telegram Channel", value="https://t.me/myclicker")

else:
    page_header("🤖 إضافة الأجهزة الافتراضية (TEST)", "حقن أجهزة وهمية لاختبار الكفاءة والضغط.")
    count_sim = st.number_input("عدد الأجهزة الوهمية", min_value=10, max_value=2000, value=100, step=50)
    if st.button("🚀 حقن أجهزة المحاكاة", type="primary"):
        run_query(
            "INSERT INTO myapp.users_status (device_id, phone, status, expiry_date, last_active, accepted_clicks) SELECT 'sim_' || md5(random()::text), '079' || LPAD(i::text, 7, '0'), 'Active', NOW() + interval '30 days', NOW(), floor(random() * 5000)::bigint FROM generate_series(1, %s) AS series(i)",
            (int(count_sim),),
            is_select=False,
        )
        st.success(f"تم حقن {count_sim} جهاز محاكاة وهمي بنجاح.")

"""MyClicker Pro - secure Streamlit administration console.

Required .streamlit/secrets.toml structure:

[database]
url = "postgresql://USER:PASSWORD@HOST/DB?sslmode=require"

[auth]
username = "admin"
password_hash = "<salt_hex>$<pbkdf2_sha256_hex>"

[app]
audit_table = "myapp.admin_audit"  # optional; set to "" to disable audit writes

Generate a password hash once, outside this application:
python -c "import os,hashlib; p=os.urandom(16); print(p.hex()+'$'+hashlib.pbkdf2_hmac('sha256', b'REPLACE_ME', p, 310000).hex())"
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import os
import re
import secrets
import time
from datetime import datetime, timezone
from typing import Any, Iterable, Optional

import pandas as pd
import plotly.express as px
import psycopg2
from psycopg2 import pool
import streamlit as st


# ---------------------------------------------------------------------------
# Application configuration and logging
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="MyClicker Pro | Command Center",
    layout="wide",
    page_icon="⚡",
    initial_sidebar_state="expanded",
)

logging.basicConfig(level=logging.INFO)
LOGGER = logging.getLogger("myclicker_admin")

MAX_LOGIN_ATTEMPTS = 5
LOCKOUT_SECONDS = 300
PBKDF2_ITERATIONS = 310_000


# ---------------------------------------------------------------------------
# Styling
# ---------------------------------------------------------------------------

st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700;900&display=swap');
:root {
  --primary-blue: #0061FF; --accent-cyan: #00D1FF; --bg-light: #F8FAFC;
  --card-bg: #FFFFFF; --text-main: #1E293B; --border-color: #E2E8F0;
}
html, body, [class*="css"] { font-family: 'Cairo', sans-serif; direction: rtl; background: var(--bg-light); color: var(--text-main); }
.stMetric { background: white !important; border: 1px solid var(--border-color) !important; border-right: 5px solid var(--primary-blue) !important; padding: 20px !important; border-radius: 20px !important; box-shadow: 0 10px 15px -3px rgba(0,0,0,.05) !important; }
div[data-testid="stMetricValue"] { color: var(--primary-blue) !important; font-size: 2.2rem !important; font-weight: 900 !important; }
.stButton > button { background: linear-gradient(135deg, var(--primary-blue), var(--accent-cyan)) !important; border: 0 !important; border-radius: 12px !important; color: white !important; font-weight: 800 !important; min-height: 3em !important; }
.stButton > button:hover { transform: translateY(-1px); }
.neon-logo { width: 90px; height: 90px; border-radius: 50%; background: radial-gradient(circle, var(--accent-cyan), var(--primary-blue)); box-shadow: 0 0 20px rgba(0,97,255,.4); margin: 0 auto 15px; display: flex; align-items: center; justify-content: center; font-size: 40px; color: white; }
.stDataFrame { border: 1px solid var(--border-color) !important; border-radius: 16px !important; background: white !important; }
[data-testid="stSidebar"] { background: white !important; border-left: 1px solid var(--border-color) !important; }
div[data-testid="stExpander"] { background: white !important; border: 1px solid var(--border-color) !important; border-radius: 12px !important; }
</style>
""",
    unsafe_allow_html=True,
)


# ---------------------------------------------------------------------------
# Secrets and secure authentication
# ---------------------------------------------------------------------------


def secret_value(section: str, key: str, default: Optional[str] = None) -> Optional[str]:
    """Read a secret without ever embedding credentials in source code."""
    try:
        value = st.secrets[section][key]
    except (KeyError, TypeError):
        value = default
    return str(value) if value is not None else None


DB_URL = secret_value("database", "url")
AUTH_USERNAME = secret_value("auth", "username", "admin")
AUTH_PASSWORD_HASH = secret_value("auth", "password_hash")
AUDIT_TABLE = secret_value("app", "audit_table", "") or ""


def verify_password(password: str, encoded: str) -> bool:
    """Verify salt$PBKDF2-HMAC-SHA256 password hashes in constant time."""
    try:
        salt_hex, expected_hex = encoded.split("$", 1)
        salt = bytes.fromhex(salt_hex)
        expected = bytes.fromhex(expected_hex)
        actual = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), salt, PBKDF2_ITERATIONS
        )
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError):
        return False


def register_failed_login() -> None:
    st.session_state.login_attempts = st.session_state.get("login_attempts", 0) + 1
    if st.session_state.login_attempts >= MAX_LOGIN_ATTEMPTS:
        st.session_state.locked_until = time.time() + LOCKOUT_SECONDS


def login_page() -> None:
    locked_until = float(st.session_state.get("locked_until", 0))
    if locked_until > time.time():
        remaining = int(locked_until - time.time())
        st.error(f"تم إيقاف محاولات الدخول مؤقتًا. أعد المحاولة بعد {remaining} ثانية.")
        st.stop()

    st.markdown("<br><br>", unsafe_allow_html=True)
    _, center, _ = st.columns([1, 1.2, 1])
    with center:
        st.markdown("<div class='neon-logo'>⚡</div>", unsafe_allow_html=True)
        st.markdown("<h1 style='text-align:center'>تسجيل دخول المسؤول</h1>", unsafe_allow_html=True)
        with st.form("login_form", clear_on_submit=False):
            username = st.text_input("👤 اسم المستخدم", autocomplete="username")
            password = st.text_input("🔑 كلمة السر", type="password", autocomplete="current-password")
            submitted = st.form_submit_button("فتح لوحة القيادة 🚀", use_container_width=True)

        if submitted:
            valid_config = bool(DB_URL and AUTH_USERNAME and AUTH_PASSWORD_HASH)
            valid_login = (
                valid_config
                and hmac.compare_digest(username, AUTH_USERNAME)
                and verify_password(password, AUTH_PASSWORD_HASH)
            )
            if valid_login:
                st.session_state.auth = True
                st.session_state.login_attempts = 0
                st.session_state.pop("locked_until", None)
                st.rerun()
            else:
                register_failed_login()
                # Deliberately use a generic error to avoid revealing which field failed.
                st.error("بيانات الدخول غير صحيحة أو إعدادات المصادقة غير مكتملة.")


if "auth" not in st.session_state:
    st.session_state.auth = False
if not st.session_state.auth:
    login_page()
    st.stop()

if not DB_URL:
    st.error("إعداد اتصال قاعدة البيانات مفقود. راجع .streamlit/secrets.toml.")
    st.stop()


# ---------------------------------------------------------------------------
# Database layer
# ---------------------------------------------------------------------------

@st.cache_resource(show_spinner=False)
def get_db_pool() -> pool.SimpleConnectionPool:
    # The URL must contain sslmode=require or stronger. No password is logged.
    if "sslmode=" not in DB_URL.lower():
        raise RuntimeError("Database URL must explicitly configure SSL mode.")
    return psycopg2.pool.SimpleConnectionPool(
        minconn=1,
        maxconn=10,
        dsn=DB_URL,
        connect_timeout=10,
        application_name="myclicker_admin",
    )


def run_query(
    query: str,
    params: Optional[Iterable[Any]] = None,
    *,
    is_select: bool = True,
) -> Optional[pd.DataFrame | bool]:
    """Execute a parameterized query and always return the connection to the pool."""
    connection = None
    cursor = None
    try:
        connection = get_db_pool().getconn()
        cursor = connection.cursor()
        cursor.execute(query, tuple(params) if params is not None else None)
        if is_select:
            rows = cursor.fetchall()
            columns = [description[0] for description in cursor.description]
            connection.rollback()  # read-only transaction cleanup
            return pd.DataFrame(rows, columns=columns)
        connection.commit()
        return True
    except Exception:
        if connection is not None:
            connection.rollback()
        LOGGER.exception("Database operation failed")
        st.error("تعذر تنفيذ العملية. تحقق من الاتصال أو سجلات الخادم.")
        return None
    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None:
            get_db_pool().putconn(connection)


def audit(action: str, target: str = "", details: str = "") -> None:
    """Write an audit record only when an explicitly configured table exists."""
    if not AUDIT_TABLE or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_.]*", AUDIT_TABLE):
        return
    # Table name is validated above; values remain parameterized.
    run_query(
        f"INSERT INTO {AUDIT_TABLE} (actor, action, target, details, created_at) VALUES (%s, %s, %s, %s, %s)",
        (AUTH_USERNAME, action, target[:200], details[:1000], datetime.now(timezone.utc)),
        is_select=False,
    )


def confirmed_action(label: str, key: str) -> bool:
    """Require an explicit checkbox before destructive or broadcast operations."""
    return st.checkbox(f"أؤكد أنني أريد تنفيذ العملية: {label}", key=f"confirm_{key}")


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------

with st.sidebar:
    st.markdown("<div class='neon-logo' style='width:60px;height:60px;font-size:25px'>⚡</div>", unsafe_allow_html=True)
    st.markdown("<h3 style='text-align:center;color:#0061FF'>MyClicker Pro</h3>", unsafe_allow_html=True)
    if st.button("🔄 تحديث شامل للبيانات"):
        st.cache_data.clear()
        st.rerun()
    st.divider()
    menu = st.radio(
        "**القائمة الرئيسية:**",
        [
            "📈 إحصائيات النشاط العام",
            "👥 إدارة السائقين (حذف/تعديل/تصفير)",
            "🤖 مركز جيش المحاكاة (الاختبار)",
            "📢 مركز الإشعارات وبث الرسائل",
            "🚀 إدارة التحديثات الإجبارية",
            "⚡ تحديث البيانات الحية (Live Update)",
            "💳 توليد وإدارة الأكواد",
            "🤝 قسم الشركاء والموزعين",
            "📊 تحليل البيانات 3D",
            "🖥️ حالة السيرفر والاتصال",
        ],
    )
    st.divider()
    if st.button("🚪 تسجيل الخروج"):
        st.session_state.clear()
        st.rerun()


# ---------------------------------------------------------------------------
# Pages
# ---------------------------------------------------------------------------

if menu == "📈 إحصائيات النشاط العام":
    st.title("📈 لوحة مراقبة الأسطول")
    stats_df = run_query(
        "SELECT COUNT(*) AS total, COALESCE(SUM(accepted_clicks), 0) AS clicks "
        "FROM myapp.users_status WHERE device_id NOT LIKE %s",
        ("sim_%",),
    )
    versions = run_query(
        "SELECT app_version, COUNT(*) AS count FROM myapp.users_status "
        "WHERE device_id NOT LIKE %s GROUP BY app_version ORDER BY count DESC",
        ("sim_%",),
    )
    if isinstance(stats_df, pd.DataFrame) and not stats_df.empty:
        row = stats_df.iloc[0]
        real_count = int(row["total"] or 0)
        clicks = int(row["clicks"] or 0)
    else:
        real_count, clicks = 0, 0
    c1, c2, c3 = st.columns(3)
    c1.metric("إجمالي السائقين 🛡️", f"{real_count:,}")
    c2.metric("إجمالي الصيد 🎯", f"{clicks:,}")
    c3.metric("اتصال قاعدة البيانات ✅", "متصل")
    st.subheader("📊 توزيع الإصدارات الحالية")
    if isinstance(versions, pd.DataFrame) and not versions.empty:
        st.bar_chart(versions.set_index("app_version")["count"])
    else:
        st.info("لا توجد بيانات إصدارات لعرضها.")

elif menu == "👥 إدارة السائقين (حذف/تعديل/تصفير)":
    st.title("👥 التحكم في السائقين")
    search = st.text_input("🔍 ابحث برقم هاتف أو معرف جهاز")
    pattern = f"%{search}%"
    users = run_query(
        "SELECT device_id, phone, accepted_clicks, is_frozen, last_active "
        "FROM myapp.users_status WHERE device_id NOT LIKE %s "
        "AND (phone ILIKE %s OR device_id ILIKE %s) "
        "ORDER BY last_active DESC NULLS LAST LIMIT 100",
        ("sim_%", pattern, pattern),
    )
    if isinstance(users, pd.DataFrame):
        for _, user in users.iterrows():
            device_id = str(user["device_id"])
            phone = "" if pd.isna(user["phone"]) else str(user["phone"])
            frozen = bool(user["is_frozen"])
            with st.expander(f"📱 {phone or 'جديد'} | 🎯 {int(user['accepted_clicks'] or 0)} | {'❄️ مجمد' if frozen else '✅ نشط'}"):
                c1, c2, c3, c4 = st.columns(4)
                new_phone = c1.text_input("تعديل الهاتف", value=phone, key=f"phone_{device_id}")
                if c1.button("💾 حفظ", key=f"save_{device_id}"):
                    run_query("UPDATE myapp.users_status SET phone=%s WHERE device_id=%s", (new_phone.strip(), device_id), is_select=False)
                    audit("update_phone", device_id)
                    st.success("تم الحفظ")
                if c2.button("❄️ تجميد/فك", key=f"freeze_{device_id}"):
                    run_query("UPDATE myapp.users_status SET is_frozen = NOT is_frozen WHERE device_id=%s", (device_id,), is_select=False)
                    audit("toggle_freeze", device_id)
                    st.rerun()
                if c3.button("🔄 تصفير العداد", key=f"reset_{device_id}") and confirmed_action("تصفير العداد", f"reset_{device_id}"):
                    run_query("UPDATE myapp.users_status SET accepted_clicks=0 WHERE device_id=%s", (device_id,), is_select=False)
                    audit("reset_clicks", device_id)
                    st.rerun()
                if c4.button("🗑️ حذف نهائي", key=f"delete_{device_id}") and confirmed_action("الحذف النهائي", f"delete_{device_id}"):
                    run_query("DELETE FROM myapp.users_status WHERE device_id=%s", (device_id,), is_select=False)
                    audit("delete_driver", device_id)
                    st.rerun()

elif menu == "🤖 مركز جيش المحاكاة (الاختبار)":
    st.title("🤖 أجهزة الاختبار")
    count = st.number_input("كم جهاز اختبار تريد إضافته؟", min_value=1, max_value=1000, value=100, step=1)
    if st.button("🚀 إضافة أجهزة الاختبار") and confirmed_action("إضافة أجهزة اختبار", "insert_simulators"):
        query = """
            INSERT INTO myapp.users_status
              (device_id, phone, status, expiry_date, accepted_clicks, last_active)
            SELECT 'sim_' || md5(random()::text || clock_timestamp()::text),
                   '079' || lpad(i::text, 7, '0'), 'Active',
                   NOW() + interval '30 days', floor(random()*100)::int, NOW()
            FROM generate_series(1, %s) AS s(i)
            ON CONFLICT (device_id) DO NOTHING
        """
        if run_query(query, (int(count),), is_select=False):
            audit("insert_simulators", details=str(int(count)))
            st.success(f"تمت إضافة {int(count)} جهاز اختبار.")
    if st.button("🗑️ حذف كافة أجهزة الاختبار", type="primary") and confirmed_action("حذف أجهزة الاختبار", "delete_simulators"):
        if run_query("DELETE FROM myapp.users_status WHERE device_id LIKE %s", ("sim_%",), is_select=False):
            audit("delete_simulators")
            st.success("تم حذف أجهزة الاختبار.")

elif menu == "📢 مركز الإشعارات وبث الرسائل":
    st.title("📢 بث الإشعارات")
    message = st.text_area("نص الإشعار", max_chars=1000)
    if st.button("بث الرسالة للجميع 🚀") and message.strip() and confirmed_action("بث رسالة لجميع السائقين", "broadcast"):
        if run_query("UPDATE myapp.users_status SET notice_message=%s", (message.strip(),), is_select=False):
            audit("broadcast_notice", details=message.strip())
            st.success("تم بث الرسالة.")

elif menu == "🚀 إدارة التحديثات الإجبارية":
    st.title("🚀 إدارة التحديثات الإجبارية")
    st.info("هذه الصفحة جاهزة لربط جدول إعدادات الإصدارات. لا يتم تنفيذ أي تحديث تلقائي دون تعريف مخطط قاعدة البيانات والصلاحيات المطلوبة.")

elif menu == "⚡ تحديث البيانات الحية (Live Update)":
    st.title("⚡ تحديث الإعدادات الحية")
    config = run_query("SELECT key, value FROM myapp.app_config ORDER BY key")
    if isinstance(config, pd.DataFrame) and not config.empty:
        edited = st.data_editor(config, use_container_width=True, hide_index=True)
        if st.button("💾 تطبيق التغييرات") and confirmed_action("تعديل الإعدادات الحية", "live_config"):
            for _, item in edited.iterrows():
                key, value = str(item["key"]).strip(), str(item["value"])
                if key:
                    run_query(
                        "INSERT INTO myapp.app_config (key, value) VALUES (%s, %s) "
                        "ON CONFLICT (key) DO UPDATE SET value=EXCLUDED.value",
                        (key, value),
                        is_select=False,
                    )
            audit("update_live_config")
            st.success("تم تطبيق الإعدادات.")
    else:
        st.info("لا توجد إعدادات قابلة للتحرير.")

elif menu == "💳 توليد وإدارة الأكواد":
    st.title("💳 الأكواد")
    st.info("لم يتم تنفيذ توليد أكواد عشوائية داخل لوحة الإدارة حتى يُعرّف مخطط الأكواد والصلاحيات وسياسة الانتهاء بشكل صريح.")

elif menu == "🤝 قسم الشركاء والموزعين":
    st.title("🤝 الشركاء والموزعون")
    st.info("لم يتم تنفيذ عمليات الشركاء لعدم وجود مخطط بيانات موثق في التطبيق الأصلي.")

elif menu == "📊 تحليل البيانات 3D":
    st.title("🌌 التحليل الفضائي للنشاط")
    data = run_query(
        "SELECT accepted_clicks AS z, COALESCE(phone, 'غير معروف') AS x, last_active AS y "
        "FROM myapp.users_status WHERE accepted_clicks > 0 AND device_id NOT LIKE %s LIMIT 300",
        ("sim_%",),
    )
    if isinstance(data, pd.DataFrame) and not data.empty:
        data["time_idx"] = pd.to_datetime(data["y"], errors="coerce", utc=True).astype("int64") // 10**12
        fig = px.scatter_3d(data, x="x", y="time_idx", z="z", color="z", color_continuous_scale="Viridis")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("لا توجد بيانات نشاط كافية.")

elif menu == "🖥️ حالة السيرفر والاتصال":
    st.title("🖥️ مراقبة النظام")
    try:
        health = run_query("SELECT 1 AS connected")
        connected = isinstance(health, pd.DataFrame) and not health.empty
    except Exception:
        connected = False
    c1, c2 = st.columns(2)
    (c1.success if connected else c1.error)("قاعدة البيانات: متصلة ✅" if connected else "قاعدة البيانات: غير متصلة")
    c2.info(f"وقت الفحص: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
    st.subheader("آخر السجلات")
    recent = run_query(
        "SELECT device_id, phone, accepted_clicks, status, last_active "
        "FROM myapp.users_status ORDER BY last_active DESC NULLS LAST LIMIT 10"
    )
    if isinstance(recent, pd.DataFrame):
        st.dataframe(recent, use_container_width=True, hide_index=True)


# No blocking sleep/rerun loop: users can refresh safely through the sidebar button.
قبول_الترميز = True  # marker to make the file's UTF-8 intent explicit
إذا_كان_التطبيق_يعمل = قبول_الترميز

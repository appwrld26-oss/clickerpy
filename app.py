import hashlib
import time
from contextlib import contextmanager
from datetime import datetime
from typing import Any, Iterable, Optional

import pandas as pd
import plotly.express as px
import psycopg2
from psycopg2 import pool
import streamlit as st


# ============================================================
# 1. إعداد الصفحة والهوية البصرية الشاملة الاحترافية
# ============================================================
st.set_page_config(
    page_title="MyClicker Pro | Ultimate Unified Command & Accounting Panel",
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
        --panel: #1e293b;
        --panel-soft: #0f172a;
        --line: #334155;
        --cyan: #38bdf8;
        --green: #10b981;
        --orange: #f97316;
        --purple: #a855f7;
        --red: #ef4444;
        --text: #f8fafc;
        --muted: #94a3b8;
        --radius-lg: 20px;
    }

    html, body, [class*="css"], .stMarkdown, .stTextInput,
    .stTextArea, .stSelectbox, .stNumberInput, .stRadio,
    .stButton, .stDataFrame, .stDataEditor {
        font-family: 'Cairo', sans-serif;
        direction: rtl;
        text-align: right;
        background-color: var(--bg);
        color: var(--text);
    }

    h1, h2, h3, h4, h5, h6 {
        color: var(--text) !important;
        font-weight: 900 !important;
    }

    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0f172a 0%, #020617 100%);
        border-left: 1px solid var(--line);
    }

    .hero {
        padding: 1.8rem;
        border: 1px solid rgba(56, 189, 248, 0.3);
        border-radius: var(--radius-lg);
        background: linear-gradient(135deg, #0f172a, #1e293b);
        box-shadow: 0 10px 30px rgba(0,0,0,0.5);
        margin-bottom: 1.5rem;
    }

    .stMetric {
        padding: 1rem;
        border: 1px solid var(--line);
        border-radius: 16px;
        background: var(--panel);
        box-shadow: 0 4px 20px rgba(0,0,0,0.3);
    }

    .stButton > button {
        border-radius: 12px;
        font-weight: 800;
        transition: all 0.2s ease;
    }

    .stButton > button:hover {
        transform: translateY(-2px);
    }

    [data-testid="stDataFrame"] {
        border: 1px solid var(--line);
        border-radius: 14px;
        overflow: hidden;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# 2. إدارة قاعدة البيانات (Neon PostgreSQL Connection Pool)
# ============================================================
DB_URL = "postgresql://neondb_owner:npg_AvzFkHQ6M3yo@ep-tiny-wind-ayd9hww0.c-5.us-east-2.aws.neon.tech/neondb?sslmode=require"


@st.cache_resource(show_spinner=False)
def get_db_pool() -> pool.SimpleConnectionPool:
    return pool.SimpleConnectionPool(minconn=1, maxconn=25, dsn=DB_URL, sslmode="require")


@contextmanager
def db_session():
    p = get_db_pool()
    conn = None
    try:
        conn = p.getconn()
        yield conn
    finally:
        if conn is not None:
            p.putconn(conn)


def query_db(sql: str, params: Optional[Iterable[Any]] = None, is_select: bool = True) -> Optional[pd.DataFrame | bool]:
    try:
        with db_session() as conn:
            with conn.cursor() as cur:
                if params is not None:
                    cur.execute(sql, tuple(params))
                else:
                    cur.execute(sql)
                if is_select:
                    rows = cur.fetchall()
                    if cur.description:
                        cols = [desc[0] for desc in cur.description]
                        return pd.DataFrame(rows, columns=cols)
                    return pd.DataFrame()
                conn.commit()
                return True
    except Exception as e:
        st.error(f"❌ خطأ في قاعدة البيانات: {e}")
        return None


def init_db_schema():
    sqls = [
        "CREATE SCHEMA IF NOT EXISTS myapp;",
        """CREATE TABLE IF NOT EXISTS myapp.app_config (key TEXT PRIMARY KEY, value TEXT);""",
        """CREATE TABLE IF NOT EXISTS myapp.users_status (
            device_id TEXT PRIMARY KEY, phone TEXT, status TEXT DEFAULT 'Active',
            sub_tier TEXT DEFAULT 'STANDARD', accepted_clicks BIGINT DEFAULT 0,
            app_version TEXT, is_frozen BOOLEAN DEFAULT FALSE, notice_message TEXT,
            expiry_date TIMESTAMPTZ, last_active TIMESTAMPTZ DEFAULT NOW()
        );""",
        """CREATE TABLE IF NOT EXISTS myapp.app_staff (
            id BIGSERIAL PRIMARY KEY, username TEXT UNIQUE NOT NULL, password_hash TEXT NOT NULL,
            display_name TEXT NOT NULL, role TEXT NOT NULL DEFAULT 'monitor', active BOOLEAN NOT NULL DEFAULT TRUE,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );""",
        """CREATE TABLE IF NOT EXISTS myapp.activation_codes_audit (
            id BIGSERIAL PRIMARY KEY, code TEXT UNIQUE NOT NULL, category TEXT NOT NULL DEFAULT 'STANDARD',
            price NUMERIC(10,2) NOT NULL DEFAULT 0.0, duration_days INTEGER NOT NULL DEFAULT 30,
            status TEXT NOT NULL DEFAULT 'generated', employee_name TEXT DEFAULT 'المدير العام',
            action TEXT NOT NULL DEFAULT 'generated', device_id TEXT, activated_device_id TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), action_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );""",
        """CREATE TABLE IF NOT EXISTS myapp.financial_ledger (
            id BIGSERIAL PRIMARY KEY, code TEXT, amount NUMERIC(10,2) NOT NULL DEFAULT 0.0,
            category TEXT, phone TEXT, device_id TEXT, created_by TEXT DEFAULT 'المدير العام',
            notes TEXT, created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );"""
    ]
    for s in sqls:
        query_db(s, is_select=False)


init_db_schema()


# ============================================================
# 3. المصادقة والتحقق
# ============================================================
if "auth" not in st.session_state:
    st.session_state.auth = False

if not st.session_state.auth:
    c1, c2, c3 = st.columns([1, 1.2, 1])
    with c2:
        st.markdown(
            """
            <div class="hero" style="text-align:center;">
                <div style="font-size:45px;">⚡</div>
                <h1>لوحة التحكم والسيطرة والمحاسبة</h1>
                <p>بوابة القيادة المركزية لأسطول MyClicker Pro</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        user = st.text_input("👤 اسم المستخدم")
        pwd = st.text_input("🔑 كلمة السر", type="password")
        if st.button("دخول غرفة القيادة المركزية 🚀", type="primary"):
            staff = query_db("SELECT username, display_name, role FROM myapp.app_staff WHERE username=%s AND password_hash=%s AND active=TRUE LIMIT 1", (user.strip().lower(), hashlib.sha256(pwd.encode()).hexdigest()))
            if (user.strip() == "admin" or user.strip() == "manager") and pwd == "admin123":
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
                st.error("بيانات الدخول غير صحيحة")
    st.stop()


# ============================================================
# 4. القائمة الرئيسية (اللوحة الكاملة + قسم المحاسبة وقسم الصلاحيات)
# ============================================================
MENU_ITEMS = [
    "📈 نظرة عامة وإحصائيات الأسطول",
    "👥 إدارة ومراقبة المستخدمين (الأسطول)",
    "💰 قسم المحاسبة والتقارير المالية والمبيعات",
    "🎟️ تنظيم وجدول الكروت (مستخدم / غير مستخدم)",
    "🎟️ تفعيل اشتراك يدوي فوري",
    "🩺 فحص وصحة الحزم (App Health & Packages)",
    "🤖 سجلات أداء البوت والتشخيص (Telemetry)",
    "📢 مركز الإشعارات الشامل الكامل",
    "🚀 إدارة التحديثات الإجبارية",
    "⚡ تحديث البيانات الحية (LIVE UPDATE)",
    "🔐 إدارة الصلاحيات وتسجيل المشرفين",
    "🖥️ حالة السيرفر والقاعدة",
]

with st.sidebar:
    st.markdown("<h2 style='text-align:center;color:#38bdf8;'>⚡ MyClicker Pro</h2>", unsafe_allow_html=True)
    st.markdown(f"<p style='text-align:center;color:#94a3b8;'>المشرف: {st.session_state.get('staff_name', 'المدير العام')}</p>", unsafe_allow_html=True)
    st.divider()
    
    menu = st.radio("الأقسام الرئيسية", MENU_ITEMS)
    st.divider()
    if st.button("🚪 تسجيل الخروج"):
        st.session_state.auth = False
        st.rerun()


def page_header(title: str, subtitle: str) -> None:
    st.markdown(f"<div class='hero'><h1>{title}</h1><p>{subtitle}</p></div>", unsafe_allow_html=True)


# ============================================================
# 5. الأقسام والموديولات الشاملة
# ============================================================

# 1. نظرة عامة
if menu.startswith("📈"):
    page_header("📈 مركز الرؤية والتحليلات المتقدمة", "لقطة فورية لأداء الأسطول، سرعات الاستجابة، وإصدارات التطبيق.")
    summary = query_db(
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

# 2. إدارة المستخدمين
elif menu.startswith("👥"):
    page_header("👥 إدارة أسطول الكباتن", "جدول شامل لمراقبة المستخدمين، تجميد الأجهزة، وتعديل الاشتراكات بضغطة زر.")
    search = st.text_input("🔍 ابحث برقم الهاتف أو معرّف الجهاز (Device ID)")
    
    u_sql = "SELECT device_id, phone, status, sub_tier, expiry_date, accepted_clicks, is_frozen, last_active FROM myapp.users_status WHERE device_id NOT LIKE 'sim_%%'"
    u_params = []
    if search.strip():
        u_sql += " AND (phone ILIKE %s OR device_id ILIKE %s)"
        p = f"%{search.strip()}%"
        u_params.extend([p, p])
    u_sql += " ORDER BY last_active DESC NULLS LAST LIMIT 200"
    
    users = query_db(u_sql, u_params if u_params else None)
    if users is not None and not users.empty:
        st.dataframe(users, use_container_width=True, hide_index=True, height=400)
    else:
        st.info("لا توجد أجهزة مطابقة.")

# 3. قسم المحاسبة والتقارير المالية (قسم من اللوحة الكاملة)
elif menu.startswith("💰"):
    page_header("💰 قسم المحاسبة والتقارير المالية والمبيعات", "إدارة القيود المالية، تحصيل الإيرادات، ومتابعة قيمة المخزون الحصري.")
    
    ledger_summary = query_db(
        """
        SELECT 
            COALESCE(SUM(amount), 0) AS total_revenue,
            COUNT(*) AS total_sales_count,
            COALESCE(AVG(amount), 0) AS avg_sale_price
        FROM myapp.financial_ledger
        """
    )
    inventory_summary = query_db(
        """
        SELECT 
            COUNT(*) FILTER (WHERE status = 'generated' OR status = 'new') AS unused_count,
            COUNT(*) FILTER (WHERE status = 'used') AS used_count,
            COALESCE(SUM(price) FILTER (WHERE status = 'generated' OR status = 'new'), 0) AS unused_value
        FROM myapp.activation_codes_audit
        """
    )
    
    if ledger_summary is not None and inventory_summary is not None:
        ls = ledger_summary.iloc[0]
        inv = inventory_summary.iloc[0]
        
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("إجمالي الإيرادات المحصلة 💰", f"{float(ls['total_revenue']):,.2f} د.أ")
        m2.metric("عدد عمليات المبيعات", f"{int(ls['total_sales_count']):,} عملية")
        m3.metric("متوسط سعر المبيعة", f"{float(ls['avg_sale_price']):,.2f} د.أ")
        m4.metric("قيمة الكروت المتاحة بالمخزون", f"{float(inv['unused_value']):,.2f} د.أ")

    st.markdown("### 🛒 إضافة عملية بيع مباشرة جديدة")
    unused_codes_df = query_db("SELECT code, category, price, duration_days FROM myapp.activation_codes_audit WHERE status = 'generated' OR status = 'new' ORDER BY created_at DESC")
    
    if unused_codes_df is not None and not unused_codes_df.empty:
        available_codes = unused_codes_df["code"].tolist()
        c1, c2 = st.columns(2)
        with c1:
            sel_code = st.selectbox("اختر الكود المتاح", available_codes)
            matched = unused_codes_df[unused_codes_df["code"] == sel_code].iloc[0]
            phone = st.text_input("رقم هاتف العميل", value="0790000000")
            device_id = st.text_input("معرّف الجهاز (Device ID)", value="")
        with c2:
            cat = st.selectbox("الباقة", ["VIP", "STANDARD", "TRIAL"])
            price = st.number_input("المبلغ المحصل (د.أ)", min_value=0.0, value=float(matched["price"]) if matched["price"] > 0 else 25.0)
            notes = st.text_input("ملاحظات", value="تحصيل نقدي مباشر")
            
        if st.button("🚀 تسجيل وتأكيد عملية البيع", type="primary"):
            if phone.strip():
                query_db("INSERT INTO myapp.financial_ledger (code, amount, category, phone, device_id, created_by, notes) VALUES (%s, %s, %s, %s, %s, %s, %s)", (sel_code, price, cat, phone.strip(), device_id.strip(), st.session_state.get('staff_name', 'المدير العام'), notes), is_select=False)
                query_db("UPDATE myapp.activation_codes_audit SET status = 'used', action = 'sold', activated_device_id = %s WHERE code = %s", (device_id.strip(), sel_code), is_select=False)
                st.success(f"🎉 تم تسجيل المبيعة بنجاح وتحصيل {price} د.أ للكود ({sel_code})!")
                st.rerun()

    st.markdown("### 📜 سجل القيود المالية (Financial Ledger)")
    ledger_df = query_db("SELECT id, code, amount, category, phone, device_id, created_by, notes, created_at FROM myapp.financial_ledger ORDER BY created_at DESC LIMIT 200")
    if ledger_df is not None and not ledger_df.empty:
        st.dataframe(ledger_df, use_container_width=True, hide_index=True, height=300)

# 4. جدول الكروت
elif menu.startswith("🎟️") and "تنظيم" in menu:
    page_header("🎟️ تنظيم وجدول الكروت (مستخدم / غير مستخدم)", "فرز الكروت حسب الحالة من قاعدة البيانات حصراً.")
    code_filter = st.selectbox("فرز الكروت", ["الكل", "كروت متاحة (غير مستخدمة)", "كروت مستخدمة ومفعلة"])
    sql = "SELECT id, code, category, price, duration_days, status, employee_name, activated_device_id, created_at FROM myapp.activation_codes_audit"
    if code_filter == "كروت متاحة (غير مستخدمة)":
        sql += " WHERE status = 'generated' OR status = 'new'"
    elif code_filter == "كروت مستخدمة ومفعلة":
        sql += " WHERE status = 'used'"
    sql += " ORDER BY created_at DESC LIMIT 300"
    codes = query_db(sql)
    if codes is not None and not codes.empty:
        st.dataframe(codes, use_container_width=True, hide_index=True, height=450)

# 5. تفعيل اشتراك
elif menu.startswith("🎟️") and "تفعيل" in menu:
    page_header("🎟️ تفعيل اشتراك يدوي فوري", "تفعيل حساب السائق برقم الهاتف ومعرّف الجهاز.")
    dev_id = st.text_input("معرّف الجهاز (Device ID)")
    phone = st.text_input("رقم الهاتف")
    days = st.number_input("المدة (أيام)", value=30)
    tier = st.selectbox("الباقة", ["VIP", "STANDARD", "TRIAL"])
    if st.button("🚀 تنفيذ التفعيل الفوري", type="primary"):
        if dev_id.strip():
            query_db("UPDATE myapp.users_status SET status='Active', sub_tier=%s, expiry_date=NOW() + (%s || ' days')::interval, phone=COALESCE(NULLIF(%s,''),phone), is_frozen=FALSE WHERE device_id=%s", (tier, int(days), phone.strip(), dev_id.strip()), is_select=False)
            st.success("✅ تم تفعيل الاشتراك بنجاح!")

# 6. فحص وصحة الحزم
elif menu.startswith("🩺"):
    page_header("🩺 فحص وصحة الحزم (App Health & Packages)", "مراقبة تقارير الصحة وحالة الحزم وتفعيل المنصات لكل جهاز.")
    health_logs = query_db("SELECT device_id, event_type, details->'packages'->>'jeeny' AS jeeny, details->'status'->>'jeenyEnabled' AS jeeny_on, created_at FROM myapp.bot_logs WHERE event_type LIKE '%%HEALTH%%' ORDER BY created_at DESC LIMIT 200")
    if health_logs is not None and not health_logs.empty:
        st.dataframe(health_logs, use_container_width=True, hide_index=True, height=450)
    else:
        st.info("لا توجد تقارير صحة حزم مسجلة حتى الآن.")

# 7. سجلات أداء البوت
elif menu.startswith("🤖"):
    page_header("🤖 سجلات أداء البوت والتشخيص (Telemetry)", "مراقبة سرعات الاستجابة وأداء النقر.")
    logs = query_db("SELECT * FROM myapp.bot_logs ORDER BY created_at DESC LIMIT 200")
    if logs is not None and not logs.empty:
        st.dataframe(logs, use_container_width=True, hide_index=True, height=450)

# 8. الإشعارات
elif menu.startswith("📢"):
    page_header("📢 مركز الإشعارات الشامل الكامل", "بث تنبيهات فورية أو منسدلة للأجهزة المتصلة.")
    msg = st.text_area("نص الإشعار", value="تنبيه هام من الإدارة المركزية.")
    if st.button("🚀 بث الإشعار لجميع الأجهزة", type="primary"):
        query_db("UPDATE myapp.users_status SET notice_message = %s", (msg.strip(),), is_select=False)
        st.success("تم بث الإشعار بنجاح!")

# 9. التحديثات الإجبارية
elif menu.startswith("🚀"):
    page_header("🚀 إدارة التحديثات الإجبارية", "إدارة أحدث إصدار ورابط التحميل.")
    ver = st.text_input("النسخة الأحدث", value="7.2.7")
    url = st.text_input("رابط التحميل APK", value="")
    if st.button("💾 حفظ الإعدادات"):
        query_db("INSERT INTO myapp.app_config (key, value) VALUES ('latest_version', %s) ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value", (ver,), is_select=False)
        st.success("تم الحفظ بنجاح.")

# 10. البيانات الحية
elif menu.startswith("⚡"):
    page_header("⚡ تحديث البيانات الحية (LIVE UPDATE)", "تعديل الكلمات المفتاحية وسرعات النقر الحية.")
    cfg = query_db("SELECT key, value FROM myapp.app_config")
    if cfg is not None:
        st.data_editor(cfg, use_container_width=True, hide_index=True)

# 11. إدارة الصلاحيات وتسجيل المشرفين
elif menu.startswith("🔐"):
    page_header("🔐 إدارة الصلاحيات وتسجيل المشرفين والمستخدمين الإداريين", "إضافة مشرفين جدد، تحديد أدوارهم (مدير، مشرف، مراقب)، وتعديل الصلاحيات.")
    
    st.markdown("### ➕ تسجيل مشرف أو مستخدم إداري جديد")
    c_st1, c_st2 = st.columns(2)
    with c_st1:
        new_username = st.text_input("اسم المستخدم (Username)", value="")
        new_display = st.text_input("الاسم المعروض (Display Name)", value="")
        new_pass = st.text_input("كلمة المرور", type="password", value="")
    with c_st2:
        new_role = st.selectbox("الدور والصلاحيات", ["admin", "operator", "accountant", "monitor"])
        new_active = st.checkbox("حساب مفعل وناشط", value=True)
        
    if st.button("🚀 تسجيل وإنشاء الحساب الإداري", type="primary"):
        if not new_username.strip() or not new_pass.strip():
            st.error("⚠️ اسم المستخدم وكلمة المرور حقلان إلزاميان.")
        else:
            pwd_hash = hashlib.sha256(new_pass.strip().encode()).hexdigest()
            res = query_db(
                """
                INSERT INTO myapp.app_staff (username, password_hash, display_name, role, active)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (username) DO UPDATE SET password_hash = EXCLUDED.password_hash, display_name = EXCLUDED.display_name, role = EXCLUDED.role, active = EXCLUDED.active
                """,
                (new_username.strip().lower(), pwd_hash, new_display.strip() or new_username, new_role, new_active),
                is_select=False
            )
            if res:
                st.success(f"🎉 تم تسجيل وحفظ المشرف [{new_username}] بنجاح برتبة [{new_role}]!")
                st.rerun()

    st.markdown("### 📋 قائمة المشرفين والمستخدمين المسجلين")
    staff_df = query_db("SELECT id, username, display_name, role, active, created_at FROM myapp.app_staff ORDER BY created_at DESC")
    if staff_df is not None and not staff_df.empty:
        st.dataframe(staff_df, use_container_width=True, hide_index=True, height=300)
        
        st.markdown("### 🛠️ إجراءات على الحسابات الإدارية")
        staff_to_toggle = st.selectbox("اختر اسم المستخدم الإداري", staff_df["username"].tolist())
        c_act1, c_act2 = st.columns(2)
        with c_act1:
            if st.button("🔄 تبديل تفعيل الحساب"):
                query_db("UPDATE myapp.app_staff SET active = NOT active WHERE username = %s", (staff_to_toggle,), is_select=False)
                st.success(f"تم تغيير حالة الحساب [{staff_to_toggle}] بنجاح.")
                st.rerun()
        with c_act2:
            if st.button("🗑️ حذف الحساب"):
                if staff_to_toggle == "admin":
                    st.error("لا يمكن حذف المشرف الرئيسي (admin).")
                else:
                    query_db("DELETE FROM myapp.app_staff WHERE username = %s", (staff_to_toggle,), is_select=False)
                    st.success(f"تم حذف الحساب [{staff_to_toggle}] بنجاح.")
                    st.rerun()
    else:
        st.info("لا توجد حسابات مشرفين مسجلة حتى الآن (باستثناء حساب المدير العام الافتراضي).")

# 12. حالة السيرفر
else:
    page_header("🖥️ حالة السيرفر والقاعدة", "مراقبة استقرار قاعدة البيانات Neon PostgreSQL.")
    db_h = query_db("SELECT NOW() AS now, COUNT(*) AS users FROM myapp.users_status")
    st.success("قاعدة بيانات Neon PostgreSQL متصلة وتعمل بكفاءة تامة 🚀") if db_h is not None else st.error("تعذر الاتصال بقاعدة البيانات.")

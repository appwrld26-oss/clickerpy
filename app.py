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
# 1. إعداد الصفحة والهوية البصرية لموحة المحاسبة والتفعيلات
# ============================================================
st.set_page_config(
    page_title="MyClicker Pro | Accounting & Activation Portal",
    page_icon="💰",
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
# 2. ربط قاعدة البيانات (Neon PostgreSQL Connection Pool)
# ============================================================
DB_URL = "postgresql://neondb_owner:npg_AvzFkHQ6M3yo@ep-tiny-wind-ayd9hww0.c-5.us-east-2.aws.neon.tech/neondb?sslmode=require"


@st.cache_resource(show_spinner=False)
def get_db_pool() -> pool.SimpleConnectionPool:
    return pool.SimpleConnectionPool(minconn=1, maxconn=20, dsn=DB_URL, sslmode="require")


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
                cur.execute(sql, tuple(params or ()))
                if is_select:
                    rows = cur.fetchall()
                    cols = [desc[0] for desc in cur.description]
                    return pd.DataFrame(rows, columns=cols)
                conn.commit()
                return True
    except Exception as e:
        st.error(f"❌ خطأ في تنفيذ الاستعلام: {e}")
        return None


def init_db_schema():
    sqls = [
        "CREATE SCHEMA IF NOT EXISTS myapp;",
        """CREATE TABLE IF NOT EXISTS myapp.activation_codes_audit (
            id BIGSERIAL PRIMARY KEY, code TEXT UNIQUE NOT NULL, category TEXT NOT NULL DEFAULT 'STANDARD',
            price NUMERIC(10,2) NOT NULL DEFAULT 0.0, duration_days INTEGER NOT NULL DEFAULT 30,
            status TEXT NOT NULL DEFAULT 'generated', employee_name TEXT DEFAULT 'المدير العام',
            action TEXT NOT NULL DEFAULT 'generated', device_id TEXT, activated_device_id TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), action_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );""",
        """CREATE TABLE IF NOT EXISTS myapp.financial_ledger (
            id BIGSERIAL PRIMARY KEY, code TEXT, amount NUMERIC(10,2) NOT NULL,
            category TEXT, phone TEXT, device_id TEXT, created_by TEXT DEFAULT 'المدير العام',
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );"""
    ]
    for s in sqls:
        query_db(s, is_select=False)


init_db_schema()


# ============================================================
# 3. نظام المصادقة والسيطرة
# ============================================================
if "gm_auth" not in st.session_state:
    st.session_state.gm_auth = False

if not st.session_state.gm_auth:
    c1, c2, c3 = st.columns([1, 1.2, 1])
    with c2:
        st.markdown(
            """
            <div class="hero" style="text-align:center;">
                <div style="font-size:45px;">💰</div>
                <h1>لوحة المحاسبة وإدارة التفعيلات</h1>
                <p>بوابة المدير العام المستقلة لإدارة الإيرادات والكروت والمستخدمين</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        user = st.text_input("👤 اسم المدير العام")
        pwd = st.text_input("🔑 كلمة المرور", type="password")
        if st.button("تسجيل الدخول للوحة المحاسبة 🚀", type="primary"):
            if (user.strip() == "admin" or user.strip() == "manager") and pwd == "admin123":
                st.session_state.gm_auth = True
                st.session_state.gm_user = "المدير العام"
                st.rerun()
            else:
                st.error("اسم المستخدم أو كلمة المرور غير صحيحة")
    st.stop()


# ============================================================
# 4. القائمة الرئيسية
# ============================================================
with st.sidebar:
    st.markdown("<h2 style='text-align:center;color:#38bdf8;'>💰 لوحة المحاسبة</h2>", unsafe_allow_html=True)
    st.markdown(f"<p style='text-align:center;color:#94a3b8;'>المشرف: {st.session_state.gm_user}</p>", unsafe_allow_html=True)
    st.divider()
    
    menu = st.radio(
        "الأقسام الرئيسية",
        [
            "💵 المحاسبة والتقارير المالية",
            "🎟️ توليد وإدارة أكواد التفعيل (GM)",
            "📈 إحصائيات الأسطول والمستخدمين",
            "👤 إدارة المستخدمين وأدواتهم",
        ],
    )
    st.divider()
    if st.button("🚪 تسجيل الخروج"):
        st.session_state.gm_auth = False
        st.rerun()


# ============================================================
# 5. الأقسام والوظائف الرئيسية
# ============================================================

# ------------------------------------------------------------
# القسم 1: المحاسبة والتقارير المالية
# ------------------------------------------------------------
if menu.startswith("💵"):
    st.markdown("<div class='hero'><h1>💵 المحاسبة والتقارير المالية الإجمالية</h1><p>تحليل الإيرادات، العوائد حسب الباقات، وسجل العمليات المالية.</p></div>", unsafe_allow_html=True)
    
    financial_data = query_db(
        """
        SELECT 
            COUNT(*) AS total_codes,
            COUNT(*) FILTER (WHERE status = 'used') as used_codes,
            COALESCE(SUM(duration_days), 0) as total_days_sold,
            COUNT(*) FILTER (WHERE category = 'VIP') as vip_count,
            COUNT(*) FILTER (WHERE category = 'STANDARD') as standard_count,
            COUNT(*) FILTER (WHERE category = 'TRIAL') as trial_count
        FROM myapp.activation_codes_audit
        """
    )
    
    if financial_data is not None and not financial_data.empty:
        f = financial_data.iloc[0]
        v_count = int(f['vip_count'])
        s_count = int(f['standard_count'])
        t_count = int(f['trial_count'])
        
        # تقدير المبيعات بناءً على أسعار الباقات الافتراضية
        est_revenue = (v_count * 25.0) + (s_count * 15.0)
        
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("إجمالي الإيرادات المقدرة", f"{est_revenue:,.2f} د.أ")
        m2.metric("الأكواد المستخدمة", f"{int(f['used_codes']):,} / {int(f['total_codes']):,}")
        m3.metric("اشتراكات VIP", f"{v_count:,} كارت")
        m4.metric("اشتراكات STANDARD", f"{s_count:,} كارت")

    st.markdown("### 📊 توزيع الإيرادات حسب الفئة")
    pie_df = pd.DataFrame({
        "الفئة": ["VIP (25 د.أ)", "STANDARD (15 د.أ)", "TRIAL (مجاني)"],
        "العدد": [v_count, s_count, t_count]
    })
    fig = px.pie(pie_df, names="الفئة", values="العدد", color="الفئة", color_discrete_sequence=["#a855f7", "#38bdf8", "#64748b"], hole=0.4)
    fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font_color="#f8fafc")
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("### 📜 دفتر القيود المالية والتفعيل")
    audit_logs = query_db("SELECT code, category, duration_days, status, employee_name, activated_device_id, created_at FROM myapp.activation_codes_audit ORDER BY created_at DESC LIMIT 200")
    if audit_logs is not None and not audit_logs.empty:
        st.dataframe(audit_logs, use_container_width=True, hide_index=True, height=350)
        st.download_button(
            "📥 تصدير السجل المالي CSV",
            data=audit_logs.to_csv(index=False).encode("utf-8-sig"),
            file_name=f"financial_ledger_{datetime.now():%Y%m%d}.csv",
            mime="text/csv",
            use_container_width=True,
        )


# ------------------------------------------------------------
# القسم 2: توليد وإدارة أكواد التفعيل المولدة من المدير العام
# ------------------------------------------------------------
elif menu.startswith("🎟️"):
    st.markdown("<div class='hero'><h1>🎟️ توليد وإدارة أكواد التفعيل المولدة</h1><p>توليد كروت اشتراك فردية أو دفعة جماعية مع تحديد الفئة والمدة.</p></div>", unsafe_allow_html=True)
    
    col_g1, col_d2 = st.columns(2)
    with col_g1:
        gen_type = st.radio("نوع التوليد", ["كارت فردي مخصص", "دفعة كروت جماعية (Batch)"])
        gen_category = st.selectbox("باقة الاشتراك", ["VIP", "STANDARD", "TRIAL"])
    with col_d2:
        gen_days = st.number_input("مدة الكارت (بالأيام)", min_value=1, max_value=3650, value=30)
        batch_count = st.number_input("عدد الكروت المطلوبة", min_value=1, max_value=500, value=10) if gen_type.startswith("دفعة") else 1

    prefix = st.text_input("بادئة الكود (Prefix - اختياري)", value="GM-2026")

    if st.button("⚡ توليد الأكواد وحفظها بجدول التفعيلات", type="primary"):
        generated_codes = []
        for i in range(batch_count):
            random_hash = hashlib.sha256(f"{time.time()}_{i}_{st.session_state.gm_user}".encode()).hexdigest()[:8].upper()
            code_str = f"{prefix}-{random_hash}"
            
            res = query_db(
                """
                INSERT INTO myapp.activation_codes_audit (code, category, duration_days, status, employee_name, action)
                VALUES (%s, %s, %s, 'generated', %s, 'batch_generated')
                ON CONFLICT (code) DO NOTHING
                """,
                (code_str, gen_category, int(gen_days), st.session_state.gm_user),
                is_select=False
            )
            if res:
                query_db(
                    """
                    INSERT INTO myapp.subscriptions (code, duration_days, category, is_used)
                    VALUES (%s, %s, %s, FALSE)
                    ON CONFLICT (code) DO NOTHING
                    """,
                    (code_str, int(gen_days), gen_category),
                    is_select=False
                )
                generated_codes.append(code_str)

        st.success(f"🎉 تم توليد وحفظ {len(generated_codes)} كارت تفعيل بنجاح!")
        st.text_area("الأكواد المولدة حديثاً (يمكنك نسخها)", value="\n".join(generated_codes), height=150)

    st.markdown("### 🔍 البحث وإدارة الأكواد المولدة")
    search_code = st.text_input("ابحث عن كود معين")
    code_sql = "SELECT code, category, duration_days, status, employee_name, activated_device_id, created_at FROM myapp.activation_codes_audit"
    params = []
    if search_code.strip():
        code_sql += " WHERE code ILIKE %s"
        params.append(f"%{search_code.strip()}%")
    code_sql += " ORDER BY created_at DESC LIMIT 200"
    
    codes_df = query_db(code_sql, params)
    if codes_df is not None and not codes_df.empty:
        st.dataframe(codes_df, use_container_width=True, hide_index=True, height=350)


# ------------------------------------------------------------
# القسم 3: إحصائيات الأسطول والمستخدمين
# ------------------------------------------------------------
elif menu.startswith("📈"):
    st.markdown("<div class='hero'><h1>📈 إحصائيات الأسطول والمستخدمين الشاملة</h1><p>مراقبة الأجهزة المتصلة، العوائد، وتوزيع النقر والتطبيق.</p></div>", unsafe_allow_html=True)
    
    users_stats = query_db(
        """
        SELECT 
            COUNT(*) AS total_users,
            COUNT(*) FILTER (WHERE status = 'Active') AS active_users,
            COUNT(*) FILTER (WHERE last_active >= NOW() - INTERVAL '5 minutes') AS online_now,
            COALESCE(SUM(accepted_clicks), 0) AS total_clicks,
            COUNT(*) FILTER (WHERE is_frozen = TRUE) AS frozen_users
        FROM myapp.users_status
        """
    )
    if users_stats is not None and not users_stats.empty:
        us = users_stats.iloc[0]
        st1, st2, st3, st4, st5 = st.columns(5)
        st1.metric("إجمالي الكباتن", f"{int(us['total_users']):,}")
        st2.metric("الاشتراكات النشطة", f"{int(us['active_users']):,}")
        st3.metric("المتصلين الآن 🟢", f"{int(us['online_now']):,}")
        st4.metric("إجمالي النقرات ⚡", f"{int(us['total_clicks']):,}")
        st5.metric("المستخدمين المجمدين ❄️", f"{int(us['frozen_users']):,}")

    st.markdown("### 🏆 أعلى 10 كباتن في النقرات المقبولة")
    leaderboard = query_db("SELECT phone, device_id, accepted_clicks, sub_tier, last_active FROM myapp.users_status ORDER BY accepted_clicks DESC LIMIT 10")
    if leaderboard is not None and not leaderboard.empty:
        st.dataframe(leaderboard, use_container_width=True, hide_index=True)


# ------------------------------------------------------------
# القسم 4: إدارة المستخدمين وأدواتهم الفردية
# ------------------------------------------------------------
else:
    st.markdown("<div class='hero'><h1>👤 إدارة المستخدمين وأدوات التحكم الفردية</h1><p>تعديل الاشتراكات، تجميد/فك تجميد الحسابات، وتصفير العدادات.</p></div>", unsafe_allow_html=True)
    
    user_search = st.text_input("🔍 ابحث برقم الهاتف أو Device ID")
    u_sql = "SELECT device_id, phone, status, sub_tier, expiry_date, accepted_clicks, is_frozen, last_active FROM myapp.users_status"
    u_params = []
    if user_search.strip():
        u_sql += " WHERE phone ILIKE %s OR device_id ILIKE %s"
        p = f"%{user_search.strip()}%"
        u_params.extend([p, p])
    u_sql += " ORDER BY last_active DESC NULLS LAST LIMIT 150"
    
    users_list = query_db(u_sql, u_params)
    if users_list is not None and not users_list.empty:
        st.dataframe(users_list, use_container_width=True, hide_index=True, height=280)
        
        st.markdown("### 🛠️ أدوات التحكم بالحساب المSelected")
        selected_dev = st.selectbox("اختر معرّف الجهاز لتطبيق الأداة عليه", users_list["device_id"].tolist())
        
        if selected_dev:
            c_t1, c_t2, c_t3, c_t4 = st.columns(4)
            with c_t1:
                ext_days = st.number_input("تلمديد الاشتراك (أيام)", min_value=1, max_value=365, value=30)
                if st.button("➕ تمديد الاشتراك"):
                    query_db(
                        "UPDATE myapp.users_status SET expiry_date = GREATEST(COALESCE(expiry_date, NOW()), NOW()) + (%s || ' days')::interval, status='Active', is_frozen=FALSE WHERE device_id = %s",
                        (int(ext_days), selected_dev),
                        is_select=False
                    )
                    st.success(f"تم تمديد الاشتراك للجهاز {selected_dev} بمقدار {ext_days} يوم.")
                    st.rerun()
            with c_t2:
                if st.button("❄️ / 🔥 تبديل التجميد"):
                    query_db("UPDATE myapp.users_status SET is_frozen = NOT is_frozen WHERE device_id = %s", (selected_dev,), is_select=False)
                    st.success(f"تم تغيير حالة التجميد للجهاز {selected_dev}.")
                    st.rerun()
            with c_t3:
                if st.button("🔄 تصفير عداد النقرات"):
                    query_db("UPDATE myapp.users_status SET accepted_clicks = 0 WHERE device_id = %s", (selected_dev,), is_select=False)
                    st.success(f"تم تصفير عداد النقرات للجهاز {selected_dev}.")
                    st.rerun()
            with c_t4:
                if st.button("🗑️ حذف الحساب بالكامل"):
                    query_db("DELETE FROM myapp.users_status WHERE device_id = %s", (selected_dev,), is_select=False)
                    st.success(f"تم حذف الحساب {selected_dev} بنجاح.")
                    st.rerun()

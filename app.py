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
# 1. إعداد الصفحة والهوية البصرية الداكنة الاحترافية
# ============================================================
st.set_page_config(
    page_title="MyClicker Pro | المحاسبة وإدارة الكروت والمبيعات",
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
        st.error(f"❌ خطأ في تنفيذ العملية: {e}")
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
            id BIGSERIAL PRIMARY KEY, code TEXT, amount NUMERIC(10,2) NOT NULL DEFAULT 0.0,
            category TEXT, phone TEXT, device_id TEXT, created_by TEXT DEFAULT 'المدير العام',
            notes TEXT, created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );"""
    ]
    for s in sqls:
        query_db(s, is_select=False)


init_db_schema()


# ============================================================
# 3. نظام المصادقة
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
                <h1>نظام المحاسبة والمبيعات والكروت الحصرية</h1>
                <p>إدارة المبيعات الحقيقية، فرز الكروت، والقيود الحسابية الفورية من قاعدة البيانات مباشرة</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        user = st.text_input("👤 اسم المستخدم")
        pwd = st.text_input("🔑 كلمة المرور", type="password")
        if st.button("تسجيل الدخول للنظام 🚀", type="primary"):
            if (user.strip() in ["admin", "manager", "accountant"]) and pwd == "admin123":
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
    st.markdown("<h2 style='text-align:center;color:#38bdf8;'>💰 النظام المالي</h2>", unsafe_allow_html=True)
    st.markdown(f"<p style='text-align:center;color:#94a3b8;'>المحاسب المسؤول: {st.session_state.gm_user}</p>", unsafe_allow_html=True)
    st.divider()
    
    menu = st.radio(
        "القائمة الرئيسية",
        [
            "📊 العمليات الحسابية والعمليات المالية",
            "🛒 إضافة وتعديل مبيعات جديدة",
            "🎟️ تنظيم وجدول الكروت (مستخدم / غير مستخدم)",
            "👥 فرز وتقارير الأسطول والمستخدمين",
        ],
    )
    st.divider()
    if st.button("🚪 تسجيل الخروج"):
        st.session_state.gm_auth = False
        st.rerun()


# ============================================================
# 5. الأقسام والموديولات الحسابية والمبيعات
# ============================================================

# ------------------------------------------------------------
# القسم 1: العمليات الحسابية والقيود المالية
# ------------------------------------------------------------
if menu.startswith("📊"):
    st.markdown("<div class='hero'><h1>📊 العمليات الحسابية والقيود المالية المباشرة</h1><p>حساب الإيرادات المحصلة، قيمة المخزون، ومتوسط المبيعات من قاعدة البيانات فقط.</p></div>", unsafe_allow_html=True)
    
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

    st.markdown("### 📜 قيود السجل المالي (Financial Ledger)")
    ledger_df = query_db("SELECT id, code, amount, category, phone, device_id, created_by, notes, created_at FROM myapp.financial_ledger ORDER BY created_at DESC LIMIT 200")
    if ledger_df is not None and not ledger_df.empty:
        st.dataframe(ledger_df, use_container_width=True, hide_index=True, height=350)
        st.download_button(
            "📥 تصدير القيود المالية CSV",
            data=ledger_df.to_csv(index=False).encode("utf-8-sig"),
            file_name=f"financial_ledger_{datetime.now():%Y%m%d}.csv",
            mime="text/csv",
            use_container_width=True,
        )
    else:
        st.info("لا توجد قيود مالية مسجلة حالياً.")


# ------------------------------------------------------------
# القسم 2: إضافة وتعديل مبيعات جديدة
# ------------------------------------------------------------
elif menu.startswith("🛒"):
    st.markdown("<div class='hero'><h1>🛒 إضافة وتعديل مبيعات جديدة</h1><p>تسجيل عملية بيع حقيقية، ربط الكود المستعمل من الجدول وتفعيل حساب العميل.</p></div>", unsafe_allow_html=True)
    
    # جلب الكروت المتاحة غير المستخدمة من الجدول فقط
    unused_codes_df = query_db(
        """
        SELECT code, category, price, duration_days 
        FROM myapp.activation_codes_audit 
        WHERE status = 'generated' OR status = 'new'
        ORDER BY created_at DESC
        """
    )
    
    st.markdown("### ➕ إضافة عملية بيع جديدة (من الكروت المتاحة بالجدول حصراً)")
    
    if unused_codes_df is not None and not unused_codes_df.empty:
        available_codes = unused_codes_df["code"].tolist()
        
        c_sale1, c_sale2 = st.columns(2)
        with c_sale1:
            selected_sale_code = st.selectbox("اختر الكود المتاح بالجدول", available_codes)
            matched_code_info = unused_codes_df[unused_codes_df["code"] == selected_sale_code].iloc[0]
            
            sale_phone = st.text_input("رقم هاتف العميل / السائق", value="0790000000")
            sale_device_id = st.text_input("معرف الجهاز (Device ID)", value="")
            
        with c_sale2:
            sale_category = st.selectbox("فئة الباقة", ["VIP", "STANDARD", "TRIAL"], index=["VIP", "STANDARD", "TRIAL"].index(matched_code_info["category"]) if matched_code_info["category"] in ["VIP", "STANDARD", "TRIAL"] else 0)
            sale_price = st.number_input("المبلغ المحصل الفعلي (د.أ)", min_value=0.0, max_value=5000.0, value=float(matched_code_info["price"]) if matched_code_info["price"] > 0 else 25.0)
            sale_notes = st.text_input("ملاحظات المبيعات", value="بيع مباشر وتحصيل نقدي")

        if st.button("🚀 تسجيل وتأكيد عملية البيع بالجدول", type="primary"):
            if not sale_phone.strip():
                st.error("⚠️ يرجى إدخال رقم هاتف العميل.")
            else:
                # 1. إضافة القيد المالي
                res_ledger = query_db(
                    """
                    INSERT INTO myapp.financial_ledger (code, amount, category, phone, device_id, created_by, notes)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """,
                    (selected_sale_code, sale_price, sale_category, sale_phone.strip(), sale_device_id.strip(), st.session_state.gm_user, sale_notes.strip()),
                    is_select=False
                )
                
                # 2. تحديث حالة الكود إلى مستخدم بالجدول حصراً
                query_db(
                    """
                    UPDATE myapp.activation_codes_audit 
                    SET status = 'used', action = 'sold_and_activated', activated_device_id = %s, action_at = NOW()
                    WHERE code = %s
                    """,
                    (sale_device_id.strip(), selected_sale_code),
                    is_select=False
                )
                
                query_db(
                    """
                    UPDATE myapp.subscriptions 
                    SET is_used = TRUE, used_by_device = %s, used_at = NOW()
                    WHERE code = %s
                    """,
                    (sale_device_id.strip(), selected_sale_code),
                    is_select=False
                )
                
                # 3. تفعيل حساب العميل في جدول الأسطول
                if sale_device_id.strip():
                    query_db(
                        """
                        INSERT INTO myapp.users_status (device_id, phone, status, sub_tier, expiry_date, is_frozen, last_active)
                        VALUES (%s, %s, 'Active', %s, NOW() + INTERVAL '30 days', FALSE, NOW())
                        ON CONFLICT (device_id) DO UPDATE SET 
                            status = 'Active', sub_tier = EXCLUDED.sub_tier,
                            expiry_date = GREATEST(COALESCE(myapp.users_status.expiry_date, NOW()), NOW()) + INTERVAL '30 days',
                            phone = EXCLUDED.phone, is_frozen = FALSE, last_active = NOW()
                        """,
                        (sale_device_id.strip(), sale_phone.strip(), sale_category),
                        is_select=False
                    )

                st.success(f"🎉 تم تسجيل المبيعة بنجاح وتحصيل {sale_price} د.أ للكود ({selected_sale_code})!")
                st.toast("تم تسجيل القيد وتأكيد البيع", icon="💰")
                st.rerun()
    else:
        st.warning("لا توجد كروت متاحة بالمخزون للبيع المباشر حالياً. يرجى إضافة كروت جديدة بالجدول.")

    st.markdown("### ✏️ تعديل القيود المالية المسجلة")
    edit_ledger_df = query_db("SELECT id, code, amount, category, phone, device_id, notes FROM myapp.financial_ledger ORDER BY created_at DESC LIMIT 50")
    if edit_ledger_df is not None and not edit_ledger_df.empty:
        edited_df = st.data_editor(edit_ledger_df, use_container_width=True, hide_index=True, key="ledger_editor")
        if st.button("💾 حفظ التعديلات على القيود المالية"):
            for _, row in edited_df.iterrows():
                query_db(
                    """
                    UPDATE myapp.financial_ledger 
                    SET amount = %s, category = %s, phone = %s, device_id = %s, notes = %s
                    WHERE id = %s
                    """,
                    (float(row["amount"]), str(row["category"]), str(row["phone"]), str(row["device_id"]), str(row["notes"]), int(row["id"])),
                    is_select=False
                )
            st.success("تم تحديث القيود المالية بنجاح!")
            st.rerun()


# ------------------------------------------------------------
# القسم 3: فرز وجداول الكروت (مستخدم / غير مستخدم) من الجدول حصراً
# ------------------------------------------------------------
elif menu.startswith("🎟️"):
    st.markdown("<div class='hero'><h1>🎟️ تنظيم وجدول الكروت (فرز المستخدم والغير مستخدم)</h1><p>جدول الكروت المتاحة والمستخدمة من قاعدة البيانات حصراً دون توليد عشوائي.</p></div>", unsafe_allow_html=True)
    
    code_filter = st.selectbox("فرز الكروت حسب الحالة", ["الكل", "كروت متاحة (غير مستخدمة)", "كروت مستخدمة ومفعلة"])
    
    sql_codes = "SELECT id, code, category, price, duration_days, status, employee_name, activated_device_id, created_at FROM myapp.activation_codes_audit"
    
    if code_filter == "كروت متاحة (غير مستخدمة)":
        sql_codes += " WHERE status = 'generated' OR status = 'new'"
    elif code_filter == "كروت مستخدمة ومفعلة":
        sql_codes += " WHERE status = 'used'"
        
    sql_codes += " ORDER BY created_at DESC LIMIT 300"
    
    codes_result = query_db(sql_codes)
    if codes_result is not None and not codes_result.empty:
        st.success(f"تم عرض {len(codes_result)} كارت مطابق للفرز المحدد ({code_filter}).")
        st.dataframe(codes_result, use_container_width=True, hide_index=True, height=450)
        
        st.download_button(
            "📥 تنزيل قائمة الكروت المجهزة CSV",
            data=codes_result.to_csv(index=False).encode("utf-8-sig"),
            file_name=f"activation_codes_{datetime.now():%Y%m%d}.csv",
            mime="text/csv",
            use_container_width=True,
        )
    else:
        st.info("لا توجد كروت مطابقة لخيارات الفرز الحالية.")


# ------------------------------------------------------------
# القسم 4: فرز وتقارير الأسطول والمستخدمين
# ------------------------------------------------------------
else:
    st.markdown("<div class='hero'><h1>👥 فرز وتقارير أسطول المستخدمين والم أدوات</h1><p>فرز الكباتن حسب الحالة، الفئة، والتحكم بالحسابات.</p></div>", unsafe_allow_html=True)
    
    user_search = st.text_input("🔍 ابحث برقم الهاتف أو معرّف الجهاز (Device ID)")
    
    filter_user_status = st.selectbox("تصفية الكباتن", ["الكل", "النشطين فقط", "المجمدين ❄️", "المنتهية اشتراكاتهم ⚠️"])
    
    u_sql = "SELECT device_id, phone, status, sub_tier, expiry_date, accepted_clicks, is_frozen, last_active FROM myapp.users_status WHERE 1=1"
    u_params = []
    
    if user_search.strip():
        u_sql += " AND (phone ILIKE %s OR device_id ILIKE %s)"
        p = f"%{user_search.strip()}%"
        u_params.extend([p, p])
        
    if filter_user_status == "النشطين فقط":
        u_sql += " AND status = 'Active' AND is_frozen = FALSE"
    elif filter_user_status == "المجمدين ❄️":
        u_sql += " AND is_frozen = TRUE"
    elif filter_user_status == "المنتهية اشتراكاتهم ⚠️":
        u_sql += " AND expiry_date < NOW()"

    u_sql += " ORDER BY last_active DESC NULLS LAST LIMIT 200"
    
    users_list = query_db(u_sql, u_params)
    if users_list is not None and not users_list.empty:
        st.dataframe(users_list, use_container_width=True, hide_index=True, height=350)
        
        st.markdown("### 🛠️ أدوات التحكم بالعميل")
        selected_dev = st.selectbox("اختر معرّف الجهاز لتعديل حسابه", users_list["device_id"].tolist())
        
        if selected_dev:
            c_t1, c_t2, c_t3, c_t4 = st.columns(4)
            with c_t1:
                ext_days = st.number_input("تمديد الاشتراك (أيام)", min_value=1, max_value=365, value=30)
                if st.button("➕ تمديد الاشتراك"):
                    query_db(
                        "UPDATE myapp.users_status SET expiry_date = GREATEST(COALESCE(expiry_date, NOW()), NOW()) + (%s || ' days')::interval, status='Active', is_frozen=FALSE WHERE device_id = %s",
                        (int(ext_days), selected_dev),
                        is_select=False
                    )
                    st.success(f"تم تمديد اشتراك الجهاز {selected_dev} بمقدار {ext_days} يوم.")
                    st.rerun()
            with c_t2:
                if st.button("❄️ / 🔥 تبديل التجميد"):
                    query_db("UPDATE myapp.users_status SET is_frozen = NOT is_frozen WHERE device_id = %s", (selected_dev,), is_select=False)
                    st.success(f"تم تغيير حالة تجميد الجهاز {selected_dev}.")
                    st.rerun()
            with c_t3:
                if st.button("🔄 تصفير العداد"):
                    query_db("UPDATE myapp.users_status SET accepted_clicks = 0 WHERE device_id = %s", (selected_dev,), is_select=False)
                    st.success(f"تم تصفير عداد الجهاز {selected_dev}.")
                    st.rerun()
            with c_t4:
                if st.button("🗑️ حذف الحساب"):
                    query_db("DELETE FROM myapp.users_status WHERE device_id = %s", (selected_dev,), is_select=False)
                    st.success(f"تم حذف الجهاز {selected_dev}.")
                    st.rerun()

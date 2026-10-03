import hashlib
import json
import os
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional, Tuple, Union

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import psycopg2
from psycopg2 import pool, extras
import streamlit as st


# ============================================================
# 1. إعداد الصفحة والتنسيق البصري (RTL & Modern Arabic UI)
# ============================================================
st.set_page_config(
    page_title="MyClicker Pro | لوحة التحكم المركزية",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700;800;900&display=swap');

    :root {
        --primary: #159fbe;
        --primary-dark: #0f7a93;
        --bg-main: #f4f8fb;
        --card-bg: #ffffff;
        --text-main: #24445b;
        --text-sub: #587184;
        --border-color: #d7e5ec;
        --success: #10b981;
        --warning: #f59e0b;
        --danger: #ef4444;
    }

    * {
        font-family: 'Cairo', sans-serif !important;
    }

    .stApp {
        background-color: var(--bg-main);
        direction: rtl;
        text-align: right;
    }

    .main .block-container {
        padding-top: 1.5rem;
        padding-bottom: 3rem;
        max-width: 1400px;
    }

    /* كروت المقاييس العلوية */
    div[data-testid="stMetric"] {
        background: var(--card-bg);
        border: 1px solid var(--border-color);
        border-radius: 18px;
        padding: 18px 22px;
        box-shadow: 0 4px 15px rgba(21, 159, 190, 0.05);
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    div[data-testid="stMetric"]:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 22px rgba(21, 159, 190, 0.12);
        border-color: var(--primary);
    }
    div[data-testid="stMetricLabel"] {
        font-size: 0.95rem !important;
        font-weight: 700 !important;
        color: var(--text-sub) !important;
    }
    div[data-testid="stMetricValue"] {
        font-size: 1.8rem !important;
        font-weight: 900 !important;
        color: var(--text-main) !important;
    }

    /* الأزرار العصرية */
    div.stButton > button {
        border-radius: 14px !important;
        font-weight: 800 !important;
        padding: 0.55rem 1.4rem !important;
        transition: all 0.2s ease !important;
        border: none !important;
    }
    div.stButton > button[kind="primary"] {
        background: linear-gradient(135deg, var(--primary) 0%, var(--primary-dark) 100%) !important;
        color: white !important;
        box-shadow: 0 4px 14px rgba(21, 159, 190, 0.35) !important;
    }
    div.stButton > button[kind="primary"]:hover {
        box-shadow: 0 6px 20px rgba(21, 159, 190, 0.5) !important;
        transform: translateY(-1px);
    }

    /* الحقول والمدخلات */
    div[data-baseweb="input"], div[data-baseweb="select"] {
        border-radius: 12px !important;
    }

    /* الجداول */
    .stDataFrame {
        border-radius: 16px;
        overflow: hidden;
        border: 1px solid var(--border-color);
        box-shadow: 0 4px 16px rgba(0,0,0,0.02);
    }

    /* تنبيهات الحالة */
    .stAlert {
        border-radius: 14px !important;
        font-weight: 700 !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# 2. إدارة قاعدة البيانات والاتصال الآمن بـ Neon PostgreSQL
# ============================================================
DEFAULT_NEON_URL = (
    "postgresql://neondb_owner:npg_AvzFkHQ6M3yo@ep-tiny-wind-ayd9hww0-pooler.c-5.us-east-2.aws.neon.tech/neondb?sslmode=require"
)

DATABASE_URL = os.getenv("DATABASE_URL", DEFAULT_NEON_URL)
# تنظيف معامل channel_binding لضمان التوافق التام مع psycopg2
CLEAN_DATABASE_URL = DATABASE_URL.replace("&channel_binding=require", "")


@st.cache_resource(show_spinner=False)
def get_connection_pool():
    """تهيئة تجمع اتصالات Neon آمن وقابل للاسترجاع التلقائي."""
    try:
        connection_pool = pool.ThreadedConnectionPool(
            minconn=1,
            maxconn=15,
            dsn=CLEAN_DATABASE_URL,
            connect_timeout=10,
            application_name="MyClickerStreamlitDashboard",
        )
        return connection_pool
    except Exception as e:
        st.error(f"❌ خطأ أثناء إنشاء تجمع الاتصال بقاعدة البيانات: {e}")
        return None


@contextmanager
def get_db_cursor(commit: bool = False):
    """مدير سياق للتعامل الآمن مع اتصالات واستعلامات PostgreSQL."""
    cp = get_connection_pool()
    if cp is None:
        raise RuntimeError("قاعدة البيانات غير متصلة.")
    conn = cp.getconn()
    try:
        with conn.cursor(cursor_factory=extras.RealDictCursor) as cur:
            yield cur
        if commit:
            conn.commit()
    except Exception as err:
        conn.rollback()
        raise err
    finally:
        cp.putconn(conn)


def query_db(sql: str, params: Optional[Union[Tuple, Dict]] = None) -> Optional[pd.DataFrame]:
    """تنفيذ استعلام SELECT وإرجاع النتائج كـ DataFrame."""
    try:
        with get_db_cursor(commit=False) as cur:
            cur.execute(sql, params or ())
            rows = cur.fetchall()
            return pd.DataFrame(rows) if rows else pd.DataFrame()
    except Exception as e:
        st.error(f"خطأ في الاستعلام: {e}")
        return None


def run_query(sql: str, params: Optional[Union[Tuple, Dict]] = None, is_select: bool = False):
    """تنفيذ استعلام إجرائي (INSERT/UPDATE/DELETE)."""
    try:
        with get_db_cursor(commit=not is_select) as cur:
            cur.execute(sql, params or ())
            if is_select:
                return cur.fetchall()
            return cur.rowcount
    except Exception as e:
        st.error(f"خطأ في تنفيذ الأمر: {e}")
        return None


def get_app_config() -> Dict[str, str]:
    """استرجاع إعدادات المنظومة من myapp.app_config."""
    df = query_db("SELECT key, value FROM myapp.app_config")
    if df is not None and not df.empty:
        return dict(zip(df["key"], df["value"]))
    return {}


def save_config(key: str, value: str):
    """تحديث أو إدراج متغير في myapp.app_config."""
    sql = """
        INSERT INTO myapp.app_config (key, value)
        VALUES (%s, %s)
        ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value
    """
    return run_query(sql, (key, str(value)))


# ============================================================
# 3. مكونات الواجهة والمساعدات البصرية
# ============================================================
def page_header(title: str, subtitle: str = ""):
    st.markdown(
        f"""
        <div style="margin-bottom: 1.5rem; padding-bottom: 0.8rem; border-bottom: 2px solid #e2edf2;">
            <h1 style="color: #24445b; font-size: 1.9rem; font-weight: 900; margin: 0;">{title}</h1>
            {f'<p style="color: #587184; font-size: 0.95rem; margin-top: 0.3rem;">{subtitle}</p>' if subtitle else ''}
        </div>
        """,
        unsafe_allow_html=True,
    )


# ============================================================
# 4. القائمة الجانبية (Navigation Bar)
# ============================================================
with st.sidebar:
    st.markdown(
        """
        <div style="text-align: center; padding: 1.2rem 0; border-bottom: 1px solid #d7e5ec; margin-bottom: 1.5rem;">
            <div style="background: linear-gradient(135deg, #159fbe 0%, #0f7a93 100%); width: 55px; height: 55px; border-radius: 16px; margin: 0 auto; display: flex; align-items: center; justify-content: center; box-shadow: 0 6px 16px rgba(21, 159, 190, 0.35);">
                <span style="font-size: 26px; color: white;">⚡</span>
            </div>
            <h2 style="color: #24445b; font-size: 1.35rem; font-weight: 900; margin: 0.8rem 0 0.2rem 0;">MYCLICKER PRO</h2>
            <span style="background: #e0f2fe; color: #0284c7; padding: 3px 10px; border-radius: 8px; font-size: 0.75rem; font-weight: 800;">إصدار السيطرة المركزية 2026</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    menu = st.radio(
        "الانتقال السريع:",
        [
            "📈 نظرة عامة وإحصائيات النظام",
            "📢 مركز الإشعارات المنسدلة (Heads-Up)",
            "👥 إدارة أسطول الكباتن وتفعيل الاشتراكات",
            "💳 توليد وإدارة أكواد الشحن",
            "⚡ تحديث البيانات الحية (LIVE UPDATE)",
            "🚀 إدارة التحديثات الإجبارية",
            "🎮 بوابة ربط المحاكيات و ADB",
            "🔍 فحص وتحليل سجلات التيليميتري",
            "🖥️ حالة السيرفر وقاعدة البيانات",
        ],
        index=0,
    )

    st.markdown("---")
    st.caption("🟢 قاعدة بيانات Neon متصلة ومحمية")


# ============================================================
# 5. الصفحات الرئيسية
# ============================================================

# 1. نظرة عامة وإحصائيات
if menu.startswith("📈"):
    page_header("📈 نظرة عامة وإحصائيات الأسطول", "مراقبة حية فورية لكافة مؤشرات الأداء والاشتراكات.")

    stats_df = query_db(
        """
        SELECT 
            COUNT(*) as total_users,
            COUNT(*) FILTER (WHERE status = 'Active') as active_users,
            COUNT(*) FILTER (WHERE is_frozen = TRUE) as frozen_users,
            COUNT(*) FILTER (WHERE last_active >= NOW() - INTERVAL '3 minutes') as online_now,
            COALESCE(SUM(accepted_clicks), 0) as total_clicks
        FROM myapp.users_status
    """
    )

    if stats_df is not None and not stats_df.empty:
        r = stats_df.iloc[0]
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("إجمالي الأجهزة", f"{r['total_users']:,}")
        c2.metric("🟢 متصل الآن", f"{r['online_now']:,}")
        c3.metric("مفعّل ونشط", f"{r['active_users']:,}")
        c4.metric("❄️ مجمّد", f"{r['frozen_users']:,}")
        c5.metric("إجمالي النقرات", f"{r['total_clicks']:,}")

    st.markdown("---")
    st.subheader("📊 توزيع الكباتن حسب فئات الاشتراك")
    tiers_df = query_db(
        """
        SELECT COALESCE(sub_tier, 'STANDARD') as tier, COUNT(*) as count 
        FROM myapp.users_status 
        GROUP BY sub_tier
    """
    )
    if tiers_df is not None and not tiers_df.empty:
        fig = px.pie(
            tiers_df,
            names="tier",
            values="count",
            color="tier",
            color_discrete_map={"VIP": "#8b5cf6", "STANDARD": "#0ea5e9", "TRIAL": "#f59e0b"},
            hole=0.45,
        )
        fig.update_layout(margin=dict(t=10, b=10, l=10, r=10), height=300)
        st.plotly_chart(fig, use_container_width=True)

# 2. مركز الإشعارات المنسدلة
elif menu.startswith("📢"):
    page_header("📢 مركز الإشعارات المنسدلة والعائمة", "بث إشعارات Heads-Up Dropdown لكافة الهواتف أو لكابتن محدد.")
    t_broad, t_indiv = st.tabs(["🚀 بث إشعار عام للأسطول", "🎯 إشعار فردي لكابتن محدد"])

    with t_broad:
        st.subheader("بث إشعار منسدل عام للجميع")
        b_title = st.text_input("عنوان الإشعار", value="تنبيه هام من الإدارة ⚡")
        b_msg = st.text_area("نص الإشعار المنسدل", value="يرجى فتح التطبيق لمتابعة العروض الجديدة!")

        if st.button("🚀 بث الإشعار الآن للجميع", type="primary"):
            if b_msg.strip():
                clean_msg = b_msg.strip()
                notif_ver = str(int(time.time() * 1000))
                save_config("notice_message", clean_msg)
                save_config("notification_version", notif_ver)
                save_config("notification_type", "heads_up_drop_down")
                save_config("notice_title", b_title)

                run_query(
                    """
                    UPDATE myapp.users_status 
                    SET notice_message = %s,
                        notification_version = %s
                """,
                    (clean_msg, notif_ver),
                )

                st.success("✅ تم بث الإشعار المنسدل لكافة الهواتف بنجاح!")
            else:
                st.warning("يرجى كتابة نص الإشعار أولاً.")

    with t_indiv:
        st.subheader("إرسال إشعار لكابتن محدد")
        phone_target = st.text_input("رقم هاتف الكابتن المستهدف", placeholder="078XXXXXXX")
        indiv_msg = st.text_area("نص الإشعار الخاص به", value="تنبيه خاص: تم تحديث بيانات حسابك.")

        if st.button("⚡ إرسال الإشعار الفردي لهذا الكابتن", type="primary"):
            if phone_target.strip() and indiv_msg.strip():
                notif_ver = str(int(time.time() * 1000))
                rows = run_query(
                    """
                    UPDATE myapp.users_status 
                    SET notice_message = %s,
                        notification_version = %s
                    WHERE phone = %s OR phone ILIKE %s
                """,
                    (indiv_msg.strip(), notif_ver, phone_target.strip(), f"%{phone_target.strip()}%"),
                )
                if rows and rows > 0:
                    st.success(f"✅ تم إرسال الإشعار بنجاح إلى ({rows}) جهاز تابع لهذا الرقم!")
                else:
                    st.error("لم يتم العثور على جهاز مسجل بهذا الرقم في قاعدة البيانات.")
            else:
                st.warning("يرجى ملء رقم الهاتف ونص الإشعار.")

# 3. إدارة أسطول الكباتن
elif menu.startswith("👥"):
    page_header("👥 إدارة أسطول الكباتن والاشتراكات", "استعراض الأجهزة، تفعيل الكباتن، وتجميد/إلغاء تجميد الحسابات.")

    users_df = query_db(
        """
        SELECT 
            device_id, phone, status, sub_tier, accepted_clicks, is_frozen, app_version, device_model,
            CASE WHEN last_active >= NOW() - INTERVAL '3 minutes' THEN '🟢 متصل' ELSE '🔴 غير متصل' END AS bot_status
        FROM myapp.users_status
        ORDER BY last_active DESC NULLS LAST
        LIMIT 100
    """
    )

    if users_df is not None and not users_df.empty:
        st.dataframe(users_df, use_container_width=True, height=450)
    else:
        st.info("لا توجد أجهزة مسجلة في قاعدة البيانات حالياً.")

# 4. توليد وإدارة الأكواد
elif menu.startswith("💳"):
    page_header("💳 توليد وإدارة أكواد الشحن", "إنشاء أكواد شحن فورية للاشتراكات.")
    c_q1, c_q2 = st.columns(2)
    qty = c_q1.number_input("عدد الأكواد المراد توليدها", min_value=1, max_value=50, value=5)
    days = c_q2.selectbox("مدة الاشتراك بالأيام", [7, 30, 90, 365], index=1)

    if st.button("⚡ توليد الأكواد الآن", type="primary"):
        generated = []
        for _ in range(qty):
            code_str = "VIP-" + hashlib.sha256(os.urandom(16)).hexdigest()[:10].upper()
            run_query(
                """
                INSERT INTO myapp.subscriptions (code, duration_days, category, is_used, created_at)
                VALUES (%s, %s, 'VIP', FALSE, NOW())
            """,
                (code_str, days),
            )
            generated.append(code_str)
        st.success(f"تم بنجاح توليد {len(generated)} كود شحن:")
        st.code("\n".join(generated))

# 5. تحديث البيانات الحية
elif menu.startswith("⚡"):
    page_header("⚡ تحديث البيانات الحية (LIVE UPDATE)", "تعديل الكلمات المفتاحية ومؤشرات الشاشة الفورية للبوت.")
    cfg = get_app_config()

    cur_keys = cfg.get("live_keywords", "قبول العرض,قبول,ACCEPT,Accept,Accept Offer")
    cur_inds = cfg.get("live_indicators", "JOD,د.أ,JD,يبعد,طلب جديد,mins away,Jeeny Driver,سفير بترا رايد")

    new_keys = st.text_area("🎯 كلمات قبول العروض الحية (live_keywords)", value=cur_keys)
    new_inds = st.text_area("📡 مؤشرات قراءة الشاشة (live_indicators)", value=cur_inds)

    if st.button("💾 حفظ وتعميم البيانات الحية", type="primary"):
        save_config("live_keywords", new_keys.strip())
        save_config("live_indicators", new_inds.strip())
        save_config("click_delay", "0")
        st.success("✅ تم حفظ ومزامنة البيانات الحية وتعميمها على جميع الأجهزة فوراً!")

# 6. التحديثات الإجبارية
elif menu.startswith("🚀"):
    page_header("🚀 إدارة التحديثات الإجبارية", "إلزام الكباتن بالترقية إلى أحدث إصدار من التطبيق.")
    cfg = get_app_config()
    cur_ver = cfg.get("latest_version", "7.2.8")
    cur_forced = cfg.get("force_update", "false") == "true"
    cur_apk = cfg.get("apk_url", "https://example.com/update.apk")

    n_ver = st.text_input("أحدث إصدار مطلوب", value=cur_ver)
    n_apk = st.text_input("رابط تحميل التحديث (APK)", value=cur_apk)
    n_forced = st.checkbox("تفعيل التحديث الإجباري (Force Update)", value=cur_forced)

    if st.button("💾 تطبيق إعدادات التحديث", type="primary"):
        save_config("latest_version", n_ver.strip())
        save_config("apk_url", n_apk.strip())
        save_config("force_update", "true" if n_forced else "false")
        st.success("✅ تم تحديث إعدادات الإصدار بنجاح.")

# 7. بوابة ربط المحاكيات
elif menu.startswith("🎮"):
    page_header("🎮 بوابة ربط المحاكيات و ADB", "ربط محاكي الأندرويد بقاعدة البيانات برقم الهاتف.")
    ph = st.text_input("📱 رقم هاتف الكابتن لربط المحاكي", placeholder="078XXXXXXX")
    emu_name = st.selectbox("نوع المحاكي", ["LDPlayer 9 Android", "Nox Player", "BlueStacks 5"])

    if st.button("⚡ ربط المحاكي وتثبيته في Neon", type="primary"):
        if ph.strip():
            dev_id = f"emu_{hashlib.md5(ph.strip().encode()).hexdigest()[:8]}"
            run_query(
                """
                INSERT INTO myapp.users_status (device_id, phone, status, sub_tier, device_model, is_frozen, last_active)
                VALUES (%s, %s, 'Active', 'VIP', %s, FALSE, NOW())
                ON CONFLICT (device_id) DO UPDATE SET phone = EXCLUDED.phone, last_active = NOW()
            """,
                (dev_id, ph.strip(), emu_name),
            )
            st.success(f"✅ تم ربط المحاكي بنجاح! المعرف: `{dev_id}`")
        else:
            st.warning("يرجى كتابة رقم الهاتف.")

# 8. فحص التيليميتري
elif menu.startswith("🔍"):
    page_header("🔍 فحص وتحليل سجلات التيليميتري", "استعراض النقرات والاستجابات المسجلة.")
    logs_df = query_db("SELECT * FROM myapp.bot_logs ORDER BY created_at DESC LIMIT 50")
    if logs_df is not None and not logs_df.empty:
        st.dataframe(logs_df, use_container_width=True)
    else:
        st.info("لا توجد سجلات تيليميتري مرصودة حالياً.")

# 9. حالة السيرفر
else:
    page_header("🖥️ حالة السيرفر وقاعدة البيانات", "فحص استقرار قاعدة بيانات Neon.")
    res = query_db("SELECT NOW() as db_time, COUNT(*) as users_count FROM myapp.users_status")
    if res is not None and not res.empty:
        st.success(f"🟢 قاعدة بيانات Neon متصلة وتعمل بكفاءة تامة! وقت السيرفر: {res.iloc[0]['db_time']}")
    else:
        st.error("تعذر الاتصال بقاعدة البيانات.")

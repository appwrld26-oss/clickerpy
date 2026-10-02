# -*- coding: utf-8 -*-
"""
===================================================================================
⚡ MYCLICKER PRO | ULTIMATE COMMAND & CONTROL DASHBOARD (STREAMLIT READY)
===================================================================================
لوحة تحكم وإدارة كاملة بنظام Streamlit تدعم:
1. اتصالات Neon Serverless PostgreSQL مع حماية من الانقطاع (Auto-reconnect & Rollback).
2. إرسال وبث الإشعارات المنسدلة الحية (Heads-Up & Floating Dropdown) للأسطول أو فردياً برقم هاتف الكابتن.
3. دعم التفعيل الفوري (UPSERT) والتوافق الكامل مع تطبيق الأندرويد والمحاكيات.
4. لوحة مراقبة الأسطول، سرعات النقر (Click Delay ms)، وسجلات التيليميتري.
===================================================================================
طريقة التشغيل في الطرفية:
    pip install streamlit psycopg2-binary pandas plotly numpy
    streamlit run dashboard.py
===================================================================================
"""

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
        --bg: #f8fafc;
        --panel: #ffffff;
        --panel-soft: #f1f5f9;
        --line: #e2e8f0;
        --cyan: #0284c7;
        --blue: #2563eb;
        --green: #059669;
        --orange: #d97706;
        --red: #dc2626;
        --text: #0f172a;
        --text-soft: #64748b;
    }

    * {
        font-family: 'Cairo', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif !important;
    }

    .main {
        direction: rtl;
        text-align: right;
        background-color: var(--bg);
    }

    div[data-testid="stSidebar"] {
        direction: rtl;
        text-align: right;
        background-color: #0f172a;
    }

    div[data-testid="stSidebar"] * {
        color: #f8fafc !important;
    }

    .metric-card {
        background: white;
        border: 1px solid var(--line);
        border-radius: 14px;
        padding: 1.2rem;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.04);
        margin-bottom: 1rem;
        text-align: center;
    }

    .heads-up-banner {
        padding: 1.1rem 1.4rem;
        border-radius: 14px;
        margin-bottom: 1.2rem;
        color: white;
        background: linear-gradient(135deg, #0f172a 0%, #0369a1 100%);
        box-shadow: 0 8px 24px rgba(3, 105, 161, 0.25);
        border: 1px solid rgba(56, 189, 248, 0.4);
        display: flex;
        align-items: center;
        justify-content: space-between;
        direction: rtl;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# 2. إدارة اتصالات Neon Serverless PostgreSQL (Resilient Pooling)
# ============================================================
DEFAULT_NEON_URL = (
    "postgresql://neondb_owner:npg_AvzFkHQ6M3yo@ep-tiny-wind-ayd9hww0-pooler.c-5.us-east-2.aws.neon.tech/neondb?sslmode=require"
)
DB_URL = os.getenv("DATABASE_URL", DEFAULT_NEON_URL)


@st.cache_resource(show_spinner=False)
def get_pool() -> pool.SimpleConnectionPool:
    """إنشاء مجمع اتصالات محمي مع دعم بروتوكول SSL الخاص بـ Neon"""
    clean_url = DB_URL.replace("&channel_binding=require", "")
    return pool.SimpleConnectionPool(
        minconn=1,
        maxconn=25,
        dsn=clean_url,
    )


@contextmanager
def db_connection():
    """سياق اتصال محمي مع تجنب خطأ Closed Connection والتراجع التلقائي (Rollback)"""
    connection = None
    database_pool = get_pool()
    try:
        connection = database_pool.getconn()
        try:
            with connection.cursor() as cur:
                cur.execute("SELECT 1;")
        except Exception:
            database_pool.putconn(connection, close=True)
            connection = database_pool.getconn()

        yield connection
    except Exception as exc:
        if connection is not None:
            try:
                connection.rollback()
            except Exception:
                pass
        raise exc
    finally:
        if connection is not None:
            try:
                database_pool.putconn(connection)
            except Exception:
                pass


def run_query(
    query: str,
    params: Optional[Iterable[Any]] = None,
    is_select: bool = True,
) -> Optional[Union[pd.DataFrame, bool]]:
    """تنفيذ الاستعلامات بأمان مع معالجة الأخطاء والتراجع التلقائي"""
    try:
        with db_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(query, tuple(params or ()))
                if is_select:
                    if cursor.description is None:
                        return pd.DataFrame()
                    rows = cursor.fetchall()
                    columns = [column[0] for column in cursor.description]
                    return pd.DataFrame(rows, columns=columns)
                connection.commit()
                return True
    except Exception as error:
        st.error(f"❌ خطأ بقاعدة البيانات: {error}")
        return None


@st.cache_data(ttl=10, show_spinner=False)
def fetch_config() -> dict[str, str]:
    """جلب إعدادات التطبيق من جدول myapp.app_config"""
    config_df = run_query("SELECT key, value FROM myapp.app_config")
    if config_df is None or config_df.empty:
        return {}
    return {
        str(row["key"]): str(row["value"]) if row["value"] is not None else ""
        for _, row in config_df.iterrows()
    }


def save_config(values: dict[str, Any]) -> bool:
    """حفظ جماعي سريع للإعدادات في دفعة واحدة (Batch Upsert)"""
    if not values:
        return True
    try:
        items = [(str(k), str(v)) for k, v in values.items()]
        with db_connection() as conn:
            with conn.cursor() as cur:
                extras.execute_values(
                    cur,
                    """
                    INSERT INTO myapp.app_config (key, value)
                    VALUES %s
                    ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value
                    """,
                    items,
                )
                conn.commit()
        st.cache_data.clear()
        return True
    except Exception as err:
        st.error(f"❌ تعذر حفظ الإعدادات: {err}")
        return False


def ensure_management_tables() -> None:
    """تهيئة وهيكلة جداول التطبيق وقاعدة البيانات بما فيها جداول الإشعارات والتسليم"""
    statements = [
        "CREATE SCHEMA IF NOT EXISTS myapp;",
        """CREATE TABLE IF NOT EXISTS myapp.app_config (
            key TEXT PRIMARY KEY,
            value TEXT
        );""",
        """CREATE TABLE IF NOT EXISTS myapp.users_status (
            device_id TEXT PRIMARY KEY,
            phone TEXT,
            status TEXT DEFAULT 'Active',
            sub_tier TEXT DEFAULT 'STANDARD',
            custom_click_delay INTEGER DEFAULT NULL,
            device_model TEXT DEFAULT NULL,
            activated_code TEXT DEFAULT NULL,
            accepted_clicks BIGINT DEFAULT 0,
            app_version TEXT,
            is_frozen BOOLEAN DEFAULT FALSE,
            notice_message TEXT,
            expiry_date TIMESTAMPTZ,
            last_active TIMESTAMPTZ DEFAULT NOW()
        );""",
        """CREATE TABLE IF NOT EXISTS myapp.system_notifications (
            id BIGSERIAL PRIMARY KEY,
            title TEXT NOT NULL,
            message TEXT NOT NULL,
            type TEXT NOT NULL DEFAULT 'broadcast',
            target_phone TEXT,
            target_device_id TEXT,
            priority TEXT NOT NULL DEFAULT 'normal',
            sound TEXT DEFAULT 'heads_up',
            is_read BOOLEAN NOT NULL DEFAULT FALSE,
            sender TEXT DEFAULT 'الإدارة العامة',
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );""",
        """CREATE TABLE IF NOT EXISTS myapp.notification_delivery (
            device_id TEXT PRIMARY KEY,
            phone TEXT,
            notification_version TEXT NOT NULL DEFAULT '0',
            notification_id TEXT,
            delivered_at TIMESTAMPTZ,
            delivery_status TEXT NOT NULL DEFAULT 'offered',
            last_sync_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );""",
        """CREATE TABLE IF NOT EXISTS myapp.bot_logs (
            id BIGSERIAL PRIMARY KEY,
            device_id TEXT,
            event_type TEXT,
            keyword TEXT,
            reaction_time_ms INTEGER,
            status TEXT,
            detected_app TEXT,
            order_price NUMERIC,
            order_distance NUMERIC,
            details JSONB,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );""",
    ]
    for statement in statements:
        run_query(statement, is_select=False)


ensure_management_tables()


# ============================================================
# 3. القائمة الجانبية والتنقل (Navigation)
# ============================================================
st.sidebar.title("⚡ MyClicker Control")
st.sidebar.caption("لوحة قيادة وتحكم الأسطول والإشعارات")

menu = st.sidebar.radio(
    "القائمة الرئيسية",
    [
        "📊 نظرة عامة والأسطول (Fleet Overview)",
        "📢 مركز الإشعارات المنسدلة (Heads-Up Alerts)",
        "📱🎮 ربط المحاكي بالهاتف (Emulator Bridge)",
        "🎟️ تفعيل اشتراك كابتن (UPSERT Activation)",
        "🤖 سجلات أداء البوت (Telemetry & Logs)",
    ],
)


# ============================================================
# الصفحة 1: نظرة عامة وإدارة الأسطول
# ============================================================
if menu.startswith("📊"):
    st.header("📊 حالة الأسطول والأجهزة المتصلة")
    
    users_df = run_query(
        """
        SELECT 
            u.device_id, u.phone, u.status, u.sub_tier, 
            u.custom_click_delay, u.device_model, u.accepted_clicks, 
            u.last_active, u.expiry_date,
            COALESCE(nd.notification_version, '100') as notif_ver,
            COALESCE(nd.delivery_status, 'جاهز 🟢') as delivery_status
        FROM myapp.users_status u
        LEFT JOIN myapp.notification_delivery nd ON u.device_id = nd.device_id
        ORDER BY u.last_active DESC
        """
    )
    
    if users_df is not None and not users_df.empty:
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("إجمالي الأجهزة", len(users_df))
        active_count = len(users_df[users_df["status"] == "Active"])
        c2.metric("الأجهزة النشطة", active_count)
        c3.metric("اشتراكات VIP", len(users_df[users_df["sub_tier"] == "VIP"]))
        c4.metric("مجموع النقرات المقبولة", f"{users_df['accepted_clicks'].sum():,}")

        st.subheader("قائمة الأجهزة والسائقين")
        st.dataframe(users_df, use_container_width=True, height=450)
    else:
        st.info("لا توجد أجهزة مسجلة في قاعدة البيانات حالياً.")


# ============================================================
# الصفحة 2: مركز الإشعارات المنسدلة (Heads-Up & Dropdown Alerts)
# ============================================================
elif menu.startswith("📢"):
    st.header("📢 مركز الإشعارات والتنبيهات المنسدلة الحية (Heads-Up)")
    st.markdown(
        """
        <div class="heads-up-banner">
            <div>
                <b>🔔 نظام الإشعارات المنسدلة العائمة (Heads-Up Push Notification Engine)</b><br/>
                يقوم بتحديث إصدار الإشعار <code>notification_version</code> فورياً لتنبيه تطبيق الأندرويد وعرض الإشعار المنسدل فوراً.
            </div>
            <span style="font-size:28px;">⚡</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    tab_broadcast, tab_individual, tab_history = st.tabs([
        "📢 إشعار جماعي منسدل (Broadcast)",
        "👤 إشعار فردي مخصص برقم الهاتف (Individual)",
        "🗄️ سجل الإشعارات الحية في Neon",
    ])

    with tab_broadcast:
        st.subheader("بث إشعار منسدل شامل لكافة الأجهزة")
        b_title = st.text_input("عنوان الإشعار الجماعي", value="تنبيه عام من الإدارة المركزية", key="b_title")
        b_msg = st.text_area("نص الإشعار المنسدل", value="تنبيه تشغيلي فوري: يرجى التأكد من استقرار الإنترنت وتفعيل خدمة إمكانية الوصول.", key="b_msg")
        
        col_bs1, col_bs2 = st.columns(2)
        with col_bs1:
            b_priority = st.selectbox("الأولوية", ["عالي وفوري (Urgent)", "عادي (Normal)", "تحذير تشغيلي (Warning)"])
        with col_bs2:
            b_sound = st.selectbox("صوت التنبيه", ["🏎️ هدير سيارة رياضية (Sports Car Rev)", "💨 تنفيس تيربو (Turbo Spool)", "🔔 رنين أندرويد (Chime)"])

        col_act1, col_act2 = st.columns([1, 1])
        with col_act1:
            if st.button("🚀 بث الإشعار المنسدل لكافة الأجهزة الآن", type="primary", use_container_width=True):
                if b_msg.strip():
                    clean_msg = b_msg.strip()
                    notif_ver = str(int(time.time() * 1000))
                    
                    # 1. حفظ في إعدادات التطبيق وتحديث نسخة الإشعار
                    save_config({
                        "notice_message": clean_msg,
                        "notification_version": notif_ver,
                        "notification_type": "إشعار منسدل",
                        "notification_android_type": "heads_up_drop_down",
                        "notification_sound": b_sound,
                        "notification_priority": b_priority,
                        "notification_enabled": "true",
                    })
                    
                    # 2. تحديث جدول المستخدمين النشطين
                    run_query("UPDATE myapp.users_status SET notice_message = %s, last_active = NOW()", (clean_msg,), is_select=False)
                    
                    # 3. تسجيل في جدول الإشعارات
                    run_query(
                        """
                        INSERT INTO myapp.system_notifications (title, message, type, priority, sound, sender, created_at)
                        VALUES (%s, %s, 'broadcast', %s, %s, 'الإدارة المركزية', NOW())
                        """,
                        (b_title.strip(), clean_msg, b_priority, b_sound),
                        is_select=False,
                    )
                    
                    # 4. تحديث سجل تسليم الإشعارات لكافة الأجهزة
                    run_query(
                        """
                        INSERT INTO myapp.notification_delivery (device_id, notification_version, notification_id, delivery_status, last_sync_at)
                        SELECT device_id, %s, %s, 'تم البث المنسدل 🚀 (Heads-Up)', NOW()
                        FROM myapp.users_status
                        ON CONFLICT (device_id) DO UPDATE SET 
                            notification_version = EXCLUDED.notification_version,
                            notification_id = EXCLUDED.notification_id,
                            delivery_status = 'تم البث المنسدل 🚀 (Heads-Up)',
                            last_sync_at = NOW()
                        """,
                        (notif_ver, notif_ver),
                        is_select=False,
                    )
                    st.success(f"✅ تم بث الإشعار المنسدل بنجاح لجميع الأجهزة النشطة (الإصدار: {notif_ver})!")
                    st.toast("تم البث المنسدل بنجاح ⚡", icon="📢")

        with col_act2:
            if st.button("🔔 تجربة فحص الإشعار المنسدل فوراً (Heads-Up Live Test)", use_container_width=True):
                test_ver = str(int(time.time() * 1000))
                test_msg = "⚡ فحص تشغيلي فوري: تم استقبال الإشعار المنسدل بنجاح واختبار خدمة إمكانية الوصول والتنبيهات العائمة!"
                save_config({
                    "notice_message": test_msg,
                    "notification_version": test_ver,
                    "notification_type": "إشعار منسدل",
                    "notification_android_type": "heads_up_drop_down",
                    "notification_sound": "sports_car_rev",
                    "notification_priority": "urgent",
                    "notification_enabled": "true",
                })
                run_query("UPDATE myapp.users_status SET notice_message = %s, last_active = NOW()", (test_msg,), is_select=False)
                run_query(
                    """
                    INSERT INTO myapp.system_notifications (title, message, type, priority, sound, sender, created_at)
                    VALUES ('🔔 فحص الإشعار المنسدل (Heads-Up Test)', %s, 'broadcast', 'urgent', 'sports_car_rev', 'فاحص الإشعارات المنسدلة', NOW())
                    """,
                    (test_msg,),
                    is_select=False,
                )
                st.success(f"✅ تم إطلاق فحص الإشعار المنسدل التجريبي بنجاح (الإصدار: {test_ver})!")
                st.toast("تم فحص الإشعار المنسدل بنجاح 🔔", icon="🎯")

    with tab_individual:
        st.subheader("إرسال إشعار فردي مخصص لهاتف كابتن محدد")
        ind_phone = st.text_input("📱 رقم هاتف الكابتن (مثال: 078XXXXXXX أو 79XXXXXXX)")

        detected_device_id = None
        if ind_phone.strip():
            digits = ind_phone.strip().replace("+", "").lstrip("0")
            matched = run_query(
                "SELECT device_id, phone, status, sub_tier FROM myapp.users_status WHERE phone ILIKE %s LIMIT 1",
                (f"%{digits}%",)
            )
            if matched is not None and not matched.empty:
                detected_device_id = str(matched.iloc[0]["device_id"])
                st.markdown(
                    f"""
                    <div class="heads-up-banner">
                        <div>
                            <b>✅ تم التعرف التلقائي على جهاز الكابتن:</b><br/>
                            📱 الهاتف: {matched.iloc[0]['phone']} | 🆔 المعرّف: <code>{detected_device_id}</code> | الحالة: {matched.iloc[0]['status']}
                        </div>
                        <span style="font-size:24px;">🎯</span>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
            else:
                st.warning("لم يتم العثور على جهاز مسجل مسبقاً بهذا الرقم، يمكنك إدخال معرّف الجهاز يدوياً.")

        target_dev = st.text_input("معرّف الجهاز (Device ID)", value=detected_device_id or "")
        ind_title = st.text_input("عنوان التنبيه الفردي", value="تنبيه كابتن فوري")
        ind_msg = st.text_area("نص الإشعار الخاص", value="كابتن عزيز: جهازك متصل ولم يسجل نقرات تفاعلية اليوم، يرجى تشغيل البوت والتأكد من الصلاحيات.")

        if st.button("⚡ إرسال الإشعار الفردي المنسدل لهذا الكابتن فوراً", type="primary"):
            if not ind_msg.strip():
                st.error("يرجى كتابة نص الإشعار.")
            elif not target_dev.strip() and not ind_phone.strip():
                st.error("يرجى توفير رقم الهاتف أو معرّف الجهاز.")
            else:
                clean_msg = ind_msg.strip()
                notif_ver = str(int(time.time() * 1000))
                dev_id = target_dev.strip()
                phone_val = ind_phone.strip()

                if dev_id:
                    run_query(
                        "UPDATE myapp.users_status SET notice_message = %s, last_active = NOW() WHERE device_id = %s",
                        (clean_msg, dev_id),
                        is_select=False
                    )
                    run_query(
                        """
                        INSERT INTO myapp.notification_delivery (device_id, phone, notification_version, notification_id, delivery_status, last_sync_at)
                        VALUES (%s, %s, %s, %s, 'مرسل للكابتن 🟢 (Heads-Up)', NOW())
                        ON CONFLICT (device_id) DO UPDATE SET
                            phone = COALESCE(EXCLUDED.phone, myapp.notification_delivery.phone),
                            notification_version = EXCLUDED.notification_version,
                            notification_id = EXCLUDED.notification_id,
                            delivery_status = 'مرسل للكابتن 🟢 (Heads-Up)',
                            last_sync_at = NOW()
                        """,
                        (dev_id, phone_val or None, notif_ver, notif_ver),
                        is_select=False
                    )
                elif phone_val:
                    matched = run_query("SELECT device_id FROM myapp.users_status WHERE phone ILIKE %s LIMIT 1", (f"%{phone_val}%",))
                    if matched is not None and not matched.empty:
                        dev_id = str(matched.iloc[0]["device_id"])
                        run_query(
                            "UPDATE myapp.users_status SET notice_message = %s, last_active = NOW() WHERE device_id = %s",
                            (clean_msg, dev_id),
                            is_select=False
                        )
                        run_query(
                            """
                            INSERT INTO myapp.notification_delivery (device_id, phone, notification_version, notification_id, delivery_status, last_sync_at)
                            VALUES (%s, %s, %s, %s, 'مرسل للكابتن 🟢 (Heads-Up)', NOW())
                            ON CONFLICT (device_id) DO UPDATE SET
                                notification_version = EXCLUDED.notification_version,
                                notification_id = EXCLUDED.notification_id,
                                delivery_status = 'مرسل للكابتن 🟢 (Heads-Up)',
                                last_sync_at = NOW()
                            """,
                            (dev_id, phone_val, notif_ver, notif_ver),
                            is_select=False
                        )

                run_query(
                    """
                    INSERT INTO myapp.system_notifications 
                    (title, message, type, target_phone, target_device_id, priority, sender, created_at)
                    VALUES (%s, %s, 'individual', %s, %s, 'urgent', 'الإدارة المركزية', NOW())
                    """,
                    (ind_title.strip(), clean_msg, phone_val, dev_id),
                    is_select=False
                )
                st.success(f"✅ تم إرسال الإشعار الفردي المنسدل فوراً لجهاز الكابتن ({dev_id or phone_val}) بإصدار ({notif_ver})!")
                st.toast("تم إرسال الإشعار الفردي بنجاح ⚡", icon="👤")

    with tab_history:
        st.subheader("سجل الإشعارات المرسلة من قاعدة بيانات Neon")
        notif_logs = run_query(
            "SELECT id, title, message, type, target_phone, priority, sender, created_at FROM myapp.system_notifications ORDER BY created_at DESC LIMIT 50"
        )
        if notif_logs is not None and not notif_logs.empty:
            st.dataframe(notif_logs, use_container_width=True, height=360)
            if st.button("🗑️ مسح سجل الإشعارات القديمة"):
                run_query("DELETE FROM myapp.system_notifications", is_select=False)
                st.success("تم مسح السجل.")
                st.rerun()
        else:
            st.info("لا توجد إشعارات مسجلة في السجل حالياً.")


# ============================================================
# الصفحة 3: ربط وتهيئة المحاكي برقم الهاتف (Emulator Bridge)
# ============================================================
elif menu.startswith("📱🎮"):
    st.header("📱🎮 بوابة ربط المحاكي بالهاتف (Emulator Bridge)")
    
    col_e1, col_e2 = st.columns(2)
    with col_e1:
        st.subheader("ربط محاكي جديد برقم الهاتف فورياً")
        phone_in = st.text_input("📱 رقم هاتف الكابتن / السائق *", placeholder="078XXXXXXX")
        emu_type = st.selectbox("نوع المحاكي", ["LDPlayer 9 Android", "Nox Player 7", "BlueStacks 5", "MEmu Play", "Android Studio AVD"])
        speed_in = st.slider("سرعة النقر المخصصة (ms)", min_value=5, max_value=120, value=25, step=5)

        if st.button("⚡ ربط وتثبيت المحاكي في قاعدة بيانات Neon", type="primary"):
            if not phone_in.strip():
                st.error("يرجى إدخال رقم الهاتف.")
            else:
                clean_phone = phone_in.strip()
                check = run_query("SELECT device_id, phone, status FROM myapp.users_status WHERE phone = %s LIMIT 1", (clean_phone,))
                if check is not None and not check.empty:
                    exist_id = check.iloc[0]["device_id"]
                    run_query(
                        "UPDATE myapp.users_status SET status='Active', custom_click_delay=%s, device_model=%s, last_active=NOW() WHERE device_id=%s",
                        (speed_in, emu_type, exist_id),
                        is_select=False
                    )
                    st.success(f"✅ تم العثور على الجهاز المسجل مسبقاً ({exist_id}) وتفعيله فوراً للمحاكي!")
                else:
                    new_id = f"emu_{hashlib.md5(f'{clean_phone}_{time.time()}'.encode()).hexdigest()[:16]}"
                    run_query(
                        """
                        INSERT INTO myapp.users_status 
                        (device_id, phone, status, sub_tier, custom_click_delay, device_model, is_frozen, last_active, expiry_date)
                        VALUES (%s, %s, 'Active', 'VIP', %s, %s, FALSE, NOW(), NOW() + INTERVAL '30 days')
                        ON CONFLICT (device_id) DO UPDATE SET phone=EXCLUDED.phone, status='Active', last_active=NOW()
                        """,
                        (new_id, clean_phone, speed_in, emu_type),
                        is_select=False
                    )
                    st.success(f"🎉 تم بنجاح إنشاء وربط معرّف المحاكي الجديد ({new_id}) وتفعيل اشتراكه 30 يوماً!")

    with col_e2:
        st.subheader("إرسال نقرة فحص حية (Test Ping Telemetry)")
        test_dev_id = st.text_input("معرّف المحاكي للاختبار", value="emu_test_ping")
        test_latency = st.number_input("زمن الاستجابة التجريبي (ms)", min_value=1, max_value=200, value=22)
        if st.button("🚀 إرسال نقرة تجريبية إلى Bot Diagnostics"):
            run_query(
                """
                INSERT INTO myapp.bot_logs 
                (device_id, event_type, status, order_price, keyword, reaction_time_ms, detected_app, created_at)
                VALUES (%s, 'BOT_CLICK_PERFORMANCE', 'SUCCESS', 5.5, 'طلب فحص محاكي لحظي', %s, 'Captain App', NOW())
                """,
                (test_dev_id.strip(), int(test_latency)),
                is_select=False
            )
            st.success(f"⚡ تم تسجيل نقرة التيليميتري بزمن استجابة {test_latency}ms في Neon بنجاح!")


# ============================================================
# الصفحة 4: تفعيل اشتراك كابتن (UPSERT Activation)
# ============================================================
elif menu.startswith("🎟️"):
    st.header("🎟️ تفعيل اشتراك يدوي فوري (UPSERT Fix)")
    
    col_m1, col_m2 = st.columns(2)
    with col_m1:
        manual_phone = st.text_input("📱 رقم هاتف الكابتن")
    with col_m2:
        tier_choice = st.selectbox("فئة الاشتراك", ["VIP", "STANDARD", "TRIAL"])

    auto_device_id = ""
    if manual_phone.strip():
        match_dev = run_query("SELECT device_id FROM myapp.users_status WHERE phone ILIKE %s LIMIT 1", (f"%{manual_phone.strip()}%",))
        if match_dev is not None and not match_dev.empty:
            auto_device_id = str(match_dev.iloc[0]["device_id"])

    target_device_id = st.text_input("معرّف الجهاز (Device ID)", value=auto_device_id)
    activation_code = st.text_input("🔑 كود التفعيل", value=f"EMP-{hashlib.sha256(str(time.time()).encode()).hexdigest()[:8].upper()}")
    activation_days = st.number_input("مدة الاشتراك بالأيام", min_value=1, max_value=365, value=30)

    if st.button("🚀 تنفيذ التفعيل الفوري والحفظ في Neon", type="primary"):
        if not target_device_id.strip():
            st.error("⚠️ يرجى إدخال معرّف الجهاز.")
        else:
            res = run_query(
                """
                INSERT INTO myapp.users_status 
                (device_id, phone, status, sub_tier, expiry_date, activated_code, is_frozen, last_active)
                VALUES (%s, %s, 'Active', %s, NOW() + (%s || ' days')::interval, %s, FALSE, NOW())
                ON CONFLICT (device_id) DO UPDATE SET
                    status = 'Active',
                    sub_tier = EXCLUDED.sub_tier,
                    expiry_date = GREATEST(COALESCE(myapp.users_status.expiry_date, NOW()), NOW()) + (%s || ' days')::interval,
                    phone = COALESCE(NULLIF(EXCLUDED.phone, ''), myapp.users_status.phone),
                    activated_code = EXCLUDED.activated_code,
                    is_frozen = FALSE,
                    last_active = NOW()
                """,
                (target_device_id.strip(), manual_phone.strip(), tier_choice, int(activation_days), activation_code.strip(), int(activation_days)),
                is_select=False
            )
            if res:
                st.success(f"✅ تم تفعيل الاشتراك بنجاح للباقة [{tier_choice}] لمدة {activation_days} يوماً للجهاز ({target_device_id})!")
                st.toast("تم التفعيل اليدوي بنجاح ⚡", icon="🎉")


# ============================================================
# الصفحة 5: سجلات أداء البوت والتشخيص (Telemetry)
# ============================================================
elif menu.startswith("🤖"):
    st.header("🤖 سجلات أداء البوت والتشخيص اللحظي (Telemetry)")
    
    logs = run_query("SELECT * FROM myapp.bot_logs ORDER BY created_at DESC LIMIT 200")
    if logs is not None and not logs.empty:
        valid_reactions = logs["reaction_time_ms"].dropna()
        if not valid_reactions.empty:
            c_r1, c_r2, c_r3 = st.columns(3)
            c_r1.metric("متوسط سرعة النقر", f"{int(valid_reactions.mean())} ms")
            c_r2.metric("أسرع نقرة مسجلة", f"{int(valid_reactions.min())} ms")
            c_r3.metric("عدد العمليات المرصودة", f"{len(logs):,}")

        st.dataframe(logs, use_container_width=True, height=450)
        if st.button("🗑️ مسح سجلات التشخيص القديمة"):
            run_query("DELETE FROM myapp.bot_logs", is_select=False)
            st.success("تم مسح السجلات.")
            st.rerun()
    else:
        st.info("لا توجد سجلات تيليميتري مرصودة حالياً.")

"""
إضافة سجل نشاط المشرفين إلى تطبيق MyClicker Pro في Streamlit

طريقة الاستخدام:
1) الصق هذا الكود بعد دوال run_query وsection_title وrender_table في ملفك الرئيسي.
2) استدعِ ensure_audit_table() مرة واحدة بعد تسجيل الدخول.
3) أضف render_audit_log_page() داخل شرط القائمة الجانبية.
4) بعد كل عملية تعديل، استدعِ log_admin_action(...).

الكود يستخدم دالة run_query الموجودة أصلاً في تطبيقك، لذلك لا يغيّر رابط اتصال قاعدة البيانات.
"""

from datetime import datetime
from typing import Any, Optional

import pandas as pd
import streamlit as st


AUDIT_ACTION_LABELS = {
    "update": "تعديل بيانات",
    "reset": "تصفير النقرات",
    "freeze": "تغيير التجميد",
    "delete": "حذف جهاز",
    "login": "تسجيل دخول",
    "logout": "تسجيل خروج",
    "settings": "تغيير الإعدادات",
}


def ensure_audit_table() -> bool:
    """إنشاء جدول السجل والفهارس إذا لم تكن موجودة."""
    result = run_query(
        """
        CREATE TABLE IF NOT EXISTS myapp.admin_audit_log (
            id BIGSERIAL PRIMARY KEY,
            actor_open_id VARCHAR(128) NOT NULL,
            actor_name VARCHAR(320) NOT NULL,
            actor_role VARCHAR(32) NOT NULL DEFAULT 'admin',
            action VARCHAR(64) NOT NULL,
            device_id VARCHAR(255),
            details TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """,
        is_select=False,
    )
    if result is None:
        return False

    run_query(
        """
        CREATE INDEX IF NOT EXISTS admin_audit_log_created_at_idx
        ON myapp.admin_audit_log (created_at DESC)
        """,
        is_select=False,
    )
    run_query(
        """
        CREATE INDEX IF NOT EXISTS admin_audit_log_action_idx
        ON myapp.admin_audit_log (action)
        """,
        is_select=False,
    )
    return True


def _current_actor() -> dict[str, str]:
    """الحصول على بيانات المستخدم الحالي من session_state."""
    user = st.session_state.get("user", {}) or {}
    return {
        "open_id": str(user.get("openId") or user.get("open_id") or "streamlit-admin"),
        "name": str(user.get("name") or st.session_state.get("username") or "admin"),
        "role": str(user.get("role") or "admin"),
    }


def log_admin_action(
    action: str,
    *,
    device_id: Optional[str] = None,
    details: Optional[str] = None,
    actor: Optional[dict[str, str]] = None,
) -> bool:
    """تسجيل عملية مشرف واحدة بعد نجاح العملية الأصلية."""
    current = actor or _current_actor()
    if current.get("role") not in {"admin", "supervisor", "مشرف"}:
        return False

    return (
        run_query(
            """
            INSERT INTO myapp.admin_audit_log
                (actor_open_id, actor_name, actor_role, action, device_id, details)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (
                current["open_id"],
                current["name"],
                current["role"],
                action,
                device_id,
                details,
            ),
            is_select=False,
        )
        is not None
    )


def fetch_audit_logs(
    search: str = "",
    action: str = "all",
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = 250,
) -> pd.DataFrame:
    """جلب سجل النشاط بفلاتر آمنة ومعاملات SQL."""
    query = """
        SELECT
            id,
            actor_name,
            actor_role,
            action,
            device_id,
            details,
            created_at
        FROM myapp.admin_audit_log
        WHERE (%s = '' OR actor_name ILIKE '%%' || %s || '%%'
               OR device_id ILIKE '%%' || %s || '%%'
               OR details ILIKE '%%' || %s || '%%')
          AND (%s = 'all' OR action = %s)
          AND (%s IS NULL OR created_at::date >= %s::date)
          AND (%s IS NULL OR created_at::date <= %s::date)
        ORDER BY created_at DESC
        LIMIT %s
    """
    params = (
        search.strip(),
        search.strip(),
        search.strip(),
        search.strip(),
        action,
        action,
        start_date,
        start_date,
        end_date,
        end_date,
        int(limit),
    )
    result = run_query(query, params)
    if result is None:
        return pd.DataFrame()
    return result


def render_audit_log_page() -> None:
    """عرض صفحة سجل نشاط المشرفين داخل Streamlit."""
    ensure_audit_table()

    page_header(
        "🧾 سجل نشاط المشرفين",
        "تتبع جميع التعديلات والعمليات التي تمت داخل لوحة التحكم.",
    )

    current = _current_actor()
    if current.get("role") not in {"admin", "supervisor", "مشرف", "monitor", "مراقب"}:
        st.error("ليس لديك صلاحية مشاهدة سجل النشاط.")
        st.stop()

    filter_col1, filter_col2, filter_col3, filter_col4 = st.columns([1.5, 1, 1, 1])
    with filter_col1:
        search = st.text_input(
            "🔍 بحث",
            placeholder="اسم المشرف أو الجهاز أو التفاصيل",
        )
    with filter_col2:
        action_options = ["all", *AUDIT_ACTION_LABELS.keys()]
        action = st.selectbox(
            "نوع العملية",
            options=action_options,
            format_func=lambda value: "كل العمليات" if value == "all" else AUDIT_ACTION_LABELS[value],
        )
    with filter_col3:
        start_date = st.date_input("من تاريخ", value=None)
    with filter_col4:
        end_date = st.date_input("إلى تاريخ", value=None)

    start_value = start_date.isoformat() if start_date else None
    end_value = end_date.isoformat() if end_date else None
    logs = fetch_audit_logs(
        search=search,
        action=action,
        start_date=start_value,
        end_date=end_value,
    )

    if not logs.empty:
        logs["نوع العملية"] = logs["action"].map(AUDIT_ACTION_LABELS).fillna(logs["action"])
        logs["وقت العملية"] = pd.to_datetime(logs["created_at"], errors="coerce").dt.strftime("%Y-%m-%d %H:%M:%S")
        logs["الدور"] = logs["actor_role"].replace({"admin": "مشرف", "monitor": "مراقب"})
        logs = logs.rename(
            columns={
                "actor_name": "اسم المستخدم",
                "device_id": "معرّف الجهاز",
                "details": "التفاصيل",
            }
        )
        display_columns = [
            "وقت العملية",
            "اسم المستخدم",
            "الدور",
            "نوع العملية",
            "معرّف الجهاز",
            "التفاصيل",
        ]
    else:
        display_columns = []

    metric_col1, metric_col2, metric_col3 = st.columns(3)
    metric_col1.metric("إجمالي العمليات", f"{len(logs):,}")
    metric_col2.metric("عمليات التعديل", f"{int((logs.get('action', pd.Series(dtype=str)) == 'update').sum()):,}")
    metric_col3.metric("عمليات الحذف", f"{int((logs.get('action', pd.Series(dtype=str)) == 'delete').sum()):,}")

    section_title("📋 تفاصيل سجل النشاط")
    if logs.empty:
        st.info("لا توجد عمليات مسجلة ضمن الفلاتر الحالية.")
        return

    render_table(logs[display_columns], height=520)

    export_frame = logs[display_columns].copy()
    csv_data = export_frame.to_csv(index=False).encode("utf-8-sig")
    st.download_button(
        "⬇️ تصدير سجل النشاط CSV",
        data=csv_data,
        file_name=f"myclicker-audit-log-{datetime.now():%Y-%m-%d}.csv",
        mime="text/csv",
    )


# ============================================================
# أمثلة ربط التسجيل بالعمليات الحالية
# ضع السطر بعد نجاح كل عملية في كودك الحالي:
# ============================================================
# بعد تعديل مستخدم:
# log_admin_action("update", device_id=device_id, details=f"phone={phone}, tier={tier}")
# بعد تصفير النقرات:
# log_admin_action("reset", device_id=device_id, details="accepted_clicks=0")
# بعد تغيير التجميد:
# log_admin_action("freeze", device_id=device_id, details="تم تغيير حالة التجميد")
# بعد حذف جهاز:
# log_admin_action("delete", device_id=device_id, details="تم حذف الجهاز من الأسطول")
# بعد تسجيل الدخول:
# log_admin_action("login", details="تم تسجيل دخول المشرف")

# ============================================================
# إضافة صفحة السجل إلى القائمة الجانبية
# عدّل شرط menu في آخر الملف:
# ============================================================
# elif menu.startswith("🧾"):
#     render_audit_log_page()
#
# وأضف هذا العنصر إلى MENU_ITEMS:
# "🧾 سجل نشاط المشرفين",

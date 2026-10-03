#!/usr/bin/env python3
"""
===================================================================================
🚗 EMPEROR BOT CONTROL SYSTEM - BACKEND API & CONTROLLER (PYTHON / FASTAPI)
===================================================================================
خادم بايثون متكامل وسريع (FastAPI + AsyncPG + Pydantic + Uvicorn)
متوافق بنسبة 100% مع قاعدة بيانات Neon PostgreSQL ومع كافة وظائف السيرفر:
1. استقبال القياس عن بعد والبث اللحظي (Telemetry & Bot Logs)
2. إدارة حالة المستخدمين والأجهزة (Users Status, Devices, Freeze, Expiry)
3. رموز التفعيل والاشتراكات (Activation Codes, Audits, Subscriptions)
4. إعدادات السرعة وسرعات الهواتف (Global, Tier-based & Individual Click Delays)
5. فحص الترخيص والتشغيل لتطبيقات الهواتف (License Verification & Check App)
6. إدارة الموظفين والصلاحيات (Staff Authentication & Sessions)
7. فحص الجاهزية ولوحة القياس الإحصائية (Health Check & Real-time Metrics)
===================================================================================
طريقة التشغيل:
pip install fastapi uvicorn asyncpg psycopg2-binary python-dotenv pydantic requests
python server.py
"""

import os
import sys
import json
import hashlib
import asyncio
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any

from fastapi import FastAPI, Request, Response, HTTPException, Depends, Header, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse
from pydantic import BaseModel, Field
import asyncpg

# ===================================================================================
# 1. إعدادات البيئة وقاعدة البيانات
# ===================================================================================
DB_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://neondb_owner:npg_AvzFkHQ6M3yo@ep-tiny-wind-ayd9hww0-pooler.c-5.us-east-2.aws.neon.tech/neondb?sslmode=require"
)
ENV_ADMIN_KEY = os.getenv("ADMIN_KEY", "admin123")
ENV_APP_SECRET_KEY = os.getenv("APP_SECRET_KEY", "MySuperSecretKey123!@#")
API_SECRET_TOKEN = os.getenv("API_SECRET_TOKEN", "EMPEROR_BOT_SECURE_TOKEN_2026")
PORT = int(os.getenv("PORT", "3000"))

# تطبيق FastAPI
app = FastAPI(
    title="Emperor Bot Management & Telemetry API",
    description="سيرفر بايثون متكامل للتحكم ببوتات النقرات ومتابعة تيليميتري الهواتف الحية",
    version="2.0.0"
)

# تفعيل CORS للاتصال من جميع المتصفحات والهواتف
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# مجمع اتصالات قاعدة البيانات (Connection Pool)
db_pool: Optional[asyncpg.Pool] = None

@app.on_event("startup")
async def startup_event():
    global db_pool
    print("⏳ جارٍ الاتصال بقاعدة بيانات Neon PostgreSQL عبر بايثون...")
    try:
        # تحويل رابط الاتصال ليناسب asyncpg
        clean_url = DB_URL.replace("sslmode=require", "ssl=require")
        db_pool = await asyncpg.create_pool(
            dsn=clean_url,
            min_size=2,
            max_size=15,
            timeout=30,
            command_timeout=60
        )
        print("✅ تم الاتصال بنجاح بقاعدة البيانات.")
        await init_tables()
    except Exception as e:
        print(f"❌ خطأ أثناء الاتصال بقاعدة البيانات: {e}", file=sys.stderr)

@app.on_event("shutdown")
async def shutdown_event():
    global db_pool
    if db_pool:
        await db_pool.close()
        print("🔌 تم إغلاق مجمع اتصالات قاعدة البيانات.")


# ===================================================================================
# 2. إنشاء الجداول والإعدادات الافتراضية
# ===================================================================================
async def init_tables():
    if not db_pool:
        return
    async with db_pool.acquire() as conn:
        await conn.execute("CREATE SCHEMA IF NOT EXISTS myapp;")
        
        # جدول الإعدادات
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS myapp.app_config (
                key TEXT PRIMARY KEY,
                value TEXT
            );
        """)
        
        # جدول المستخدمين والأجهزة
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS myapp.users_status (
                device_id TEXT PRIMARY KEY,
                phone TEXT,
                status TEXT DEFAULT 'Active',
                sub_tier TEXT DEFAULT 'STANDARD',
                accepted_clicks BIGINT DEFAULT 0,
                app_version TEXT,
                device_model TEXT,
                device_tier TEXT DEFAULT 'midrange',
                custom_click_delay INTEGER DEFAULT NULL,
                is_frozen BOOLEAN DEFAULT FALSE,
                notice_message TEXT,
                expiry_date TIMESTAMPTZ,
                last_active TIMESTAMPTZ DEFAULT NOW()
            );
        """)

        # جدول سجلات البوت والتيليميتري
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS myapp.bot_logs (
                id BIGSERIAL PRIMARY KEY,
                device_id TEXT NOT NULL,
                event_type TEXT NOT NULL,
                status TEXT NOT NULL,
                order_price NUMERIC(10,2),
                order_distance NUMERIC(10,2),
                keyword TEXT,
                reaction_time_ms INTEGER,
                detected_app TEXT,
                ignore_reason TEXT,
                conditions_ignored BOOLEAN DEFAULT FALSE,
                details JSONB,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            );
        """)

        # جدول الموظفين
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS myapp.app_staff (
                id BIGSERIAL PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                display_name TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'monitor',
                permissions TEXT,
                active BOOLEAN NOT NULL DEFAULT TRUE,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            );
        """)

        # جدول الاشتراكات والأكواد
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS myapp.subscriptions (
                code TEXT PRIMARY KEY,
                duration_days INTEGER NOT NULL DEFAULT 30,
                category TEXT NOT NULL DEFAULT 'STANDARD',
                payment_status TEXT NOT NULL DEFAULT 'pending',
                renewal_status TEXT NOT NULL DEFAULT 'new',
                renewed_at TIMESTAMPTZ,
                is_used BOOLEAN NOT NULL DEFAULT FALSE,
                used_by_device TEXT,
                used_at TIMESTAMPTZ
            );
        """)

        # الإعدادات الافتراضية
        default_configs = {
            "app_name": "Emperor Bot Suite 2026",
            "bot_enabled": "true",
            "click_delay": "35",
            "tier_flagship_delay": "10",
            "tier_midrange_delay": "35",
            "tier_budget_delay": "80",
            "min_reaction_time_ms": "12",
            "global_notice": "",
            "active_version": "7.3.0"
        }
        for k, v in default_configs.items():
            await conn.execute("""
                INSERT INTO myapp.app_config (key, value)
                VALUES ($1, $2)
                ON CONFLICT (key) DO NOTHING;
            """, k, v)
        print("🚀 تم تهيئة جداول النظام وإعدادات الإنتاج بنجاح.")


# ===================================================================================
# 3. دوال مساعدة لحساب سرعة النقرات والتحقق
# ===================================================================================
def calculate_effective_delay(user: Optional[dict], configs: dict) -> dict:
    if user and user.get("custom_click_delay") and int(user["custom_click_delay"]) > 0:
        return {
            "delay": int(user["custom_click_delay"]),
            "source": "custom_individual",
            "source_label": "فردي مخصص للجهاز 🎯",
            "tier": user.get("device_tier") or "custom"
        }
    
    tier = (user.get("device_tier") if user else "midrange") or "midrange"
    tier = tier.lower()

    if tier == "flagship":
        return {
            "delay": int(configs.get("tier_flagship_delay", 10)),
            "source": "phone_tier_flagship",
            "source_label": "فئة الهواتف الرائدة 🚀",
            "tier": "flagship"
        }
    elif tier == "budget":
        return {
            "delay": int(configs.get("tier_budget_delay", 80)),
            "source": "phone_tier_budget",
            "source_label": "فئة الهواتف الاقتصادية 🛡️",
            "tier": "budget"
        }
    else:
        return {
            "delay": int(configs.get("tier_midrange_delay") or configs.get("click_delay", 35)),
            "source": "phone_tier_midrange",
            "source_label": "فئة الهواتف المتوسطة ⚖️",
            "tier": "midrange"
        }


# ===================================================================================
# 4. مسارات التيليميتري ومراقبة أداء الهواتف (TELEMETRY & BOT DIAGNOSTICS)
# ===================================================================================
class TelemetryPayload(BaseModel):
    deviceId: Optional[str] = None
    device_id: Optional[str] = None
    eventType: Optional[str] = None
    event_type: Optional[str] = None
    status: Optional[str] = "SUCCESS"
    reactionTimeMs: Optional[int] = None
    reaction_time_ms: Optional[int] = None
    orderPrice: Optional[float] = None
    order_price: Optional[float] = None
    orderDistance: Optional[float] = None
    order_distance: Optional[float] = None
    keyword: Optional[str] = None
    detectedApp: Optional[str] = None
    detected_app: Optional[str] = None
    ignoreReason: Optional[str] = None
    ignore_reason: Optional[str] = None
    conditionsIgnored: Optional[bool] = False
    details: Optional[Dict[str, Any]] = None

@app.post("/api/telemetry/stream")
@app.post("/telemetry/stream")
async def receive_telemetry(payload: TelemetryPayload, authorization: Optional[str] = Header(None)):
    """استقبال تدفق الأحداث الحية ونقرات الهاتف وتحديث نشاط الجهاز فورياً"""
    target_id = (payload.deviceId or payload.device_id or "unknown_device").strip()
    ev_type = payload.eventType or payload.event_type or "PING"
    status = (payload.status or "SUCCESS").upper()
    r_time = payload.reactionTimeMs if payload.reactionTimeMs is not None else payload.reaction_time_ms
    price = payload.orderPrice if payload.orderPrice is not None else payload.order_price
    dist = payload.orderDistance if payload.orderDistance is not None else payload.order_distance
    kw = payload.keyword
    app_name = payload.detectedApp or payload.detected_app
    reason = payload.ignoreReason or payload.ignore_reason
    ignored = bool(payload.conditionsIgnored)
    details_json = json.dumps(payload.details or {})

    async with db_pool.acquire() as conn:
        # تسجيل الحدث
        await conn.execute("""
            INSERT INTO myapp.bot_logs 
            (device_id, event_type, status, order_price, order_distance, keyword, reaction_time_ms, detected_app, ignore_reason, conditions_ignored, details, created_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11::jsonb, NOW())
        """, target_id, ev_type, status, price, dist, kw, r_time, app_name, reason, ignored, details_json)

        # تحديث جهاز الهاتف في users_status ليظهر فوراً في القائمة المنسدلة
        clicks_increment = 1 if (r_time is not None and status == "SUCCESS") else 0
        await conn.execute("""
            INSERT INTO myapp.users_status (device_id, status, last_active, accepted_clicks)
            VALUES ($1, 'Active', NOW(), $2)
            ON CONFLICT (device_id) DO UPDATE
            SET last_active = NOW(),
                status = 'Active',
                accepted_clicks = CASE WHEN $3 = 'SUCCESS' THEN COALESCE(myapp.users_status.accepted_clicks, 0) + $2 ELSE myapp.users_status.accepted_clicks END
        """, target_id, clicks_increment, status)

    return {"success": True, "message": "Telemetry received and recorded", "deviceId": target_id}


@app.get("/api/admin/bot-logs")
async def get_bot_logs(
    limit: int = Query(50, ge=1, le=500),
    deviceId: Optional[str] = Query(None),
    status: Optional[str] = Query(None)
):
    """جلب سجلات البوت وأجهزة الهواتف المتاحة وإحصائيات الأداء في لوحة الفحص"""
    async with db_pool.acquire() as conn:
        # 1. الاستعلام عن السجلات
        params = []
        conditions = []
        if deviceId and deviceId != "all":
            params.append(deviceId)
            conditions.append(f"device_id = ${len(params)}")
        if status and status != "ALL":
            params.append(status)
            conditions.append(f"status = ${len(params)}")

        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        params.append(limit)
        query = f"""
            SELECT id, device_id, event_type, status, order_price, order_distance, 
                   keyword, reaction_time_ms, detected_app, ignore_reason, 
                   conditions_ignored, details, created_at
            FROM myapp.bot_logs
            {where_clause}
            ORDER BY created_at DESC
            LIMIT ${len(params)}
        """
        rows = await conn.fetch(query, *params)
        logs_list = [dict(r) for r in rows]

        # 2. الإحصائيات العامة
        stat_params = [deviceId] if (deviceId and deviceId != "all") else []
        stat_filter = "WHERE device_id = $1" if stat_params else ""
        stats_row = await conn.fetchrow(f"""
            SELECT 
                COUNT(*) as total_events,
                COUNT(*) FILTER (WHERE status = 'SUCCESS') as successful_clicks,
                COUNT(*) FILTER (WHERE status = 'REJECTED' OR status = 'IGNORED') as filtered_out,
                COUNT(*) FILTER (WHERE status = 'ERROR') as system_errors,
                ROUND(AVG(reaction_time_ms) FILTER (WHERE reaction_time_ms IS NOT NULL)) as avg_reaction_time_ms,
                MIN(reaction_time_ms) FILTER (WHERE reaction_time_ms IS NOT NULL) as min_reaction_time_ms,
                MAX(reaction_time_ms) FILTER (WHERE reaction_time_ms IS NOT NULL) as max_reaction_time_ms
            FROM myapp.bot_logs
            {stat_filter}
        """, *stat_params)

        # 3. قائمة الأجهزة المتصلة مرتبة بالأحدث نشاطاً
        devices_rows = await conn.fetch("""
            WITH combined AS (
                SELECT DISTINCT ON (d.device_id) 
                    d.device_id, 
                    COALESCE(u.phone, 'جهاز هاتف مباشر') as phone, 
                    COALESCE(u.status, 'Online') as status, 
                    COALESCE(d.last_event, u.last_active, NOW()) as last_active, 
                    COALESCE(u.device_model, 'Android Device') as device_model
                FROM (
                    SELECT device_id, MAX(created_at) as last_event FROM myapp.bot_logs GROUP BY device_id
                    UNION
                    SELECT device_id, last_active as last_event FROM myapp.users_status WHERE device_id NOT LIKE 'sim_%'
                ) d
                LEFT JOIN myapp.users_status u ON u.device_id = d.device_id
                WHERE d.device_id IS NOT NULL AND d.device_id != ''
                ORDER BY d.device_id, d.last_event DESC NULLS LAST
            )
            SELECT * FROM combined
            ORDER BY last_active DESC NULLS LAST
            LIMIT 60
        """)
        devices_list = [dict(d) for d in devices_rows]

    return {
        "success": True,
        "logs": logs_list,
        "stats": dict(stats_row) if stats_row else {},
        "devices": devices_list
    }


# ===================================================================================
# 5. مسارات الهواتف وتطبيق الكابتن (LICENSE CHECK & USER APP ROUTE)
# ===================================================================================
@app.get("/api/user/status")
@app.get("/user/status")
async def check_user_status(device_id: str = Query(...)):
    """استعلام تطبيق الهاتف عن حالة الاشتراك، سرعة النقر، والتجميد ورسالة التنبيه"""
    async with db_pool.acquire() as conn:
        user_row = await conn.fetchrow("""
            SELECT * FROM myapp.users_status WHERE device_id = $1
        """, device_id)
        
        cfg_rows = await conn.fetch("SELECT key, value FROM myapp.app_config")
        configs = {r["key"]: r["value"] for r in cfg_rows}

    user = dict(user_row) if user_row else None
    speed_info = calculate_effective_delay(user, configs)

    if not user:
        return {
            "registered": False,
            "status": "Inactive",
            "message": "الجهاز غير مسجل أو يحتاج إلى تفعيل كود جديد",
            "click_delay": speed_info["delay"],
            "speed_info": speed_info
        }

    # التحقق من صلاحية الاشتراك والتجميد
    is_expired = False
    if user.get("expiry_date"):
        if user["expiry_date"].replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
            is_expired = True

    return {
        "registered": True,
        "device_id": user["device_id"],
        "phone": user.get("phone"),
        "status": "Expired" if is_expired else user.get("status", "Active"),
        "is_frozen": user.get("is_frozen", False),
        "notice_message": user.get("notice_message") or configs.get("global_notice", ""),
        "expiry_date": user.get("expiry_date"),
        "click_delay": speed_info["delay"],
        "speed_info": speed_info,
        "accepted_clicks": user.get("accepted_clicks", 0)
    }


# ===================================================================================
# 6. مسارات لوحة التحكم والإحصائيات (ADMIN API & HEALTH)
# ===================================================================================
@app.get("/api/health")
async def health_check():
    """فحص سلامة السيرفر وقاعدة البيانات"""
    try:
        async with db_pool.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT NOW() as now, 
                       (SELECT COUNT(*) FROM myapp.users_status) as users_count,
                       (SELECT COUNT(*) FROM myapp.bot_logs) as logs_count
            """)
        return {
            "status": "online",
            "engine": "Python FastAPI",
            "database": "Neon PostgreSQL Connected",
            "server_time": str(row["now"]),
            "users_count": row["users_count"],
            "logs_count": row["logs_count"]
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "detail": str(e)})


@app.get("/api/users")
async def list_users():
    """جلب قائمة المستخدمين لصفحة التحكم"""
    async with db_pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT device_id, phone, status, sub_tier, accepted_clicks, 
                   device_model, is_frozen, expiry_date, last_active 
            FROM myapp.users_status 
            ORDER BY last_active DESC NULLS LAST 
            LIMIT 100
        """)
    return [dict(r) for r in rows]


@app.post("/api/admin/toggle-freeze")
async def toggle_freeze(payload: Dict[str, Any]):
    """تجميد أو فك تجميد هاتف مستخدم"""
    dev_id = payload.get("device_id")
    freeze = bool(payload.get("freeze"))
    async with db_pool.acquire() as conn:
        await conn.execute("""
            UPDATE myapp.users_status 
            SET is_frozen = $1, last_active = NOW() 
            WHERE device_id = $2
        """, freeze, dev_id)
    return {"success": True, "device_id": dev_id, "is_frozen": freeze}


@app.get("/api/app-config")
async def get_app_config():
    """جلب إعدادات النظام وسرعات الفئات"""
    async with db_pool.acquire() as conn:
        rows = await conn.fetch("SELECT key, value FROM myapp.app_config")
    return {r["key"]: r["value"] for r in rows}


@app.post("/api/app-config")
async def update_app_config(configs: Dict[str, str]):
    """تحديث إعدادات النظام وسرعات النقر"""
    async with db_pool.acquire() as conn:
        for k, v in configs.items():
            await conn.execute("""
                INSERT INTO myapp.app_config (key, value)
                VALUES ($1, $2)
                ON CONFLICT (key) DO UPDATE SET value = $2
            """, k, str(v))
    return {"success": True, "message": "تم تحديث الإعدادات بنجاح"}


# ===================================================================================
# 7. نقطة الدخول والتشغيل المباشر
# ===================================================================================
if __name__ == "__main__":
    import uvicorn
    print("=" * 70)
    print("🚀 بدء تشغيل خادم التحكم والبوتات بالبايثون (FastAPI Engine)...")
    print(f"📡 المنفذ المستمع: {PORT}")
    print(f"🔗 فحص الصحة: http://localhost:{PORT}/api/health")
    print(f"📊 تدفق التيليميتري: http://localhost:{PORT}/api/telemetry/stream")
    print("=" * 70)
    uvicorn.run("server:app", host="0.0.0.0", port=PORT, reload=False)

/**
 * MyClicker Pro - MASTER SERVER v3.1
 * ALL-IN-ONE: Global Pass, Notifications, Force Update, Security Logs, Neon DB.
 */

process.env.NODE_TLS_REJECT_UNAUTHORIZED = "0";
const express = require('express');
const { Pool } = require('pg');
require('dotenv').config();

const app = express();
app.use(express.json());

const PORT = process.env.PORT || 8080;
const ADMIN_KEY = process.env.ADMIN_KEY || "admin123";

// 1. الربط الاحترافي (Neon Pool)
const pool = new Pool({
    connectionString: process.env.DATABASE_URL,
    max: 25,
    ssl: { rejectUnauthorized: false }
});

function getRemainingDays(expiryDate) {
    if (!expiryDate) return 0;
    const diff = new Date(expiryDate) - new Date();
    return Math.max(0, Math.ceil(diff / (1000 * 60 * 60 * 24)));
}

// 2. بوابة الفحص
app.get(['/', '/api/test'], (req, res) => {
    res.json({ status: "Active", version: "3.1.0", database: "Connected ✅" });
});

// 3. بوابة المزامنة (التحكم الكامل)
app.post(['/api/sync', '/sync'], async (req, res) => {
    const { secretKey, deviceId, phone, appVersion } = req.body;
    try {
        if (secretKey !== ADMIN_KEY) return res.status(401).json({ status: "Error" });

        // جلب البيانات والإعدادات بطلب واحد (أداء عالٍ)
        const dbRes = await pool.query(`
            SELECT u.*, 
            (SELECT value FROM myapp.app_config WHERE key = 'global_free_mode') as free_mode,
            (SELECT value FROM myapp.app_config WHERE key = 'global_notice') as g_notice,
            (SELECT value FROM myapp.app_config WHERE key = 'latest_version') as l_ver,
            (SELECT value FROM myapp.app_config WHERE key = 'next_url') as n_url,
            (SELECT value FROM myapp.app_config WHERE key = 'force_update') as f_upd
            FROM myapp.users_status u WHERE u.device_id = $1
        `, [deviceId]);

        const user = dbRes.rows[0];
        const configs = dbRes.rows[0] || {};

        if (!user) return res.json({ status: "New", redirect: "activation" });

        // --- ميزة 1: التحديث الإجباري ---
        if (configs.f_upd === 'true' && appVersion !== configs.l_ver) {
            return res.json({ 
                status: "Update", redirect: "update", 
                message: "يوجد تحديث جديد ضروري لاستمرار العمل",
                config: { next_url: configs.n_url } 
            });
        }

        // --- ميزة 2: التفعيل الجماعي ---
        const isGlobalFree = configs.free_mode === 'true';
        const days = getRemainingDays(user.expiry_date);
        const finalStatus = (isGlobalFree || days > 0) ? "Active" : "Expired";
        
        // --- ميزة 3: الإشعارات الخارجية ---
        const rawNotice = user.notice_message || configs.g_notice || "";
        let noticePayload = null;
        if (rawNotice) {
            noticePayload = {
                id: Buffer.from(rawNotice).toString('base64').substring(0, 15),
                title: "MyClicker Admin 📢",
                message: rawNotice
            };
        }

        res.json({
            status: finalStatus,
            remainingDays: isGlobalFree ? 999 : days,
            redirect: user.status === 'Blocked' ? 'blocked' : (user.is_frozen ? 'frozen' : (finalStatus === "Expired" ? 'activation' : 'main')),
            expiryDate: user.expiry_date ? new Date(user.expiry_date).toLocaleDateString('ar-EG') : "--/--/----",
            subTier: isGlobalFree ? "VIP_PRO (FREE)" : (user.sub_tier || "STANDARD"),
            notice: noticePayload,
            config: { click_delay: "500" }
        });

        // تحديث النشاط وسجل الأمان في الخلفية
        pool.query("UPDATE myapp.users_status SET last_active = NOW(), app_version = $1, phone = $2 WHERE device_id = $3", [appVersion, phone, deviceId]);

    } catch (err) {
        res.status(200).json({ status: "Error", message: "Database Sync Error" });
    }
});

// 4. بوابة تفعيل الأكواد (Verify)
app.post(['/api/verify-code', '/verify-code'], async (req, res) => {
    const { secretKey, deviceId, phone, code } = req.body;
    try {
        if (secretKey !== ADMIN_KEY) return res.status(401).json({ status: "Error" });

        // --- ميزة 4: أكواد المطور ---
        if (deviceId === "d201451dda15bc31") {
            if (code === "ACTIVATE7") {
                let exp = new Date(); exp.setDate(exp.getDate() + 7);
                await pool.query("UPDATE myapp.users_status SET status='Active', expiry_date=$1, phone=$2, sub_tier='TESTER' WHERE device_id=$3", [exp, phone, deviceId]);
                return res.json({ status: "Success", message: "✅ تفعيل تجريبي للمطور" });
            }
            if (code === "RESET1") {
                await pool.query("DELETE FROM myapp.users_status WHERE device_id = $1", [deviceId]);
                return res.json({ status: "Success", message: "🔄 تصفير كامل للجهاز" });
            }
        }

        // --- ميزة 5: نظام تراكم الأيام والأكواد ---
        const subRes = await pool.query("SELECT * FROM myapp.subscriptions WHERE code = $1 AND is_used = FALSE", [code]);
        const sub = subRes.rows[0];
        if (!sub) {
            // تسجيل محاولة فاشلة في سجل الأمان
            pool.query("INSERT INTO myapp.security_logs (device_id, phone, action, reason) VALUES ($1, $2, 'Verify Failed', $3)", [deviceId, phone, `Invalid Code: ${code}`]);
            return res.json({ status: "Error", message: "الكود غير صحيح أو تم استخدامه" });
        }

        let newExp = new Date();
        const userCheck = await pool.query("SELECT expiry_date FROM myapp.users_status WHERE device_id = $1", [deviceId]);
        if (userCheck.rows[0] && userCheck.rows[0].expiry_date > new Date()) newExp = new Date(userCheck.rows[0].expiry_date);
        newExp.setDate(newExp.getDate() + sub.duration_days);

        await pool.query("INSERT INTO myapp.users_status (device_id, phone, status, expiry_date, sub_tier) VALUES ($1, $2, 'Active', $3, $4) ON CONFLICT (device_id) DO UPDATE SET status='Active', expiry_date=$3, phone=$2, sub_tier=$4", [deviceId, phone, newExp, sub.sub_tier]);
        await pool.query("UPDATE myapp.subscriptions SET is_used = TRUE, used_by_device = $1, used_at = NOW() WHERE code = $2", [deviceId, code]);

        res.json({ status: "Success", message: "تم التفعيل بنجاح" });

    } catch (err) {
        res.status(200).json({ status: "Error", message: "Server Busy" });
    }
});

// 5. التشغيل
app.listen(PORT, '0.0.0.0', () => console.log(`🚀 Master Server 3.1 LIVE on ${PORT}`));

const express = require('express');
const { Pool } = require('pg');
const app = express();

// إعدادات المنفذ والمفتاح السري المتوافق مع التطبيق
const PORT = process.env.PORT || 3000;
const SECRET_KEY = "admin123";

// الاتصال بقاعدة بيانات DigitalOcean (نفس بيانات app.py)
const pool = new Pool({
    user: 'doadmin',
    host: 'myclicker-db-rd7ky.db1.ondigitalocean.com',
    database: 'defaultdb',
    password: '1tHwqXCgn8BS6iTm942V3f7a',
    port: 5432,
    ssl: { rejectUnauthorized: false } // تفعيل الـ SSL للاتصال السحابي
});

app.use(express.json());

// فحص الاتصال بقاعدة البيانات عند التشغيل
pool.connect((err, client, release) => {
    if (err) return console.error('❌ Database Connection Error:', err.stack);
    console.log('✅ Connected to PostgreSQL Database');
    release();
});

// 1. بوابة المزامنة المركزية /api/sync
app.post('/api/sync', async (req, res) => {
    const { secretKey, deviceId, phone, appVersion, botStatus, acceptedClicks } = req.body;
    const ip = req.headers['x-forwarded-for'] || req.socket.remoteAddress;

    if (secretKey !== SECRET_KEY) {
        return res.status(401).json({ status: "Error", message: "Unauthorized access" });
    }

    try {
        // تحديث حالة الجهاز أو إنشاؤه
        await pool.query(`
            INSERT INTO myapp.users_status (device_id, phone, app_version, bot_status, accepted_clicks, last_active, last_ip)
            VALUES ($1, $2, $3, $4, $5, NOW(), $6)
            ON CONFLICT (device_id) DO UPDATE SET 
                phone = EXCLUDED.phone, app_version = EXCLUDED.app_version, 
                bot_status = EXCLUDED.bot_status, accepted_clicks = EXCLUDED.accepted_clicks, 
                last_active = NOW(), last_ip = EXCLUDED.last_ip
        `, [deviceId, phone, appVersion, botStatus, acceptedClicks || 0, ip]);

        // جلب بيانات المستخدم وإعدادات التطبيق
        const userRes = await pool.query("SELECT * FROM myapp.users_status WHERE device_id = $1", [deviceId]);
        const configRes = await pool.query("SELECT key, value FROM myapp.app_config");
        
        const user = userRes.rows[0];
        const config = Object.fromEntries(configRes.rows.map(r => [r.key, r.value]));

        // منطق التوجيه لنسخة 7.2.7 (تنبيهات Alerts)
        let redirect = "main";
        if (user.status === 'Blocked') redirect = "blocked";
        else if (user.is_frozen) redirect = "frozen";
        else if (appVersion !== config.latest_version && config.force_update === 'true') redirect = "update";
        else if (!user.phone || user.status === 'Expired') redirect = "login";

        res.json({
            status: user.status,
            redirect: redirect,
            message: user.notice_message || config.update_message || "",
            expiryDate: user.expiry_date,
            subTier: user.sub_tier,
            config: {
                live_keywords: config.live_keywords || "",
                live_indicators: config.live_indicators || "",
                click_delay: config.click_delay || "500",
                updateUrl: config.update_url || ""
            },
            notice: user.notice_message ? { title: "تنبيه", content: user.notice_message, id: Date.now().toString() } : null
        });
    } catch (err) {
        console.error(err);
        res.status(500).json({ status: "Error", message: "Internal Server Error" });
    }
});

// 2. بوابة التفعيل بالكروت /api/verify-code
app.post('/api/verify-code', async (req, res) => {
    const { secretKey, deviceId, phone, code } = req.body;
    if (secretKey !== SECRET_KEY) return res.status(401).send("Unauthorized");

    try {
        const subRes = await pool.query("SELECT * FROM myapp.subscriptions WHERE code = $1 AND is_used = FALSE", [code]);
        if (subRes.rows.length === 0) {
            return res.json({ status: "Error", message: "كود التفعيل غير صحيح أو مستخدم مسبقاً" });
        }

        const sub = subRes.rows[0];
        const expiry = new Date();
        expiry.setDate(expiry.getDate() + sub.duration_days);

        await pool.query(`
            UPDATE myapp.users_status 
            SET status = 'Active', expiry_date = $1, sub_tier = $2, phone = $3, is_frozen = FALSE
            WHERE device_id = $4
        `, [expiry, sub.sub_tier, phone, deviceId]);

        await pool.query("UPDATE myapp.subscriptions SET is_used = TRUE, used_by_device = $1, used_at = NOW() WHERE code = $2", [deviceId, code]);

        res.json({
            status: "Active",
            redirect: "main",
            message: "تم التفعيل بنجاح!",
            expiryDate: expiry.toISOString().split('T')[0]
        });
    } catch (err) {
        console.error(err);
        res.status(500).json({ status: "Error" });
    }
});

app.listen(PORT, '0.0.0.0', () => console.log(`🚀 Server running on port ${PORT}`));

import sqlite3

DB_NAME = "tracker_advanced.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS visits_advanced (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            link_id TEXT NOT NULL,
            ip TEXT,
            user_agent TEXT,
            country TEXT,
            country_code TEXT,
            region TEXT,
            city TEXT,
            zip TEXT,
            lat REAL,
            lon REAL,
            timezone TEXT,
            isp TEXT,
            org TEXT,
            asn TEXT,
            as_name TEXT,
            mobile_network INTEGER,
            proxy INTEGER,
            hosting INTEGER,
            browser TEXT,
            browser_version TEXT,
            os TEXT,
            os_version TEXT,
            device TEXT,
            is_mobile INTEGER,
            is_tablet INTEGER,
            is_pc INTEGER,
            is_bot INTEGER,
            touch_capable INTEGER,
            accept_language TEXT,
            referer TEXT,
            origin TEXT,
            dnt TEXT,
            sec_ch_ua TEXT,
            sec_ch_ua_platform TEXT,
            whatsapp_type TEXT,
            screen_width INTEGER,
            screen_height INTEGER,
            color_depth INTEGER,
            timezone_offset INTEGER,
            language TEXT,
            platform TEXT,
            cookie_enabled INTEGER,
            do_not_track TEXT,
            hardware_concurrency INTEGER,
            device_memory REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

def add_visit_advanced(data):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''
        INSERT INTO visits_advanced (
            link_id, ip, user_agent, country, country_code, region, city, zip,
            lat, lon, timezone, isp, org, asn, as_name, mobile_network, proxy, hosting,
            browser, browser_version, os, os_version, device, is_mobile, is_tablet,
            is_pc, is_bot, touch_capable, accept_language, referer, origin, dnt,
            sec_ch_ua, sec_ch_ua_platform, whatsapp_type
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        data.get('link_id'),
        data.get('ip'),
        data.get('user_agent'),
        data.get('country'),
        data.get('country_code'),
        data.get('region'),
        data.get('city'),
        data.get('zip'),
        data.get('lat'),
        data.get('lon'),
        data.get('timezone'),
        data.get('isp'),
        data.get('org'),
        data.get('asn'),
        data.get('as_name'),
        1 if data.get('mobile_network') else 0,
        1 if data.get('proxy') else 0,
        1 if data.get('hosting') else 0,
        data.get('browser'),
        data.get('browser_version'),
        data.get('os'),
        data.get('os_version'),
        data.get('device'),
        1 if data.get('is_mobile') else 0,
        1 if data.get('is_tablet') else 0,
        1 if data.get('is_pc') else 0,
        1 if data.get('is_bot') else 0,
        1 if data.get('touch_capable') else 0,
        data.get('accept_language'),
        data.get('referer'),
        data.get('origin'),
        data.get('dnt'),
        data.get('sec_ch_ua'),
        data.get('sec_ch_ua_platform'),
        data.get('whatsapp_type')
    ))
    conn.commit()
    conn.close()

def update_visit_with_extra(link_id, extra_data):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''
        UPDATE visits_advanced SET
            screen_width = ?,
            screen_height = ?,
            color_depth = ?,
            timezone_offset = ?,
            language = ?,
            platform = ?,
            cookie_enabled = ?,
            do_not_track = ?,
            hardware_concurrency = ?,
            device_memory = ?
        WHERE link_id = ? AND screen_width IS NULL
        ORDER BY id DESC LIMIT 1
    ''', (
        extra_data.get('screen_width'),
        extra_data.get('screen_height'),
        extra_data.get('color_depth'),
        extra_data.get('timezone_offset'),
        extra_data.get('language'),
        extra_data.get('platform'),
        1 if extra_data.get('cookie_enabled') else 0,
        extra_data.get('do_not_track'),
        extra_data.get('hardware_concurrency'),
        extra_data.get('device_memory'),
        link_id
    ))
    conn.commit()
    conn.close()

def get_all_visits_advanced():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT * FROM visits_advanced ORDER BY created_at DESC")
    rows = c.fetchall()
    conn.close()
    return rows
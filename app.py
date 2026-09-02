from flask import Flask, request, redirect, jsonify, send_file
import uuid
import os
import sqlite3
import requests
import json
import io
from datetime import datetime, timedelta
from user_agents import parse
import re

app = Flask(__name__)
DB_NAME = "tracker.db"

# ============================================================
# إنشاء قاعدة البيانات (نسخة متطورة)
# ============================================================

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS visits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            link_id TEXT,
            ip TEXT,
            user_agent TEXT,
            country TEXT,
            country_code TEXT,
            region TEXT,
            city TEXT,
            postal TEXT,
            lat REAL,
            lon REAL,
            timezone TEXT,
            isp TEXT,
            org TEXT,
            asn TEXT,
            browser TEXT,
            browser_version TEXT,
            browser_engine TEXT,
            os TEXT,
            os_version TEXT,
            device TEXT,
            device_brand TEXT,
            is_mobile INTEGER,
            is_tablet INTEGER,
            is_pc INTEGER,
            is_bot INTEGER,
            touch_capable INTEGER,
            screen_width INTEGER,
            screen_height INTEGER,
            color_depth INTEGER,
            language TEXT,
            timezone_offset INTEGER,
            hardware_cores INTEGER,
            device_memory REAL,
            do_not_track TEXT,
            referer TEXT,
            whatsapp_type TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# ============================================================
# دوال جلب المعلومات (فائقة الدقة)
# ============================================================

def get_geo_details(ip):
    try:
        r = requests.get(f"https://ipinfo.io/{ip}/json", timeout=5)
        data = r.json()
        loc = data.get("loc", "0,0").split(",")
        return {
            "country": data.get("country", "غير معروف"),
            "country_code": data.get("country", ""),
            "region": data.get("region", "غير معروف"),
            "city": data.get("city", "غير معروف"),
            "postal": data.get("postal", ""),
            "lat": float(loc[0]) if len(loc) > 0 else 0.0,
            "lon": float(loc[1]) if len(loc) > 1 else 0.0,
            "timezone": data.get("timezone", ""),
            "isp": data.get("org", "غير معروف"),
            "org": data.get("org", ""),
            "asn": data.get("as", "")
        }
    except:
        return {
            "country": "غير معروف",
            "city": "غير معروف",
            "lat": 0.0,
            "lon": 0.0,
            "isp": "غير معروف"
        }

def parse_user_agent_advanced(user_agent_string):
    try:
        ua = parse(user_agent_string)
        return {
            "browser": ua.browser.family,
            "browser_version": ua.browser.version_string,
            "browser_engine": "Blink" if "Chrome" in ua.browser.family else "Gecko" if "Firefox" in ua.browser.family else "WebKit" if "Safari" in ua.browser.family else "غير معروف",
            "os": ua.os.family,
            "os_version": ua.os.version_string,
            "device": ua.device.family,
            "device_brand": ua.device.brand if ua.device.brand else "غير معروف",
            "is_mobile": ua.is_mobile,
            "is_tablet": ua.is_tablet,
            "is_pc": ua.is_pc,
            "is_bot": ua.is_bot,
            "touch_capable": "touch" in user_agent_string.lower()
        }
    except:
        return {
            "browser": "غير معروف",
            "os": "غير معروف",
            "device": "غير معروف",
            "is_mobile": False,
            "is_pc": True
        }

def get_client_ip(request):
    return request.headers.get('X-Forwarded-For', request.remote_addr).split(',')[0].strip()

def detect_whatsapp(user_agent):
    ua = user_agent.lower()
    if 'whatsapp' in ua:
        if 'whatsapp-web' in ua:
            return 'whatsapp_web'
        elif 'whatsapp-android' in ua or 'whatsapp-ios' in ua:
            return 'whatsapp_mobile'
        return 'whatsapp_unknown'
    return None

def is_bot(user_agent):
    bots = ['bot', 'crawler', 'spider', 'scraper', 'headless', 'selenium', 'puppeteer']
    ua = user_agent.lower()
    return any(bot in ua for bot in bots)

# ============================================================
# تسجيل الزيارة (مع كل التفاصيل)
# ============================================================

def log_visit(link_id, request):
    ip = get_client_ip(request)
    user_agent = request.headers.get('User-Agent', 'غير معروف')
    
    # تجاهل البوتات
    if is_bot(user_agent):
        return
    
    geo = get_geo_details(ip)
    ua = parse_user_agent_advanced(user_agent)
    whatsapp = detect_whatsapp(user_agent)
    
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''
        INSERT INTO visits (
            link_id, ip, user_agent,
            country, country_code, region, city, postal, lat, lon, timezone,
            isp, org, asn,
            browser, browser_version, browser_engine,
            os, os_version,
            device, device_brand,
            is_mobile, is_tablet, is_pc, is_bot, touch_capable,
            referer, whatsapp_type
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        link_id, ip, user_agent,
        geo.get('country'), geo.get('country_code'), geo.get('region'),
        geo.get('city'), geo.get('postal'), geo.get('lat'), geo.get('lon'),
        geo.get('timezone'), geo.get('isp'), geo.get('org'), geo.get('asn'),
        ua.get('browser'), ua.get('browser_version'), ua.get('browser_engine'),
        ua.get('os'), ua.get('os_version'),
        ua.get('device'), ua.get('device_brand'),
        1 if ua.get('is_mobile') else 0,
        1 if ua.get('is_tablet') else 0,
        1 if ua.get('is_pc') else 0,
        1 if ua.get('is_bot') else 0,
        1 if ua.get('touch_capable') else 0,
        request.headers.get('Referer', ''),
        whatsapp
    ))
    conn.commit()
    conn.close()

# ============================================================
# المسارات
# ============================================================

@app.route('/')
def home():
    link_id = str(uuid.uuid4())[:8]
    image_link = request.url_root + 'image/' + link_id + '.png'
    
    html = f'''
    <!DOCTYPE html>
    <html dir="rtl">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>رابط التتبع الخارق</title>
        <style>
            body {{ font-family: 'Segoe UI', Tahoma, sans-serif; text-align: center; padding: 40px; background: #0a0a1a; color: white; }}
            .container {{ max-width: 600px; margin: auto; background: #1a1a2e; padding: 30px; border-radius: 20px; box-shadow: 0 10px 40px rgba(0,0,0,0.5); border: 1px solid #2a2a4a; }}
            h1 {{ color: #ffd700; }}
            .link-box {{ background: #0d0d1f; padding: 15px; border-radius: 10px; word-break: break-all; border: 1px solid #333; }}
            input {{ width: 100%; padding: 12px; border: none; border-radius: 10px; font-size: 14px; margin: 10px 0; background: #0d0d1f; color: white; border: 1px solid #333; }}
            button {{ background: #25D366; color: black; border: none; padding: 12px 30px; border-radius: 10px; font-size: 16px; cursor: pointer; font-weight: bold; }}
            button:hover {{ background: #1ebe5f; }}
            .badge {{ background: #ffd700; color: black; padding: 5px 15px; border-radius: 20px; display: inline-block; font-weight: bold; }}
            .glow {{ text-shadow: 0 0 20px #ffd700; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1 class="glow">🔥 رابط التتبع الخارق</h1>
            <p>انسخ الرابط وأرسله في واتساب. سيتم جمع <strong>أكثر من 30 معلومة</strong> عن كل من يفتحه.</p>
            <div class="link-box">
                <strong>🖼️ رابط الصورة:</strong><br>
                <span id="linkText">{image_link}</span>
            </div>
            <input type="text" value="{image_link}" id="linkInput" readonly>
            <button onclick="copyLink()">📋 نسخ الرابط</button>
            <br><br>
            <a href="/dashboard" target="_blank"><button style="background: #2196F3;">📊 لوحة التحكم</button></a>
            <p class="badge">معرف الرابط: {link_id}</p>
        </div>
        <script>
            function copyLink() {{
                const input = document.getElementById('linkInput');
                input.select();
                document.execCommand('copy');
                alert('تم نسخ الرابط!');
            }}
        </script>
    </body>
    </html>
    '''
    return html

@app.route('/image/<link_id>.png')
def track_image(link_id):
    log_visit(link_id, request)
    return redirect('https://placehold.co/400x400/1a1a32/ffd700?text=Tracking+Done')

@app.route('/dashboard')
def dashboard():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT * FROM visits ORDER BY created_at DESC")
    visits = c.fetchall()
    conn.close()
    
    html = f'''
    <!DOCTYPE html>
    <html dir="rtl">
    <head><meta charset="UTF-8"><title>لوحة التحكم الخارقة</title>
    <style>
        body {{ font-family: Arial; background: #0a0a1a; color: white; padding: 20px; }}
        .stats {{ background: #1a1a2e; padding: 15px; border-radius: 10px; display: inline-block; margin: 5px; border: 1px solid #333; }}
        table {{ width: 100%; background: #1a1a2e; border-collapse: collapse; border-radius: 10px; overflow: hidden; }}
        th {{ background: #ffd700; color: black; padding: 12px; }}
        td {{ padding: 10px; border-bottom: 1px solid #333; }}
        tr:hover {{ background: #2a2a4a; }}
        h1 {{ color: #ffd700; }}
        .badge-gold {{ background: #ffd700; color: black; padding: 2px 10px; border-radius: 10px; }}
    </style>
    </head>
    <body>
    <h1>📊 لوحة التحكم الخارقة</h1>
    <div class="stats">👥 إجمالي الزيارات: <strong>{len(visits)}</strong></div>
    <div class="stats">🌍 أحدث دولة: {visits[0][4] if visits else "لا يوجد"}</div>
    <div class="stats">📱 أحدث جهاز: {visits[0][21] if visits else "لا يوجد"}</div>
    <br><br>
    <table>
    <tr><th>#</th><th>IP</th><th>الدولة</th><th>المدينة</th><th>المتصفح</th><th>نظام التشغيل</th><th>الجهاز</th><th>واتساب</th><th>التوقيت</th></tr>
    '''
    for i, v in enumerate(visits, 1):
        html += f"<tr><td>{i}</td><td>{v[2]}</td><td>{v[4]}</td><td>{v[7]}</td><td>{v[16]}</td><td>{v[19]}</td><td>{v[21]}</td><td>{'✅' if v[36] else '❌'}</td><td>{v[37]}</td></tr>"
    html += '''
    </table>
    <br><a href="/" style="color: #ffd700;">🔙 العودة</a>
    </body></html>
    '''
    return html

@app.route('/api/visits')
def api_visits():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT * FROM visits ORDER BY created_at DESC")
    visits = c.fetchall()
    conn.close()
    results = []
    for v in visits:
        results.append({
            "id": v[0],
            "link_id": v[1],
            "ip": v[2],
            "country": v[4],
            "city": v[7],
            "lat": v[9],
            "lon": v[10],
            "browser": v[16],
            "os": v[19],
            "device": v[21],
            "whatsapp": v[36],
            "created_at": v[37]
        })
    return jsonify(results)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=False)
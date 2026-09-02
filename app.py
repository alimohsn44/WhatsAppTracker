from flask import Flask, request, render_template, redirect, jsonify, send_file
import uuid
import os
import sqlite3
import requests
import json
from datetime import datetime
from user_agents import parse
import io

app = Flask(__name__)
DB_NAME = "tracker.db"

# ============================================================
# إنشاء قاعدة البيانات الجديدة (مع كل الأعمدة)
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
# دوال مساعدة
# ============================================================

def get_geo(ip):
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

def get_client_ip(request):
    return request.headers.get('X-Forwarded-For', request.remote_addr).split(',')[0].strip()

def detect_whatsapp(user_agent):
    ua = user_agent.lower()
    if 'whatsapp' in ua:
        return 'whatsapp'
    return None

def parse_ua(user_agent):
    try:
        ua = parse(user_agent)
        return {
            "browser": ua.browser.family,
            "browser_version": ua.browser.version_string,
            "os": ua.os.family,
            "os_version": ua.os.version_string,
            "device": ua.device.family,
            "device_brand": ua.device.brand or "غير معروف",
            "is_mobile": ua.is_mobile,
            "is_tablet": ua.is_tablet,
            "is_pc": ua.is_pc,
            "is_bot": ua.is_bot,
            "touch_capable": "touch" in user_agent.lower()
        }
    except:
        return {
            "browser": "غير معروف",
            "os": "غير معروف",
            "device": "غير معروف",
            "is_mobile": False,
            "is_pc": True
        }

# ============================================================
# تسجيل الزيارة
# ============================================================

def log_visit(link_id, request):
    ip = get_client_ip(request)
    user_agent = request.headers.get('User-Agent', 'غير معروف')
    geo = get_geo(ip)
    ua = parse_ua(user_agent)
    whatsapp = detect_whatsapp(user_agent)
    
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''
        INSERT INTO visits (
            link_id, ip, user_agent,
            country, country_code, region, city, postal, lat, lon, timezone,
            isp, org, asn,
            browser, browser_version,
            os, os_version,
            device, device_brand,
            is_mobile, is_tablet, is_pc, is_bot, touch_capable,
            referer, whatsapp_type
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        link_id, ip, user_agent,
        geo.get('country'), geo.get('country_code'), geo.get('region'),
        geo.get('city'), geo.get('postal'), geo.get('lat'), geo.get('lon'),
        geo.get('timezone'), geo.get('isp'), geo.get('org'), geo.get('asn'),
        ua.get('browser'), ua.get('browser_version'),
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
    return render_template('index.html', image_link=image_link, link_id=link_id)

@app.route('/image/<link_id>.png')
def track_image(link_id):
    log_visit(link_id, request)
    return redirect('https://placehold.co/400x400/1a1a32/ffffff?text=Tracking+Done')

@app.route('/dashboard')
def dashboard():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT * FROM visits ORDER BY created_at DESC")
    visits = c.fetchall()
    conn.close()
    
    html = """
    <!DOCTYPE html>
    <html dir="rtl">
    <head><meta charset="UTF-8"><title>لوحة التحكم</title>
    <style>
        body { font-family: Arial; background: #f0f2f5; padding: 20px; }
        .stats { background: white; padding: 15px; border-radius: 10px; display: inline-block; margin: 5px; }
        table { width: 100%; background: white; border-collapse: collapse; border-radius: 10px; overflow: hidden; }
        th { background: #1a237e; color: white; padding: 10px; }
        td { padding: 8px; border-bottom: 1px solid #eee; }
        tr:hover { background: #f5f5f5; }
    </style>
    </head>
    <body>
    <h1>📊 لوحة التحكم</h1>
    <div class="stats">👥 إجمالي الزيارات: <strong>""" + str(len(visits)) + """</strong></div>
    <br><br>
    <table>
    <tr><th>#</th><th>IP</th><th>الدولة</th><th>المدينة</th><th>المتصفح</th><th>نظام التشغيل</th><th>الجهاز</th><th>واتساب</th><th>التوقيت</th></tr>
    """
    for i, v in enumerate(visits, 1):
        html += f"<tr><td>{i}</td><td>{v[2]}</td><td>{v[4]}</td><td>{v[7]}</td><td>{v[16]}</td><td>{v[18]}</td><td>{v[20]}</td><td>{'✅' if v[35] else '❌'}</td><td>{v[36]}</td></tr>"
    html += """
    </table>
    <br><a href="/">🔙 العودة</a>
    </body></html>
    """
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
            "os": v[18],
            "device": v[20],
            "whatsapp": v[35],
            "created_at": v[36]
        })
    return jsonify(results)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=False)
from flask import Flask, request, render_template, redirect, jsonify, send_file
import uuid
import os
import sqlite3
import requests
import json
from datetime import datetime
from user_agents import parse
import io
from PIL import Image, ImageDraw

app = Flask(__name__)
DB_NAME = "tracker_advanced.db"

# ============================================================
# إعداد قاعدة البيانات المتطورة
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
# دوال جلب المعلومات فائقة الدقة
# ============================================================

def get_geo_details(ip):
    try:
        # استخدام ipinfo.io للحصول على معلومات أكثر دقة
        r = requests.get(f"https://ipinfo.io/{ip}/json", timeout=5)
        data = r.json()
        location = data.get("loc", "0,0").split(",")
        return {
            "country": data.get("country", "غير معروف"),
            "country_code": data.get("country", ""),
            "region": data.get("region", "غير معروف"),
            "city": data.get("city", "غير معروف"),
            "postal": data.get("postal", ""),
            "lat": float(location[0]) if len(location) > 0 else 0.0,
            "lon": float(location[1]) if len(location) > 1 else 0.0,
            "timezone": data.get("timezone", ""),
            "isp": data.get("org", "غير معروف"),
            "org": data.get("org", ""),
            "asn": data.get("as", ""),
        }
    except Exception as e:
        # استخدام ip-api.com كبديل إذا فشلت ipinfo
        try:
            r = requests.get(f"http://ip-api.com/json/{ip}?fields=status,country,countryCode,region,regionName,city,zip,lat,lon,timezone,isp,org,as", timeout=5)
            data = r.json()
            if data.get("status") == "success":
                return {
                    "country": data.get("country", "غير معروف"),
                    "country_code": data.get("countryCode", ""),
                    "region": data.get("regionName", "غير معروف"),
                    "city": data.get("city", "غير معروف"),
                    "postal": data.get("zip", ""),
                    "lat": data.get("lat", 0.0),
                    "lon": data.get("lon", 0.0),
                    "timezone": data.get("timezone", ""),
                    "isp": data.get("isp", "غير معروف"),
                    "org": data.get("org", ""),
                    "asn": data.get("as", ""),
                }
        except:
            pass
    return {
        "country": "غير معروف",
        "country_code": "",
        "region": "غير معروف",
        "city": "غير معروف",
        "postal": "",
        "lat": 0.0,
        "lon": 0.0,
        "timezone": "",
        "isp": "غير معروف",
        "org": "",
        "asn": ""
    }

def parse_user_agent_advanced(user_agent_string):
    try:
        ua = parse(user_agent_string)
        return {
            "browser": ua.browser.family,
            "browser_version": ua.browser.version_string,
            "browser_engine": ua.browser.family,  # تقريبي
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
            "browser_version": "",
            "browser_engine": "",
            "os": "غير معروف",
            "os_version": "",
            "device": "غير معروف",
            "device_brand": "غير معروف",
            "is_mobile": False,
            "is_tablet": False,
            "is_pc": True,
            "is_bot": False,
            "touch_capable": False
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

# ============================================================
# تسجيل الزيارة بكل التفاصيل
# ============================================================

def log_visit(link_id, request, extra_data=None):
    ip = get_client_ip(request)
    user_agent = request.headers.get('User-Agent', 'غير معروف')
    geo = get_geo_details(ip)
    ua_info = parse_user_agent_advanced(user_agent)
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
            screen_width, screen_height, color_depth,
            language, timezone_offset,
            hardware_cores, device_memory,
            do_not_track, referer, whatsapp_type
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        link_id, ip, user_agent,
        geo.get('country'), geo.get('country_code'), geo.get('region'),
        geo.get('city'), geo.get('postal'), geo.get('lat'), geo.get('lon'),
        geo.get('timezone'), geo.get('isp'), geo.get('org'), geo.get('asn'),
        ua_info.get('browser'), ua_info.get('browser_version'), ua_info.get('browser_engine'),
        ua_info.get('os'), ua_info.get('os_version'),
        ua_info.get('device'), ua_info.get('device_brand'),
        1 if ua_info.get('is_mobile') else 0,
        1 if ua_info.get('is_tablet') else 0,
        1 if ua_info.get('is_pc') else 0,
        1 if ua_info.get('is_bot') else 0,
        1 if ua_info.get('touch_capable') else 0,
        extra_data.get('screen_width') if extra_data else None,
        extra_data.get('screen_height') if extra_data else None,
        extra_data.get('color_depth') if extra_data else None,
        extra_data.get('language') if extra_data else None,
        extra_data.get('timezone_offset') if extra_data else None,
        extra_data.get('hardware_cores') if extra_data else None,
        extra_data.get('device_memory') if extra_data else None,
        extra_data.get('do_not_track') if extra_data else None,
        request.headers.get('Referer', ''),
        whatsapp
    ))
    conn.commit()
    conn.close()
    return {"status": "ok"}

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
    # جمع معلومات إضافية من request headers
    extra = {
        "screen_width": request.args.get('sw'),
        "screen_height": request.args.get('sh'),
        "color_depth": request.args.get('cd'),
        "language": request.args.get('lang'),
        "timezone_offset": request.args.get('tz'),
        "hardware_cores": request.args.get('cores'),
        "device_memory": request.args.get('mem'),
        "do_not_track": request.headers.get('DNT')
    }
    log_visit(link_id, request, extra)
    
    # إنشاء صورة محلية بدلاً من الاعتماد على خدمة خارجية
    try:
        from PIL import Image, ImageDraw, ImageFont
        img = Image.new('RGB', (400, 400), color=(30, 30, 50))
        draw = ImageDraw.Draw(img)
        draw.rectangle([50, 50, 350, 350], outline=(255, 200, 100), width=3)
        draw.text((100, 150), "🔒", fill=(255, 255, 255))
        draw.text((100, 200), "Secure Connection", fill=(200, 200, 200))
        draw.text((80, 250), "Loading...", fill=(150, 150, 150))
        img_io = io.BytesIO()
        img.save(img_io, 'PNG')
        img_io.seek(0)
        return send_file(img_io, mimetype='image/png')
    except:
        # إذا فشلت مكتبة PIL، استخدم صورة خارجية
        return redirect('https://placehold.co/400x400/1a1a32/ffffff?text=Tracking+Done')

@app.route('/dashboard')
def dashboard():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT * FROM visits ORDER BY created_at DESC")
    visits = c.fetchall()
    conn.close()
    
    # عرض بسيط مع إحصائيات
    html = """
    <!DOCTYPE html>
    <html dir="rtl">
    <head><meta charset="UTF-8"><title>لوحة التحكم المتطورة</title>
    <style>
        body { font-family: Arial; background: #f0f2f5; padding: 20px; }
        .stats { background: white; padding: 15px; border-radius: 10px; margin: 10px 0; display: inline-block; }
        table { width: 100%; background: white; border-collapse: collapse; border-radius: 10px; overflow: hidden; }
        th { background: #1a237e; color: white; padding: 10px; }
        td { padding: 8px; border-bottom: 1px solid #eee; }
        tr:hover { background: #f5f5f5; }
    </style>
    </head>
    <body>
    <h1>📊 لوحة التحكم المتطورة</h1>
    <div class="stats">👥 إجمالي الزيارات: <strong>""" + str(len(visits)) + """</strong></div>
    <div class="stats">🌍 أحدث دولة: """ + (visits[0][4] if visits else "لا يوجد") + """</div>
    <br><br>
    <table>
    <tr><th>#</th><th>IP</th><th>الدولة</th><th>المدينة</th><th>المتصفح</th><th>نظام التشغيل</th><th>الجهاز</th><th>واتساب</th><th>التوقيت</th></tr>
    """
    for i, v in enumerate(visits, 1):
        html += f"<tr><td>{i}</td><td>{v[2]}</td><td>{v[4]}</td><td>{v[7]}</td><td>{v[16]}</td><td>{v[19]}</td><td>{v[21]}</td><td>{'✅' if v[35] else '❌'}</td><td>{v[36]}</td></tr>"
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
            "id": v[0], "link_id": v[1], "ip": v[2],
            "country": v[4], "city": v[7], "lat": v[9], "lon": v[10],
            "browser": v[16], "os": v[19], "device": v[21],
            "whatsapp": v[35], "created_at": v[36]
        })
    return jsonify(results)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=False)
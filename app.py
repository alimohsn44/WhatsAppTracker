from flask import Flask, request, redirect, jsonify, render_template_string
import uuid
import os
import sqlite3
import requests
import json
from datetime import datetime
from user_agents import parse
import statistics

app = Flask(__name__)
DB_NAME = "tracker_super.db"

# ============================================================
# إنشاء قاعدة البيانات (نسخة فائقة الدقة)
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
            lat_accurate REAL,
            lon_accurate REAL,
            accuracy INTEGER,
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
            referer TEXT,
            whatsapp_type TEXT,
            is_vpn INTEGER,
            risk_score INTEGER,
            visitor_type TEXT,
            location_source TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# ============================================================
# دالة get_geo_super (فائقة الدقة)
# ============================================================

def get_geo_super(ip):
    """جلب الموقع من 3 خدمات مع حساب دقة الموقع"""
    results = []
    
    # 1. ipinfo.io
    try:
        r = requests.get(f"https://ipinfo.io/{ip}/json", timeout=5)
        if r.status_code == 200:
            data = r.json()
            loc = data.get("loc", "0,0").split(",")
            results.append({
                "lat": float(loc[0]) if len(loc) > 0 else 0,
                "lon": float(loc[1]) if len(loc) > 1 else 0,
                "country": data.get("country", ""),
                "city": data.get("city", ""),
                "region": data.get("region", ""),
                "source": "ipinfo"
            })
    except:
        pass
    
    # 2. ip-api.com
    try:
        r = requests.get(f"http://ip-api.com/json/{ip}?fields=status,country,regionName,city,zip,lat,lon,timezone,isp,org,as", timeout=5)
        if r.status_code == 200:
            data = r.json()
            if data.get("status") == "success":
                results.append({
                    "lat": data.get("lat", 0),
                    "lon": data.get("lon", 0),
                    "country": data.get("country", ""),
                    "city": data.get("city", ""),
                    "region": data.get("regionName", ""),
                    "source": "ip-api"
                })
    except:
        pass
    
    # 3. ipgeolocation.io
    try:
        api_key = "4e9c90d3228e496faeb44e94ce6037b0"  # ضع مفتاحك هنا
        if api_key != "4e9c90d3228e496faeb44e94ce6037b0":
            r = requests.get(f"https://api.ipgeolocation.io/ipgeo?apiKey={api_key}&ip={ip}", timeout=5)
            if r.status_code == 200:
                data = r.json()
                results.append({
                    "lat": float(data.get("latitude", 0)),
                    "lon": float(data.get("longitude", 0)),
                    "country": data.get("country_name", ""),
                    "city": data.get("city", ""),
                    "region": data.get("state_prov", ""),
                    "source": "ipgeolocation"
                })
    except:
        pass
    
    if not results:
        return {
            "lat": 0.0,
            "lon": 0.0,
            "country": "غير معروف",
            "city": "غير معروف",
            "region": "غير معروف",
            "source": "لا يوجد",
            "accuracy": 0
        }
    
    # حساب متوسط الإحداثيات
    lats = [r["lat"] for r in results if r["lat"] != 0]
    lons = [r["lon"] for r in results if r["lon"] != 0]
    
    avg_lat = sum(lats) / len(lats) if lats else 0
    avg_lon = sum(lons) / len(lons) if lons else 0
    
    # حساب الدقة
    if len(results) >= 3:
        try:
            lat_std = statistics.stdev(lats) if len(lats) > 1 else 0
            lon_std = statistics.stdev(lons) if len(lons) > 1 else 0
            avg_error = (lat_std + lon_std) / 2
            accuracy = max(0, min(100, 100 - (avg_error * 100)))
        except:
            accuracy = 75
    elif len(results) == 2:
        accuracy = 50
    else:
        accuracy = 30
    
    # اختيار أفضل مصدر للمعلومات الإضافية
    best_source = results[0]
    for r in results:
        if r.get("city") and r["city"] not in ["", "غير معروف"]:
            best_source = r
            break
    
    return {
        "lat": avg_lat,
        "lon": avg_lon,
        "country": best_source.get("country", "غير معروف"),
        "city": best_source.get("city", "غير معروف"),
        "region": best_source.get("region", "غير معروف"),
        "source": ", ".join([r.get("source", "") for r in results]),
        "accuracy": int(accuracy)
    }

# ============================================================
# دالة parse_ua (تحليل الجهاز بدقة)
# ============================================================

def parse_ua(user_agent):
    """تحليل User-Agent مع التعرف على الجهاز بدقة"""
    try:
        ua = parse(user_agent)
        
        device_name = ua.device.family or "غير معروف"
        
        # إذا كان الجهاز غير معروف، نحاول استخراجه من النص
        if device_name == "غير معروف" or device_name == "Other":
            ua_lower = user_agent.lower()
            if "iphone" in ua_lower:
                device_name = "iPhone"
            elif "ipad" in ua_lower:
                device_name = "iPad"
            elif "android" in ua_lower and "mobile" in ua_lower:
                device_name = "Android Phone"
            elif "android" in ua_lower:
                device_name = "Android Tablet"
            elif "windows" in ua_lower:
                device_name = "Windows PC"
            elif "macintosh" in ua_lower:
                device_name = "Mac"
            elif "linux" in ua_lower:
                device_name = "Linux PC"
        
        return {
            "browser": ua.browser.family or "غير معروف",
            "browser_version": ua.browser.version_string or "",
            "os": ua.os.family or "غير معروف",
            "os_version": ua.os.version_string or "",
            "device": device_name,
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
# دوال مساعدة أخرى
# ============================================================

def get_client_ip(request):
    return request.headers.get('X-Forwarded-For', request.remote_addr).split(',')[0].strip()

def detect_whatsapp(user_agent):
    return 'whatsapp' in user_agent.lower()

def detect_vpn(ip):
    try:
        r = requests.get(f"https://ipinfo.io/{ip}/json", timeout=3)
        data = r.json()
        org = data.get("org", "").lower()
        keywords = ['vpn', 'proxy', 'hosting', 'cloud', 'data center', 'server']
        return 1 if any(kw in org for kw in keywords) else 0
    except:
        return 0

def get_risk_score(ip, user_agent):
    risk = 0
    if detect_vpn(ip):
        risk += 30
    if "headless" in user_agent.lower():
        risk += 25
    if "bot" in user_agent.lower():
        risk += 20
    return min(risk, 100)

def classify_visitor(user_agent, referer, ip):
    ua = user_agent.lower()
    if "bot" in ua or "crawler" in ua:
        return "بوت"
    if "headless" in ua:
        return "أداة أتمتة"
    if detect_vpn(ip):
        return "مستخدم VPN"
    if "whatsapp" in ua:
        return "واتساب"
    if "google" in referer or "bing" in referer:
        return "محرك بحث"
    return "زائر عادي"

# ============================================================
# تسجيل الزيارة (باستخدام الدوال الجديدة)
# ============================================================

def log_visit(link_id, request):
    ip = get_client_ip(request)
    user_agent = request.headers.get('User-Agent', 'غير معروف')
    
    geo = get_geo_super(ip)
    ua = parse_ua(user_agent)
    whatsapp = detect_whatsapp(user_agent)
    vpn = detect_vpn(ip)
    risk = get_risk_score(ip, user_agent)
    visitor_type = classify_visitor(user_agent, request.headers.get('Referer', ''), ip)
    
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''
        INSERT INTO visits (
            link_id, ip, user_agent,
            country, country_code, region, city, postal,
            lat, lon, lat_accurate, lon_accurate, accuracy,
            timezone, isp, org, asn,
            browser, browser_version,
            os, os_version,
            device, device_brand,
            is_mobile, is_tablet, is_pc, is_bot, touch_capable,
            referer, whatsapp_type,
            is_vpn, risk_score, visitor_type,
            location_source
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        link_id, ip, user_agent,
        geo.get('country'), "", geo.get('region'),
        geo.get('city'), "",
        geo.get('lat'), geo.get('lon'),
        geo.get('lat'), geo.get('lon'),
        geo.get('accuracy'),
        "", geo.get('org'), "", "",
        ua.get('browser'), ua.get('browser_version'),
        ua.get('os'), ua.get('os_version'),
        ua.get('device'), ua.get('device_brand'),
        1 if ua.get('is_mobile') else 0,
        1 if ua.get('is_tablet') else 0,
        1 if ua.get('is_pc') else 0,
        1 if ua.get('is_bot') else 0,
        1 if ua.get('touch_capable') else 0,
        request.headers.get('Referer', ''),
        'whatsapp' if whatsapp else None,
        vpn,
        risk,
        visitor_type,
        geo.get('source')
    ))
    conn.commit()
    conn.close()

# ============================================================
# المسارات
# ============================================================

@app.route('/')
def home():
    link_id = str(uuid.uuid4())[:8]
    image_link = request.url_root + 'i/' + link_id + '.png'
    
    html = f'''
    <!DOCTYPE html>
    <html dir="rtl">
    <head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🔥 رابط فائق الدقة</title>
    <style>
        body {{ font-family: 'Segoe UI', sans-serif; background: #0a0a1a; color: #fff; text-align: center; padding: 50px; }}
        .container {{ max-width: 600px; margin: auto; background: #1a1a2e; padding: 30px; border-radius: 20px; border: 1px solid #2a2a4a; }}
        h1 {{ color: #ffd700; }}
        .link-box {{ background: #0d0d1f; padding: 15px; border-radius: 10px; word-break: break-all; border: 1px solid #333; }}
        input {{ width: 100%; padding: 12px; border: none; border-radius: 10px; background: #0d0d1f; color: #fff; border: 1px solid #333; }}
        .btn {{ padding: 12px 30px; border: none; border-radius: 10px; font-weight: bold; cursor: pointer; margin: 5px; }}
        .btn-green {{ background: #25D366; color: #000; }}
        .btn-blue {{ background: #2196F3; color: #fff; }}
        .badge {{ background: #ffd700; color: #000; padding: 5px 15px; border-radius: 20px; display: inline-block; }}
    </style>
    </head>
    <body>
    <div class="container">
        <h1>🌍 رابط فائق الدقة</h1>
        <p>انسخ الرابط وأرسله في واتساب. يتم تحديد الموقع بدقة عالية جداً.</p>
        <div class="link-box">
            <strong>🖼️ رابط الصورة:</strong><br>
            <span id="linkText">{image_link}</span>
        </div>
        <input type="text" value="{image_link}" id="linkInput" readonly>
        <button class="btn btn-green" onclick="copyLink()">📋 نسخ الرابط</button>
        <br><br>
        <a href="/dashboard" target="_blank"><button class="btn btn-blue">📊 لوحة التحكم</button></a>
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

@app.route('/i/<link_id>.png')
def track_image(link_id):
    log_visit(link_id, request)
    return redirect('https://placehold.co/400x400/1a1a2e/ffd700?text=Tracking+Done')

@app.route('/dashboard')
def dashboard():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT * FROM visits ORDER BY created_at DESC")
    visits = c.fetchall()
    conn.close()
    
    def safe_str(value):
        if value is None:
            return "غير معروف"
        return str(value)
    
    total = len(visits)
    latest_country = safe_str(visits[0][4]) if total > 0 else "لا يوجد"
    latest_city = safe_str(visits[0][7]) if total > 0 else "لا يوجد"
    latest_device = safe_str(visits[0][21]) if total > 0 else "لا يوجد"
    latest_accuracy = safe_str(visits[0][13]) if total > 0 and len(visits[0]) > 13 else "0"
    latest_source = safe_str(visits[0][34]) if total > 0 and len(visits[0]) > 34 else "غير معروف"
    
    html = f'''
    <!DOCTYPE html>
    <html dir="rtl">
    <head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>لوحة التحكم فائقة الدقة</title>
    <style>
        body {{ font-family: Arial; background: #0a0a1a; color: #fff; padding: 20px; }}
        .stats {{ background: #1a1a2e; padding: 15px; border-radius: 10px; display: inline-block; margin: 5px; border: 1px solid #333; }}
        table {{ width: 100%; background: #1a1a2e; border-collapse: collapse; border-radius: 10px; overflow: hidden; font-size: 0.9em; }}
        th {{ background: #ffd700; color: #000; padding: 12px; }}
        td {{ padding: 10px; border-bottom: 1px solid #333; }}
        tr:hover {{ background: #2a2a4a; }}
        h1 {{ color: #ffd700; }}
        .btn-back {{ display: inline-block; margin-top: 20px; padding: 12px 30px; background: #ffd700; color: #000; border-radius: 10px; text-decoration: none; font-weight: bold; }}
        .accuracy-high {{ color: #4CAF50; }}
        .accuracy-medium {{ color: #FF9800; }}
        .accuracy-low {{ color: #f44336; }}
    </style>
    </head>
    <body>
    <h1>📊 لوحة التحكم فائقة الدقة</h1>
    <div class="stats">👥 إجمالي الزيارات: <strong>{total}</strong></div>
    <div class="stats">🌍 الدولة: <strong>{latest_country}</strong></div>
    <div class="stats">🏙️ المدينة: <strong>{latest_city}</strong></div>
    <div class="stats">📱 الجهاز: <strong>{latest_device}</strong></div>
    <div class="stats">📡 الدقة: <strong>{latest_accuracy}%</strong></div>
    <div class="stats">🔍 المصدر: <strong>{latest_source}</strong></div>
    <br><br>
    <table>
    <tr><th>#</th><th>IP</th><th>الدولة</th><th>المدينة</th><th>الإحداثيات</th><th>الدقة</th><th>الجهاز</th><th>VPN</th><th>النوع</th><th>التوقيت</th></tr>
    '''
    for i, v in enumerate(visits, 1):
        lat = safe_str(v[9])
        lon = safe_str(v[10])
        accuracy = safe_str(v[13]) if len(v) > 13 else "0"
        try:
            acc_int = int(accuracy) if accuracy.isdigit() else 0
        except:
            acc_int = 0
        acc_class = "accuracy-high" if acc_int > 70 else "accuracy-medium" if acc_int > 40 else "accuracy-low"
        html += f"""
        <tr>
            <td>{i}</td>
            <td>{safe_str(v[2])}</td>
            <td>{safe_str(v[4])}</td>
            <td>{safe_str(v[7])}</td>
            <td><small>{lat}, {lon}</small></td>
            <td class='{acc_class}'>{accuracy}%</td>
            <td>{safe_str(v[21])}</td>
            <td>{'✅' if v[31] else '❌'}</td>
            <td>{safe_str(v[33]) if len(v) > 33 else 'عادي'}</td>
            <td>{safe_str(v[35]) if len(v) > 35 else '?'}</td>
        </tr>
        """
    html += '''
    </table>
    <br>
    <a href="/" class="btn-back">🔙 العودة للرابط</a>
    </body>
    </html>
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
            "country": v[4] or "غير معروف",
            "city": v[7] or "غير معروف",
            "lat": v[9] or 0,
            "lon": v[10] or 0,
            "lat_accurate": v[11] or 0,
            "lon_accurate": v[12] or 0,
            "accuracy": v[13] or 0,
            "browser": v[17] or "غير معروف",
            "os": v[19] or "غير معروف",
            "device": v[21] or "غير معروف",
            "vpn": bool(v[31]) if len(v) > 31 else False,
            "type": v[33] if len(v) > 33 else "عادي",
            "source": v[34] if len(v) > 34 else "غير معروف",
            "created_at": v[35] if len(v) > 35 else ""
        })
    return jsonify(results)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=False)
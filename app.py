from flask import Flask, request, redirect, jsonify
import uuid
import os
import sqlite3
import requests
from datetime import datetime
from user_agents import parse

app = Flask(__name__)
DB_NAME = "tracker.db"

# ============================================================
# إنشاء قاعدة البيانات
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
            is_vpn INTEGER,
            risk_score INTEGER,
            visitor_type TEXT,
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
            "browser": ua.browser.family or "غير معروف",
            "browser_version": ua.browser.version_string or "",
            "os": ua.os.family or "غير معروف",
            "os_version": ua.os.version_string or "",
            "device": ua.device.family or "غير معروف",
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

def classify_visitor(user_agent, referer):
    ua = user_agent.lower()
    if "bot" in ua or "crawler" in ua:
        return "بوت"
    if "headless" in ua:
        return "أداة أتمتة"
    if detect_vpn(request.remote_addr):
        return "مستخدم VPN"
    if "whatsapp" in ua:
        return "واتساب"
    if "google" in referer or "bing" in referer:
        return "محرك بحث"
    return "زائر عادي"

# ============================================================
# تسجيل الزيارة
# ============================================================

def log_visit(link_id, request):
    ip = get_client_ip(request)
    user_agent = request.headers.get('User-Agent', 'غير معروف')
    geo = get_geo(ip)
    ua = parse_ua(user_agent)
    whatsapp = detect_whatsapp(user_agent)
    vpn = detect_vpn(ip)
    risk = get_risk_score(ip, user_agent)
    visitor_type = classify_visitor(user_agent, request.headers.get('Referer', ''))
    
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
            referer, whatsapp_type,
            is_vpn, risk_score, visitor_type
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        link_id, ip, user_agent,
        geo.get('country'), geo.get('country_code'), geo.get('region'),
        geo.get('city'), geo.get('postal'), geo.get('lat'), geo.get('lon'),
        geo.get('timezone'), geo.get('isp'), geo.get('org'), geo.get('asn'),
        ua.get('browser'), ua.get('browser_version'), "غير معروف",
        ua.get('os'), ua.get('os_version'),
        ua.get('device'), ua.get('device_brand'),
        1 if ua.get('is_mobile') else 0,
        1 if ua.get('is_tablet') else 0,
        1 if ua.get('is_pc') else 0,
        1 if ua.get('is_bot') else 0,
        1 if ua.get('touch_capable') else 0,
        request.headers.get('Referer', ''),
        whatsapp,
        vpn,
        risk,
        visitor_type
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
    <title>🔥 النظام المتطور</title>
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
        <h1>🔥 الرابط المتطور</h1>
        <p>انسخ الرابط وأرسله في واتساب. يتم جمع معلومات دقيقة عن كل زائر.</p>
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
    
    # تحويل القيم الفارغة إلى نصوص آمنة
    def safe_str(value):
        return str(value) if value is not None else "غير معروف"
    
    total = len(visits)
    latest_country = safe_str(visits[0][4]) if total > 0 else "لا يوجد"
    latest_device = safe_str(visits[0][21]) if total > 0 else "لا يوجد"
    latest_risk = safe_str(visits[0][38]) if total > 0 and len(visits[0]) > 38 else "0"
    latest_type = safe_str(visits[0][39]) if total > 0 and len(visits[0]) > 39 else "عادي"
    
    html = f'''
    <!DOCTYPE html>
    <html dir="rtl">
    <head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>لوحة التحكم المتطورة</title>
    <style>
        body {{ font-family: Arial; background: #0a0a1a; color: #fff; padding: 20px; }}
        .stats {{ background: #1a1a2e; padding: 15px; border-radius: 10px; display: inline-block; margin: 5px; border: 1px solid #333; }}
        table {{ width: 100%; background: #1a1a2e; border-collapse: collapse; border-radius: 10px; overflow: hidden; }}
        th {{ background: #ffd700; color: #000; padding: 12px; }}
        td {{ padding: 10px; border-bottom: 1px solid #333; }}
        tr:hover {{ background: #2a2a4a; }}
        h1 {{ color: #ffd700; }}
        .btn-back {{ display: inline-block; margin-top: 20px; padding: 12px 30px; background: #ffd700; color: #000; border-radius: 10px; text-decoration: none; font-weight: bold; }}
        .risk-low {{ background: #4CAF50; color: #fff; padding: 3px 10px; border-radius: 20px; }}
        .risk-medium {{ background: #FF9800; color: #fff; padding: 3px 10px; border-radius: 20px; }}
        .risk-high {{ background: #f44336; color: #fff; padding: 3px 10px; border-radius: 20px; }}
    </style>
    </head>
    <body>
    <h1>📊 لوحة التحكم المتطورة</h1>
    <div class="stats">👥 إجمالي الزيارات: <strong>{total}</strong></div>
    <div class="stats">🌍 أحدث دولة: <strong>{latest_country}</strong></div>
    <div class="stats">📱 أحدث جهاز: <strong>{latest_device}</strong></div>
    <div class="stats">⚡ المخاطر: <strong>{latest_risk}%</strong></div>
    <div class="stats">🏷️ النوع: <strong>{latest_type}</strong></div>
    <br><br>
    <table>
    <tr><th>#</th><th>IP</th><th>الدولة</th><th>المدينة</th><th>المتصفح</th><th>نظام التشغيل</th><th>الجهاز</th><th>VPN</th><th>المخاطر</th><th>النوع</th><th>التوقيت</th></tr>
    '''
    for i, v in enumerate(visits, 1):
        risk = safe_str(v[38]) if len(v) > 38 else "0"
        risk_class = "risk-low" if int(risk) < 30 else "risk-medium" if int(risk) < 60 else "risk-high"
        html += f"""
        <tr>
            <td>{i}</td>
            <td>{safe_str(v[2])}</td>
            <td>{safe_str(v[4])}</td>
            <td>{safe_str(v[7])}</td>
            <td>{safe_str(v[16])}</td>
            <td>{safe_str(v[19])}</td>
            <td>{safe_str(v[21])}</td>
            <td>{'✅' if v[37] else '❌'}</td>
            <td><span class='{risk_class}'>{risk}%</span></td>
            <td>{safe_str(v[39]) if len(v) > 39 else 'عادي'}</td>
            <td>{safe_str(v[40]) if len(v) > 40 else '?'}</td>
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
            "browser": v[16] or "غير معروف",
            "os": v[19] or "غير معروف",
            "device": v[21] or "غير معروف",
            "whatsapp": v[36] or "لا",
            "vpn": bool(v[37]) if len(v) > 37 else False,
            "risk": v[38] if len(v) > 38 else 0,
            "type": v[39] if len(v) > 39 else "عادي",
            "created_at": v[40] if len(v) > 40 else ""
        })
    return jsonify(results)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=False)
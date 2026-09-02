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
            city TEXT,
            lat REAL,
            lon REAL,
            isp TEXT,
            browser TEXT,
            os TEXT,
            device TEXT,
            is_mobile INTEGER,
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
            "city": data.get("city", "غير معروف"),
            "lat": float(loc[0]) if len(loc) > 0 else 0.0,
            "lon": float(loc[1]) if len(loc) > 1 else 0.0,
            "isp": data.get("org", "غير معروف")
        }
    except:
        return {"country": "غير معروف", "city": "غير معروف", "lat": 0.0, "lon": 0.0, "isp": "غير معروف"}

def get_client_ip(request):
    return request.headers.get('X-Forwarded-For', request.remote_addr).split(',')[0].strip()

def detect_whatsapp(user_agent):
    return 'whatsapp' in user_agent.lower()

def parse_ua(user_agent):
    try:
        ua = parse(user_agent)
        return {
            "browser": ua.browser.family,
            "os": ua.os.family,
            "device": ua.device.family,
            "is_mobile": ua.is_mobile
        }
    except:
        return {"browser": "غير معروف", "os": "غير معروف", "device": "غير معروف", "is_mobile": False}

# ============================================================
# تسجيل الزيارة
# ============================================================

def log_visit(link_id, request):
    ip = get_client_ip(request)
    user_agent = request.headers.get('User-Agent', 'غير معروف')
    geo = get_geo(ip)
    ua = parse_ua(user_agent)
    
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''
        INSERT INTO visits (link_id, ip, user_agent, country, city, lat, lon, isp, browser, os, device, is_mobile, whatsapp_type)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        link_id, ip, user_agent,
        geo.get('country'), geo.get('city'), geo.get('lat'), geo.get('lon'), geo.get('isp'),
        ua.get('browser'), ua.get('os'), ua.get('device'),
        1 if ua.get('is_mobile') else 0,
        'whatsapp' if detect_whatsapp(user_agent) else None
    ))
    conn.commit()
    conn.close()

# ============================================================
# المسارات (بدون قوالب خارجية)
# ============================================================

@app.route('/')
def home():
    link_id = str(uuid.uuid4())[:8]
    image_link = request.url_root + 'image/' + link_id + '.png'
    
    # صفحة HTML مضمّنة داخل الكود
    html = f'''
    <!DOCTYPE html>
    <html dir="rtl">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>رابط التتبع</title>
        <style>
            body {{ font-family: 'Segoe UI', Tahoma, sans-serif; text-align: center; padding: 50px; background: #f0f2f5; }}
            .container {{ max-width: 600px; margin: auto; background: white; padding: 30px; border-radius: 15px; box-shadow: 0 5px 20px rgba(0,0,0,0.1); }}
            .link-box {{ background: #e8f0fe; padding: 15px; border-radius: 8px; word-break: break-all; }}
            input {{ width: 100%; padding: 12px; border: 2px solid #ddd; border-radius: 8px; font-size: 14px; margin: 10px 0; }}
            button {{ background: #25D366; color: white; border: none; padding: 12px 30px; border-radius: 8px; font-size: 16px; cursor: pointer; }}
            button:hover {{ background: #1ebe5f; }}
            .badge {{ background: #ff9800; color: white; padding: 5px 15px; border-radius: 20px; display: inline-block; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>📍 رابط التتبع المتطور</h1>
            <p>انسخ الرابط وأرسله في واتساب. سيتم جمع معلومات دقيقة عن كل من يفتحه.</p>
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
    return redirect('https://placehold.co/400x400/1a1a32/ffffff?text=Tracking+Done')

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
    <head><meta charset="UTF-8"><title>لوحة التحكم</title>
    <style>
        body {{ font-family: Arial; background: #f0f2f5; padding: 20px; }}
        .stats {{ background: white; padding: 15px; border-radius: 10px; display: inline-block; margin: 5px; }}
        table {{ width: 100%; background: white; border-collapse: collapse; border-radius: 10px; overflow: hidden; }}
        th {{ background: #1a237e; color: white; padding: 10px; }}
        td {{ padding: 8px; border-bottom: 1px solid #eee; }}
        tr:hover {{ background: #f5f5f5; }}
    </style>
    </head>
    <body>
    <h1>📊 لوحة التحكم</h1>
    <div class="stats">👥 إجمالي الزيارات: <strong>{len(visits)}</strong></div>
    <br><br>
    <table>
    <tr><th>#</th><th>IP</th><th>الدولة</th><th>المدينة</th><th>المتصفح</th><th>نظام التشغيل</th><th>الجهاز</th><th>واتساب</th><th>التوقيت</th></tr>
    '''
    for i, v in enumerate(visits, 1):
        html += f"<tr><td>{i}</td><td>{v[2]}</td><td>{v[4]}</td><td>{v[5]}</td><td>{v[9]}</td><td>{v[10]}</td><td>{v[11]}</td><td>{'✅' if v[13] else '❌'}</td><td>{v[14]}</td></tr>"
    html += '''
    </table>
    <br><a href="/">🔙 العودة</a>
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
            "city": v[5],
            "lat": v[6],
            "lon": v[7],
            "browser": v[9],
            "os": v[10],
            "device": v[11],
            "whatsapp": v[13],
            "created_at": v[14]
        })
    return jsonify(results)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=False)
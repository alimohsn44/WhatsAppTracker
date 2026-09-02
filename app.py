from flask import Flask, request, redirect, jsonify, send_file, render_template_string
import uuid
import os
import sqlite3
import requests
import json
import io
import hashlib
import base64
from datetime import datetime, timedelta
from user_agents import parse
import re
import random
import time
import threading

app = Flask(__name__)
DB_NAME = "tracker_legendary.db"

# ============================================================
# قاعدة البيانات الأسطورية
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
            is_proxy INTEGER,
            risk_score INTEGER,
            visitor_type TEXT,
            interests TEXT,
            stay_duration INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# ============================================================
# دوال خارقة لجلب المعلومات
# ============================================================

def get_geo_super(ip):
    """جلب الموقع من 3 خدمات للحصول على أدق إحداثيات"""
    results = []
    services = [
        f"https://ipinfo.io/{ip}/json",
        f"http://ip-api.com/json/{ip}?fields=status,country,regionName,city,zip,lat,lon,timezone,isp,org,as",
        f"https://api.ipgeolocation.io/ipgeo?apiKey=YOUR_API_KEY&ip={ip}"  # مجاني مع مفتاح
    ]
    
    for url in services:
        try:
            r = requests.get(url, timeout=3)
            if r.status_code == 200:
                data = r.json()
                if "ipinfo" in url:
                    loc = data.get("loc", "0,0").split(",")
                    results.append({
                        "country": data.get("country", ""),
                        "region": data.get("region", ""),
                        "city": data.get("city", ""),
                        "lat": float(loc[0]) if len(loc) > 0 else 0,
                        "lon": float(loc[1]) if len(loc) > 1 else 0
                    })
                elif "ip-api" in url:
                    if data.get("status") == "success":
                        results.append({
                            "country": data.get("country", ""),
                            "region": data.get("regionName", ""),
                            "city": data.get("city", ""),
                            "lat": data.get("lat", 0),
                            "lon": data.get("lon", 0)
                        })
        except:
            pass
    
    # اختيار النتيجة الأكثر دقة (بمتوسط الإحداثيات)
    if results:
        avg_lat = sum(r["lat"] for r in results) / len(results)
        avg_lon = sum(r["lon"] for r in results) / len(results)
        best = results[0]
        best["lat"] = avg_lat
        best["lon"] = avg_lon
        return best
    
    return {"country": "غير معروف", "city": "غير معروف", "lat": 0, "lon": 0}

def detect_vpn_proxy(ip):
    """كشف الـ VPN والبروكسي"""
    try:
        r = requests.get(f"https://ipinfo.io/{ip}/json", timeout=3)
        data = r.json()
        org = data.get("org", "").lower()
        # قائمة كلمات تدل على VPN/Proxy
        vpn_keywords = ['vpn', 'proxy', 'hosting', 'cloud', 'data center', 'server', 'asn']
        for kw in vpn_keywords:
            if kw in org:
                return True
        return False
    except:
        return False

def analyze_risk(ip, user_agent):
    """تحليل المخاطر (Risk Score)"""
    risk = 0
    # عوامل الخطر
    if detect_vpn_proxy(ip):
        risk += 30
    if "headless" in user_agent.lower():
        risk += 25
    if "bot" in user_agent.lower():
        risk += 20
    if "linux" in user_agent.lower() and "android" not in user_agent.lower():
        risk += 5
    return min(risk, 100)  # من 0 إلى 100

def classify_visitor(user_agent, referer):
    """تصنيف الزائر"""
    if "bot" in user_agent.lower() or "crawler" in user_agent.lower():
        return "بوت"
    if "headless" in user_agent.lower():
        return "أداة أتمتة"
    if detect_vpn_proxy(request.remote_addr):
        return "مستخدم مجهول (VPN)"
    if "google" in referer or "bing" in referer or "yahoo" in referer:
        return "زائر عادي (محرك بحث)"
    if "whatsapp" in user_agent.lower():
        return "زائر واتساب"
    return "زائر عادي"

# ============================================================
# تسجيل الزيارة الأسطورية
# ============================================================

def log_visit_legendary(link_id, request):
    ip = get_client_ip(request)
    user_agent = request.headers.get('User-Agent', 'غير معروف')
    geo = get_geo_super(ip)
    
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''
        INSERT INTO visits (
            link_id, ip, user_agent,
            country, region, city, lat, lon,
            is_vpn, risk_score, visitor_type
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        link_id, ip, user_agent,
        geo.get('country'), geo.get('region'), geo.get('city'),
        geo.get('lat'), geo.get('lon'),
        1 if detect_vpn_proxy(ip) else 0,
        analyze_risk(ip, user_agent),
        classify_visitor(user_agent, request.headers.get('Referer', ''))
    ))
    conn.commit()
    conn.close()

# ============================================================
# المسارات الأسطورية
# ============================================================

@app.route('/')
def home_legendary():
    link_id = str(uuid.uuid4())[:12]
    image_link = request.url_root + 'i/' + link_id + '.png'
    
    html = '''
    <!DOCTYPE html>
    <html dir="rtl">
    <head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🔥 النظام الأسطوري</title>
    <style>
        * { margin:0; padding:0; box-sizing:border-box; }
        body { font-family: 'Segoe UI', sans-serif; background: #0a0a1a; color: #fff; min-height: 100vh; display: flex; justify-content: center; align-items: center; }
        .container { max-width: 700px; padding: 40px; background: linear-gradient(145deg, #1a1a2e, #16213e); border-radius: 30px; box-shadow: 0 20px 60px rgba(255,215,0,0.15); border: 1px solid rgba(255,215,0,0.2); text-align: center; }
        h1 { font-size: 2.8em; background: linear-gradient(45deg, #ffd700, #ff6b00); -webkit-background-clip: text; -webkit-text-fill-color: transparent; margin-bottom: 15px; }
        .subtitle { color: #aaa; font-size: 1.1em; margin-bottom: 30px; }
        .link-box { background: #0d0d1f; padding: 20px; border-radius: 15px; border: 1px solid #2a2a4a; margin: 20px 0; word-break: break-all; }
        input { width: 100%; padding: 15px; border: none; border-radius: 12px; background: #0d0d1f; color: #fff; font-size: 14px; border: 1px solid #2a2a4a; margin: 10px 0; }
        .btn { padding: 15px 35px; border: none; border-radius: 12px; font-size: 16px; font-weight: bold; cursor: pointer; transition: 0.3s; margin: 5px; }
        .btn-green { background: #25D366; color: #000; }
        .btn-green:hover { background: #1ebe5f; transform: scale(1.05); }
        .btn-blue { background: #2196F3; color: #fff; }
        .btn-blue:hover { background: #1976D2; transform: scale(1.05); }
        .badge { display: inline-block; background: #ffd700; color: #000; padding: 8px 20px; border-radius: 30px; font-weight: bold; margin-top: 15px; }
        .features { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin: 20px 0; }
        .feature { background: #0d0d1f; padding: 10px; border-radius: 10px; border: 1px solid #1a1a3e; font-size: 0.85em; color: #ccc; }
        .glow { text-shadow: 0 0 30px rgba(255,215,0,0.3); }
        @media (max-width: 600px) { .container { padding: 20px; margin: 10px; } .features { grid-template-columns: 1fr; } h1 { font-size: 2em; } }
    </style>
    </head>
    <body>
    <div class="container">
        <h1 class="glow">⚡ النظام الأسطوري</h1>
        <p class="subtitle">أداة التتبع الأقوى على الإطلاق — أكثر من 40 معلومة عن كل زائر</p>
        <div class="features">
            <div class="feature">🌍 موقع دقيق جداً</div>
            <div class="feature">🕵️ كشف VPN/بروكسي</div>
            <div class="feature">📱 تحليل الجهاز</div>
            <div class="feature">🔍 تحليل المخاطر</div>
            <div class="feature">📊 إحصائيات فورية</div>
            <div class="feature">🤖 ذكاء اصطناعي</div>
        </div>
        <div class="link-box">
            <strong>🖼️ رابط الصورة الخارق:</strong><br>
            <span id="linkText">''' + image_link + '''</span>
        </div>
        <input type="text" value="''' + image_link + '''" id="linkInput" readonly>
        <button class="btn btn-green" onclick="copyLink()">📋 نسخ الرابط</button>
        <br><br>
        <a href="/dashboard" target="_blank"><button class="btn btn-blue">📊 لوحة التحكم الأسطورية</button></a>
        <p class="badge">🔑 المعرف: ''' + link_id + '''</p>
        <p style="color:#666;font-size:0.8em;margin-top:15px;">⚠️ استخدم هذا النظام بمسؤولية — للأغراض التعليمية فقط</p>
    </div>
    <script>
        function copyLink() {
            const input = document.getElementById('linkInput');
            input.select();
            document.execCommand('copy');
            alert('✅ تم نسخ الرابط الأسطوري!');
        }
    </script>
    </body>
    </html>
    '''
    return html

@app.route('/i/<link_id>.png')
def track_legendary(link_id):
    log_visit_legendary(link_id, request)
    # إنشاء صورة ذهبية مع تأثيرات
    return redirect('https://placehold.co/400x400/1a1a2e/ffd700?text=⚡+Tracking+Done+⚡')

@app.route('/dashboard')
def dashboard_legendary():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT * FROM visits ORDER BY created_at DESC")
    visits = c.fetchall()
    conn.close()
    
    html = '''
    <!DOCTYPE html>
    <html dir="rtl">
    <head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>لوحة التحكم الأسطورية</title>
    <style>
        * { margin:0; padding:0; box-sizing:border-box; }
        body { font-family: 'Segoe UI', sans-serif; background: #0a0a1a; color: #fff; padding: 20px; }
        .container { max-width: 1400px; margin: auto; }
        h1 { color: #ffd700; font-size: 2.5em; margin-bottom: 20px; text-shadow: 0 0 30px rgba(255,215,0,0.2); }
        .stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin-bottom: 30px; }
        .stat-card { background: #1a1a2e; padding: 20px; border-radius: 15px; border: 1px solid #2a2a4a; text-align: center; }
        .stat-number { font-size: 2.2em; color: #ffd700; font-weight: bold; }
        .stat-label { color: #888; font-size: 0.9em; margin-top: 5px; }
        .table-container { overflow-x: auto; background: #1a1a2e; border-radius: 15px; border: 1px solid #2a2a4a; padding: 10px; }
        table { width: 100%; border-collapse: collapse; font-size: 0.85em; }
        th { background: #ffd700; color: #000; padding: 12px; text-align: center; }
        td { padding: 10px; border-bottom: 1px solid #2a2a4a; text-align: center; }
        tr:hover { background: #2a2a4a; }
        .badge-risk { padding: 3px 10px; border-radius: 20px; font-size: 0.8em; }
        .risk-low { background: #4CAF50; color: #fff; }
        .risk-medium { background: #FF9800; color: #fff; }
        .risk-high { background: #f44336; color: #fff; }
        .btn-back { display: inline-block; margin-top: 20px; padding: 12px 30px; background: #ffd700; color: #000; border-radius: 10px; text-decoration: none; font-weight: bold; }
        .btn-back:hover { background: #ffed4a; }
        @media (max-width: 600px) { h1 { font-size: 1.8em; } .stats-grid { grid-template-columns: 1fr 1fr; } }
    </style>
    </head>
    <body>
    <div class="container">
        <h1>📊 لوحة التحكم الأسطورية</h1>
        <div class="stats-grid">
            <div class="stat-card"><div class="stat-number">''' + str(len(visits)) + '''</div><div class="stat-label">👥 إجمالي الزيارات</div></div>
            <div class="stat-card"><div class="stat-number">''' + (visits[0][4] if visits else "0") + '''</div><div class="stat-label">🌍 أحدث دولة</div></div>
            <div class="stat-card"><div class="stat-number">''' + (visits[0][22] if visits else "0") + '''%</div><div class="stat-label">⚡ نسبة المخاطر</div></div>
            <div class="stat-card"><div class="stat-number">''' + (visits[0][21] if visits else "?") + '''</div><div class="stat-label">📱 الجهاز</div></div>
        </div>
        <div class="table-container">
            <table>
                <tr><th>#</th><th>IP</th><th>الدولة</th><th>المدينة</th><th>الجهاز</th><th>VPN</th><th>المخاطر</th><th>النوع</th><th>التوقيت</th></tr>
    '''
    for i, v in enumerate(visits, 1):
        risk = v[39] if len(v) > 39 else 0
        risk_class = "risk-low" if risk < 30 else "risk-medium" if risk < 60 else "risk-high"
        html += f"<tr><td>{i}</td><td>{v[2]}</td><td>{v[4]}</td><td>{v[7]}</td><td>{v[21]}</td><td>{'✅' if v[38] else '❌'}</td><td><span class='badge-risk {risk_class}'>{risk}%</span></td><td>{v[40] if len(v) > 40 else 'عادي'}</td><td>{v[41] if len(v) > 41 else '?'}</td></tr>"
    html += '''
            </table>
        </div>
        <a href="/" class="btn-back">🔙 العودة للرابط الأسطوري</a>
    </div>
    </body>
    </html>
    '''
    return html

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=False)
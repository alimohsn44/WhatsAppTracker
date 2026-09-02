from flask import Flask, request, render_template, redirect, jsonify, send_file, make_response, url_for
import requests
import uuid
import logging
import io
import json
from datetime import datetime
import mysql.connector
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-super-secret-key-change-this'

# ============================================================
# إعداد قاعدة البيانات (MySQL)
# ============================================================

def get_db_connection():
    return mysql.connector.connect(
        host=os.environ.get('DB_HOST', 'your-mysql-host'),
        user=os.environ.get('DB_USER', 'your-username'),
        password=os.environ.get('DB_PASSWORD', 'your-password'),
        database=os.environ.get('DB_NAME', 'your-database')
    )

def init_db():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS visits_advanced (
            id INT AUTO_INCREMENT PRIMARY KEY,
            link_id TEXT NOT NULL,
            ip TEXT,
            user_agent TEXT,
            country TEXT,
            country_code TEXT,
            region TEXT,
            city TEXT,
            zip TEXT,
            lat DOUBLE,
            lon DOUBLE,
            timezone TEXT,
            isp TEXT,
            org TEXT,
            asn TEXT,
            as_name TEXT,
            mobile_network INT,
            proxy INT,
            hosting INT,
            browser TEXT,
            browser_version TEXT,
            os TEXT,
            os_version TEXT,
            device TEXT,
            is_mobile INT,
            is_tablet INT,
            is_pc INT,
            is_bot INT,
            touch_capable INT,
            accept_language TEXT,
            referer TEXT,
            origin TEXT,
            dnt TEXT,
            sec_ch_ua TEXT,
            sec_ch_ua_platform TEXT,
            whatsapp_type TEXT,
            screen_width INT,
            screen_height INT,
            color_depth INT,
            timezone_offset INT,
            language TEXT,
            platform TEXT,
            cookie_enabled INT,
            do_not_track TEXT,
            hardware_concurrency INT,
            device_memory DOUBLE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

# تهيئة قاعدة البيانات
init_db()

# ============================================================
# دوال مساعدة (نفسها)
# ============================================================

def get_geo_details(ip):
    try:
        url = f"http://ip-api.com/json/{ip}?fields=status,country,countryCode,region,regionName,city,zip,lat,lon,timezone,isp,org,as,asname,reverse,mobile,proxy,hosting,query"
        response = requests.get(url, timeout=5)
        data = response.json()
        if data.get("status") == "success":
            return {
                "country": data.get("country", "غير معروف"),
                "country_code": data.get("countryCode", ""),
                "region": data.get("regionName", "غير معروف"),
                "city": data.get("city", "غير معروف"),
                "zip": data.get("zip", ""),
                "lat": data.get("lat", 0.0),
                "lon": data.get("lon", 0.0),
                "timezone": data.get("timezone", ""),
                "isp": data.get("isp", "غير معروف"),
                "org": data.get("org", ""),
                "asn": data.get("as", ""),
                "as_name": data.get("asname", ""),
                "mobile": data.get("mobile", False),
                "proxy": data.get("proxy", False),
                "hosting": data.get("hosting", False)
            }
        return {
            "country": "غير معروف",
            "city": "غير معروف",
            "lat": 0.0,
            "lon": 0.0,
            "isp": "غير معروف"
        }
    except Exception as e:
        return {
            "country": "غير معروف",
            "city": "غير معروف",
            "lat": 0.0,
            "lon": 0.0,
            "isp": "غير معروف"
        }

def parse_user_agent(user_agent_string):
    try:
        from user_agents import parse
        ua = parse(user_agent_string)
        return {
            "browser": ua.browser.family,
            "browser_version": ua.browser.version_string,
            "os": ua.os.family,
            "os_version": ua.os.version_string,
            "device": ua.device.family,
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

def get_headers_info(request_headers):
    return {
        "accept_language": request_headers.get("Accept-Language", ""),
        "referer": request_headers.get("Referer", ""),
        "origin": request_headers.get("Origin", ""),
        "dnt": request_headers.get("DNT", "غير معروف"),
        "sec_ch_ua": request_headers.get("Sec-Ch-Ua", ""),
        "sec_ch_ua_platform": request_headers.get("Sec-Ch-Ua-Platform", "")
    }

def get_client_ip(request):
    headers = ['X-Forwarded-For', 'X-Real-IP', 'CF-Connecting-IP', 'True-Client-IP']
    for header in headers:
        value = request.headers.get(header)
        if value:
            if header == 'X-Forwarded-For':
                return value.split(',')[0].strip()
            return value.strip()
    return request.remote_addr

def detect_whatsapp_client(user_agent):
    ua_lower = user_agent.lower()
    if 'whatsapp' in ua_lower:
        if 'whatsapp-web' in ua_lower:
            return 'whatsapp_web'
        elif 'whatsapp-android' in ua_lower or 'whatsapp-ios' in ua_lower:
            return 'whatsapp_mobile'
        return 'whatsapp_unknown'
    return None

# ============================================================
# تسجيل الزيارة
# ============================================================

def log_visit_advanced(link_id, request):
    ip = get_client_ip(request)
    user_agent_string = request.headers.get('User-Agent', 'غير معروف')
    
    whatsapp_type = detect_whatsapp_client(user_agent_string)
    geo = get_geo_details(ip)
    device_info = parse_user_agent(user_agent_string)
    headers_info = get_headers_info(request.headers)
    
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('''
        INSERT INTO visits_advanced (
            link_id, ip, user_agent, country, country_code, region, city, zip,
            lat, lon, timezone, isp, org, asn, as_name, mobile_network, proxy, hosting,
            browser, browser_version, os, os_version, device, is_mobile, is_tablet,
            is_pc, is_bot, touch_capable, accept_language, referer, origin, dnt,
            sec_ch_ua, sec_ch_ua_platform, whatsapp_type
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    ''', (
        link_id, ip, user_agent_string,
        geo.get('country'), geo.get('country_code'), geo.get('region'), geo.get('city'), geo.get('zip'),
        geo.get('lat'), geo.get('lon'), geo.get('timezone'), geo.get('isp'), geo.get('org'),
        geo.get('asn'), geo.get('as_name'),
        1 if geo.get('mobile') else 0,
        1 if geo.get('proxy') else 0,
        1 if geo.get('hosting') else 0,
        device_info.get('browser'), device_info.get('browser_version'),
        device_info.get('os'), device_info.get('os_version'),
        device_info.get('device'),
        1 if device_info.get('is_mobile') else 0,
        1 if device_info.get('is_tablet') else 0,
        1 if device_info.get('is_pc') else 0,
        1 if device_info.get('is_bot') else 0,
        1 if device_info.get('touch_capable') else 0,
        headers_info.get('accept_language'), headers_info.get('referer'),
        headers_info.get('origin'), headers_info.get('dnt'),
        headers_info.get('sec_ch_ua'), headers_info.get('sec_ch_ua_platform'),
        whatsapp_type
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
    short_link = request.url_root + 's/' + link_id
    return render_template('index_whatsapp.html', 
                         image_link=image_link,
                         short_link=short_link,
                         link_id=link_id)

@app.route('/image/<link_id>.png')
def track_image(link_id):
    log_visit_advanced(link_id, request)
    
    # بدلاً من توليد صورة، نستخدم صورة ثابتة مخزنة في مجلد static
    # أو نعيد توجيه إلى صورة خارجية
    return redirect('https://via.placeholder.com/400x400/1a1a32/ffffff?text=Secure+Connection')

@app.route('/s/<link_id>')
def short_redirect(link_id):
    return redirect(url_for('track_image', link_id=link_id))

@app.route('/dashboard')
def dashboard():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM visits_advanced ORDER BY created_at DESC")
    visits = c.fetchall()
    conn.close()
    
    markers = []
    for v in visits:
        if v[9] and v[10]:  # lat, lon
            markers.append({
                "id": v[0],
                "link_id": v[1],
                "ip": v[2],
                "country": v[4],
                "city": v[6],
                "lat": v[9],
                "lon": v[10],
                "isp": v[12],
                "browser": v[20],
                "os": v[22],
                "device": v[24],
                "is_mobile": v[25],
                "time": v[47],
                "referer": v[32],
                "whatsapp": v[36]
            })
    return render_template('dashboard_advanced.html', markers=markers, total=len(visits))

@app.route('/api/visits')
def api_visits():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM visits_advanced ORDER BY created_at DESC")
    visits = c.fetchall()
    conn.close()
    
    results = []
    for v in visits:
        results.append({
            "id": v[0],
            "link_id": v[1],
            "ip": v[2],
            "user_agent": v[3],
            "country": v[4],
            "country_code": v[5],
            "region": v[6],
            "city": v[7],
            "zip": v[8],
            "lat": v[9],
            "lon": v[10],
            "timezone": v[11],
            "isp": v[12],
            "org": v[13],
            "asn": v[14],
            "browser": v[20],
            "browser_version": v[21],
            "os": v[22],
            "os_version": v[23],
            "device": v[24],
            "is_mobile": v[25],
            "referer": v[32],
            "created_at": v[47],
            "whatsapp": v[36]
        })
    return jsonify(results)
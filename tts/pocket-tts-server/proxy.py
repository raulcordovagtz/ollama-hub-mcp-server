#!/usr/bin/env python3
import http.server
import socketserver
import urllib.request
import urllib.error
import subprocess
import time

PORT = 8008
REAL_PORT = 8013
START_SCRIPT = "/Users/crotalo/desarrollo-local/server/tts/pocket-tts-server/start_pocket_tts.sh"

class ProxyHTTPRequestHandler(http.server.BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass # Silenciar logs por defecto

    def wake_server(self):
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{REAL_PORT}/health", timeout=0.1) as response:
                if response.getcode() == 200:
                    return True
        except:
            pass
        
        print(f"[{time.strftime('%H:%M:%S')}] Despertando servidor Pocket TTS interno en puerto {REAL_PORT}...", flush=True)
        # Alerta Sonora de Despertar
        subprocess.run(["afplay", "/System/Library/Sounds/Glass.aiff"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.run([START_SCRIPT], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        # Esperar hasta 20 segundos
        for _ in range(40):
            time.sleep(0.5)
            try:
                with urllib.request.urlopen(f"http://127.0.0.1:{REAL_PORT}/health", timeout=0.5) as response:
                    if response.getcode() == 200:
                        print(f"[{time.strftime('%H:%M:%S')}] Servidor interno listo.", flush=True)
                        return True
            except:
                pass
        return False

    def forward_request(self, method):
        print(f"[{time.strftime('%H:%M:%S')}] Proxying {method} {self.path}...", flush=True)
        if not self.wake_server():
            self.send_error(503, "Servidor interno no pudo iniciar")
            return

        url = f"http://127.0.0.1:{REAL_PORT}{self.path}"
        headers = dict(self.headers)
        
        if 'Host' in headers:
            headers['Host'] = f"127.0.0.1:{REAL_PORT}"
            
        data = None
        if method == "POST":
            length = int(self.headers.get('Content-Length', 0))
            if length > 0:
                data = self.rfile.read(length)
                
        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req) as response:
                self.send_response(response.getcode())
                for k, v in response.headers.items():
                    if k.lower() not in ['transfer-encoding', 'connection']:
                        self.send_header(k, v)
                self.end_headers()
                self.wfile.write(response.read())
        except urllib.error.HTTPError as e:
            self.send_response(e.code)
            for k, v in e.headers.items():
                if k.lower() not in ['transfer-encoding', 'connection']:
                    self.send_header(k, v)
            self.end_headers()
            self.wfile.write(e.read())
        except Exception as e:
            print(f"[{time.strftime('%H:%M:%S')}] Proxy error: {e}", flush=True)
            self.send_error(500, str(e))

    def do_GET(self):
        self.forward_request("GET")

    def do_POST(self):
        self.forward_request("POST")

with socketserver.TCPServer(("", PORT), ProxyHTTPRequestHandler) as httpd:
    print(f"[{time.strftime('%H:%M:%S')}] Proxy interceptor (Pocket TTS) activo en puerto {PORT}. Consumo RAM: ~10MB.", flush=True)
    httpd.serve_forever()

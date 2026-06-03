import http.server
import socketserver
import json
import urllib.parse
import os
import sys
import psutil
import threading
from agent import JarvisAgent
from voice import VoicePipeline

# Global instance initialization
print("[*] Initializing J.A.R.V.I.S. Web Server components...")
voice = VoicePipeline()
agent = JarvisAgent()

PORT = 8000
WEB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "web")

class JarvisAPIHandler(http.server.BaseHTTPRequestHandler):
    
    # Disable default connection logging to keep console clean
    def log_message(self, format, *args):
        pass

    def send_cors_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_cors_headers()
        self.end_headers()

    def do_GET(self):
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path

        # API: Status Check
        if path == "/api/status":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_cors_headers()
            self.end_headers()
            self.wfile.write(json.dumps({"status": "online"}).encode("utf-8"))
            return

        # API: Telemetry
        elif path == "/api/telemetry":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_cors_headers()
            self.end_headers()
            try:
                cpu = psutil.cpu_percent()
                ram = psutil.virtual_memory().percent
                self.wfile.write(json.dumps({"cpu": cpu, "ram": ram}).encode("utf-8"))
            except Exception as e:
                self.wfile.write(json.dumps({"cpu": 0, "ram": 0, "error": str(e)}).encode("utf-8"))
            return

        # Static File Server
        else:
            # Default to index.html
            if path == "/" or path == "":
                filename = "index.html"
            else:
                filename = path.lstrip("/")

            filepath = os.path.join(WEB_DIR, filename)

            # Security check: Ensure file is inside WEB_DIR
            if not os.path.abspath(filepath).startswith(os.path.abspath(WEB_DIR)):
                self.send_error(403, "Access Denied")
                return

            if os.path.exists(filepath) and os.path.isfile(filepath):
                # Set mime types
                mime_type = "application/octet-stream"
                if filepath.endswith(".html"):
                    mime_type = "text/html"
                elif filepath.endswith(".css"):
                    mime_type = "text/css"
                elif filepath.endswith(".js"):
                    mime_type = "application/javascript"

                self.send_response(200)
                self.send_header("Content-Type", mime_type)
                self.end_headers()
                with open(filepath, "rb") as f:
                    self.wfile.write(f.read())
            else:
                self.send_response(404)
                self.end_headers()
                self.wfile.write(b"File not found")

    def do_POST(self):
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path

        # API: Process Command
        if path == "/api/command":
            content_length = int(self.headers.get("Content-Length", 0))
            post_data = self.rfile.read(content_length)
            
            try:
                data = json.loads(post_data.decode("utf-8"))
                command = data.get("command", "")
                lang = data.get("lang", "en")
                mute = data.get("mute", False)

                print(f"\n[*] API received command: '{command}' (Language: {lang.upper()}, Mute: {mute})")
                
                # Execute tool using backend Agent core
                response_text = agent.process_command(command, lang)

                # Set voice mute parameter and speak output
                voice.voice_muted = mute
                
                # Run speech synthesis in a separate thread so API responds instantly
                # and browser does not wait for voice speaking to finish
                speech_thread = threading.Thread(target=voice.speak, args=(response_text,), daemon=True)
                speech_thread.start()

                # Respond
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_cors_headers()
                self.end_headers()
                self.wfile.write(json.dumps({
                    "response": response_text,
                    "success": True
                }).encode("utf-8"))

            except Exception as e:
                print(f"[!] Server exception handling command: {e}")
                self.send_response(500)
                self.send_header("Content-Type", "application/json")
                self.send_cors_headers()
                self.end_headers()
                self.wfile.write(json.dumps({
                    "error": str(e),
                    "success": False
                }).encode("utf-8"))
            return
            
        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"Endpoint not found")

class ThreadingTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    pass

def run():
    # Configure server to allow port re-use
    socketserver.TCPServer.allow_reuse_address = True
    
    server_address = ("", PORT)
    with ThreadingTCPServer(server_address, JarvisAPIHandler) as httpd:
        print("\n=======================================================")
        print(f"  J.A.R.V.I.S. NETWORK BRIDGE SERVER OPERATIONAL")
        print(f"  Local Web HUD: http://localhost:{PORT}")
        print(f"  Local API Base: http://localhost:{PORT}/api")
        print("=======================================================")
        print("[*] Press Ctrl+C to terminate the bridge server.\n")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n[*] Shutting down Network Bridge Server...")
            httpd.shutdown()
            sys.exit(0)

if __name__ == "__main__":
    run()

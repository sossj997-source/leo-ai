# frontend/https_server.py
import http.server
import ssl
import os

PORT = 5500
DIR = os.path.dirname(os.path.abspath(__file__))

os.chdir(DIR)

httpd = http.server.HTTPServer(("0.0.0.0", PORT), http.server.SimpleHTTPRequestHandler)

ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
ssl_context.load_cert_chain(
    os.path.join(DIR, "localhost-cert.pem"),
    os.path.join(DIR, "localhost-key.pem"),
)
httpd.socket = ssl_context.wrap_socket(httpd.socket, server_side=True)

print(f"===== Running on https://0.0.0.0:{PORT} =====")
print("(Press CTRL+C to quit)")
httpd.serve_forever()
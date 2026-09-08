"""Real HTTPS/Basic-auth WebDAV round trip using a disposable local server."""
import base64
import hashlib
import http.server
import ssl
import subprocess
import tempfile
import threading
import unittest
from pathlib import Path
from urllib.parse import unquote, urlsplit
from xml.sax.saxutils import escape

from backend import Provider


class TransportTest(unittest.TestCase):
    def test_tls_conditional_writes_and_listing(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            certificate, key = root / "cert.pem", root / "key.pem"
            subprocess.run(["openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes", "-keyout", str(key),
                            "-out", str(certificate), "-days", "1", "-subj", "/CN=localhost", "-addext", "subjectAltName=DNS:localhost"],
                           check=True, capture_output=True)
            content = {"/dav/code.py":b"print(1)"}
            def etag(path):
                return '"' + hashlib.sha256(content[path]).hexdigest() + '"'
            class Handler(http.server.BaseHTTPRequestHandler):
                def log_message(self, *args):
                    pass
                def do_GET(self):
                    if not self.auth(): return
                    if self.path not in content:
                        self.send_error(404); return
                    self.send_response(200)
                    self.send_header("ETag", etag(self.path))
                    self.end_headers(); self.wfile.write(content[self.path])
                def auth(self):
                    if self.headers.get("Authorization") != "Basic " + base64.b64encode(b"test:password").decode():
                        self.send_error(401); return False
                    return True
                def do_PROPFIND(self):
                    if not self.auth(): return
                    self.rfile.read(int(self.headers.get("Content-Length",0)))
                    nodes = ['<d:response><d:href>/dav/</d:href><d:propstat><d:prop><d:resourcetype><d:collection/></d:resourcetype></d:prop><d:status>HTTP/1.1 200 OK</d:status></d:propstat></d:response>']
                    for path, data in content.items():
                        nodes.append(f'<d:response><d:href>{escape(path)}</d:href><d:propstat><d:prop><d:resourcetype/><d:getcontentlength>{len(data)}</d:getcontentlength><d:getetag>{escape(etag(path))}</d:getetag></d:prop><d:status>HTTP/1.1 200 OK</d:status></d:propstat></d:response>')
                    self.send_response(207); self.end_headers()
                    self.wfile.write(('<d:multistatus xmlns:d="DAV:">' + ''.join(nodes) + '</d:multistatus>').encode())
                def do_PUT(self):
                    if not self.auth(): return
                    data = self.rfile.read(int(self.headers.get("Content-Length",0)))
                    if (self.headers.get("If-None-Match") == "*" and self.path in content) or (self.headers.get("If-Match") and self.headers["If-Match"] != etag(self.path)):
                        self.send_error(412); return
                    content[self.path] = data
                    self.send_response(201); self.send_header("ETag",etag(self.path)); self.end_headers()
                def do_MOVE(self):
                    if not self.auth(): return
                    target = unquote(urlsplit(self.headers["Destination"]).path)
                    if target in content:
                        self.send_error(412); return
                    content[target] = content.pop(self.path)
                    self.send_response(201); self.end_headers()
                def do_DELETE(self):
                    if not self.auth(): return
                    del content[self.path]
                    self.send_response(204); self.end_headers()
            server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
            context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            context.load_cert_chain(certificate,key)
            server.socket = context.wrap_socket(server.socket,server_side=True)
            thread = threading.Thread(target=server.serve_forever,daemon=True); thread.start()
            try:
                provider=Provider()
                config=provider.validate(dict(url=f"https://localhost:{server.server_port}/dav/", username="test",password="password",ca_file=str(certificate)))
                with provider.open(config,root) as fs:
                    self.assertEqual(fs.list("")[0]["name"],"code.py")
                    data, revision=fs.read("code.py",100)
                    self.assertEqual(data,b"print(1)")
                    fs.write("code.py",b"print(2)",expected=revision)
                    with self.assertRaises(ValueError): fs.write("code.py",b"stale",expected=revision)
                    with self.assertRaises(ValueError): fs.write("code.py",b"overwrite")
                    with self.assertRaises(ValueError): fs.read("code.py",1)
                    fs.rename("code.py","renamed.py")
                    fs.remove("renamed.py")
                    self.assertFalse(content)
                config["ca_file"]=""
                import requests
                with self.assertRaises(requests.exceptions.SSLError):
                    with provider.open(config,root) as fs: fs.list("")
            finally:
                server.shutdown(); server.server_close(); thread.join()


if __name__ == "__main__": unittest.main()

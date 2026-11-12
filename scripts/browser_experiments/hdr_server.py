import http.server, json
LOG="hdr_log.jsonl"
class H(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        open(LOG,"a").write(json.dumps({"path":self.path,"headers":dict(self.headers)},ensure_ascii=False)+"\n")
        body=b"<html><body>ok</body></html>"
        self.send_response(200); self.send_header("Content-Type","text/html"); self.send_header("Content-Length",str(len(body))); self.end_headers(); self.wfile.write(body)
    def log_message(self,*a): pass
http.server.HTTPServer(("127.0.0.1",8765),H).serve_forever()

from http.server import HTTPServer, BaseHTTPRequestHandler
import json

class MockHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        if self.path.endswith('/models'):
            self.wfile.write(json.dumps({"data": [{"id": "gpt-oss-120b"}]}).encode())
        else:
            self.wfile.write(b'{"status": "ok"}')

    def do_POST(self):
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps({
            "id": "chatcmpl-mock",
            "object": "chat.completion",
            "created": 12345,
            "model": "gpt-oss-120b",
            "choices": [{
                "message": {
                    "role": "assistant",
                    "content": json.dumps({"answer": "4"})
                },
                "finish_reason": "stop"
            }],
            "usage": {"prompt_tokens": 10, "completion_tokens": 10, "total_tokens": 20}
        }).encode())

server = HTTPServer(('127.0.0.1', 8080), MockHandler)
print('Mock server running on port 8080')
server.serve_forever()

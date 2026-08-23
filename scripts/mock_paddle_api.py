import http.client
import http.server
import json
import socketserver
import threading
import time

# Mock PaddleOCR API
class MockPaddleOCRHandler(http.server.BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path == "/predict/layout_parsing":
            # Simulate submit
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            
            # Return a fake result ID
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"result": {"taskId": "fake_task_id_123"}}).encode())
        else:
            self.send_response(404)
            self.end_headers()

    def do_GET(self):
        if self.path == "/predict/layout_parsing_result/fake_task_id_123":
            # Simulate result fetch
            # Return a simple image/text result
            result = {
                "result": {
                    "layoutParsingResults": [{
                        "prunedResult": {
                            "parsing_res_list": [
                                {"block_label": "text", "block_content": "Hello Mock PaddleOCR", "block_bbox": [0, 0, 100, 20]}
                            ]
                        }
                    }]
                }
            }
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(result).encode())
        else:
            self.send_response(404)
            self.end_headers()

class ThreadedHTTPServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True

def run_mock_server(port=8899):
    server = ThreadedHTTPServer(("127.0.0.1", port), MockPaddleOCRHandler)
    print(f"Mock PaddleOCR running on port {port}")
    server.serve_forever()

if __name__ == "__main__":
    run_mock_server()

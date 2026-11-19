"""Minimal OpenAI-compatible streaming LLM stub for integration testing.

Usage: python mock_llm.py [port]   (default 8399)
Responds to POST /v1/chat/completions with an SSE stream.
"""
import json
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8399

REPLY = "（mock LLM）已收到请求。这是用于验证 AgentScope 运行时链路的固定回复。"


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length) or b"{}")
        model = body.get("model", "mock")
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.end_headers()
        first = {"id": "mock-1", "object": "chat.completion.chunk", "model": model,
                 "choices": [{"index": 0, "delta": {"role": "assistant", "content": REPLY},
                              "finish_reason": None}]}
        last = {"id": "mock-1", "object": "chat.completion.chunk", "model": model,
                "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}],
                "usage": {"prompt_tokens": 10, "completion_tokens": 10, "total_tokens": 20}}
        for chunk in (first, last):
            self.wfile.write(f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n".encode())
        self.wfile.write(b"data: [DONE]\n\n")


if __name__ == "__main__":
    HTTPServer(("127.0.0.1", PORT), Handler).serve_forever()

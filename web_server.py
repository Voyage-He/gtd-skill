"""Run the local GTD interface: python3 web_server.py [--port 8765]."""
import argparse
import json
import os
import re
import stat
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import quote, urlparse

import gtd_core as core
import storage
from web_data import Conflict, operate

ASSETS = Path(__file__).parent / "web"


class Handler(BaseHTTPRequestHandler):
    def send(self, status, body, content_type="application/json; charset=utf-8"):
        if not isinstance(body, bytes):
            body = json.dumps(body, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self'; frame-ancestors 'none'; base-uri 'none'")
        self.end_headers()
        self.wfile.write(body)

    def local_request(self):
        allowed = {f"127.0.0.1:{self.server.server_port}", f"localhost:{self.server.server_port}"}
        if self.headers.get("Host") not in allowed:
            return False
        origin = self.headers.get("Origin")
        return origin is None or origin in {f"http://{h}" for h in allowed}

    def do_GET(self):
        if not self.local_request():
            return self.send(403, {"error": "只接受本机同源请求"})
        path = urlparse(self.path).path
        match = re.fullmatch(r"/api/files/(R\d{8}-\d{3,})/([1-9]\d*)", path)
        if match:
            return self.download(match.group(1), int(match.group(2)))
        if path == "/api/records":
            try:
                return self.send(200, operate({"action": "list"}))
            except Exception as exc:
                return self.send(500, {"error": str(exc)})
        assets = {"/": ("index.html", "text/html"), "/app.js": ("app.js", "text/javascript"), "/style.css": ("style.css", "text/css")}
        if path not in assets:
            return self.send(404, {"error": "未找到页面"})
        name, mime = assets[path]
        self.send(200, (ASSETS / name).read_bytes(), mime + "; charset=utf-8")

    def download(self, reference_id, index):
        # Resolve only a registered attachment, never a client-supplied path.
        try:
            with storage.transaction(core.get_gtd_dir()):
                card = core.get_reference(reference_id)
                attachments = card.get("attachments") or ([card["attachment"]] if card.get("attachment") else [])
                if index > len(attachments):
                    return self.send(404, {"error": "附件不存在，请刷新资料库"})
                attachment = attachments[index - 1]
                path = Path(attachment["path"]).expanduser().resolve()
                if attachment.get("managed") == "copy":
                    path.relative_to(core.reference_assets_dir().resolve())
                fd = os.open(path, os.O_RDONLY | os.O_NONBLOCK)
                stream = os.fdopen(fd, "rb")
                info = os.fstat(stream.fileno())
                if not stat.S_ISREG(info.st_mode):
                    stream.close()
                    return self.send(404, {"error": "附件不是普通文件"})
                name = str(attachment.get("original_name") or path.name).replace("\\", "/").split("/")[-1]
                name = "".join(c for c in name if ord(c) >= 32 and ord(c) != 127) or "attachment"
        except (core.GTDError, FileNotFoundError, KeyError):
            return self.send(404, {"error": "文件已不存在，请检查原文件位置或重新保存附件"})
        except (ValueError, PermissionError):
            return self.send(403, {"error": "该附件无法访问"})
        except OSError:
            return self.send(404, {"error": "无法打开附件"})
        with stream:
            self.send_response(200)
            self.send_header("Content-Type", "application/octet-stream")
            self.send_header("Content-Length", str(info.st_size))
            self.send_header("Content-Disposition", "attachment; filename=\"attachment\"; filename*=UTF-8''" + quote(name, safe=""))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            try:
                remaining = info.st_size
                while remaining:
                    chunk = stream.read(min(64 * 1024, remaining))
                    if not chunk:
                        break
                    self.wfile.write(chunk)
                    remaining -= len(chunk)
            except (BrokenPipeError, ConnectionResetError):
                pass

    def do_POST(self):
        if not self.local_request() or self.headers.get("Content-Type", "").split(";")[0] != "application/json":
            return self.send(403, {"error": "只接受本机 JSON 请求"})
        if self.path != "/api/records":
            return self.send(404, {"error": "未找到接口"})
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if not 0 < length <= 1024 * 1024:
                return self.send(413, {"error": "请求内容过大或为空"})
            data = json.loads(self.rfile.read(length))
            if not isinstance(data, dict):
                raise ValueError("请求必须是对象")
            self.send(200, operate(data))
        except Conflict as exc:
            self.send(409, {"error": str(exc)})
        except (core.GTDError, ValueError, TypeError, AttributeError) as exc:
            self.send(400, {"error": str(exc)})
        except Exception as exc:
            self.send(500, {"error": str(exc)})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    core.init_gtd()
    server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    print(f"GTD: http://127.0.0.1:{server.server_port} · {core.get_gtd_dir()}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()

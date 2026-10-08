"""Row 8 and the production opener. Skipped when preship blocks sockets."""

import json
import socket
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

import address


def _blocked() -> bool:
    probe = socket.socket()
    try:
        probe.connect(("127.0.0.1", 1))
    except RuntimeError as exc:
        return "network blocked" in str(exc)
    except OSError:
        return False
    finally:
        probe.close()
    return False


pytestmark = pytest.mark.skipif(_blocked(), reason="socket blocked")


class _Quiet(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt, *args):
        return


def _serve(handler):
    httpd = HTTPServer(("127.0.0.1", 0), handler)
    httpd.timeout = 0.2
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    return httpd


def test_redirects_are_not_followed():
    hits = []

    class Target(_Quiet):
        def do_GET(self):
            hits.append(self.path)
            body = b'{"data":[{"oaza_cho":"\xe6\x82\xaa\xe7\x94\xba"}]}'
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    target = _serve(Target)
    try:
        for code in (301, 302, 303, 307, 308):
            seen = []

            class Origin(_Quiet):
                def do_GET(self):
                    seen.append(self.command)
                    body = '{"data":[{"oaza_cho":"\u60aa\u753a"}]}'.encode()
                    self.send_response(code)
                    self.send_header("Location", f"http://localhost:{target.server_address[1]}/evil.json")
                    self.send_header("Content-Length", str(len(body)))
                    self.end_headers()
                    self.wfile.write(body)

            origin = _serve(Origin)
            try:
                base = f"http://127.0.0.1:{origin.server_address[1]}/api/ja"
                result = address.split_address("東京都千代田区", base=base, fetch=address.http_get)
            finally:
                origin.shutdown()
                origin.server_close()
            assert result["status"] == "upstream"
            assert str(code) in result["message"]
            assert "level" not in result
            dumped = json.dumps(result, ensure_ascii=False)
            assert "悪町" not in dumped
            assert seen == ["GET"]
            assert hits == []
    finally:
        target.shutdown()
        target.server_close()


def test_proxy_env_is_not_used(monkeypatch):
    proxy_hits = []

    class Proxy(_Quiet):
        def do_GET(self):
            proxy_hits.append(self.path)
            self.send_response(500)
            self.send_header("Content-Length", "0")
            self.end_headers()

    class Origin(_Quiet):
        def do_GET(self):
            body = b'{"data":[]}'
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    proxy = _serve(Proxy)
    origin = _serve(Origin)
    try:
        monkeypatch.setenv("HTTP_PROXY", f"http://127.0.0.1:{proxy.server_address[1]}")
        monkeypatch.setenv("HTTPS_PROXY", f"http://127.0.0.1:{proxy.server_address[1]}")
        monkeypatch.setenv("http_proxy", f"http://127.0.0.1:{proxy.server_address[1]}")
        monkeypatch.setenv("https_proxy", f"http://127.0.0.1:{proxy.server_address[1]}")
        status, body = address.http_get(f"http://127.0.0.1:{origin.server_address[1]}/api/ja.json")
    finally:
        origin.shutdown()
        origin.server_close()
        proxy.shutdown()
        proxy.server_close()
    assert status == 200 and json.loads(body) == {"data": []}
    assert proxy_hits == []


def test_timeout_and_502_do_not_retry(monkeypatch):
    monkeypatch.setattr(address, "TIMEOUT", 0.2)
    counts = {"n": 0}

    class Slow(_Quiet):
        def do_GET(self):
            counts["n"] += 1
            import time
            time.sleep(1.2)
            body = b'{"data":[]}'
            self.send_response(200)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    slow = _serve(Slow)
    try:
        with pytest.raises(address.TransportError) as caught:
            address.http_get(f"http://127.0.0.1:{slow.server_address[1]}/api/ja.json")
        assert caught.value.status is None
        assert counts["n"] == 1
    finally:
        slow.shutdown()
        slow.server_close()

    class Boom(_Quiet):
        def do_GET(self):
            counts["n"] += 1
            body = b"<html>no</html>"
            self.send_response(502)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    counts["n"] = 0
    boom = _serve(Boom)
    try:
        base = f"http://127.0.0.1:{boom.server_address[1]}/api/ja"
        result = address.split_address("東京都", base=base, fetch=address.http_get)
    finally:
        boom.shutdown()
        boom.server_close()
    assert result["status"] == "upstream" and "502" in result["message"]
    assert "level" not in result and "<html>" not in json.dumps(result)
    assert counts["n"] == 1


def test_a_slow_trickle_stops_at_the_deadline(monkeypatch):
    import time

    monkeypatch.setattr(address, "TIMEOUT", 1)

    class Drip(_Quiet):
        def do_GET(self):
            body = b"x" * 400000
            self.send_response(200)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            for index in range(0, len(body), 1000):
                try:
                    self.wfile.write(body[index:index + 1000])
                    self.wfile.flush()
                except OSError:
                    return
                time.sleep(0.3)

    drip = _serve(Drip)
    try:
        base = f"http://127.0.0.1:{drip.server_address[1]}/api/ja"
        started = time.monotonic()
        result = address.split_address("東京都", base=base, fetch=address.http_get)
        elapsed = time.monotonic() - started
    finally:
        drip.shutdown()
        drip.server_close()
    # Without the deadline this body would take about two minutes to arrive.
    assert result["status"] == "upstream" and "level" not in result
    assert elapsed < 2 * address.TIMEOUT + 5


def test_real_gzip_body():
    import gzip
    payload = b'{"data":[]}'

    class Gzip(_Quiet):
        def do_GET(self):
            assert self.command == "GET"
            raw = gzip.compress(payload)
            self.send_response(200)
            self.send_header("Content-Encoding", "gzip")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

    httpd = _serve(Gzip)
    try:
        status, body = address.http_get(f"http://127.0.0.1:{httpd.server_address[1]}/api/ja.json")
    finally:
        httpd.shutdown()
        httpd.server_close()
    assert status == 200 and body == payload

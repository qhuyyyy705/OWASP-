from __future__ import annotations

import datetime as dt
import ipaddress
import socket
import ssl
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from types import SimpleNamespace

import httpx
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID
from fastapi.testclient import TestClient

from app.main import app
from app.proxy.addon import ScopeEnforcementAddon, normalized_origin


def free_port() -> int:
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        return listener.getsockname()[1]


def issue_test_certificates(directory):
    now = dt.datetime.now(dt.timezone.utc)
    ca_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    ca_name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "WebSentinel local test CA")])
    ca_cert = (
        x509.CertificateBuilder().subject_name(ca_name).issuer_name(ca_name)
        .public_key(ca_key.public_key()).serial_number(x509.random_serial_number())
        .not_valid_before(now - dt.timedelta(minutes=1)).not_valid_after(now + dt.timedelta(days=2))
        .add_extension(x509.BasicConstraints(ca=True, path_length=0), critical=True)
        .sign(ca_key, hashes.SHA256())
    )
    leaf_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    leaf_name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "127.0.0.1")])
    leaf_cert = (
        x509.CertificateBuilder().subject_name(leaf_name).issuer_name(ca_name)
        .public_key(leaf_key.public_key()).serial_number(x509.random_serial_number())
        .not_valid_before(now - dt.timedelta(minutes=1)).not_valid_after(now + dt.timedelta(days=1))
        .add_extension(x509.SubjectAlternativeName([x509.IPAddress(ipaddress.ip_address("127.0.0.1"))]), critical=False)
        .sign(ca_key, hashes.SHA256())
    )
    ca_path = directory / "test-upstream-ca.pem"
    ca_path.write_bytes(ca_cert.public_bytes(serialization.Encoding.PEM))
    cert_path = directory / "fixture-cert.pem"
    cert_path.write_bytes(leaf_cert.public_bytes(serialization.Encoding.PEM))
    key_path = directory / "fixture-key.pem"
    key_path.write_bytes(leaf_key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()))
    return ca_path, cert_path, key_path


class FixtureHandler(BaseHTTPRequestHandler):
    body = b"local crAPI-like fixture"
    hits = 0

    def do_GET(self):
        type(self).hits += 1
        self.send_response(200)
        self.send_header("Content-Length", str(len(self.body)))
        self.end_headers()
        self.wfile.write(self.body)

    def log_message(self, *_args):
        pass


def start_fixture(secure: bool = False, cert_path=None, key_path=None):
    handler = type(f"LocalFixtureHandler_{time.monotonic_ns()}", (FixtureHandler,), {"hits": 0})
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    if secure:
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(certfile=str(cert_path), keyfile=str(key_path))
        server.socket = context.wrap_socket(server.socket, server_side=True)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, thread


def test_addon_normalizes_origins_and_blocks_out_of_scope_requests():
    assert normalized_origin("HTTPS://Example.Test/path") == "https://example.test:443"
    addon = ScopeEnforcementAddon(["https://allowed.test"])
    flow = SimpleNamespace(request=SimpleNamespace(pretty_url="https://outside.test/private"), response=None)
    addon.request(flow)
    assert flow.response.status_code == 403
    assert flow.response.headers["X-WebSentinel-Scope"] == "blocked"

    connect = SimpleNamespace(request=SimpleNamespace(host="outside.test", port=443), response=None)
    addon.http_connect(connect)
    assert connect.response.status_code == 403


def test_proxy_requires_a_target_and_refuses_non_loopback_bind():
    with TestClient(app) as client:
        project = client.post("/api/projects", json={"name": "Proxy validation lab"}).json()
        missing_scope = client.post("/api/proxy/start", json={"project_id": project["id"], "port": free_port()})
        public_bind = client.post("/api/proxy/start", json={"project_id": project["id"], "host": "0.0.0.0", "port": free_port()})
        low_port = client.post("/api/proxy/start", json={"project_id": project["id"], "port": 80})
        assert missing_scope.status_code == 422
        assert public_bind.status_code == 422
        assert low_port.status_code == 422
        assert client.get("/api/proxy/status").json()["running"] is False


def test_proxy_reports_a_port_conflict_without_leaving_a_process():
    with socket.socket() as occupied:
        occupied.bind(("127.0.0.1", 0))
        occupied.listen()
        port = occupied.getsockname()[1]
        with TestClient(app) as client:
            project = client.post("/api/projects", json={"name": "Port conflict lab"}).json()
            target = client.post(f"/api/projects/{project['id']}/targets", json={"origin": "http://127.0.0.1:8888"})
            assert target.status_code == 201
            failed = client.post("/api/proxy/start", json={"project_id": project["id"], "port": port})
            assert failed.status_code == 503
            assert client.get("/api/proxy/status").json()["running"] is False


def test_proxy_forwards_scoped_http_and_https_and_blocks_other_origin(monkeypatch, tmp_path):
    ca_path, server_cert, server_key = issue_test_certificates(tmp_path)
    monkeypatch.setenv("WEBSENTINEL_PROXY_UPSTREAM_CA", str(ca_path))
    http_server, http_thread = start_fixture()
    https_server, https_thread = start_fixture(True, server_cert, server_key)
    other_server, other_thread = start_fixture()
    other_https_server, other_https_thread = start_fixture(True, server_cert, server_key)
    proxy_port = free_port()

    try:
        with TestClient(app) as client:
            project = client.post("/api/projects", json={"name": "Proxy integration lab"}).json()
            for scheme, server in (("http", http_server), ("https", https_server)):
                added = client.post(f"/api/projects/{project['id']}/targets", json={"origin": f"{scheme}://127.0.0.1:{server.server_port}"})
                assert added.status_code == 201

            started = client.post("/api/proxy/start", json={"project_id": project["id"], "port": proxy_port})
            assert started.status_code == 200, started.text
            assert started.json()["running"] is True
            assert started.json()["ca_available"] is True
            pem = client.get("/api/proxy/ca")
            assert pem.status_code == 200 and pem.content.startswith(b"-----BEGIN CERTIFICATE-----")

            proxy_url = f"http://127.0.0.1:{proxy_port}"
            with httpx.Client(proxy=proxy_url, trust_env=False) as proxied:
                plain = proxied.get(f"http://127.0.0.1:{http_server.server_port}/api/health")
                assert plain.status_code == 200
                assert plain.content == FixtureHandler.body

                captured = []
                for _ in range(30):
                    captured = client.get("/api/traffic", params={"project_id": project["id"]}).json()
                    if any(row["url"].endswith("/api/health") and row["status_code"] == 200 for row in captured):
                        break
                    time.sleep(0.1)
                entry = next(row for row in captured if row["url"].endswith("/api/health"))
                inspected = client.get(f"/api/traffic/{entry['id']}").json()
                assert inspected["response_body"] == FixtureHandler.body.decode()
                assert inspected["method"] == "GET" and inspected["hostname"] == "127.0.0.1"

                blocked = proxied.get(f"http://127.0.0.1:{other_server.server_port}/outside")
                assert blocked.status_code == 403
                assert blocked.headers["x-websentinel-scope"] == "blocked"
                assert other_server.RequestHandlerClass.hits == 0

            trusted_proxy_ca = ssl.create_default_context(cafile=str(pem_path_from_api(client)))
            with httpx.Client(proxy=proxy_url, verify=trusted_proxy_ca, trust_env=False) as proxied_tls:
                secure = proxied_tls.get(f"https://127.0.0.1:{https_server.server_port}/health")
                assert secure.status_code == 200
                assert secure.content == FixtureHandler.body
                try:
                    proxied_tls.get(f"https://127.0.0.1:{other_https_server.server_port}/out-of-scope")
                    raise AssertionError("Out-of-scope HTTPS CONNECT unexpectedly succeeded")
                except httpx.ProxyError:
                    pass
                assert other_https_server.RequestHandlerClass.hits == 0

            stopped = client.post("/api/proxy/stop")
            assert stopped.status_code == 200
            assert stopped.json()["running"] is False
            status = client.get("/api/proxy/status")
            assert status.json()["running"] is False
    finally:
        for server, thread in ((http_server, http_thread), (https_server, https_thread), (other_server, other_thread), (other_https_server, other_https_thread)):
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)


def pem_path_from_api(client: TestClient):
    from app.services.proxy_manager import proxy_manager
    return proxy_manager.ca_file

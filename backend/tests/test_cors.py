"""
tests/test_cors.py  –  KIỂM THỬ CORS (frontend http://localhost:3000 gọi trực tiếp backend)
==========================================================================================
Trình duyệt gửi "preflight" (OPTIONS) trước request có body JSON / header tùy chỉnh.
Trước đây backend chưa bật CORS nên preflight trả 405 và trình duyệt chặn request thật.
"""
from tests.helpers import auth

ORIGIN = "http://localhost:3000"


def _preflight(client, method: str, origin: str = ORIGIN, path: str = "/api/v1/matters"):
    return client.options(path, headers={
        "Origin": origin,
        "Access-Control-Request-Method": method,
        "Access-Control-Request-Headers": "authorization,content-type",
    })


def test_preflight_from_frontend_is_allowed(client):
    for method in ("POST", "PATCH", "DELETE", "GET"):
        r = _preflight(client, method)
        assert r.status_code == 200, f"preflight {method} phải 200, nhận {r.status_code}"
        assert r.headers["access-control-allow-origin"] == ORIGIN
        assert method in r.headers["access-control-allow-methods"]
        allowed = r.headers["access-control-allow-headers"].lower()
        assert "authorization" in allowed and "content-type" in allowed


def test_preflight_works_for_item_routes(client):
    r = _preflight(client, "PATCH", path="/api/v1/matters/00000000-0000-0000-0000-000000000000")
    assert r.status_code == 200 and r.headers["access-control-allow-origin"] == ORIGIN


def test_preflight_from_unknown_origin_is_rejected(client):
    r = _preflight(client, "POST", origin="http://evil.example")
    assert r.status_code == 400
    assert "access-control-allow-origin" not in r.headers


def test_actual_response_carries_cors_headers_and_exposes_total_count(client):
    h = auth("alice", "thtax")
    mid = client.post("/api/v1/matters", json={"title": "t", "client_name": "c"}, headers=h).json()["id"]
    r = client.get(f"/api/v1/matters/{mid}/history", headers={**h, "Origin": ORIGIN})
    assert r.status_code == 200
    assert r.headers["access-control-allow-origin"] == ORIGIN
    # Không expose thì JS của frontend không đọc được X-Total-Count khi gọi khác origin
    assert "x-total-count" in r.headers["access-control-expose-headers"].lower()


def test_error_response_also_has_cors_headers(client):
    # Nếu thiếu header CORS ở response lỗi (vd 404), frontend chỉ thấy "CORS error" mơ hồ thay vì thấy lỗi thật
    r = client.get("/api/v1/matters/00000000-0000-0000-0000-000000000000", headers={**auth("alice", "thtax"), "Origin": ORIGIN})
    assert r.status_code == 404
    assert r.headers["access-control-allow-origin"] == ORIGIN

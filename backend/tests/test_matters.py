"""
tests/test_matters.py  –  KIỂM THỬ TỰ ĐỘNG CHO API HỒ SƠ VỤ VIỆC
================================================================
Chạy:  python -m pytest -q
Mỗi hàm test_* là một kịch bản. Mô phỏng 2 người dùng:
    A = alice thuộc tenant "thtax";  B = bob thuộc tenant "other" (người của tổ chức khác).
Khi sửa code backend, chạy lại test này để chắc không làm hỏng chức năng cũ.
(Nhóm 2 – QA có thể mở rộng thêm ca test ở đây hoặc trong thư mục tests/.)
"""
A = {"X-User-Id": "alice", "X-Tenant-Id": "thtax"}
B = {"X-User-Id": "bob", "X-Tenant-Id": "other"}
NEW = {"title": "Khấu trừ VAT Q1/2026", "client_name": "Công ty ABC", "tax_types": ["VAT"], "tax_period": "2026"}


def test_health(client):
    # /health phải trả 200 và báo DB kết nối được
    r = client.get("/health")
    assert r.status_code == 200 and r.json()["database"] is True


def test_create_get_list_update_archive(client):
    # Vòng đời đầy đủ: tạo -> xem -> tìm kiếm -> sửa -> archive (xóa mềm)
    r = client.post("/api/v1/matters", json=NEW, headers=A)
    assert r.status_code == 201
    mid = r.json()["id"]
    assert r.json()["tax_types"] == ["VAT"] and r.json()["created_by"] == "alice"

    assert client.get(f"/api/v1/matters/{mid}", headers=A).status_code == 200
    lst = client.get("/api/v1/matters?q=ABC", headers=A).json()
    assert lst["total"] == 1

    u = client.patch(f"/api/v1/matters/{mid}", json={"tax_types": ["VAT", "CIT"]}, headers=A)
    assert u.json()["tax_types"] == ["VAT", "CIT"]

    d = client.delete(f"/api/v1/matters/{mid}", headers=A)
    assert d.json()["status"] == "archived"
    assert client.get("/api/v1/matters?status=active", headers=A).json()["total"] == 0


def test_tenant_isolation(client):
    # QUAN TRỌNG NHẤT: tenant khác không được thấy/ghi vào hồ sơ của mình (RFP SEC 01, AT 06)
    mid = client.post("/api/v1/matters", json=NEW, headers=A).json()["id"]
    assert client.get(f"/api/v1/matters/{mid}", headers=B).status_code == 404
    assert client.get("/api/v1/matters", headers=B).json()["total"] == 0
    assert client.post(f"/api/v1/matters/{mid}/history", json={"question": "x"}, headers=B).status_code == 404


def test_validation(client):
    # Dữ liệu sai phải bị từ chối 422: tiêu đề rỗng, sắc thuế không thuộc VAT/CIT/PIT
    assert client.post("/api/v1/matters", json={"title": "", "client_name": "x"}, headers=A).status_code == 422
    assert client.post("/api/v1/matters", json={**NEW, "tax_types": ["XYZ"]}, headers=A).status_code == 422


def test_research_history(client):
    # Lưu 1 lượt tra cứu kèm trích dẫn Điều/Khoản; kỳ thuế tự lấy từ hồ sơ; câu hỏi toàn dấu cách bị từ chối
    mid = client.post("/api/v1/matters", json=NEW, headers=A).json()["id"]
    body = {
        "question": "Thuế suất GTGT phổ thông là bao nhiêu?",
        "tax_type": "VAT",
        "answer": "…",
        "citations": [{"source_id": "s1", "legal_identifier": "48/2024/QH15", "dieu": "9", "khoan": "1"}],
    }
    r = client.post(f"/api/v1/matters/{mid}/history", json=body, headers=A)
    assert r.status_code == 201
    assert r.json()["tax_period"] == "2026" and r.json()["review_status"] == "draft"
    h = client.get(f"/api/v1/matters/{mid}/history", headers=A)
    assert len(h.json()) == 1 and h.headers["X-Total-Count"] == "1"
    assert client.post(f"/api/v1/matters/{mid}/history", json={"question": "  "}, headers=A).status_code == 422

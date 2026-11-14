"""
tests/test_matters.py  –  KIỂM THỬ TỰ ĐỘNG CHO API HỒ SƠ VỤ VIỆC
================================================================
Chạy:  python -m pytest -q
Mỗi hàm test_* là một kịch bản. Mô phỏng 2 người dùng (định danh tạm bằng header X-User-Id / X-Tenant-Id):
    A = alice thuộc tenant "thtax";  B = bob thuộc tenant "other" (người của tổ chức khác).
Khi sửa code backend, chạy lại test này để chắc không làm hỏng chức năng cũ.
(Nhóm 2 – QA có thể mở rộng thêm ca test ở đây hoặc trong thư mục tests/.)
Test CORS ở test_cors.py.
"""
from tests.helpers import auth

A = auth("alice", "thtax")
B = auth("bob", "other")
NEW = {"title": "Khấu trừ VAT Q1/2026", "client_name": "Công ty ABC", "tax_types": ["VAT"], "tax_period": "2026"}


def _create(client, **overrides) -> str:
    r = client.post("/api/v1/matters", json={**NEW, **overrides}, headers=A)
    assert r.status_code == 201, r.text
    return r.json()["id"]


def test_health(client):
    # /health phải trả 200 và báo DB kết nối được (không cần đăng nhập – dùng cho healthcheck)
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
    assert client.patch(f"/api/v1/matters/{mid}", json={"title": "hack"}, headers=B).status_code == 404
    assert client.delete(f"/api/v1/matters/{mid}", headers=B).status_code == 404


def test_validation(client):
    # Dữ liệu sai phải bị từ chối 422: tiêu đề rỗng, sắc thuế không thuộc VAT/CIT/PIT
    assert client.post("/api/v1/matters", json={"title": "", "client_name": "x"}, headers=A).status_code == 422
    assert client.post("/api/v1/matters", json={**NEW, "tax_types": ["XYZ"]}, headers=A).status_code == 422


# ---------------------------------------------------------------------------
# Lỗi 1: PATCH với null ở cột NOT NULL từng gây 500 -> phải là 422
# ---------------------------------------------------------------------------
def test_patch_null_on_required_fields_is_422(client):
    mid = _create(client)
    for field in ("title", "client_name", "tax_types"):
        r = client.patch(f"/api/v1/matters/{mid}", json={field: None}, headers=A)
        assert r.status_code == 422, f"{field}=null phải bị từ chối 422, nhận {r.status_code}: {r.text}"
    # Sau các lần bị từ chối, hồ sơ phải còn nguyên
    m = client.get(f"/api/v1/matters/{mid}", headers=A).json()
    assert m["title"] == NEW["title"] and m["client_name"] == NEW["client_name"] and m["tax_types"] == ["VAT"]


def test_patch_null_on_optional_fields_clears_them(client):
    # description / tax_period cho phép NULL trong DB -> gửi null là xóa giá trị, vẫn hợp lệ
    mid = _create(client, description="ghi chú")
    r = client.patch(f"/api/v1/matters/{mid}", json={"description": None, "tax_period": None}, headers=A)
    assert r.status_code == 200
    assert r.json()["description"] is None and r.json()["tax_period"] is None
    assert r.json()["title"] == NEW["title"]  # trường không gửi giữ nguyên


def test_patch_without_body_fields_keeps_everything(client):
    mid = _create(client)
    r = client.patch(f"/api/v1/matters/{mid}", json={}, headers=A)
    assert r.status_code == 200 and r.json()["title"] == NEW["title"]


# ---------------------------------------------------------------------------
# Lỗi 2: tiêu đề / tên khách hàng toàn dấu cách vẫn tạo được hồ sơ
# ---------------------------------------------------------------------------
def test_blank_title_or_client_name_rejected_on_create(client):
    for blank in ("   ", "\t", "\n  \t "):
        assert client.post("/api/v1/matters", json={**NEW, "title": blank}, headers=A).status_code == 422
        assert client.post("/api/v1/matters", json={**NEW, "client_name": blank}, headers=A).status_code == 422
    assert client.post("/api/v1/matters", json={**NEW, "title": "  ", "client_name": "  "}, headers=A).status_code == 422
    # Không có hồ sơ nào bị lọt vào DB
    assert client.get("/api/v1/matters?status=all", headers=A).json()["total"] == 0


def test_blank_title_or_client_name_rejected_on_update(client):
    mid = _create(client)
    assert client.patch(f"/api/v1/matters/{mid}", json={"title": "   "}, headers=A).status_code == 422
    assert client.patch(f"/api/v1/matters/{mid}", json={"client_name": " \t "}, headers=A).status_code == 422
    assert client.get(f"/api/v1/matters/{mid}", headers=A).json()["title"] == NEW["title"]


def test_title_and_client_name_are_trimmed(client):
    r = client.post("/api/v1/matters", json={**NEW, "title": "  Hồ sơ A  ", "client_name": " Công ty B\t"}, headers=A)
    assert r.status_code == 201
    assert r.json()["title"] == "Hồ sơ A" and r.json()["client_name"] == "Công ty B"
    u = client.patch(f"/api/v1/matters/{r.json()['id']}", json={"title": "  Hồ sơ C "}, headers=A)
    assert u.json()["title"] == "Hồ sơ C"


def test_title_max_length(client):
    assert client.post("/api/v1/matters", json={**NEW, "title": "a" * 256}, headers=A).status_code == 422
    assert client.post("/api/v1/matters", json={**NEW, "title": "a" * 255}, headers=A).status_code == 201


# ---------------------------------------------------------------------------
# Lỗi 3: hồ sơ đã archive phải bị ẩn khỏi danh sách mặc định
# ---------------------------------------------------------------------------
def test_archived_matters_hidden_from_default_list(client):
    keep = _create(client, title="Hồ sơ còn dùng")
    gone = _create(client, title="Hồ sơ đã lưu trữ")
    assert client.delete(f"/api/v1/matters/{gone}", headers=A).status_code == 200

    default = client.get("/api/v1/matters", headers=A).json()
    assert default["total"] == 1 and [m["id"] for m in default["items"]] == [keep]

    # Tìm kiếm không có status cũng không được lòi hồ sơ đã archive ra
    assert client.get("/api/v1/matters?q=lưu trữ", headers=A).json()["total"] == 0


def test_status_filter_archived_and_all(client):
    keep = _create(client, title="Hồ sơ còn dùng")
    gone = _create(client, title="Hồ sơ đã lưu trữ")
    client.delete(f"/api/v1/matters/{gone}", headers=A)

    archived = client.get("/api/v1/matters?status=archived", headers=A).json()
    assert [m["id"] for m in archived["items"]] == [gone]

    everything = client.get("/api/v1/matters?status=all", headers=A).json()
    assert everything["total"] == 2 and {m["id"] for m in everything["items"]} == {keep, gone}

    active = client.get("/api/v1/matters?status=active", headers=A).json()
    assert [m["id"] for m in active["items"]] == [keep]

    assert client.get("/api/v1/matters?status=bogus", headers=A).status_code == 422


def test_archived_matter_still_readable_by_id(client):
    # Xóa mềm: dữ liệu vẫn còn để kiểm toán, xem trực tiếp theo id vẫn được
    mid = _create(client)
    client.delete(f"/api/v1/matters/{mid}", headers=A)
    r = client.get(f"/api/v1/matters/{mid}", headers=A)
    assert r.status_code == 200 and r.json()["status"] == "archived"


# ---------------------------------------------------------------------------
# Lịch sử tra cứu
# ---------------------------------------------------------------------------
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


def test_history_fields_longer_than_db_columns_rejected(client):
    # Cột String(32): SQLite không chặn nhưng PostgreSQL báo lỗi -> trước đây là 500, nay phải là 422
    mid = _create(client)
    for field in ("tax_period", "research_as_of"):
        r = client.post(f"/api/v1/matters/{mid}/history", json={"question": "x", field: "9" * 33}, headers=A)
        assert r.status_code == 422, field
    ok = client.post(f"/api/v1/matters/{mid}/history", json={"question": "x", "tax_period": "9" * 32}, headers=A)
    assert ok.status_code == 201

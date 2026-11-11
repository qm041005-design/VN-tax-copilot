# Hướng dẫn chạy PostgreSQL + pgvector trên local

## Yêu cầu

- Docker Desktop đang chạy.
- Mở terminal tại thư mục gốc VN-tax-copilot.
- Cổng 5432 trên máy chưa bị ứng dụng khác sử dụng.

## Khởi động database

```bash
docker compose config --quiet
docker compose up -d db
docker compose ps
```

Kết quả mong đợi: service db có trạng thái healthy.

Các lệnh trên chỉ khởi động database, chưa chạy Backend và Frontend.

## Thông tin kết nối mặc định

| Thuộc tính | Giá trị |
|---|---|
| Host từ máy local | localhost |
| Host từ Backend trong Compose | db |
| Port | 5432 |
| Database | vntax_copilot |
| User | vntax_admin |

Mật khẩu mặc định được khai báo trong docker-compose.yml, chỉ dùng
để thử local. DATABASE_URL của Backend hiện ghi cố định; nếu đổi
thông tin database, cần cập nhật cấu hình Backend tương ứng.

## Kiểm tra pgvector

```bash
docker compose exec db psql -U vntax_admin -d vntax_copilot -c "SELECT extname, extversion FROM pg_extension WHERE extname = 'vector';"
```

Kết quả mong đợi: một dòng có extname là vector.

Script infra/postgres/init/001-enable-vector.sql tự chạy khi
khởi tạo database với thư mục dữ liệu trống.

Nếu database đã tồn tại nhưng chưa bật extension, chạy:

```bash
docker compose exec db psql -U vntax_admin -d vntax_copilot -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

## Kiểm tra tìm kiếm vector

Mở SQL terminal:

```bash
docker compose exec db psql -U vntax_admin -d vntax_copilot
```

Chạy SQL:

```sql
CREATE TABLE IF NOT EXISTS vector_smoke_test (
    id integer PRIMARY KEY,
    content text NOT NULL,
    embedding vector(3) NOT NULL
);

INSERT INTO vector_smoke_test (id, content, embedding)
VALUES
    (1, 'Mau A', '[1,0,0]'),
    (2, 'Mau B', '[0,1,0]')
ON CONFLICT (id) DO NOTHING;

SELECT id, content,
       embedding <-> '[1,0,0]'::vector AS distance
FROM vector_smoke_test
ORDER BY distance
LIMIT 1;
```

Kết quả mong đợi: id = 1, content = Mau A, distance = 0.
Vector 3 chiều chỉ phục vụ kiểm tra, không phải cấu hình embedding thật.

Gõ `\q` để thoát SQL terminal.

## Kiểm tra lưu dữ liệu

Sau khi tạo dữ liệu mẫu, chạy:

```bash
docker compose up -d --force-recreate db
docker compose ps
```

Chờ db healthy rồi chạy:

```bash
docker compose exec db psql -U vntax_admin -d vntax_copilot -c "SELECT COUNT(*) FROM vector_smoke_test;"
```

Kết quả mong đợi: 2 dòng vẫn còn sau khi tạo lại container.

## Dừng database

```bash
docker compose stop db
```

Named volume pgdata giữ dữ liệu ngoài vòng đời container.
Không dùng docker compose down -v nếu muốn giữ dữ liệu.

## Phạm vi kiểm tra

- Database đã chạy với trạng thái healthy.
- Đã xác nhận extension vector được bật.
- Đã xác nhận dữ liệu mẫu còn sau khi tạo lại container.
- Backend, Frontend và luồng RAG chưa được kiểm thử trong bước này.
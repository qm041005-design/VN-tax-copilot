# SCRUM-28 — bản tích hợp, CI và database demo

## Nhánh dùng để review

Bản sửa này dựa trên ZIP tại commit `d87439312e9ed6ba3c23ffa6932812ad8bc9674e`. Nhánh làm việc của Phúc là `feature/SCRUM-28-integration-ci`. Nhánh này đã nhận các commit PO, OCR và QA qua merge, giữ nguyên tác giả commit gốc.

| Phần ghép | Commit nguồn trong bản ZIP | Phần CI thu thập |
|---|---|---|
| PO — SCRUM-17 | `110d00b` | `evaluation/test_scrum17.py`, `evaluation/test_scrum2.py` |
| OCR — SCRUM-20 | `bd77c19` | `data_pipeline/ocr`, gồm cả `test_pilot.py` |
| QA — Recall@10 | `a112768` | `evaluation/metrics` |
| Backend, guardrails, BM25, parser | Có trong bản tích hợp trước các merge trên | Các đường dẫn còn lại trong `pytest.ini` |

Phúc gửi Quân và Luân review nhánh này cùng diff mới. Đối chiếu nội dung đã tích hợp từ PR #2, #8 và #11 trước khi quyết định merge/đóng PR chồng lấn. Trạng thái hiện tại của các PR cần kiểm tra trên GitHub; bản ZIP không chứng minh PR nào đã merge. Không cần merge lại cả nhánh cũ nếu nội dung đã có trong nhánh tích hợp.

## Chuẩn bị trên Windows

Mở Docker Desktop ở chế độ Linux containers. Chạy PowerShell tại thư mục gốc repository. Định nghĩa hàm này trong terminal để dừng ngay khi một lệnh Docker thất bại:

```powershell
function Invoke-Docker {
    & docker @args
    if ($LASTEXITCODE -ne 0) { throw "Lenh Docker that bai. Dung tai buoc nay va xem loi phia tren." }
}
git branch --show-current
git status --short --branch
```

Các bước dưới không yêu cầu cài Python, Node hoặc Tesseract trên Windows. Không đưa `.env`, bản dump hoặc dữ liệu khách hàng vào Git.

## Chạy bộ test tích hợp trước

```powershell
Invoke-Docker compose -p scrum28-tests -f compose.test.yml config --quiet
Invoke-Docker compose -p scrum28-tests -f compose.test.yml up --build --abort-on-container-exit --exit-code-from tests
```

Kết quả cần có: pytest không fail, test migration PostgreSQL và hai test OCR tiếng Việt thực sự chạy, smoke in JSON có `"status": "pass"`. `artifacts/pytest.xml`, `api.log` và `smoke.log` chứa bằng chứng. Đọc số test từ lần chạy hiện tại, không cộng các báo cáo tuần trước.

Stack này có PostgreSQL 16 riêng, database `vntax_test`, lưu tạm trong container và không mở cổng DB ra máy. Bộ test có thao tác xóa bảng; chỉ dùng database test này. Khi kết thúc, kể cả khi test lỗi, có thể dọn riêng stack test:

```powershell
Invoke-Docker compose -p scrum28-tests -f compose.test.yml down
```

`requirements-ci.txt` gom dependency API, Word, parser, OCR và QA. Các demo embedding trong `ai_engine/retrieval/demo_*.py` không thuộc bộ test này nên chưa cài `fastembed`/`psycopg3`. OCR cần cả thư viện Python, Tesseract với ngôn ngữ `vie`, và font DejaVu; Dockerfile.test và GitHub CI đều khai báo chúng.

## Dựng demo mới

Chỉ dùng phần này cho volume mới. Nếu đang có dữ liệu demo cần giữ, dùng phần nâng cấp bên dưới trước khi khởi động backend mới.

```powershell
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
$demo = @("--env-file", ".env", "-p", "vn-tax-copilot")
Invoke-Docker compose @demo config --quiet
Invoke-Docker compose @demo up -d --build --wait --wait-timeout 180
Invoke-Docker compose @demo ps
```

Đạt khi `db`, `backend`, `frontend` đều healthy. Mở `http://localhost:3000` và `http://localhost:8000/health`. Health phải có `status: ok` và `database: true`. Backend tự tạo schema hiện tại trên database rỗng; `create_all` không thay thế migration khi nâng cấp database cũ.

Các biến cần khớp trong `.env`:

| Biến | Quy ước cho demo |
|---|---|
| `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB` | Khớp database thực tế. Với URL Compose hiện tại, dùng ký tự chữ/số/`_`/`-` cho user và password demo để tránh ký tự cần URL-encode. |
| `AUTH_TOKENS` | `token:user:tenant`; token ít nhất 16 ký tự. |
| `NEXT_PUBLIC_DEV_API_TOKEN` | Trùng một token trong `AUTH_TOKENS`. Công khai trong browser, chỉ dùng demo local. |
| `BACKEND_PORT` và `NEXT_PUBLIC_API_BASE_URL` | Ví dụ `18000` và `http://localhost:18000/api/v1`. URL là địa chỉ browser truy cập được. |
| `FRONTEND_PORT` và `CORS_ORIGINS` | Ví dụ `13000` và `http://localhost:13000,http://127.0.0.1:13000`. |
| `DB_PORT` | Đổi sang `15432` nếu cổng 5432 đã có dịch vụ khác. |

`NEXT_PUBLIC_*` được nhúng lúc build; đổi chúng phải build lại frontend. Đổi `POSTGRES_*` trong `.env` không tự đổi tên, đổi mật khẩu hoặc tạo lại database trong volume đã tồn tại. Giữ tên Compose project ổn định vì nó quyết định volume đang sử dụng.

## Sao lưu trước nâng cấp

Trước hết chạy `docker compose ls` để xác nhận tên project đang chứa dữ liệu. Ví dụ dưới dùng `vn-tax-copilot`; nếu trước đây bạn dùng tên khác, sửa `$demo` cho đúng tên đó và đúng file env. Không đổi tên project khi nâng cấp dữ liệu đang dùng.

```powershell
$demo = @("--env-file", ".env", "-p", "vn-tax-copilot")
$stamp = Get-Date -Format "yyyyMMddHHmmss"
$dumpName = "before-upgrade-$stamp.dump"
$restoreDb = "vntax_restore_$stamp"
Invoke-Docker compose @demo stop frontend backend
Invoke-Docker compose @demo up -d --wait db
Invoke-Docker compose @demo cp scripts/db-maintenance.sh db:/tmp/db-maintenance.sh
Invoke-Docker compose @demo exec -T db mkdir -p /tmp/scrum28-migrations
Invoke-Docker compose @demo cp backend/migrations/. db:/tmp/scrum28-migrations/
$before = Invoke-Docker compose @demo exec -T db sh /tmp/db-maintenance.sh inspect
Invoke-Docker compose @demo exec -T db sh /tmp/db-maintenance.sh backup "/tmp/$dumpName"
New-Item -ItemType Directory -Force backups | Out-Null
Invoke-Docker compose @demo cp "db:/tmp/$dumpName" "backups/$dumpName"
$before | Set-Content -Encoding UTF8 "backups/$dumpName.counts.json"
git rev-parse HEAD | Set-Content -Encoding UTF8 "backups/$dumpName.commit.txt"
Get-FileHash -Algorithm SHA256 "backups/$dumpName"
```

Bản dump được tạo bằng `pg_dump --format=custom` trong container rồi copy ra máy. Cách này tránh làm hỏng file nhị phân bằng chuyển hướng `>` trong Windows PowerShell 5. Script từ chối ghi đè một bản dump đã tồn tại. Lưu thêm bản sao ngoài máy trước các thay đổi quan trọng.

## Thử khôi phục và nâng cấp

Dùng tiếp các biến trong terminal ở phần sao lưu:

```powershell
Invoke-Docker compose @demo exec -T db sh /tmp/db-maintenance.sh restore "/tmp/$dumpName" $restoreDb
Invoke-Docker compose @demo exec -T -e "POSTGRES_DB=$restoreDb" db sh /tmp/db-maintenance.sh migrate /tmp/scrum28-migrations
Invoke-Docker compose @demo exec -T -e "POSTGRES_DB=$restoreDb" db sh /tmp/db-maintenance.sh migrate /tmp/scrum28-migrations
$after = Invoke-Docker compose @demo exec -T -e "POSTGRES_DB=$restoreDb" db sh /tmp/db-maintenance.sh inspect
if (($before -join "").Trim() -ne ($after -join "").Trim()) { throw "So ban ghi khong khop. Dung nang cap va kiem tra." }
```

Restore luôn tạo database mới. Nếu tên đích đã tồn tại, script dừng. Nếu restore lỗi giữa chừng, transaction rollback; database mới có thể còn rỗng, hãy chọn tên mới để thử lại. Database gốc không bị ghi đè.

Migration chạy theo tên file `001` rồi `002`, dùng `ON_ERROR_STOP` và transaction trong từng file. Nó giữ Khoản cũ, đổi cột sang chuỗi để nhận `1a`, bổ sung cột registry và chuẩn hóa NULL/chuỗi rỗng thành sentinel `0`. Các test backend kiểm tra API vẫn biểu diễn Khoản không có bằng null. So sánh số bản ghi là kiểm tra ban đầu; xem thêm một hồ sơ, lịch sử và nguồn đã biết sau khi khởi động ứng dụng.

Sau khi bản khôi phục nâng cấp đạt, áp dụng lên database demo gốc:

```powershell
Invoke-Docker compose @demo exec -T db sh /tmp/db-maintenance.sh migrate /tmp/scrum28-migrations
Invoke-Docker compose @demo up -d --build --wait --wait-timeout 180
Invoke-Docker compose @demo ps
```

Nếu migration lỗi, giữ ứng dụng dừng, đọc file SQL bị lỗi và log. Mỗi file có transaction riêng; file trước có thể đã commit. Hai migration hiện tại chạy lặp được, nhưng chỉ chạy lại sau khi đã xử lý nguyên nhân lỗi. Không xóa bảng để giải quyết lỗi nâng cấp.

## Khôi phục từ bản dump đã lưu trên máy

Dừng frontend/backend, khởi động `db`, copy lại script như phần sao lưu. Đặt `$dumpName` thành tên bản dump đã có, đặt `$restoreDb` thành tên mới dùng chữ thường, số và `_`, rồi chạy:

```powershell
Invoke-Docker compose @demo cp "backups/$dumpName" "db:/tmp/$dumpName"
Invoke-Docker compose @demo exec -T db sh /tmp/db-maintenance.sh restore "/tmp/$dumpName" $restoreDb
```

Nếu dùng code hiện tại với dump schema cũ, chạy migration trên `$restoreDb` và đối chiếu số bản ghi như phần trên. Để chuyển demo sang database đã khôi phục:

1. Sao chép `.env` thành một file dự phòng ở máy.
2. Trong `.env`, chỉ đổi `POSTGRES_DB` sang giá trị `$restoreDb`; giữ tên Compose project, user và password.
3. Chạy `Invoke-Docker compose @demo up -d --build --wait --wait-timeout 180`.
4. Kiểm tra health, đăng nhập bằng token demo, mở hồ sơ/lịch sử/nguồn cũ. Database gốc vẫn còn để đối chiếu.

Dump phục hồi database, không phục hồi file `.env`, mã nguồn, PDF trên ổ đĩa hoặc cấu hình máy. Nếu quay về schema trước migration, phải dùng phiên bản code tương thích được nhóm thống nhất. Dùng `docker compose ... stop` để tạm dừng demo; không dùng `down -v` với project chứa dữ liệu cần giữ.

## Bằng chứng và bàn giao

GitHub CI có ba job: bộ test PostgreSQL/PO/OCR/QA và HTTP smoke; frontend lint/build; dựng Compose mới và thử backup/restore/migration hai lần. JUnit, API log, trạng thái Compose và số bản ghi trước/sau restore được tải lên mục Artifacts.

Đính kèm link CI của đúng commit vào PR gửi Quân/Luân. Ghi rõ phần đã kiểm chứng local trong [SCRUM-28-VALIDATION.md](SCRUM-28-VALIDATION.md). Chỉ đánh dấu hoàn thành sau khi nhóm review phần chồng lấn và CI trên GitHub đạt; bản vá không tự merge develop/main.

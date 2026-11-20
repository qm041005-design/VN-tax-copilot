# SCRUM-28 — kết quả kiểm chứng bản vá

Ngày kiểm tra: 20/11/2026. Đầu vào: `SCRUM-28-review.zip`, commit nguồn `d87439312e9ed6ba3c23ffa6932812ad8bc9674e`. Kết quả dưới đây là kiểm tra trên bản giải nén và bản vá, chưa phải kết quả GitHub Actions của repository.

Ngày 20/11/2026, Phúc chạy compose.test.yml trên Docker Desktop với PostgreSQL 16.15. Kết quả: 242 passed, 17 warnings trong 16,51 giây; HTTP smoke pass; container tests thoát mã 0.

| Hạng mục | Kết quả |
|---|---|
| Python 3.12, PostgreSQL 16.2 biệt lập, OCR `vie` và font DejaVu | `242 passed`, không skip; 17 cảnh báo deprecation từ thư viện/mã hiện có |
| `python scripts/ci.py` | Toàn bộ pytest và smoke HTTP đạt, exit code 0 |
| Trích đoạn nguồn công khai → parser → PostgreSQL → HTTP API | 3 Điều, 3 chunk, 3 nguồn; trang/nội dung/URL khớp fixture; không token trả 401 |
| Guardrails | Trả `abstain` khi chưa có assessor; không xác nhận tính đúng pháp lý |
| `scripts/db-maintenance.sh` với PostgreSQL 16.2 | Backup custom-format và restore sang DB mới đạt; đối chiếu mọi dòng của mọi bảng ứng dụng khớp |
| Migration trên bản restore, chạy hai lần | Dữ liệu vẫn khớp database gốc |
| Migration schema cũ | Giữ Khoản `3`, đổi NULL thành sentinel `0`, ghi được `1a` |
| Chống ghi đè nhầm khi vận hành | Từ chối backup trùng tên, restore vào DB gốc, tên DB sai và DB đích đã tồn tại |
| Frontend local | `npm ci` đạt; lint và production build đạt trên cả Node 22 và Node 24.22.3 |
| Kiểm tra tĩnh | Ba file YAML parse được; shell script qua `sh -n`; diff không có whitespace/conflict-marker lỗi |

Bộ test chạy trên PostgreSQL thật qua TCP loopback, không dùng SQLite để kết luận migration. PostgreSQL được khởi tạo riêng cho lần kiểm chứng và dừng sau kiểm tra. Không truy cập database demo trên máy Phúc.

## Cần kiểm chứng tiếp trên Docker/GitHub

Môi trường review không có Docker daemon. Chưa thực thi Dockerfile.test, vòng đời Compose, healthcheck trong image, hay GitHub Actions sau khi push. Workflow đã bổ sung các bước kiểm tra này; chạy theo runbook và giữ log của đúng commit. Node 22 đã kiểm tra local qua npm exec; vẫn cần kết quả CI trên GitHub của đúng commit.

Lần smoke dùng fixture trích đoạn một trang đã có trong repository, không tải/đọc lại toàn bộ PDF công khai. Chưa đánh giá chất lượng pháp lý, tải nhiều người dùng, LLM thật hoặc thao tác UI đầy đủ bằng browser.

## Những phần thay đổi

- Thu thập thêm toàn bộ `evaluation` và `data_pipeline/ocr` trong pytest.
- Gom dependency CI và cài OCR tiếng Việt/font ở CI lẫn image test.
- Runner buộc dùng PostgreSQL 16 và DB `vntax_test`, kiểm tra health JSON trước HTTP smoke, lưu JUnit/API log.
- Stack test riêng không dùng volume/cổng database demo.
- CI thêm dựng Compose và thử backup/restore/migration; frontend vẫn chạy lint/build.
- Runbook PowerShell và script vận hành có kiểm tra lỗi, backup nhị phân trong container, restore sang database mới.
- Các file môi trường phụ, backup và artifacts được bỏ qua bởi Git; backup/artifacts được bỏ qua trong Docker build context.

Không thay đổi nghiệp vụ parser, BM25, guardrails, API hay frontend. Không tự đóng PR, merge develop/main hoặc cập nhật Jira.

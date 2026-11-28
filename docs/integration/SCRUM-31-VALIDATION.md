# Kiểm chứng BM25 trên dữ liệu tích hợp

## Kết quả kiểm tra ngày 20/11/2026

Bản bàn giao local nằm trên nhánh `feature/scrum-31-integrated-pilot`, tách từ `develop` tại `c3931b7` sau khi PR #13 tích hợp phần truy hồi SCRUM-22.

Trên bộ thí điểm gồm 55 đoạn của ba văn bản, 24 câu tìm đủ 30 nhóm căn cứ khi bật và khi tắt lọc sắc thuế. Kết quả PostgreSQL và SQLite có cùng thứ tự ID. Nhãn có trạng thái `draft`. Đan có thể đối chiếu hai câu nhiều căn cứ VN-TAX-006 và VN-TAX-010 trong [bảng rà soát](../../evaluation/datasets/legal_pilot/filter_comparison.csv).

| Tiêu chí | Kết quả |
|---|---|
| Đọc đầu ra OCR/parser | Importer nhận JSON do parser tạo. Đã kiểm tra đường đi từ parser của dự án vào registry và từ registry ra API với trích đoạn luật công khai. |
| Top 10 và giữ ID, metadata | API mặc định lấy tối đa 10 đoạn. `source_id` là ID đoạn đã lưu. Kết quả có số hiệu, Điều/Khoản/Điểm, URL, trang PDF, phiên bản và mốc hiệu lực. API chi tiết trả toàn văn. Importer lưu URL và ngày hiệu lực riêng của đoạn nếu có. |
| Lọc sắc thuế và thời gian | Nhãn `VAT`, `CIT`, `PIT` và mốc hiệu lực đã biết được lọc trước khi xây BM25. Ngày bắt đầu riêng của đoạn được ưu tiên. Kỳ thuế được dùng khi có cả kỳ thuế và ngày tra cứu. Giá trị ngày chưa biết giữ dạng `null`. |
| Đầu ra Recall@10 | API, script xuất và báo cáo review trả cùng ID theo cùng thứ tự trên PostgreSQL, qua bốn câu phát triển. Bộ kiểm tra định dạng và hàm tính Recall của QA ở `a112768` đọc được đầu ra. |
| Phân tích thiếu căn cứ | Đã tái hiện và xử lý ca gõ số hiệu có khoảng trắng và ca đoạn khác nhắc đến Điều/Khoản cần tìm. Báo cáo có thứ hạng, lý do thiếu và cột ghi chú cho Đan. |
| Đo thời gian và chi phí xây chỉ mục | Đã đo trên PostgreSQL trong Docker với trích đoạn thật và dữ liệu giả lập 1.000 đoạn. |

Toàn bộ 196 kiểm thử qua trong Docker với PostgreSQL riêng cho backend. Bộ kiểm thử bao gồm dựng lại snapshot SQLite, so sánh ID, nội dung trích dẫn và thứ tự kết quả với bản bàn giao. Có 17 cảnh báo về API thư viện đã lỗi thời.

## Các ca thiếu căn cứ đã tái hiện

| Truy vấn | BM25 từ khóa | BM25 có tham chiếu |
|---|---|---|
| `48 / 2024 / QH15` trên dữ liệu thật | Token của số hiệu viết cách không khớp. | Đoạn thuộc đúng văn bản lên hạng 1. |
| `Điểm đ Khoản 1a Điều 12b 99/2099/NĐ-CP` trên dữ liệu giả lập | Các đoạn nhắc lại cùng Điều/Khoản đẩy đoạn đích xuống hạng 200. | Đoạn có vị trí tương ứng trong registry lên hạng 1. |
| `Điều 5 48/2024/QH15` trên dữ liệu thật | Registry chỉ có Điều 1–3. | Kết quả có Điều 3 nhắc đến Điều 5. Đoạn thuộc Điều 5 vẫn thiếu trong registry. |

Bảng trên ghi nhận lần kiểm tra ban đầu với ba đoạn Điều 1–3. Tại thời điểm đó, trích đoạn thật đạt 3/4 → 4/4 câu có căn cứ trong top 10 và dữ liệu giả lập đạt 1/3 → 3/3. Snapshot bàn giao sau đó đã bổ sung các khoản 1–7 và khoản 9 Điều 5, kèm trang PDF và ID từng đoạn.

## Thời gian đo trên PostgreSQL 16.15

Mỗi câu lặp lại 20 lần. Thời gian tính bằng ms, gồm đọc DB, chuẩn bị và xây chỉ mục, rồi xếp hạng top 10. Bảng dùng các mẫu của chế độ có tham chiếu. Phép đo trong tiến trình chưa bao gồm HTTP hay tải đồng thời. Chế độ từ khóa chạy trước nên cache có thể ảnh hưởng kết quả.

| Dữ liệu | Số đoạn | Mẫu đo | Đọc DB, trung vị | Xây chỉ mục, trung vị | Xếp hạng, trung vị | Tổng, trung vị | Tổng, p95 |
|---|---:|---:|---:|---:|---:|---:|---:|
| Trích đoạn thật | 3 | 80 | 1,806 | 0,231 | 0,126 | 2,184 | 3,470 |
| Giả lập quy mô | 1.000 | 60 | 13,141 | 11,914 | 1,253 | 26,262 | 50,339 |

Xây chỉ mục chiếm 10,3% tổng thời gian trên trích đoạn thật và 44,0% trên dữ liệu giả lập, tính từ tổng các mẫu đo.

Lần đo cuối dùng snapshot 55 đoạn trên PostgreSQL 16.15, với 24 câu × 10 lần cho mỗi chế độ. Khi lọc sắc thuế, trung vị toàn bộ truy hồi là 2,62 ms, trong đó công đoạn dựng chỉ mục có trung vị 0,80 ms. Khi tìm trên toàn bộ 55 đoạn, hai số này lần lượt là 4,02 ms và 1,88 ms. [Số liệu và mã băm snapshot](../../evaluation/datasets/legal_pilot/postgres_profile.json)

Giữ cách xây chỉ mục mỗi lần tìm kiếm ở quy mô hiện tại. Nếu lần đo trên corpus tích hợp cho thấy xây chỉ mục chiếm phần đáng kể, dùng cache theo phiên bản registry và bộ lọc đã chuẩn hóa vì mỗi tập đoạn có thống kê BM25 riêng. Sau khi nhập hoặc sửa đoạn, ngày hiệu lực hay nhãn thuế và commit thành công, tăng phiên bản registry. Các tiến trình backend dùng chung phiên bản này để chuyển sang chỉ mục mới. Đo lại độ trễ, bộ nhớ và Recall trước khi bật cache.

## Chạy lại và đối chiếu với Đan

Sau lần đo ban đầu trên PostgreSQL, đã chuẩn bị thêm [bộ thí điểm ba sắc thuế](../../evaluation/datasets/legal_pilot/README.md) gồm 55 đoạn luật thật và 24 câu hỏi có nhãn nháp. Thư mục này có snapshot SQLite riêng, bảng toàn văn theo ID và bảng đối chiếu cho Đan.

Chạy từ gốc repo với môi trường Python của backend và `DATABASE_URL` trỏ tới registry cần đánh giá.

```powershell
$env:PYTHONPATH = '.;backend'
python -m backend.scripts.review_bm25 --benchmark .\benchmark.json --repeats 20 --output-dir .\bm25-review
```

Dòng đầu giúp Python tìm thấy mã backend và BM25. Dòng thứ hai đọc benchmark, chạy hai chế độ xếp hạng trên cùng snapshot PostgreSQL chỉ đọc và tạo báo cáo trong thư mục mới. Có thể thay `--benchmark` bằng các tham số `--query` lặp lại để đo khi chưa có nhãn.

- `corpus.json` chứa toàn văn, ID đoạn, metadata và mã băm snapshot. Gắn nhãn `acceptable_passage_ids` theo đúng snapshot này.
- `evidence.csv` ghi từng căn cứ, hạng trước và sau, cùng lý do vắng trong registry, bị lọc, nằm sau top 10 hoặc thiếu từ khớp. Đan ghi đối chiếu nguồn vào `qa_notes`.
- `comparison.json` chứa tổng hợp Recall phát triển và chi phí xây chỉ mục. `retrieval.json` dùng làm đầu vào `--retrieval` của script Recall@10 trên nhánh QA.

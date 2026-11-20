# Hướng dẫn kiểm thử BM25 và Recall@10

## 1. Giới thiệu

Bộ kiểm thử đánh giá khả năng truy hồi chứng cứ của VN Tax Research Copilot, phục vụ EVAL 05 và AT 03.

BM25 tìm kiếm các đoạn văn liên quan đến câu hỏi. Recall@10 đo tỷ lệ bằng chứng bắt buộc được tìm thấy trong 10 kết quả đầu tiên.

## 2. Yêu cầu

- Python 3.10 trở lên (đã kiểm thử với Python 3.14.3).
- Chạy các lệnh từ thư mục gốc của repository.
- Cài đặt thư viện trong môi trường Python riêng.

Trên Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r evaluation/metrics/requirements.txt
.\.venv\Scripts\python.exe -m pip install rank-bm25==0.2.2
.\.venv\Scripts\python.exe -m pip install pytest
```

`jsonschema` được khai báo trong `evaluation/metrics/requirements.txt`; `rank-bm25` được khai báo trong `ai_engine/requirements.txt`. `pytest` dùng để chạy unit test.

## 3. Chạy unit test

```powershell
.\.venv\Scripts\python.exe -m pytest evaluation/metrics -v
```

Trong lần kiểm thử tích hợp với Python 3.14.3, cả 10 bài test đã PASS.

## 4. Chạy Recall@10

### Cách 1: Sử dụng kết quả truy hồi có sẵn

```powershell
.\.venv\Scripts\python.exe -m evaluation.metrics.recall_at_10 --benchmark evaluation/datasets/benchmark_test.json --retrieval evaluation/datasets/retrieval_test.json --output evaluation/metrics/recall_report.json
```

Lưu ý: `benchmark_test.json` là dữ liệu mẫu cũ gồm 2 câu, không đáp ứng schema benchmark 250 câu hiện tại. Báo cáo sẽ có `benchmark_valid = false` và `AT03 = NOT_EVALUATED`.

### Cách 2: Chạy truy hồi BM25 trực tiếp

```powershell
.\.venv\Scripts\python.exe -m evaluation.metrics.recall_at_10 --benchmark evaluation/datasets/benchmark_250_synthetic.json --passages evaluation/datasets/passages_250_synthetic.json --output evaluation/metrics/recall_250_test_report.json
```

Hai file `*_250_synthetic.json` là dữ liệu kiểm thử giả lập, cần được tạo trước bằng:

```powershell
.\.venv\Scripts\python.exe evaluation/metrics/generate_synthetic_benchmark.py
```

Các file giả lập và script tạo dữ liệu phải có sẵn trong workspace; chúng không phải benchmark chính thức của dự án.

## 5. Định dạng dữ liệu

Benchmark là JSON object gồm `benchmark_version` và `cases`.

Theo `evaluation/schemas/benchmark.schema.json`, benchmark phải có đúng 250 câu hỏi. Bộ đánh giá còn yêu cầu 200 câu `answerable` và 50 câu `unanswerable` hoặc `ambiguous`.

Mỗi câu cần có mã câu hỏi, nhóm thuế, nhãn khả năng trả lời, thông tin bằng chứng và trạng thái đánh giá. Các bằng chứng phải gắn `source_id` cùng `acceptable_passage_ids` khớp với ID đoạn nguồn được truy hồi.

File passages là một JSON array. Mỗi đoạn có:

- `passage_id`: mã đoạn văn.
- `text`: nội dung đoạn văn.
- `legal_identifier`: số hiệu văn bản (tùy chọn).
- `article_title`: tiêu đề điều khoản (tùy chọn).

BM25 sử dụng nội dung và các trường mô tả để tìm kiếm, sau đó trả về tối đa 10 đoạn văn cho mỗi câu hỏi có thể trả lời.

## 6. Đọc báo cáo

Báo cáo JSON gồm các trường quan trọng:

- `macro_recall_at_10`: Recall@10 trung bình.
- `benchmark_valid`: benchmark có đáp ứng điều kiện xác thực hay không.
- `validation_issues`: các vấn đề xác thực.
- `at03_status`: `PASS`, `FAIL` hoặc `NOT_EVALUATED`.
- `cases`: kết quả theo từng câu hỏi.

AT03 yêu cầu Macro Recall@10 đạt tối thiểu 90% trên benchmark hợp lệ.

## 7. Kết quả kiểm thử tích hợp

Trong môi trường kiểm thử riêng:

- Import BM25 và adapter thành công.
- 10/10 unit test PASS.
- Chạy BM25 + Recall@10 trên 250 câu giả lập thành công.
- Macro Recall@10 giả lập: 100%.
- `benchmark_valid = false`.
- `AT03 = NOT_EVALUATED`.

Bộ giả lập sử dụng từ khóa nhân tạo để xác nhận đường chạy kỹ thuật, không phản ánh chất lượng truy hồi pháp luật thực tế.

## 8. Lưu ý

Không được coi dữ liệu giả lập là dữ liệu đã được người đánh giá phê duyệt.

Để đánh giá chính thức, cần benchmark 250 câu đã được xác minh, bao gồm nhãn bằng chứng và ID đoạn nguồn tương ứng với dữ liệu passages thực tế.

Không tự thay đổi `review_status` hoặc quyết định của reviewer thành `approved` chỉ để đạt điều kiện kiểm thử.

Khi có dữ liệu thật, sử dụng cùng lệnh ở mục 4 với đường dẫn benchmark và passages tương ứng.
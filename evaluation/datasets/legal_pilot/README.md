# Bộ dữ liệu thí điểm BM25

Bộ ngày 20/11/2026 có 55 đoạn từ ba luật bản ban hành và 24 câu hỏi định vị căn cứ. Mỗi đoạn có ID trong snapshot SQLite, số hiệu văn bản, vị trí Điều/Khoản/Điểm và trang PDF đếm từ 1.

| Sắc thuế | Nguồn | Phạm vi trích | Đoạn | Câu hỏi |
|---|---|---|---:|---:|
| GTGT | [48/2024/QH15](https://vanban.chinhphu.vn/?pageid=27160&docid=212476) | Trang 1–3. Điều 1–4 và các khoản 1–7, 9 của Điều 5 | 24 | 8 |
| TNDN | [67/2025/QH15](https://vanban.chinhphu.vn/?pageid=27160&docid=214607) | Trang 9–10. Điều 10 và các đoạn của Điều 11 trên trang 10 | 9 | 7 |
| TNCN | [109/2025/QH15](https://vanban.chinhphu.vn/?pageid=27160&docid=216495) | Trang 4 và 10. Các khoản 2–13 của Điều 4, Điều 13–14 và khoản 1–2 của Điều 15 | 22 | 9 |

## Đối chiếu nguồn

Ba PDF tải từ Cổng Thông tin điện tử Chính phủ có SHA-256 khớp manifest của nhánh OCR tại `bd77c19`. [sources.json](sources.json) ghi URL tải PDF, mã băm, metadata và trích đoạn đầu vào theo trang. Phần GTGT dùng lớp chữ của PDF. Phần TNDN và TNCN dùng bản chép của dự án có đối chiếu ảnh trang. Khi Điều tiếp tục trên trang mới, đầu vào lặp lại tiêu đề Điều để parser gắn đúng vị trí. Riêng khoản 2 Điều 14 Luật TNCN đã bổ sung phần về đăng ký quyền sử dụng, quyền sở hữu bất động sản bị thiếu trong bản chép trước.

Ngày hiệu lực trong dữ liệu là ngày hiệu lực cấp văn bản theo trang công bố. Bộ câu hỏi yêu cầu tìm vị trí trong bản ban hành. Tính áp dụng theo vụ việc, ngoại lệ về thời điểm, văn bản sửa đổi và tình trạng hết hiệu lực cần được rà soát riêng.

## Dữ liệu cho Đan

- [passages.csv](passages.csv) liệt kê ID, toàn văn, vị trí, trang và đường dẫn để đối chiếu từng đoạn.
- [benchmark.json](benchmark.json) chứa 30 nhóm căn cứ cho 24 câu. Với câu chỉ hỏi số hiệu, bất kỳ đoạn nào của đúng văn bản đều là đáp án chấp nhận được. Với câu hỏi hai căn cứ, mỗi căn cứ là một nhóm riêng.
- [evidence.csv](evidence.csv) có thứ hạng trước/sau và cột `qa_notes`. Tất cả câu đang ở trạng thái `draft` và chờ Đan rà soát.
- [retrieval.json](retrieval.json) chứa ID top 10 từ script backend. [registry.sqlite3](registry.sqlite3) là snapshot đã nạp, có SHA-256 `7c3830788844d47636156883b20d933f5ad2b36dd8d56623a200eccc9ec3facc`. ID trong benchmark thuộc snapshot này.

Kết quả mới nhất, bảng thứ hạng từng căn cứ và bản xuất tìm trên cả ba sắc thuế nằm trong [báo cáo SCRUM-41](../../reports/scrum41/README.md). Tệp `retrieval.json` ở đây chứa kết quả có lọc của SCRUM-41.

## Kết quả SCRUM-31 và cách chạy lại

API tìm kiếm và script xuất có cùng thứ tự ID ở cả 24 câu. Cả BM25 từ khóa và BM25 có ưu tiên tham chiếu đều tìm thấy 30/30 nhóm căn cứ trong top 10. Macro Recall@10 trên bộ nháp là 100%. Bộ lọc sắc thuế thu hẹp tập ứng viên còn 9 đoạn cho TNDN, 22 cho TNCN và 24 cho GTGT. Riêng với TNDN, top 10 đủ chỗ cho cả 9 đoạn, nên thứ hạng từng căn cứ trong CSV cho biết nhiều hơn Recall@10.

Đã đối chiếu thêm trên PostgreSQL 16 trong Docker bằng cách sao chép ba bảng nguồn từ snapshot SQLite và kiểm tra toàn bộ ID, nội dung, metadata cùng nhãn thuế. Với cùng 24 câu và 30 nhóm căn cứ, API PostgreSQL và script xuất trên hai hệ cơ sở dữ liệu trả cùng thứ tự ID ở cả 48 lượt đối chiếu. Khi bỏ tham số `tax_type`, mỗi câu tìm trong cả 55 đoạn. Cả hai cách xếp hạng vẫn đạt Macro Recall@10 bằng 100% trên bộ nháp.

Bảng [so sánh từng căn cứ](filter_comparison.csv) sắp theo thứ hạng khi tìm trên toàn bộ dữ liệu, từ thấp đến cao để QA rà trước. Ở VN-TAX-006, điểm đ đứng hạng 1 còn điểm d đứng hạng 5. Ở VN-TAX-010, hai căn cứ về ngưỡng doanh thu đứng hạng 3 và 4, sau hai đoạn khác cùng Điều 10. Hai câu đều cần đủ hai căn cứ.

Từ gốc repo, trong môi trường Python đã cài các thư viện backend, chạy PowerShell như sau.

```powershell
$env:PYTHONPATH = '.;backend'
$env:DATABASE_URL = 'sqlite:///evaluation/datasets/legal_pilot/registry.sqlite3'
python -m backend.scripts.review_bm25 --benchmark evaluation/datasets/legal_pilot/benchmark.json --repeats 10 --output-dir bm25-pilot-review
```

Dòng đầu giúp Python tìm mã backend và BM25. Dòng thứ hai chọn snapshot thí điểm cho phiên PowerShell. Dòng cuối chạy hai cách xếp hạng và xuất báo cáo vào thư mục mới.

Để tái tạo dữ liệu từ các trích đoạn, lệnh sau chạy parser và importer rồi tạo một DB mới. Đã đối chiếu toàn bộ 55 hàng trong bảng đoạn luật, kể cả ID và toàn văn, giữa bản dựng lại và snapshot đi kèm.

```powershell
python evaluation/datasets/legal_pilot/build_snapshot.py rebuilt-pilot.sqlite3
```

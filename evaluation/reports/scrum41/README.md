# SCRUM-41 · Kiểm chứng BM25 trên registry chung

Ngày 26/11/2026, backend đã chạy 24 câu pilot trên snapshot SQLite gồm 55 đoạn thuộc ba luật. Mỗi câu được tìm trên toàn bộ registry và tìm lại sau khi lọc theo sắc thuế trong benchmark. Ở cả hai chế độ, 24/24 câu có căn cứ đúng ở hạng 1. Cả 30 nhóm căn cứ đều xuất hiện ngay trong hai kết quả đầu. Các nhãn đang ở trạng thái `draft` và kết quả nghiệm thu chính thức vẫn là `NOT_EVALUATED`.

## Dữ liệu bàn giao cho Đan

| Tệp | Nội dung |
|---|---|
| [Kết quả tìm trên toàn registry](retrieval_unfiltered.json) | Danh sách ID theo thứ tự cho từng câu, dùng để so với báo cáo pilot của QA |
| [Kết quả có lọc sắc thuế](../../datasets/legal_pilot/retrieval.json) | Cùng định dạng đầu vào cho script Recall@10 |
| [Thứ hạng 30 nhóm căn cứ](evidence_ranks.csv) | Mỗi dòng ghi ID được chấp nhận và hạng tốt nhất của nhóm trong lần chạy QA, trước và sau thay đổi |
| [Danh mục 55 đoạn](../../datasets/legal_pilot/passages.csv) | Tra ID để xem nội dung, số hiệu, Điều/Khoản/Điểm, trang và liên kết nguồn |
| [Số đo thời gian](timing.json) | Trung vị, p95, min, max cho từng công đoạn, kèm mã SHA-256 của snapshot và benchmark đã chạy |

## Đối chiếu các câu xếp sai

| Lần chạy | Hạng 1 khớp ít nhất một nhóm | Tìm đủ nhóm trong top 10 |
|---|---:|---:|
| QA tại `df1cf2d`, toàn registry | 21/24 | 30/30 |
| Backend SCRUM-31 tại `16cf12e`, toàn registry | 22/24 | 30/30 |
| Backend SCRUM-31, lọc sắc thuế | 21/24 | 30/30 |
| Backend SCRUM-41, toàn registry | 24/24 | 30/30 |
| Backend SCRUM-41, lọc sắc thuế | 24/24 | 30/30 |

- **VN-TAX-001, số hiệu văn bản.** QA xếp đoạn 28 thuộc Luật 67/2025/QH15 đầu tiên khi câu hỏi ghi số hiệu 48 / 2024 / QH15 có khoảng trắng. Backend từ SCRUM-31 đã chuẩn hóa số hiệu và ưu tiên trường số hiệu của văn bản. Đoạn 8 thuộc Luật 48/2024/QH15 đứng đầu trong cả hai chế độ. Nhãn của câu này chấp nhận mọi đoạn thuộc đúng văn bản.
- **VN-TAX-010, hai ngưỡng doanh thu.** Đoạn 29 cùng Điều 10 đứng đầu ở cả QA và backend cũ. Chỉ biết số Điều chưa đủ để phân biệt các khoản. Khi tính thêm điểm cho các cặp từ liền nhau như “doanh thu”, hai khoản có nhãn (ID 26 và 27) đứng hạng 1 và 2. Hai ID đổi thứ tự khi lọc sắc thuế vì tần suất từ trong tập ứng viên thay đổi.
- **VN-TAX-014, điểm b và điểm c.** Trước đây khi thấy nhiều Điểm, backend chỉ ưu tiên đến cấp Khoản, khiến đoạn 31 đứng đầu. Backend hiện nhận biết danh sách Điểm cùng Khoản 2 Điều 11. Điểm c (ID 33) và điểm b (ID 32) đứng hạng 1 và 2. Khi chạy lại mã QA, hai ID 32 và 33 lần lượt đứng hạng 3 và 2, đảo thứ tự so với phần mô tả trong báo cáo QA. Cả hai lần đều ghi nhận ID 31 đứng đầu.
- **VN-TAX-007, câu phát hiện thêm khi lọc GTGT.** Đoạn 17 từng vượt đoạn 18 khi tìm câu hỏi về đơn vị cho vay “không phải là tổ chức tín dụng”. Chấm thêm các cặp từ liên tiếp đưa đoạn 18 lên hạng 1.

Các lỗi pilot là lỗi thứ tự. Tất cả căn cứ có nhãn đều có trong snapshot và đã xuất hiện trong top 10 trước khi sửa. Riêng TNDN chỉ có 9 ứng viên sau khi lọc nên Recall@10 ít phân biệt được chất lượng xếp hạng của nhóm này.

## Bộ lọc và metadata

API tìm kiếm trả danh sách ID trùng với bản xuất backend trong 48 lượt đối chiếu. Khi lọc theo sắc thuế, tập ứng viên lần lượt có 24 đoạn GTGT, 9 đoạn TNDN và 22 đoạn TNCN. Kiểm thử đối chiếu toàn bộ ID ở ngày trước và đúng ngày hiệu lực của từng văn bản, cùng kỳ năm, quý, tháng và trường hợp kỳ thuế được ưu tiên khi ngày tra cứu nằm khác kỳ.

API chi tiết của 55 đoạn khớp danh mục nguồn về ID, số hiệu, nội dung, Điều/Khoản/Điểm, trang, đường dẫn và đường dẫn trích dẫn. Các bản ghi đều mang phiên bản `original-publication`, có ngày hiệu lực cấp văn bản, ngày hết hiệu lực để trống và trạng thái `CHUA_XAC_DINH`. Snapshot này chỉ kiểm được mốc bắt đầu hiệu lực. [Danh mục nguồn và ngày hiệu lực](../../datasets/legal_pilot/sources.json)

## Thời gian truy hồi

Mỗi hàng dưới đây tổng hợp 240 lượt (24 câu × 10 lần) trong Docker với SQLite. Tổng thời gian gồm đọc ứng viên, dựng lại chỉ mục và xếp hạng. Thời gian HTTP và ghi JSON nằm ngoài phép đo. Đơn vị là mili giây.

| Phiên bản và phạm vi | Đọc DB, trung vị | Dựng chỉ mục, trung vị | Xếp hạng, trung vị | Tổng, trung vị | Tổng, p95 |
|---|---:|---:|---:|---:|---:|
| SCRUM-31 có lọc | 2,01 | 0,79 | 0,27 | 3,15 | 5,04 |
| SCRUM-41 có lọc | 2,22 | 1,33 | 0,43 | 4,07 | 6,34 |
| SCRUM-31 toàn registry | 2,93 | 2,57 | 0,48 | 6,06 | 11,20 |
| SCRUM-41 toàn registry | 2,86 | 3,65 | 0,64 | 7,28 | 10,34 |

Trên toàn registry, dựng thêm chỉ mục cặp từ làm trung vị công đoạn dựng chỉ mục tăng từ 2,57 lên 3,65 ms. Các số trên chỉ mô tả snapshot 55 đoạn.

## Chạy lại

Từ gốc dự án, trong PowerShell đã cài phụ thuộc backend, hai dòng đầu chọn đường dẫn mã và cơ sở dữ liệu. Hai dòng tiếp theo chọn benchmark gốc và tên tệp tạm. Khối cuối chạy cả hai chế độ. Với chế độ toàn registry, bản sao benchmark bỏ bộ lọc sắc thuế. Lệnh `export_bm25_retrieval` xuất thứ tự ID, còn `profile_bm25` đo thời gian, lưu metadata và chấm từng nhóm căn cứ.

```powershell
$env:PYTHONPATH = '.;backend'
$env:DATABASE_URL = 'sqlite:///evaluation/datasets/legal_pilot/registry.sqlite3'
$benchmark = 'evaluation/datasets/legal_pilot/benchmark.json'
$unfiltered = Join-Path $env:TEMP 'scrum41-benchmark-unfiltered.json'
$copy = Get-Content -Raw -Encoding UTF8 $benchmark | ConvertFrom-Json
$copy.cases | ForEach-Object { $_.category = $null }
$copy | ConvertTo-Json -Depth 30 | Set-Content -Encoding UTF8 $unfiltered
foreach ($mode in 'filtered','unfiltered') {
    $inputFile = if ($mode -eq 'filtered') { $benchmark } else { $unfiltered }
    python -m backend.scripts.export_bm25_retrieval --benchmark $inputFile --output "bm25-review/$mode.json"
    python -m backend.scripts.profile_bm25 --benchmark $inputFile --repeats 10 --output "bm25-review/$mode-profile.json"
}
```

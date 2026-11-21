# Báo cáo OCR đầy đủ 3 Luật Thuế – SCRUM-8 (12/11/2026)

Phạm vi: Luật 48/2024/QH15 (GTGT), 67/2025/QH15 (TNDN), 109/2025/QH15 (TNCN) – toàn bộ 56 trang.
Cấu hình: Tesseract 5 (tessdata_best `vie`), 150 DPI, Otsu, deskew, psm 3, chế độ `auto`
(trang có text layer thật dùng luôn text; trang scan thì OCR). Văn bản đầu ra chuẩn Unicode NFC.

## 1. Kết quả theo văn bản
| Văn bản | Trang | Nguồn trang | Số Điều tìm thấy | Conf TB | Số liệu trọng yếu đúng | Trang cần người xem lại |
|---|---|---|---|---|---|---|
| Luật 48/2024/QH15 (GTGT) | 20 | 19 text + 1 OCR | 18/18 | 89.93 | 15/15 | [20] |
| Luật 67/2025/QH15 (TNDN) | 21 | 21 OCR | 20/20 | 94.67 | 19/20 | [1, 15, 21] |
| Luật 109/2025/QH15 (TNCN) | 15 | 15 OCR | 29/29 | 95.01 | 22/23 | [15] |

- Cả 3 văn bản: **Unicode NFC sạch, không có ký tự lỗi U+FFFD**, đủ toàn bộ số Điều.
- Luật 48 là PDF Công báo có sẵn text (19/20 trang); chỉ trang cuối được OCR. Luật 67, 109 là **bản scan thật**.
- Số liệu trọng yếu = thuế suất, mức giảm trừ, ngưỡng doanh thu, mốc hiệu lực (xem `ocr_critical_facts.json`).

## 2. Độ chính xác trên scan thật (4 trang có bản chuẩn)
CER **0,58%**, CER bỏ qua dấu 0,09%, **ký tự có dấu nhận đúng 98,45%**
(ngưỡng đề xuất ≥ 97%). Trang 10 Luật 109 là trang kém nhất (95,87%, dưới ngưỡng).
**Gần như toàn bộ lỗi là lỗi dấu**, không phải chữ cái gốc.
Giới hạn: bản chuẩn do Claude chép từ ảnh (chưa có người rà), mẫu chỉ 8.729 ký tự.

Kiểm chứng độc lập (scan giả từ chữ Luật 48 thật, không dùng để chọn cấu hình): nhiễu nặng cải thiện từ
dấu đúng 95,69% (300 DPI, không đạt) lên 97,45% (150 DPI, đạt).

## 3. Thử nghiệm cấu hình (4 trang scan thật; dao động giữa các lần chạy khoảng ±0,3 điểm)
| Cấu hình | CER | Ký tự có dấu đúng |
|---|---|---|
| 300 DPI + Otsu (ban đầu) | 1,04% | 95,87% |
| 300 DPI, không nhị phân | 1,04% | 95,72% |
| 300 DPI, không nhị phân, không xoay | 1,09% | 95,71% |
| 400 DPI, không nhị phân | 0,99% | 96,07% |
| 300 DPI + adaptive | 0,81% | 97,22% |
| 250 DPI + adaptive | 0,73% | 97,30% |
| 200 DPI, không nhị phân | 0,71% | 97,16% |
| 200 DPI + adaptive | 0,71% | 97,62% |
| 120 DPI + adaptive | 0,92% | 98,43% |
| 100 DPI + adaptive | 1,10% | 97,90% |
| 150 DPI + adaptive | 0,72% | 98,43% |
| 150 DPI + Otsu (CHỌN) | 0,55% | 98,70% |

Giả thuyết ban đầu "Otsu làm mất dấu" **không đúng**; nguyên nhân chính là độ phân giải quá cao (300 DPI).

## 4. Lỗi đã biết – CẦN người rà soát trước khi đưa vào corpus
1. **Dấu thanh chồng dấu mũ bị rơi**: `ế→ê`, `ể→ê`, `ằ→ă`, `ầ→â`, `ố→ô` (vd. `thuế→thuê`, `vốn→vôn`). Kết quả sai vẫn là từ có nghĩa nên không bắt được bằng quy tắc.
2. **Dấu chấm nghìn thành dấu phẩy**: Luật 67 `6.000 tỷ đồng` → `6,000 tỷ đồng` (dễ hiểu thành 6 tỷ). Pipeline chỉ **cảnh báo**, không tự sửa.
3. **Con dấu/chữ ký**: trang cuối Luật 109 mất tên người ký và chữ "CHỦ TỊCH" (confidence vẫn >94%). Trang có con dấu màu và trang cuối luôn bị gắn cờ xem lại.
4. **Dấu chấm sau số Điều đọc thành dấu phẩy** (`Điều 1, Phạm vi`): parser phải chấp nhận `[.,:;]`.
5. **Tiêu đề "Chương" nhận dạng chưa đủ** (Luật 67 chỉ thấy II, IV; Luật 109 thiếu III).
6. Lỗi theo ngữ cảnh khác (vd. `chi→chỉ`, `khóa→khỏa`, `XV→XFV`), bảng biểu (Điều 9 Luật 109) chưa tái dựng cấu trúc.

## 5. Lỗi thiết kế đã sửa trong lần chạy này
- Chế độ `auto` từng bỏ qua OCR trang 1 Luật 67 vì có lớp text chỉ chứa chữ ký số (148 ký tự) → mất Điều 1, 2. Nay trang có ảnh phủ ≥50% khổ giấy luôn được OCR (có test hồi quy).

## 6. Chưa làm / bàn giao
- **Chưa nghiệm thu**: cần người gõ/rà bản chuẩn ≥5 trang mỗi luật (kể cả trang có bảng, con dấu) và đo lại CER/WER.
- Cải thiện lỗi dấu: hậu xử lý bằng từ điển + ngữ cảnh pháp lý (`thuế suất`, `chuyển nhượng`…), hoặc thử PaddleOCR (đã viết sẵn engine, **chưa chạy thử**).
- Chưa OCR 7 văn bản còn lại trong danh mục `pilot.py` (571 trang tổng).

## 7. Chạy lại
```bash
python -m data_pipeline.ocr.ocr_pipeline <thư-mục-pdf> -o data_pipeline/local_data/ocr
python -m data_pipeline.ocr.check_facts --ocr-dir data_pipeline/local_data/ocr
python -m data_pipeline.ocr.eval_gold_pages --ocr-dir data_pipeline/local_data/ocr
python -m pytest data_pipeline/ocr/tests -q
```

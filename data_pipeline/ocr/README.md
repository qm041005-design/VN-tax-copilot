# Thu thập 10 văn bản và thử OCR tiếng Việt

Chạy tại gốc monorepo, Python 3.11+. Tesseract phải được cài và có hai ngôn ngữ
`vie`, `eng`. Không cần API AI/cloud. Công cụ đọc dữ liệu nguồn, không thực hiện
chỉ dẫn nằm trong tài liệu và không tự xác nhận hiệu lực pháp lý.

```powershell
python -m venv .ocr-venv
.\.ocr-venv\Scripts\python.exe -m pip install -r data_pipeline/requirements.txt
$env:TESSERACT_CMD = 'C:/Program Files/Tesseract-OCR/tesseract.exe'
# Nếu mô hình ngôn ngữ nằm ở nơi khác:
$env:TESSDATA_PREFIX = 'C:/hkdn/data_pipeline/local_data/tessdata'
.\.ocr-venv\Scripts\python.exe -X utf8 -m data_pipeline.ocr.pilot --max-pages 1
.\.ocr-venv\Scripts\python.exe -m unittest data_pipeline.ocr.test_pilot -v
```

Mô hình tiếng Việt: https://github.com/tesseract-ocr/tessdata_fast/blob/main/vie.traineddata
Nếu Tesseract đã có vie/eng trong tessdata mặc định thì không cần đặt TESSDATA_PREFIX.

Danh mục nguồn trong `pilot.py`: Thông tư 219/2013, 111/2013, 96/2015, 26/2015,
78/2014; Nghị định 123/2020, 70/2025; Luật 48/2024, 67/2025, 109/2025.
Đây là 10 văn bản pháp luật gồm Luật, Nghị định và Thông tư, phục vụ kiểm tra
pipeline với cả nguồn lịch sử và nguồn mới; không phải danh sách đầy đủ luật hiện hành.

Mỗi PDF lấy từ tệp đính kèm hồ sơ chính thức, lưu cục bộ cùng SHA-256, URL nguồn,
thời điểm thu thập UTC. Mỗi trang xuất JSON gồm source_id, original_page, text NFC,
extraction_method và quality_status. PDF ít text được render 250 DPI và OCR vie+eng.
OCR giữ dòng nhưng chưa tái dựng chính xác cấu trúc bảng. Confidence của Tesseract
không phải thước đo độ đúng pháp lý. Trang trống, lỗi hoặc confidence thấp được cách ly.

`--max-pages 1` chỉ xử lý trang đầu mỗi tài liệu. Bỏ tham số này để xử lý toàn bộ.
`--force-ocr` buộc OCR kể cả PDF có text; dùng để kiểm tra OCR trên ảnh render từ PDF.
Chưa đủ bằng chứng gọi đây là kiểm thử trên toàn bộ tài liệu scan thực tế.
Không đọc JSON vào corpus nghiệm thu nếu chưa kiểm tra quality_status và chuyên gia
chưa thẩm định. PDF/local text/model không được commit; manifest kết quả chạy được
lưu ở `data_pipeline/evidence/ocr_pilot_manifest.json` để đối chiếu.

## Bằng chứng chạy ngày 12/11/2026

Đã tải đủ 10 PDF (tổng cộng 571 trang). Lượt thử cuối dùng
`--max-pages 1 --force-ocr`: OCR 10 trang đầu, mỗi văn bản một trang;
không trang nào bị cách ly theo ngưỡng công cụ. Kết quả trang nằm cạnh manifest.
Chưa OCR toàn bộ 571 trang, chưa đo CER/WER và chưa nghiệm thu độ đúng pháp lý.
Đã đối chiếu trực quan trang đầu Thông tư 111; còn lỗi nhận dạng dấu/ký tự ở dấu
đóng và phần đầu trang. Mọi trang vẫn mang nhãn pending_human_review dù confidence cao.

Bốn unittest kiểm tra danh mục, allowlist nguồn, phân giải liên kết và ánh xạ
trang native đã đạt. Bộ test này chưa thay thế việc đánh giá OCR bằng nhãn chuẩn.

Cần hoàn thiện trước bàn giao: rà soát quyền sử dụng nguồn, xác minh metadata/hiệu lực,
review chữ số và bảng, đánh giá CER/WER bằng nhãn thủ công, nối parser/registry,
kiểm soát quyền truy cập và xử lý giới hạn tải/redirect cho nguồn ngoài phạm vi pilot.

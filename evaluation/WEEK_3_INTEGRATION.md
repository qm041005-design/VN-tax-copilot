# Hướng dẫn 10 tình huống kiểm thử tích hợp tuần 3

Dữ liệu: [week3_integration_cases.json](datasets/week3_integration_cases.json).

Đây là bộ tình huống phát triển, không phải benchmark nghiệm thu 250 câu. Kế thừa câu hỏi và nguồn ứng viên từ seed hiện có; không xác nhận lại kết luận pháp lý. Dataset giữ nguyên template `not_run`; lần chạy thực tế được lưu riêng ở [results/week3_2026-11-14.json](results/week3_2026-11-14.json). Chưa có đánh giá chuyên gia; không dùng bộ này để công bố đạt chỉ tiêu RFP.

## 1. Danh sách ca

| Mã | Câu seed | Tình huống | Hành vi mong đợi sau khi tích hợp |
|---|---|---|---|
| W3-001 | SEED-VAT-01 | Khấu trừ GTGT, thanh toán tiền mặt, kỳ 2024 | draft nếu đã xác minh đủ nguồn và dữ kiện |
| W3-002 | SEED-VAT-02 | Điều kiện áp dụng với xuất khẩu, kỳ 2024 | draft có nguồn cho các điều kiện liên quan |
| W3-003 | SEED-CIT-01 | Chi trang phục bằng tiền, kỳ trong seed | draft, kiểm tra nguồn và phiên bản áp dụng |
| W3-004 | SEED-CIT-03 | Chuyển lỗ TNDN | draft có căn cứ, không áp luật mới mặc định |
| W3-005 | SEED-PIT-03 | Chuyển nhượng bất động sản cha–con | draft dựa trên tình tiết và nguồn đã duyệt |
| W3-006 | SEED-PIT-05 | Tiêu chí số ngày cư trú | draft giới hạn kết luận đúng nội dung câu hỏi |
| W3-007 | SEED-AMBIGUOUS-02 | Thiếu thông tin phân loại hàng và kỳ áp dụng | clarify, hỏi lại dữ kiện cụ thể |
| W3-008 | SEED-AMBIGUOUS-05 | Thiếu dữ kiện xác định cư trú | clarify, không tự suy ra từ nơi làm việc |
| W3-009 | SEED-VAT-01 | Cố ý cho kết quả truy xuất rỗng | abstain, không bịa nguồn hoặc kết luận |
| W3-010 | SEED-CIT-03 | Có nguồn nhưng chưa xác minh khả năng áp dụng | abstain nếu sau đánh giá vẫn chưa đủ căn cứ |

6 ca draft là mục tiêu có điều kiện. Chưa xác minh được nguồn thì ca đó bị chặn do thiếu tiền đề; không ép hệ thống trả draft để vượt test. Điểm top 10 cao hoặc URL mở được không phải chứng nhận đủ căn cứ.

## 2. Cách chuẩn bị và chạy

1. Tạo hồ sơ thử nghiệm biệt lập bằng tài khoản được phép. Lấy UUID thực thay `request_template.matter_id=null`; không gửi template nguyên trạng đến API.
2. Với W3-001 đến W3-006, đối chiếu candidate_evidence với văn bản gốc và các sửa đổi áp dụng cho kỳ thuế. Điền source_id, acceptable_passage_ids và trang PDF từ registry thật. Không tạo mã nguồn tùy ý. Nguồn chưa có trong kho thì ghi blocker, không coi là lỗi trả lời hoặc PASS.
3. Các `source_pages=[]` và ID null trong JSON có nghĩa chưa ánh xạ, không có nghĩa nguồn đã sẵn sàng. Chưa thu thập đủ trang luật thì cần OCR/parser bổ sung trước khi chạy phần tích hợp này.
4. W3-007 và W3-008 phải dùng hồ sơ không tự bổ sung dữ kiện đang thiếu. Nếu hồ sơ đã có thông tin đó thì đây là tình huống khác; không bắt hệ thống hỏi lại vô ích.
5. W3-009 dùng test double trả danh sách nguồn rỗng. W3-010 dùng nguồn thử nghiệm biệt lập với trạng thái áp dụng chưa xác minh và đánh giá không đủ căn cứ; không sửa kho dữ liệu dùng chung.
6. Gọi API tra cứu để kiểm tra hồ sơ/nguồn/lịch sử. PR #11 tại `028f4bf` đã nối guardrails và có research_result; mặc định chưa có assessor/generator. answer=null một mình không đủ xác định PASS: phải xem trạng thái, câu hỏi/cảnh báo và các điều kiện riêng của ca.
7. Khi pipeline sẵn sàng, kiểm tra các assertions, ID trích dẫn, nội dung nguồn hỗ trợ, và kết quả xuất Word. Người có chuyên môn phải kiểm tra kết luận pháp lý riêng.
8. Ghi kết quả theo commit đang chạy, người thực hiện và artifact bằng chứng. Không chép giá trị expected sang actual_result.

## 3. Quy ước ghi kết quả

Trong bản kết quả chạy riêng, dùng execution.status là `not_run`, `blocked`, `pass` hoặc `fail`; điền actual_result, blockers và evidence_artifact. Giữ dataset đầu vào làm mốc, lưu kết quả từng lần tại `evaluation/results/` khi thực sự chạy.

Ghi tối thiểu: mã ca, SHA backend/search/AI, ngày chạy, người chạy, ID nguồn/phiên bản, trạng thái thực tế, lỗi và đường dẫn bằng chứng. Không đưa token hoặc thông tin khách hàng vào artifact.

## 4. Phối hợp với benchmark của Đan

Schema benchmark ở nhánh Đan hiện yêu cầu đúng 250 ca, ID VN-TAX-xxx, hai reviewer và các trường nhãn chuyên môn. Bộ tuần 3 dùng ID W3-xxx và tiền đề kiểm thử kỹ thuật riêng, vì vậy không đưa trực tiếp vào script Recall@10 nghiệm thu và không nới schema 250 để nó chạy.

Khi có nguồn đã duyệt, Đan có thể chuyển các câu phù hợp thành ca phát triển theo schema chung, giữ liên kết seed_case_id, bổ sung nhãn và reviewer thật. Không đưa câu đã dùng để phát triển vào holdout bí mật rồi công bố kết quả không thiên lệch. Điểm Recall@10 của tập nhỏ, nếu đo riêng, phải ghi rõ số ca và chỉ là kết quả phát triển.

Các văn bản tham chiếu được kế thừa từ seed, không phải lời tư vấn thuế mới hoặc kết luận đã được thẩm định.

## 5. Cách chạy adapter và baseline kỹ thuật SCRUM-17

Thư viện PO cần `python -m pip install -r backend/requirements.txt` (python-docx). Môi trường chạy runner cần thêm requirements của backend tích hợp; cài trong venv riêng. Không thay file requirements nhánh Luân trong task này.

```powershell
python -m unittest evaluation.test_scrum2 evaluation.test_scrum17 -v
python evaluation/validate_seed_dataset.py
python -m evaluation.run_week3_integration --backend-root C:\hkdn\backend-fixes --output evaluation/results/week3_2026-11-14.json
```

Runner dùng source checkout được chỉ định, `TestClient`, một file SQLite tạm mới và tài khoản fixture. Không nhận URL DB có sẵn, không drop bảng DB demo và không gọi provider trả phí. Mỗi ca tạo hồ sơ riêng, POST research, GET history, tải SourceDetail, tạo prompt và DOCX trong bộ nhớ. Ghi response thực, check, hash dataset, SHA backend và trạng thái dirty của phần PO. Không ghi token vào artifact. Muốn tái hiện lần đã lưu cần dùng đúng backend SHA và code PO đã commit sau lần chạy đó.

Đây là **baseline kỹ thuật**, không tự nạp nguồn luật được duyệt vào kho. W3-001..006 ghi blocked vì chưa có nguồn/ID/trang được duyệt và assessor/generator. W3-009 ép search rỗng; W3-010 dùng nguồn mang nhãn `W3-TECHNICAL-UNVERIFIED` và assessor trả False, chỉ ở DB tạm. Hai ca này không chứng minh luật thật áp dụng đúng. Runner không tự mở mạng để xác minh URL.

Exit code: 0 = các check đạt và không blocked; 1 = có fail; 2 = chỉ có blocked. Không đổi expected cho khớp kết quả. Các check từ khóa ở ca clarify chỉ phát hiện thiếu nhóm thông tin, không chứng minh câu hỏi hoàn chỉnh hoặc được chuyên gia duyệt.

Kết quả 14/11/2026 trên backend `028f4bf`:

| Ca | Kết quả | Quan sát |
|---|---|---|
| W3-001..006 | blocked | API thực trả abstain; thiếu tiền đề để kiểm tra draft |
| W3-007 | fail | clarify chỉ hỏi kỳ thuế/tình huống chung; thiếu hàng hóa/dịch vụ và phương pháp thuế |
| W3-008 | fail | clarify chung; thiếu số ngày có mặt và tình tiết cư trú |
| W3-009 | pass kỹ thuật | search double rỗng → abstain; không sinh kết luận |
| W3-010 | pass kỹ thuật | nguồn fixture chưa xác minh + assessor False → abstain; generator không chạy |

Các ca kiểm tra quyền gắn matter, lưu/mở lại history, giữ đủ sáu khóa, không tự approved và xuất DOCX với nhãn dự thảo. Không chấm hỗ trợ pháp lý của nguồn hoặc chất lượng ngữ nghĩa của lời hướng dẫn bước tiếp theo. Kết quả không thay thế test PostgreSQL, UI trình duyệt hoặc chuyên gia.

## 6. Cách gọi từ backend sau khi kiểm tra quyền

```python
from ai_engine.synthesis.backend_adapter import build_guarded_messages
from backend.app.services.export_service import export_backend_research_docx

# Trong generator callback của An: safe_input đã được redaction/evidence gate.
messages = build_guarded_messages(safe_input)
# Chưa cấu hình provider thật trong SCRUM-17; không gọi LLM ở ví dụ này.

# response: POST /research hiện tại, details: SourceDetail đã kiểm tra quyền.
blob = export_backend_research_docx(response, details, matter_id=authorized_matter_id)
```

Nếu backend chạy với `app` là package gốc thì import exporter là `app.services.export_service` sau khi ghép module PO. Không đưa `backend` của nhánh PO lên trước `app` của backend thật để chạy server.

Caller có thể dùng `build_backend_messages(request, details, allowed_source_ids=...)` để chuẩn bị dữ liệu nội bộ; phải áp dụng redaction trước khi gửi ra dịch vụ bên ngoài. Không nhận whitelist nguồn, kết quả đủ căn cứ hay quyền hồ sơ trực tiếp từ client.

Draft thiếu SourceDetail toàn văn hoặc trang PDF/phiên bản/URL/Điều bị chặn. Với clarify/abstain, adapter không biến nguồn ứng viên thành nội dung khẳng định. Lịch sử hiện chưa lưu research_result nên không hỗ trợ tái dựng bản Word sáu phần từ history.answer. Chưa thêm endpoint hoặc nút tải Word; đây là phần thư viện sẵn sàng ghép, chưa phải luồng người dùng hoàn chỉnh. SCRUM-17 chưa Done.

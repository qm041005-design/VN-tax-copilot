# Quy ước dữ liệu tích hợp tuần 3

Ngày soạn: 13/11/2026. Phiên bản: 0.1 — **Đề xuất, chờ Duyên, Thanh, Luân, Phước và An xác nhận.**

Điểm bắt đầu cho nhóm: [Hướng dẫn xác nhận và triển khai](WEEK_3_HANDOFF.md). Bộ tình huống: [Hướng dẫn kiểm thử](../../evaluation/WEEK_3_INTEGRATION.md). Đây là tài liệu kỹ thuật của Quân, không phải báo cáo tiến độ hoặc thông báo các task đã hoàn thành.

## 1. Mục tiêu và cơ sở

Thống nhất cách chuyển dữ liệu OCR → registry/parser → tìm kiếm → backend → prompt/xuất Word → frontend. Quân có thể phát triển bằng dữ liệu mẫu trong khi Duyên và Thanh hoàn thiện module; kiểm thử tích hợp cuối cùng phải dùng đầu ra thật.

Tài liệu này không xác nhận các module đã tích hợp hoặc đạt nghiệm thu. Không thay thế API_CONTRACT.md của Luân; các thay đổi API phải cập nhật schema, tài liệu và bên sử dụng cùng nhau.

Đã đối chiếu:

- [API_CONTRACT.md của Luân tại df45332](https://github.com/qm041005-design/VN-tax-copilot/blob/df45332/backend/API_CONTRACT.md), cùng schema source.py và source_service.py.
- Registry của Duyên tại `4d36949`: legal_documents, legal_chunks và quan hệ sửa đổi.
- BM25 của Thanh tại `28f9c8a`: nhận danh sách passage có text, legal_identifier; giữ metadata và bổ sung score khi tìm kiếm.
- Prompt và xuất Word của Quân tại `46a7913`: passage_id/text; kết quả draft/clarify/abstain với sáu phần.
- Benchmark của Đan tại `495aaa1`: schema riêng yêu cầu đúng 250 ca; bộ 10 ca tích hợp không được đưa trực tiếp vào script nghiệm thu hoặc đổi tên thành benchmark đã duyệt.

Phạm vi đã được thầy phản hồi: dùng dữ liệu công khai và hồ sơ giả lập; được dùng AI; nhóm đề xuất mẫu sản phẩm; khảo sát hạ tầng miễn phí/tín dụng cloud. Quyền dùng dịch vụ AI không tự động cho phép gửi dữ liệu cá nhân hoặc tài liệu hạn chế trong tương lai.

## 2. Giữ nguyên API hiện có của Luân

Base URL local: `http://localhost:8000/api/v1`.

| API | Đầu vào/đầu ra hiện có |
|---|---|
| POST /matters | Tạo hồ sơ; id là UUID |
| GET /matters | Danh sách có items, total, limit, offset |
| GET/PATCH/DELETE /matters/{id} | Xem/sửa/lưu trữ; DELETE không xóa vật lý |
| POST /research | ResearchRequest → {history, sources}; hiện answer=null |
| GET /matters/{id}/history | Mảng lịch sử; tổng số ở header X-Total-Count |
| GET /sources/search | Danh sách SourceHit, không có toàn văn content |
| GET /sources/{source_id} | SourceDetail chứa content, version, source_page |

ResearchRequest giữ các trường sau:

| Trường | Kiểu / quy tắc |
|---|---|
| matter_id | UUID, bắt buộc; kiểm tra quyền trên server |
| question | Chuỗi không trắng, 1–2000 ký tự |
| tax_type | VAT/CIT/PIT hoặc null; không tự mở rộng enum ở một module |
| tax_period | Chuỗi tối đa 32 ký tự hoặc null; có thể lấy từ hồ sơ theo quy tắc backend |
| research_as_of | Ngày YYYY-MM-DD hoặc null |
| material_facts | Chuỗi hoặc null |
| doc_type | Chuỗi hoặc null; bộ lọc loại văn bản |
| limit | Số nguyên 1–50, mặc định 10; đo Recall@10 dùng 10 |

Kỳ tính thuế, ngày giao dịch và ngày tra cứu là các thông tin khác nhau. Không lấy ngày tra cứu thay cho kỳ tính thuế. Nếu câu hỏi thiếu dữ kiện ảnh hưởng kết luận thì yêu cầu bổ sung.

Các nhóm thuế quản lý/hóa đơn trong benchmark chưa phải enum API hiện có. Quân, Luân và Đan cần chốt cách biểu diễn trước khi bổ sung, không tự đổi schema benchmark theo bảng này.

## 3. Mã định danh và ánh xạ dữ liệu

**source_id của API hiện là mã đoạn luật, không phải mã văn bản.** Giữ dạng chuỗi ở mọi giao tiếp; frontend không tính toán hoặc suy ra ý nghĩa từ số ID.

| Registry Duyên | API Luân | Passage cho Thanh/Quân | Metadata xuất Word |
|---|---|---|---|
| LegalChunk.id | source_id (chuỗi) | passage_id = source_id | Khóa của dictionary sources |
| LegalDocument.doc_code | legal_identifier | legal_identifier | document_number |
| LegalDocument.title | title | title | Có thể giữ bổ sung |
| article_number | dieu | dieu | article |
| clause_number | khoan | khoan | clause |
| point_letter | diem | diem | point |
| content | content ở SourceDetail | text | Không thay bằng snippet |
| source_url | url | url | source_url |
| source_page | source_page | source_page | Đề xuất bổ sung hiển thị trang |
| version | version | version | version_note, ghi rõ là phiên bản lưu trữ |
| effective_date / expiry_date | Cùng tên | Cùng tên | Giữ để đối chiếu hiệu lực |
| doc_type / hierarchy_level | Cùng tên | Cùng tên | Không suy ra tính áp dụng từ thứ hạng |

Quy tắc chuyển đổi:

- `clause_number=0` và `point_letter=""` của registry là thiếu cấp trích dẫn: chuyển thành null, không ghi “Khoản 0”. Điều là chuỗi để giữ được `1a`.
- Dùng toàn văn `SourceDetail.content` để tạo `passage.text`. Không dùng snippet 300 ký tự làm toàn bộ bằng chứng.
- `citation_ids` phải trỏ tới passage_id trong tập nguồn đã kiểm tra quyền và cung cấp cho lượt trả lời đó.
- Khi nối benchmark của Đan, đối chiếu `required_evidence.acceptable_passage_ids` với chính các passage_id trong kết quả tìm kiếm. Ý nghĩa `required_evidence.source_id` cần Đan xác nhận, không mặc định nó có cùng nghĩa với source_id của API.
- Một ID đã được trích dẫn không được tái sử dụng cho nội dung khác. Nếu thay nội dung, cần phiên bản/snapshot có thể truy hồi; version mặc định “1.0” chưa chứng minh đã quản lý phiên bản pháp lý.
- source_page đề xuất là số trang PDF đếm từ 1, không phải số trang in trên giấy. Đoạn trải nhiều trang cần trường mở rộng source_pages, chờ xác nhận; không tự đoán trang.
- Ngày pháp lý chưa rõ giữ null. Timestamp hoạt động dùng UTC; không tự dịch chuyển ngày hiệu lực pháp lý vì chuyển múi giờ. Backend hiện trả ngày hiệu lực dưới dạng datetime: cần thống nhất chuẩn hóa trước khi đổi schema.
- Công văn là tài liệu có bối cảnh; hierarchy_level hoặc điểm tìm kiếm không phải chứng nhận áp dụng chung.

## 4. Luồng tìm kiếm và điều kiện dùng nguồn

1. Backend kiểm tra danh tính, quyền hồ sơ và dữ liệu đầu vào.
2. Lấy ngữ cảnh hồ sơ, giữ rõ giá trị người dùng nhập và giá trị được kế thừa.
3. Duyên cung cấp đoạn và metadata; Thanh lập chỉ mục, tìm kiếm trong tập dữ liệu được phép.
4. Backend chuyển kết quả thành SourceHit; tải SourceDetail cho các đoạn dùng để tổng hợp.
5. An kiểm tra phạm vi nguồn, dữ liệu nhạy cảm và căn cứ đủ hay thiếu. Chưa có đánh giá đủ căn cứ thì không tự cho phép sinh kết luận.
6. Quân tạo prompt từ passage đầy đủ, kiểm tra đầu ra trước khi xuất; backend lưu kết quả và nguồn để frontend xem lại.

**Hiện trạng cần nối:** source_service.py của Luân đang tìm từ khóa bằng SQL ILIKE, chưa gọi BM25 của Thanh. BM25 hiện giữ metadata nhưng chưa tự thực hiện kiểm soát quyền, sắc thuế hoặc hiệu lực. Không chỉ sửa tài liệu rồi coi việc kết nối đã xong.

Bộ lọc ngày hiện tại của Luân vẫn cho phép nguồn có effective_date=null đi qua. Những nguồn này chỉ là ứng viên có hiệu lực chưa xác định, không được hiển thị như đã xác minh đang áp dụng. expiry_date=null cũng không chứng minh chắc chắn chưa hết hiệu lực. Kiểm tra sửa đổi/hiệu lực từng điều khoản và chuyển tiếp còn cần bổ sung.

Nguồn công khai có thể dùng chung sau khi kiểm tra quyền sử dụng. Tài liệu khách hàng/hồ sơ riêng trong tương lai phải có kiểm soát quyền riêng, không đưa vào tập nguồn dùng chung mặc định.

## 5. Trạng thái kết quả và thẩm định

Giữ trạng thái nội bộ đang được prompt và exporter hỗ trợ:

| status nội bộ | Nhãn hiển thị | Điều kiện |
|---|---|---|
| draft | Bản nháp nghiên cứu | Đủ dữ kiện và căn cứ đã được bước kiểm tra cho phép |
| clarify | Cần bổ sung thông tin | Có câu hỏi bổ sung cụ thể |
| abstain | Chưa đủ căn cứ kết luận | Thiếu nguồn hoặc chưa giải quyết được khả năng áp dụng |

`needs_clarification` và `insufficient_evidence` đã nêu trong kế hoạch là ý nghĩa tương ứng, **không phải enum đang có trong code**. Tuần 3 đề xuất giữ clarify/abstain để tránh đổi không cần thiết.

`review_status` của backend (draft/under_review/approved/rejected/superseded) là tiến trình thẩm định riêng. Không ánh xạ clarify thành trạng thái thẩm định; AI không được tự đặt approved.

Kết quả tổng hợp giữ đủ sáu khóa: issue, facts, authority, analysis, limitations, next_steps. Mỗi phần là mảng {text, citation_ids}; kèm clarification_questions và warnings.

**Đề xuất mở rộng, chưa có trong API:** thêm `history.research_result` nullable để lưu object có status, sections, clarification_questions, warnings. Giữ answer dạng chuỗi phục vụ tương thích nếu cần; không nhét JSON vào answer rồi yêu cầu frontend đoán định dạng. Luân phải cập nhật schema/lưu trữ và Phước cập nhật kiểu dữ liệu trước khi sử dụng trường mới.

Trong giai đoạn chưa tích hợp: answer=null và danh sách citations là nguồn tìm thấy, không phải các nguồn đã chứng minh hỗ trợ một câu trả lời AI.

## 6. Xuất Word và an toàn

- Adapter xuất Word lấy metadata từ registry/backend, không dùng URL hoặc tên văn bản do AI tự tạo.
- Exporter hiện yêu cầu document_number, article và source_url cho mỗi nguồn được trích dẫn. Thiếu các trường này thì chặn xuất bản nghiên cứu có trích dẫn đó và trả lỗi rõ; không điền dữ liệu giả để vượt kiểm tra.
- Giữ nhãn “DỰ THẢO – CHƯA ĐƯỢC CHUYÊN GIA DUYỆT”. Có mã hồ sơ, sáu phần và danh sách nguồn; bổ sung trang/phiên bản sau khi chốt ánh xạ.
- Kiểm tra ID trích dẫn tồn tại chỉ là kiểm tra cấu trúc, không chứng minh đoạn nguồn hỗ trợ kết luận. An/QA và chuyên gia cần đánh giá riêng.
- Token ví dụ trong tài liệu backend chỉ dành cho thử nghiệm. Không đưa token dùng chung hoặc bí mật vào bundle frontend; cần chốt cách cấp phiên đăng nhập trước khi host công khai.

## 7. Phân công xác nhận và thứ tự làm

| Người | Cần xác nhận / thực hiện |
|---|---|
| Quân | Duy trì quy ước; adapter prompt/Word; 10 tình huống tích hợp |
| Duyên | Ánh xạ registry, null, trang, phiên bản, quan hệ sửa đổi; phối hợp Luân thống nhất model/migration |
| Thanh | passage_id/text/metadata; nối BM25 với registry; top 10 có ID đúng |
| Luân | Giữ API tương thích; nối BM25; quyền hồ sơ; quyết định mở rộng research_result và snapshot nguồn |
| Phước | Đọc SourceHit/SourceDetail đúng; phân biệt trạng thái trả lời và thẩm định; không coi nguồn tìm thấy là kết luận |
| An | Hợp đồng kiểm tra đủ căn cứ và lọc dữ liệu trước khi gọi AI |
| Đan | Kiểm tra fixture và ánh xạ ID với benchmark; chỉ tính Recall@10 trên tập có nhãn nguồn |

Đầu tiên nhóm xác nhận bảng ánh xạ và các điểm mở. Sau đó các module làm song song bằng fixture. Cuối tuần thay bằng dữ liệu thật và kiểm thử luồng tạo hồ sơ → tìm kiếm → xem trang nguồn → lưu/mở lại lịch sử. Chỉ bật sinh câu trả lời khi bước kiểm tra căn cứ sẵn sàng.

## 8. Checklist kiểm tra tích hợp

- [ ] source_id và passage_id ánh xạ duy nhất, không thất lạc metadata.
- [ ] Điều 1a giữ nguyên; Khoản 0/Điểm rỗng chuyển null.
- [ ] Prompt nhận toàn văn, không chỉ snippet.
- [ ] Thiếu kỳ thuế trọng yếu → clarify; không đủ nguồn → abstain.
- [ ] ID trích dẫn không tồn tại bị chặn; không tự gán approved.
- [ ] Nguồn thiếu ngày hiệu lực không được đánh dấu đã xác minh áp dụng.
- [ ] Word có nhãn dự thảo và nguồn truy hồi được.
- [ ] Hồ sơ không được phép truy cập bị chặn; lịch sử còn sau khởi động lại.
- [ ] JSON mẫu không được nhập nhầm vào bộ luật thật hoặc benchmark nghiệm thu.

Các JSON trong `examples/week3_data_contract.json` chỉ minh họa cấu trúc, không phải văn bản luật hay kết quả kiểm thử pháp lý. Chưa có adapter thực thi được thêm bởi tài liệu này.

## 9. Quy trình chốt phiên bản

1. Mỗi người trả lời các điểm phụ trách trong WEEK_3_HANDOFF.md bằng “đồng ý” hoặc đề xuất cụ thể; Quân ghi lại người, ngày và quyết định.
2. Các điểm chưa đồng thuận tiếp tục mang nhãn đề xuất. Không coi sự im lặng là xác nhận.
3. Khi thống nhất, Quân cập nhật phiên bản tài liệu. Luân cập nhật API_CONTRACT.md và schema API cho thay đổi liên quan; Phước cập nhật kiểu dữ liệu tương ứng.
4. Thay đổi phá vỡ tương thích phải thống nhất thời điểm chuyển đổi và người cập nhật các module phụ thuộc trước khi merge.

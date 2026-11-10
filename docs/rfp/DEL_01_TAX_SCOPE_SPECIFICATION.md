# 📑 ĐẶC TẢ PHẠM VI NGHIỆP VỤ THUẾ VIỆT NAM (DEL_01 / RES_01)
## DỰ ÁN: VIETNAM TAX RESEARCH COPILOT WITH CITATIONS (VN-TAX-COPILOT)

* **Mã yêu cầu RFP:** `DEL 01` (Discovery & Scope Register), `RES 01` (Tax Category & Period Capture), `RES 04` (Legal Hierarchy).
* **Khách hàng giả định:** THTax ([thtax.vn](https://thtax.vn))
* **Tác giả:** Đặng Minh Quân (Product Owner / Business Analyst)
* **Phiên bản:** 1.0 - Sprint 0 Baseline

---

## 1. MỤC TIÊU & PHẠM VI HỆ THỐNG (SCOPE BOUNDARIES)

Hệ thống **VN-tax-copilot** được thiết kế nhằm hỗ trợ các chuyên viên tư vấn thuế, kế toán trưởng và kiểm toán viên thực hiện việc nghiên cứu, tra cứu, đối chiếu và trích dẫn các quy định pháp luật Thuế tại Việt Nam.

### 1.1. Ba sắc thuế trọng điểm trong phạm vi (In-Scope):
1. **Thuế Giá trị gia tăng (GTGT / VAT):**
   * Đối tượng chịu thuế, đối tượng không chịu thuế, đối tượng áp dụng thuế suất 0%, 5%, 10%.
   * Điều kiện và nguyên tắc khấu trừ thuế GTGT đầu vào.
   * Các trường hợp hoàn thuế GTGT (dự án đầu tư, xuất khẩu).
2. **Thuế Thu nhập doanh nghiệp (TNDN / CIT):**
   * Doanh thu tính thuế và phương pháp tính thuế.
   * Các khoản chi phí được trừ và không được trừ khi xác định thu nhập chịu thuế.
   * Thuế suất phổ thông và thuế suất ưu đãi, miễn giảm thuế theo địa bàn / ngành nghề.
   * Quy định về chuyển lỗ và trích lập các quỹ.
3. **Thuế Thu nhập cá nhân (TNCN / PIT):**
   * Thu nhập từ tiền lương, tiền công; thu nhập từ kinh doanh; thu nhập từ đầu tư vốn, chuyển nhượng vốn, bất động sản.
   * Quy định về cư trú (cá nhân cư trú vs. cá nhân không cư trú).
   * Các khoản thu nhập được miễn thuế, giảm thuế.
   * Giảm trừ gia cảnh cho bản thân và người phụ thuộc, đóng bảo hiểm bắt buộc.
   * Biểu thuế lũy tiến từng phần và biểu thuế toàn phần.
4. **Quy định hỗ trợ liên quan (Cross-Cutting Regulations):**
   * **Quản lý thuế:** Kê khai, thời hạn nộp tờ khai, nộp thuế, xử phạt vi phạm hành chính, tiền chậm nộp.
   * **Hóa đơn điện tử (HĐĐT):** Thời điểm lập hóa đơn, định dạng hóa đơn, hóa đơn điều chỉnh/thay thế, xử lý sai sót.

### 1.2. Các nội dung nằm ngoài phạm vi (Out-of-Scope - RFP Section 1 trang 3):
* Không thực hiện kê khai thuế tự động, không nộp tờ khai lên cổng Thuế điện tử (eTax).
* Không thực hiện thanh toán tiền thuế, không đại diện người nộp thuế trước cơ quan thuế.
* Không tự động phát hành hóa đơn điện tử hoặc can thiệp vào hệ thống hóa đơn của Tổng cục Thuế.
* Không đưa ra lời khuyên pháp lý cuối cùng mà không có sự kiểm tra, phê duyệt của chuyên gia con người (Human-in-the-loop review).

---

## 2. DANH MỤC NGUỒN VĂN BẢN PHÁP LUẬT CỐT LÕI (LEGAL INVENTORY)

Dựa trên Phụ lục Annex F của RFP, hệ thống thu thập và pháp điển hóa các văn bản nền tảng:

| STT | Sắc thuế / Lĩnh vực | Văn bản cốt lõi | Văn bản sửa đổi / Hướng dẫn thi hành | Ghi chú hiệu lực |
| :-: | :--- | :--- | :--- | :--- |
| **1** | **Thuế GTGT** | **Luật số 48/2024/QH15** | Nghị định hướng dẫn thi hành, Thông tư hướng dẫn khấu trừ | Có hiệu lực từ 01/07/2025 |
| **2** | **Thuế TNDN** | **Luật số 67/2025/QH15** | Nghị định hướng dẫn chi phí được trừ, Thông tư ưu đãi thuế | Văn bản nền tảng áp dụng kỳ mới |
| **3** | **Thuế TNCN** | **Luật số 109/2025/QH15** | Nghị định biểu thuế, Thông tư giảm trừ gia cảnh | Áp dụng cho kỳ tính thuế tương ứng |
| **4** | **Quản lý thuế**| **Luật số 108/2025/QH15** | Nghị định xử phạt vi phạm hành chính, cưỡng chế nợ thuế | Quy định thủ tục chung |
| **5** | **Hóa đơn điện tử**| **Nghị định 123/2020/NĐ-CP**| **Nghị định 70/2025/NĐ-CP** (Sửa đổi, bổ sung NĐ 123) | Có hiệu lực từ 01/06/2025 |
| **6** | **Luật sửa đổi 2026**| **Luật số 09/2026/QH16** | Luật sửa đổi một số điều của Luật Thuế GTGT, TNDN, TNCN | Lưu ý các quy định chuyển tiếp |

---

## 3. NGUYÊN TẮC THỨ BẬC PHÁP LÝ (LEGAL HIERARCHY - RES 04)

Hệ thống tuân thủ nghiêm ngặt Luật Ban hành văn bản quy phạm pháp luật (`R01 - Law 64/2025/QH15 & Law 87/2025/QH15`):

```text
Cấp 1: Hiến pháp, Luật, Nghị quyết của Quốc hội (Giá trị pháp lý cao nhất)
  ▲
Cấp 2: Nghị định của Chính phủ
  ▲
Cấp 3: Thông tư của Bộ Tài chính
  ▲
Cấp 4: Công văn hướng dẫn hành chính (Cục Thuế, Tổng cục Thuế) & Giải đáp Q&A
```

### ⚠️ Quy tắc bắt buộc đối với Công văn (Administrative Letter):
* **Công văn không phải là văn bản quy phạm pháp luật chung.**
* Một Công văn chỉ có giá trị trả lời và áp dụng đối với đúng **đối tượng nhận (người nộp thuế cụ thể)** và **tình huống thực tế được nêu trong công văn đó**.
* Hệ thống khi trích dẫn Công văn **bắt buộc phải hiển thị cảnh báo**: Cơ quan ban hành, ngày ban hành, người nhận và giới hạn áp dụng, không được tự ý xem công văn là luật chung.

---

## 4. QUY TẮC HIỆU LỰC THEO THỜI GIAN (TEMPORAL APPLICABILITY - RES 05)

1. Khi người dùng đặt câu hỏi, hệ thống phải xác định **Kỳ tính thuế (Tax Period)** và **Thời điểm diễn ra giao dịch (Transaction Date)**:
   * Nếu giao dịch diễn ra trong năm 2024: Áp dụng văn bản có hiệu lực trong năm 2024.
   * Nếu giao dịch diễn ra từ sau ngày văn bản mới có hiệu lực: Áp dụng quy định mới kèm điều khoản chuyển tiếp.
2. Không bao giờ dùng luật mới để suy diễn ngược cho nghĩa vụ thuế đã phát sinh và hoàn tất trong quá khứ nếu luật không quy định hiệu lực hồi tố.

---

## 5. CẤU TRÚC CHUẨN CỦA CÂU TRẢ LỜI NGHIÊN CỨU THUẾ (RES 03)

Mọi câu trả lời của VN-tax-copilot bắt buộc phải tuân theo khung chuẩn 6 phần:
1. **Vấn đề pháp lý (Legal Issue):** Tóm tắt câu hỏi thuế cần giải quyết.
2. **Sự kiện & Giả định (Relevant Facts & Assumptions):** Nêu rõ bối cảnh (Ví dụ: Doanh nghiệp kê khai theo phương pháp khấu trừ, cá nhân cư trú...).
3. **Căn cứ pháp lý áp dụng (Applicable Authority):** Trích dẫn chính xác đến cấp **Điều, Khoản, Điểm** của văn bản còn hiệu lực.
4. **Phân tích chi tiết (Analysis):** Lập luận giải thích lý do vì sao điều khoản đó áp dụng vào tình huống này.
5. **Giới hạn & Lưu ý loại trừ (Limitations):** Nêu rõ các rủi ro, ngoại lệ hoặc điều kiện đi kèm.
6. **Bước nghiên cứu tiếp theo (Suggested Next Steps):** Đề xuất kiểm tra thêm hồ sơ chứng từ thanh toán, hợp đồng hoặc công văn giải trình.

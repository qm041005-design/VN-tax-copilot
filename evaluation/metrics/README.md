# Hướng dẫn sử dụng chương trình Recall@10

## 1. Giới thiệu

Chương trình `recall_at_10.py` được viết bằng Python nhằm kiểm tra khả năng tìm kiếm chứng cứ của hệ thống VN Tax Research Copilot. Nội dung này thuộc yêu cầu EVAL 05 và AT 03 trong tài liệu RFP của dự án.

Recall@10 được tính bằng số chứng cứ cần thiết tìm thấy trong 10 đoạn văn bản đầu tiên chia cho tổng số chứng cứ cần tìm. Macro Recall@10 là kết quả trung bình của tất cả câu hỏi có thể trả lời.

## 2. Yêu cầu

Máy tính cần cài đặt Python phiên bản 3.10 trở lên. Chương trình sử dụng các thư viện có sẵn của Python nên không cần cài đặt thêm.

## 3. Cách chạy chương trình

Mở Terminal trong VS Code tại thư mục VN-tax-copilot, sau đó nhập lệnh:

```
python .\evaluation\metrics\recall_at_10.py --benchmark .\evaluation\datasets\benchmark_test.json --retrieval .\evaluation\datasets\retrieval_test.json
```

## 4. Dữ liệu sử dụng

Chương trình sử dụng hai file JSON:

- `benchmark_test.json`: Chứa các câu hỏi mẫu và chứng cứ cần tìm.
- `retrieval_test.json`: Chứa kết quả tìm kiếm của từng câu hỏi.

Hiện tại, hai file này chỉ chứa dữ liệu giả lập để kiểm tra chương trình, chưa phải dữ liệu đánh giá chính thức của dự án.

## 5. Kết quả chương trình

Sau khi chạy, chương trình sẽ hiển thị Recall@10 của từng câu hỏi, kết quả trung bình, thống kê theo nhóm thuế và nguồn chứng cứ.

Kết quả cũng được lưu vào file `evaluation/metrics/recall_report.json` để có thể xem lại khi cần.

Trong lần kiểm thử với 2 câu hỏi mẫu, chương trình cho kết quả:

- Câu VN-TAX-001: 100%
- Câu VN-TAX-002: 50%
- Macro Recall@10: 75%

## 6. Lưu ý

Theo yêu cầu AT 03 của dự án, Macro Recall@10 cần đạt tối thiểu 90% trên 200 câu hỏi có thể trả lời.

Hiện tại, chương trình mới được kiểm tra bằng 2 câu hỏi giả lập nên chưa thể kết luận hệ thống đạt yêu cầu. Khi có đầy đủ dữ liệu benchmark và kết quả tìm kiếm thực tế, có thể sử dụng chương trình để đánh giá chính thức.
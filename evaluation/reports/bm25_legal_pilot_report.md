# BAO CAO KIEM THU BM25 - LEGAL PILOT

## 1. Thong tin kiem thu

- Du an: VN-tax-copilot
- Module: BM25 Retrieval
- Ngay kiem thu: 20/11/2026
- Du lieu: 24 cau hoi draft, 55 doan luat
- Pham vi: VAT, CIT, PIT
- Trang thai: PILOT - CHUA DANH GIA CHINH THUC

## 2. Ket qua

| Chi so | Ket qua |
|---|---|
| So cau hoi | 24 |
| Macro Recall@10 (pilot) | 100% |
| Top 1 khop nhan bang chung | 21/24 (87.5%) |
| Top 1 khong khop nhan | 3/24 (12.5%) |
| Top 1 sai van ban | 1/24 |

## 3. Cac truong hop can xem xet

### VN-TAX-001

- Cau hoi: Tim van ban 48/2024/QH15
- BM25 Top 1: Passage 28, van ban 67/2025/QH15
- Bang chung dung xuat hien tai hang: 2, 3, 4, 10
- Phat hien: Top 1 khong dung van ban duoc hoi.

### VN-TAX-010

- Cau hoi: Hai nguong doanh thu tai Dieu 10
- BM25 Top 1: Passage 29
- Bang chung nhom 1: Passage 26, hang 4
- Bang chung nhom 2: Passage 27, hang 3
- Phat hien: Top 1 khong thuoc nhan bang chung, nhung Top 10 co du hai nhom.

### VN-TAX-014

- Cau hoi: Phan biet diem b va c, khoan 2, Dieu 11
- BM25 Top 1: Passage 31
- Bang chung nhom 1: Passage 32, hang 2
- Bang chung nhom 2: Passage 33, hang 3
- Phat hien: Top 1 khong thuoc nhan bang chung, nhung Top 10 co du hai nhom.

## 4. Nhan xet

- BM25 tim du cac nhom bang chung theo nhan hien tai trong Top 10.
- Ba cau co Top 1 khong khop nhan bang chung.
- Can xem xet cai thien xep hang theo so hieu van ban, dieu, khoan va diem.
- Ket qua chua duoc reviewer xac nhan.

## 5. Gioi han

- Benchmark hien tai chi co 24 cau hoi draft, chua du 250 cau.
- Macro Recall@10 100% chi la ket qua pilot.
- Bao cao danh gia chinh thuc van o trang thai NOT_EVALUATED.
- Chua ket luan chat luong truy hoi tren du lieu thuc te day du.

## 6. De xuat

1. Nhom retrieval kiem tra lai cach xep hang BM25.
2. Nhom du lieu xac nhan cac nhan bang chung.
3. Chay lai kiem thu khi co benchmark 250 cau duoc duyet.

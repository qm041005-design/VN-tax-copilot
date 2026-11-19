"""
app/models/base_mixins.py  –  HÀM DÙNG CHUNG CHO CÁC MODEL
==========================================================
Chỉ chứa `utcnow()`: trả về thời điểm hiện tại theo giờ UTC (có múi giờ).
RFP (DAT 04) yêu cầu log/audit dùng UTC; khi hiển thị cho người dùng
thì frontend đổi sang Asia/Ho_Chi_Minh.
"""
from datetime import datetime, timezone


def utcnow() -> datetime:
    return datetime.now(timezone.utc)

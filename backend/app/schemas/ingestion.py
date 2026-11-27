"""Internal parser boundary. Invalid supplied dates must never become null."""
import re
from datetime import date, datetime, time
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.services.legal_metadata import clause_label


OcrStatus = Literal["RAW", "VERIFIED", "NEEDS_REVIEW"]
ReviewStatus = Literal["PENDING", "APPROVED", "REJECTED"]


def legal_date(value):
    """Legal calendar dates, not instants. Reject times/zones rather than truncate."""
    if value is None:
        return None
    if isinstance(value, datetime):
        if value.tzinfo is not None or value.time() != time.min:
            raise ValueError("Ngày pháp lý phải là ngày, không có giờ hoặc múi giờ.")
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", value.strip()):
        return date.fromisoformat(value.strip())
    raise ValueError("Ngày phải có dạng YYYY-MM-DD hoặc null nếu chưa biết.")


class LegalDates(BaseModel):
    model_config = ConfigDict(extra="forbid")
    issue_date: date | None = None
    effective_date: date | None = None
    expiry_date: date | None = None

    @field_validator("issue_date", "effective_date", "expiry_date", mode="before")
    @classmethod
    def dates(cls, value):
        return legal_date(value)

    @model_validator(mode="after")
    def ordered(self):
        if self.effective_date and self.expiry_date and self.expiry_date <= self.effective_date:
            raise ValueError("expiry_date phải sau effective_date (mốc kết thúc không bao gồm ngày đó).")
        return self


class DocumentInput(LegalDates):
    doc_code: str = Field(min_length=1, max_length=100)
    title: str = Field(min_length=1, max_length=500)
    doc_type: Literal["LUAT", "NGHI_DINH", "THONG_TU", "CONG_VAN", "UNKNOWN"]
    hierarchy_level: int = Field(ge=1, le=5)
    issuer: str | None = Field(default=None, max_length=200)
    preamble: str | None = None  # căn cứ / mở đầu trước Điều 1; parser lặp lại ở từng đoạn
    ocr_quality_status: OcrStatus = "RAW"
    expert_review_status: ReviewStatus = "PENDING"
    source_url: str | None = Field(default=None, max_length=1000)
    total_pages: int | None = Field(default=None, ge=1, strict=True)
    version: str = Field(default="1.0", min_length=1, max_length=50)
    amends_doc_code: str | None = Field(default=None, max_length=100)
    replaces_doc_code: str | None = Field(default=None, max_length=100)

    @field_validator("doc_code", "title", "version")
    @classmethod
    def nonblank(cls, value):
        if not value.strip():
            raise ValueError("Không được để trống.")
        return value.strip()


class ChunkInput(LegalDates):
    article_number: str = Field(min_length=1, max_length=20)
    article_title: str | None = Field(default=None, max_length=300)
    article_intro: str | None = None
    clause_number: str | None = Field(default=None, max_length=20)
    clause_intro: str | None = None
    point_letter: str | None = Field(default=None, max_length=10)
    citation_path: str = Field(min_length=1, max_length=500)
    content: str = Field(min_length=1)
    source_page: int | None = Field(default=None, ge=1, strict=True)
    hierarchy_level: int = Field(ge=1, le=5)
    source_url: str | None = Field(default=None, max_length=1000)
    doc_type: str | None = None
    version: str | None = None
    amends_doc_code: str | None = None
    replaces_doc_code: str | None = None
    status: str | None = None
    preamble: str | None = None
    ocr_quality_status: OcrStatus | None = None  # chất lượng OCR theo trang của đoạn; thiếu -> lấy của văn bản
    expert_review_status: ReviewStatus | None = None

    @field_validator("clause_number", mode="before")
    @classmethod
    def clause(cls, value):
        if value is not None and type(value) not in (str, int):
            raise ValueError("Số Khoản phải là chuỗi hoặc số nguyên.")
        return clause_label(value)

    @field_validator("point_letter", mode="before")
    @classmethod
    def point(cls, value):
        return value.strip() or None if isinstance(value, str) else value

    @field_validator("article_number", "citation_path")
    @classmethod
    def nonblank(cls, value):
        if not value.strip():
            raise ValueError("Không được để trống.")
        return value.strip()

    @field_validator("content")
    @classmethod
    def nonblank_content(cls, value):
        if not value.strip():
            raise ValueError("Không được để trống.")
        return value


class ImportInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    document: DocumentInput
    chunks: list[ChunkInput] = Field(min_length=1)
    tax_types: list[Literal["VAT", "CIT", "PIT"]] = Field(default_factory=list)
    as_of: date

    @field_validator("as_of", mode="before")
    @classmethod
    def reference_date(cls, value):
        if value is None:
            raise ValueError("Cần ngày đối chiếu rõ ràng.")
        return legal_date(value)

    @model_validator(mode="after")
    def consistent_metadata(self):
        # Đoạn mở đầu là metadata cấp văn bản: parser lặp ở mọi đoạn ("" = không có) -> gom về văn bản, phải thống nhất
        preambles = {c.preamble.strip() for c in self.chunks if c.preamble and c.preamble.strip()}
        if self.document.preamble is None and len(preambles) == 1:
            self.document.preamble = preambles.pop()
        elif preambles - {(self.document.preamble or "").strip()}:
            raise ValueError("preamble ở các đoạn không khớp văn bản.")
        # Duyệt/từ chối là quyết định của chuyên gia trong hệ thống, không nhận qua file nạp
        if {self.document.expert_review_status, *(c.expert_review_status for c in self.chunks)} - {None, "PENDING"}:
            raise ValueError("expert_review_status chỉ nhận PENDING khi nạp; phê duyệt do chuyên gia ghi trong hệ thống.")
        expected = {"LUAT": 1, "NGHI_DINH": 2, "THONG_TU": 3, "CONG_VAN": 4, "UNKNOWN": 5}
        if expected[self.document.doc_type] != self.document.hierarchy_level:
            raise ValueError("Loại văn bản không khớp hierarchy_level.")
        keys = ("issue_date", "expiry_date", "version", "amends_doc_code", "replaces_doc_code")
        for i, chunk in enumerate(self.chunks):
            for key in keys:
                # Omitted/null duplicate metadata is inherited; any supplied value must agree.
                value = getattr(chunk, key)
                if value is not None and value != getattr(self.document, key):
                    raise ValueError(f"chunks[{i}].{key} không khớp metadata văn bản.")
            if chunk.doc_type not in (None, self.document.doc_type):
                raise ValueError(f"chunks[{i}].doc_type không khớp văn bản.")
            if chunk.hierarchy_level != self.document.hierarchy_level:
                raise ValueError(f"chunks[{i}].hierarchy_level không khớp văn bản.")
            if (chunk.effective_date and self.document.expiry_date
                    and chunk.effective_date >= self.document.expiry_date):
                raise ValueError(f"chunks[{i}].effective_date phải trước ngày hết hiệu lực của văn bản.")
            if (chunk.source_page and self.document.total_pages
                    and chunk.source_page > self.document.total_pages):
                raise ValueError(f"chunks[{i}].source_page vượt số trang PDF.")
        return self

"""Internal parser boundary. Invalid supplied dates must never become null."""
import re
from datetime import date, datetime, time
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.services.legal_metadata import clause_label


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
    source_url: str | None = Field(default=None, max_length=1000)
    version: str = Field(default="1.0", min_length=1, max_length=50)
    amends_doc_code: str | None = Field(default=None, max_length=100)

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
    point_letter: str | None = Field(default=None, max_length=5)
    citation_path: str = Field(min_length=1, max_length=500)
    content: str = Field(min_length=1)
    source_page: int | None = Field(default=None, ge=1, strict=True)
    hierarchy_level: int = Field(ge=1, le=5)
    # Parser metadata is validated against the parent, not passed to ORM blindly.
    source_url: str | None = None
    doc_type: str | None = None
    version: str | None = None
    amends_doc_code: str | None = None
    replaces_doc_code: str | None = None
    status: str | None = None

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

    @field_validator("article_number", "citation_path", "content")
    @classmethod
    def nonblank(cls, value):
        if not value.strip():
            raise ValueError("Không được để trống.")
        return value.strip()


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
        expected = {"LUAT": 1, "NGHI_DINH": 2, "THONG_TU": 3, "CONG_VAN": 4, "UNKNOWN": 5}
        if expected[self.document.doc_type] != self.document.hierarchy_level:
            raise ValueError("Loại văn bản không khớp hierarchy_level.")
        keys = ("issue_date", "effective_date", "expiry_date", "source_url", "version", "amends_doc_code")
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
            if chunk.replaces_doc_code is not None:
                raise ValueError("Quan hệ thay thế chưa được importer này lưu; cần adapter registry riêng.")
        return self

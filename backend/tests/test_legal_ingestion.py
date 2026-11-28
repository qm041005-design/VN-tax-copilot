import json
from copy import deepcopy
from datetime import date, datetime
from pathlib import Path

import pytest
from pydantic import ValidationError
from sqlalchemy import func, select

from app.core.database import SessionLocal
from app.models import LegalDocument, LegalChunk, LegalDocumentTaxScope
from app.schemas.ingestion import ImportInput, legal_date
from app.services.legal_ingestion_service import ingest_legal_document
from app.services.source_service import search, to_detail
from backend.scripts.export_bm25_retrieval import retrieve_benchmark
from backend.scripts.profile_bm25 import profile
from backend.scripts.review_bm25 import digest, review, write_bundle
from data_pipeline.parser.chunker import chunk_legal_document
from tests.helpers import auth


@pytest.fixture
def payload():
    return {
        "document": {"doc_code": "FIXTURE-IMPORT", "title": "Synthetic document",
                     "doc_type": "LUAT", "hierarchy_level": 1,
                     "effective_date": "2024-01-01", "expiry_date": "2025-01-01"},
        "chunks": [{"article_number": "1a", "clause_number": "1a", "point_letter": "",
                    "content": "Intro and fixture_tax evidence.", "citation_path": "Fixture 1a",
                    "article_intro": "Intro", "clause_intro": "", "source_page": 2,
                    "hierarchy_level": 1, "doc_type": "LUAT", "source_url": None,
                    "effective_date": "2024-01-01", "expiry_date": "2025-01-01",
                    "status": "CON_HIEU_LUC", "version": "1.0",
                    "amends_doc_code": None, "replaces_doc_code": None}],
        "as_of": "2025-01-01", "tax_types": ["VAT", "VAT"],
    }


def test_import_round_trip_and_exclusive_expiry(client, payload):
    with SessionLocal.begin() as db:
        receipt = ingest_legal_document(db, payload)
        assert receipt.temporal_status == "HET_HIEU_LUC"
    with SessionLocal() as db:
        row = db.get(LegalChunk, receipt.chunk_ids[0])
        assert to_detail(row).khoan == "1a"
        assert to_detail(row).dieu == "1a"
        assert to_detail(row).content == payload["chunks"][0]["content"]
        # Importer không lưu status của parser -> nguồn hiện trạng thái tính từ ngày (hết hạn 2025-01-01)
        assert to_detail(row).status == "HET_HIEU_LUC"
        assert db.scalar(select(func.count()).select_from(LegalDocumentTaxScope)) == 1
        assert search(db, "fixture_tax", as_of=date(2024, 12, 31))
        assert search(db, "fixture_tax", as_of=date(2025, 1, 1)) == []
        assert search(db, "fixture_tax", as_of=date(2026, 1, 1), tax_period="2024", tax_type="VAT")


def test_public_excerpt_search_and_recall_share_passage_ids(client):
    fixture = Path(__file__).parent / "fixtures" / "public_law_excerpt.json"
    excerpt = json.loads(fixture.read_text(encoding="utf-8"))
    document = {key: excerpt[key] for key in (
        "doc_code", "title", "doc_type", "hierarchy_level", "source_url", "effective_date", "expiry_date"
    )}
    document["version"] = "pilot-excerpt-1"
    chunks = chunk_legal_document(
        excerpt["text"], document["doc_code"], document["hierarchy_level"], excerpt["pdf_page"], document
    )
    assert [chunk["article_number"] for chunk in chunks] == excerpt["expected_articles"]
    with SessionLocal.begin() as db:
        receipt = ingest_legal_document(db, {
            "document": document, "chunks": chunks, "tax_types": ["VAT"], "as_of": "2026-11-14",
        })

    headers = auth("alice", "thtax")
    response = client.get("/api/v1/sources/search", headers=headers, params={
        "q": excerpt["query"], "tax_type": "VAT", "as_of": "2026-11-14",
    })
    assert response.status_code == 200
    hits = response.json()
    top = hits[0]
    assert top["source_id"] == str(receipt.chunk_ids[0])
    assert top["legal_identifier"] == document["doc_code"]
    assert (top["dieu"], top["khoan"], top["diem"]) == ("1", None, None)
    assert top["url"] == document["source_url"]
    assert top["source_page"] == excerpt["pdf_page"]
    assert top["version"] == document["version"]
    assert top["effective_date"] is None and top["expiry_date"] is None
    detail = client.get(f"/api/v1/sources/{top['source_id']}", headers=headers)
    assert detail.json()["content"] == chunks[0]["content"]

    with SessionLocal() as db:
        results = retrieve_benchmark(db, {"cases": [
            {"case_id": "PUBLIC-EXCERPT", "answerability": "answerable", "category": "VAT",
             "question": excerpt["query"], "research_as_of": "2026-11-14"},
        ]})
    assert results == [{"case_id": "PUBLIC-EXCERPT", "retrieved_passage_ids": [hit["source_id"] for hit in hits]}]


def test_recall_export_takes_top_ten_after_tax_and_period_filters(client, payload):
    chunk = payload["chunks"][0]
    payload["chunks"] = [dict(chunk, article_number=str(i), citation_path=f"Điều {i}") for i in range(1, 13)]
    other = deepcopy(payload)
    other["document"]["doc_code"] = "FIXTURE-CIT"
    other["tax_types"] = ["CIT"]

    with SessionLocal.begin() as db:
        ingest_legal_document(db, other)
        receipt = ingest_legal_document(db, payload)

    case = {"case_id": "HISTORY", "answerability": "answerable", "category": "VAT",
            "question": "fixture_tax", "tax_period": "2024", "research_as_of": "2026-11-14"}
    expected_ids = [str(chunk_id) for chunk_id in receipt.chunk_ids[:10]]
    response = client.get("/api/v1/sources/search", headers=auth("alice", "thtax"), params={
        "q": case["question"], "tax_type": "VAT", "tax_period": "2024", "as_of": "2026-11-14",
    })
    assert response.status_code == 200
    assert [hit["source_id"] for hit in response.json()] == expected_ids

    with SessionLocal() as db:
        results = retrieve_benchmark(db, {"cases": [case]})
        assert results == [{"case_id": "HISTORY", "retrieved_passage_ids": expected_ids}]
        case["tax_period"] = None
        assert retrieve_benchmark(db, {"cases": [case]})[0]["retrieved_passage_ids"] == []


def test_profile_matches_backend_ids_metadata_and_reports_missing_evidence(client, payload):
    chunk = payload["chunks"][0]
    payload["chunks"] = [
        dict(chunk, article_number=str(i), citation_path=f"Điều {i}") for i in range(1, 13)
    ]
    with SessionLocal.begin() as db:
        receipt = ingest_legal_document(db, payload)
    ids = [str(pid) for pid in receipt.chunk_ids]
    case = {"case_id": "PROFILE", "answerability": "answerable", "category": "VAT",
            "question": "fixture_tax", "tax_period": "2024",
            "required_evidence": [
                {"evidence_id": "FOUND", "acceptable_passage_ids": [ids[0]]},
                {"evidence_id": "RANK", "acceptable_passage_ids": [ids[-1]]},
                {"evidence_id": "ABSENT", "acceptable_passage_ids": ["999999"]},
            ]}
    with SessionLocal() as db:
        result = profile(db, {"cases": [case]}, repeats=2)
        actual = result["cases"][0]
        expected = retrieve_benchmark(db, {"cases": [case]})[0]
        assert actual["retrieved_passage_ids"] == expected["retrieved_passage_ids"] == ids[:10]
        assert actual["top10"][0]["source_id"] == actual["top10"][0]["passage_id"] == ids[0]
        assert actual["top10"][0]["source_page"] == 2
        assert actual["top10"][0]["khoan"] == "1a"
        assert len(actual["timing_samples"]) == 2
        assert actual["recall_at_10"] == 1 / 3
        assert [e["reason"] for e in actual["evidence_results"]] == [None, "below_top10", "missing_from_registry"]
        assert result["acceptance_status"] == "NOT_EVALUATED"
        assert db.scalar(select(func.count(LegalChunk.id))) == 12


def test_profile_preserves_filters_and_leaves_unlabeled_recall_unknown(client, payload):
    with SessionLocal.begin() as db:
        receipt = ingest_legal_document(db, payload)
    cases = [
        {"case_id": "UNLABELED", "answerability": "answerable", "category": "VAT",
         "question": "fixture_tax", "tax_period": "2024"},
        {"case_id": "FILTERED", "answerability": "answerable", "category": "CIT",
         "question": "fixture_tax", "tax_period": "2024",
         "required_evidence": [{"evidence_id": "FILTER", "acceptable_passage_ids": [str(receipt.chunk_ids[0])]}]},
        {"case_id": "TRAP", "answerability": "ambiguous", "question": "fixture_tax"},
    ]
    with SessionLocal() as db:
        result = profile(db, {"cases": cases}, repeats=1)
    assert result["cases"][0]["recall_at_10"] is None
    assert result["cases"][1]["retrieved_passage_ids"] == []
    assert result["cases"][1]["evidence_results"][0]["reason"] == "excluded_by_filters"
    assert result["skipped_case_ids"] == ["TRAP"]


def test_review_measures_anchor_fix_on_same_snapshot_and_preserves_registry(client, payload, tmp_path):
    payload["document"]["doc_code"] = "99/2099/NĐ-CP"
    template = payload["chunks"][0]
    payload["chunks"] = [dict(template, article_number=str(index), clause_number="2", point_letter="a",
                               content="Tham chiếu Điều 12b Khoản 1a Điểm đ", citation_path=f"Điều {index}")
                         for index in range(1, 15)]
    payload["chunks"].append(dict(template, article_number="12b", point_letter="đ",
                                  content="Nội dung mẫu ở vị trí cần tìm", citation_path="Điểm đ Khoản 1a Điều 12b"))
    with SessionLocal.begin() as db:
        receipt = ingest_legal_document(db, payload)
    target = str(receipt.chunk_ids[-1])
    benchmark = {"cases": [{"case_id": "ANCHOR", "category": "VAT", "answerability": "answerable",
        "question": "Điểm đ Khoản 1a Điều 12b 99 / 2099 / ND - CP", "tax_period": "2024",
        "review_status": "draft", "required_evidence": [{"evidence_id": "E1", "description": "Synthetic anchor",
                                                       "source_id": "99/2099/NĐ-CP", "acceptable_passage_ids": [target]}]}]}
    with SessionLocal() as db:
        bundle = review(db, benchmark, repeats=2)
        expected = retrieve_benchmark(db, benchmark)
        api = client.get("/api/v1/sources/search", params={"q": benchmark["cases"][0]["question"],
                         "tax_type": "VAT", "tax_period": "2024"}, headers=auth("alice", "thtax"))
        assert api.status_code == 200
        assert [row["source_id"] for row in api.json()] == expected[0]["retrieved_passage_ids"]
        assert bundle["retrieval"] == expected
        assert expected[0]["retrieved_passage_ids"][0] == target
        assert bundle["comparison"]["baseline_macro_recall_at_10"] == 0
        assert bundle["comparison"]["current_macro_recall_at_10"] == 1
        assert bundle["comparison"]["improved_case_ids"] == ["ANCHOR"]
        assert bundle["comparison"]["acceptance_status"] == "NOT_EVALUATED"
        assert bundle["current"]["cases"][0]["review_status"] == "draft"
        assert db.scalar(select(func.count(LegalChunk.id))) == 15
        corpus = bundle["corpus"]
        assert [row["passage_id"] for row in corpus["passages"]] == [str(pid) for pid in receipt.chunk_ids]
        assert corpus["passages"][-1]["diem"] == "đ"
        assert corpus["passages"][-1]["source_page"] == 2
        assert corpus["passages"][-1]["tax_types"] == ["VAT"]
        assert corpus["passages"][-1]["content"] == payload["chunks"][-1]["content"]
        assert corpus["snapshot_sha256"] == digest({key: corpus[key] for key in ("documents", "tax_scopes", "passages")})
    folder = tmp_path / "review"
    write_bundle(bundle, folder)
    assert json.loads((folder / "retrieval.json").read_text(encoding="utf-8")) == expected
    round_trip = json.loads((folder / "corpus.json").read_text(encoding="utf-8"))
    assert round_trip["snapshot_sha256"] == digest({key: round_trip[key] for key in ("documents", "tax_scopes", "passages")})
    assert "Synthetic anchor" in (folder / "evidence.csv").read_text(encoding="utf-8-sig")
    with pytest.raises(ValueError, match="đã tồn tại"):
        write_bundle(bundle, folder)


def test_review_explains_missing_filtered_and_unmatched_evidence(client, payload):
    with SessionLocal.begin() as db:
        receipt = ingest_legal_document(db, payload)
    target = str(receipt.chunk_ids[0])
    cases = [{"case_id": "FILTER", "question": "fixture_tax", "category": "CIT", "answerability": "answerable",
              "required_evidence": [{"evidence_id": "E1", "acceptable_passage_ids": [target]}]},
             {"case_id": "MISSING", "question": "fixture_tax", "answerability": "answerable",
              "required_evidence": [{"evidence_id": "E2", "acceptable_passage_ids": ["999999"]}]},
             {"case_id": "WORDS", "question": "no_matching_terms", "answerability": "answerable",
              "required_evidence": [{"evidence_id": "E3", "acceptable_passage_ids": [target]}]},
             {"case_id": "DATES", "question": "fixture_tax", "category": "VAT", "tax_period": "2026",
              "answerability": "answerable", "required_evidence": [{"evidence_id": "E4", "acceptable_passage_ids": [target]}]},
             {"case_id": "TYPE", "question": "fixture_tax", "category": "VAT", "doc_type": "THONG_TU",
              "answerability": "answerable", "required_evidence": [{"evidence_id": "E5", "acceptable_passage_ids": [target]}]}]
    for case in cases:
        case.setdefault("category", "VAT")
    with SessionLocal() as db:
        bundle = review(db, {"cases": cases}, repeats=1)
        assert bundle["retrieval"] == retrieve_benchmark(db, {"cases": cases})
    assert bundle["comparison"]["missing_evidence_by_reason"] == {
        "excluded_by_filters": 3, "missing_from_registry": 1, "no_token_overlap": 1}
    assert bundle["comparison"]["regressed_case_ids"] == []


def test_profile_rejects_duplicate_evidence_ids(client, payload):
    case = {"case_id": "DUP", "question": "fixture_tax", "answerability": "answerable",
            "required_evidence": [{"evidence_id": "E", "acceptable_passage_ids": ["1"]}] * 2}
    with SessionLocal() as db, pytest.raises(ValueError, match="evidence_id"):
        profile(db, {"cases": [case]}, repeats=1)


@pytest.mark.parametrize("clause", [None, "", " ", 0, "0"])
def test_absent_clause_maps_to_null_in_api(client, payload, clause):
    payload["chunks"][0]["clause_number"] = clause
    with SessionLocal.begin() as db:
        result = ingest_legal_document(db, payload)
    with SessionLocal() as db:
        assert to_detail(db.get(LegalChunk, result.chunk_ids[0])).khoan is None


@pytest.mark.parametrize("field", ["issue_date", "effective_date", "expiry_date"])
@pytest.mark.parametrize("bad", ["invalid", "", "2024-02-30", "01/01/2024", 1700000000, True])
def test_invalid_document_date_writes_nothing(client, payload, field, bad):
    payload["document"][field] = bad
    with SessionLocal() as db:
        with pytest.raises(ValidationError):
            ingest_legal_document(db, payload)
        assert db.scalar(select(func.count()).select_from(LegalDocument)) == 0
        assert db.scalar(select(func.count()).select_from(LegalChunk)) == 0


@pytest.mark.parametrize("expiry", ["2023-12-31", "2024-01-01"])
def test_inverted_or_empty_interval_rejected(client, payload, expiry):
    payload["document"]["expiry_date"] = expiry
    with SessionLocal() as db, pytest.raises(ValidationError):
        ingest_legal_document(db, payload)


def test_bad_second_chunk_does_not_partially_import(client, payload):
    bad = deepcopy(payload["chunks"][0])
    bad["expiry_date"] = "invalid"
    payload["chunks"].append(bad)
    with SessionLocal() as db:
        with pytest.raises(ValidationError):
            ingest_legal_document(db, payload)
        assert db.scalar(select(func.count()).select_from(LegalDocument)) == 0


def test_conflicting_chunk_metadata_rejected(client, payload):
    # Ngày hiệu lực riêng của đoạn được phép khác văn bản (SCRUM-31); phiên bản thì phải khớp
    payload["chunks"][0]["version"] = "2.0"
    with SessionLocal() as db, pytest.raises(ValidationError):
        ingest_legal_document(db, payload)


@pytest.mark.parametrize("chunk_date", ["2023-12-01", "2024-02-01"])
def test_import_preserves_passage_metadata_and_filters_by_its_effective_date(client, payload, chunk_date):
    payload["document"].update(total_pages=3, replaces_doc_code="FIXTURE-OLDER",
                               source_url="https://example.invalid/document", version="2.0")
    chunk = payload["chunks"][0]
    chunk.update(effective_date=chunk_date, point_letter="đ", clause_intro="Mở đầu Khoản",
                 replaces_doc_code="FIXTURE-OLDER", source_url="https://example.invalid/document#page=2",
                 version="2.0", content="  Intro and fixture_tax evidence.\n")
    with SessionLocal.begin() as db:
        receipt = ingest_legal_document(db, payload)

    with SessionLocal() as db:
        stored = db.get(LegalChunk, receipt.chunk_ids[0])
        assert (stored.article_intro, stored.clause_intro, stored.version) == ("Intro", "Mở đầu Khoản", "2.0")
        assert (stored.document.total_pages, stored.document.replaces_doc_code) == (3, "FIXTURE-OLDER")
        assert stored.status == "CHUA_XAC_DINH"

    headers = auth("alice", "thtax")
    before = client.get("/api/v1/sources/search", headers=headers, params={
        "q": "fixture_tax", "tax_type": "VAT", "as_of": "2023-11-30",
    })
    assert before.status_code == 200 and before.json() == []
    response = client.get("/api/v1/sources/search", headers=headers, params={
        "q": "fixture_tax", "tax_type": "VAT", "as_of": chunk_date,
    })
    assert response.status_code == 200
    hit, = response.json()
    assert hit["source_id"] == str(receipt.chunk_ids[0])
    assert (hit["dieu"], hit["khoan"], hit["diem"], hit["source_page"]) == ("1a", "1a", "đ", 2)
    assert hit["effective_date"] == f"{chunk_date}T00:00:00" and hit["expiry_date"] == "2025-01-01T00:00:00"
    assert hit["url"] == chunk["source_url"]
    assert hit["version"] == "2.0"
    detail = client.get(f"/api/v1/sources/{hit['source_id']}", headers=headers)
    assert detail.json()["content"] == chunk["content"]


def test_import_rejects_passage_effective_date_after_document_expiry(client, payload):
    payload["chunks"][0].update(effective_date="2025-01-01", expiry_date=None)
    with SessionLocal() as db, pytest.raises(ValidationError, match="phải trước ngày hết hiệu lực"):
        ingest_legal_document(db, payload)


def test_duplicate_preserves_ids_and_content(client, payload):
    with SessionLocal.begin() as db:
        first = ingest_legal_document(db, payload)
    payload["chunks"][0]["content"] = "Changed content must not overwrite citation."
    with SessionLocal() as db:
        with pytest.raises(ValueError, match="Mã văn bản"):
            ingest_legal_document(db, payload)
        assert db.get(LegalChunk, first.chunk_ids[0]).content == "Intro and fixture_tax evidence."
        assert db.scalar(select(func.count()).select_from(LegalDocument)) == 1


def test_caller_can_rollback_import(client, payload):
    with SessionLocal() as db:
        ingest_legal_document(db, payload)
        db.rollback()
    with SessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(LegalDocument)) == 0


@pytest.mark.parametrize("as_of,expected", [("2023-12-31", "CHUA_CO_HIEU_LUC"),
                                          ("2024-01-01", "CON_HIEU_LUC"),
                                          ("2025-01-01", "HET_HIEU_LUC"),
                                          ("2025-01-02", "HET_HIEU_LUC")])
def test_temporal_status_does_not_trust_parser(client, payload, as_of, expected):
    payload["as_of"] = as_of
    payload["chunks"][0]["status"] = "CON_HIEU_LUC"
    with SessionLocal.begin() as db:
        assert ingest_legal_document(db, payload).temporal_status == expected


def test_missing_dates_remain_unknown(client, payload):
    for obj in [payload["document"], payload["chunks"][0]]:
        obj["effective_date"] = obj["expiry_date"] = None
    with SessionLocal.begin() as db:
        result = ingest_legal_document(db, payload)
        assert result.temporal_status == "CHUA_XAC_DINH"
        assert db.get(LegalDocument, result.document_id).expiry_date is None


def test_parser_naive_midnight_datetime_is_accepted(payload):
    payload["document"]["effective_date"] = datetime(2024, 1, 1)
    assert ImportInput.model_validate(payload).document.effective_date == date(2024, 1, 1)


@pytest.mark.parametrize("value", ["2024-01-01T00:00:00Z", datetime(2024, 1, 1, 12)])
def test_times_are_not_silently_truncated(value):
    with pytest.raises(ValueError):
        legal_date(value)


# --- SCRUM-36 + SCRUM-38/40: dữ liệu nạp bằng importer phải đi qua được bộ đánh giá AI của An ---
@pytest.mark.parametrize("period,expected", [("2023", "CHUA_CO_HIEU_LUC"), ("2024", "CON_HIEU_LUC"),
                                             ("2025", "HET_HIEU_LUC")])
def test_status_gui_guardrails_tinh_tu_ngay_theo_ky_thue(client, payload, period, expected):
    from app.services.guarded_research_service import research_from_rows
    with SessionLocal.begin() as db:
        chunk_id = ingest_legal_document(db, payload).chunk_ids[0]
    seen = []
    with SessionLocal() as db:
        research_from_rows("q", [(db.get(LegalChunk, chunk_id), 1)], tax_period=period, material_facts="Giả lập",
                           assess=lambda safe: seen.append(safe.passages[0]["status"]) or [])
    assert seen == [expected]


def test_assessor_cua_an_goi_model_voi_du_lieu_tu_importer(client, payload):
    """Trước đây status luôn CHUA_XAC_DINH -> assessor của An chặn hết, không bao giờ gọi model."""
    from ai_engine.guardrails.llm_assessor import make_assessor
    from app.services.guarded_research_service import research_from_rows
    with SessionLocal.begin() as db:
        chunk_id = ingest_legal_document(db, payload).chunk_ids[0]
    calls = []

    def completion(messages):
        calls.append(messages)
        return {"context_complete": True, "query_supported": False, "conflicts_resolved": True,
                "assessments": [{"passage_id": str(chunk_id), "sufficient": False, "reason_code": "unsupported"}]}
    with SessionLocal() as db:
        research_from_rows("q", [(db.get(LegalChunk, chunk_id), 1)], tax_period="2024", material_facts="Giả lập",
                           assess=make_assessor(completion))
    assert len(calls) == 1


def test_ma_thue_tieng_viet_va_ngay_het_hieu_luc_cua_doan(client, payload):
    payload["tax_types"] = ["TNDN", "GTGT", "VAT"]
    payload["chunks"][0].update(expiry_date="2024-07-01", tax_types=["TNDN"])
    with SessionLocal.begin() as db:
        receipt = ingest_legal_document(db, payload)
    with SessionLocal() as db:
        chunk = db.get(LegalChunk, receipt.chunk_ids[0])
        assert chunk.document.tax_types == ["CIT", "VAT"] and chunk.tax_types == ["CIT"]
        assert chunk.expiry_date == datetime(2024, 7, 1)
        assert db.scalars(select(LegalDocumentTaxScope.tax_type)).all() == ["CIT", "VAT"]
        # Khoản bị bãi bỏ từ 01/07/2024 -> không còn xuất hiện khi tra cứu sau ngày đó
        assert search(db, "fixture_tax", as_of=date(2024, 3, 1))
        assert search(db, "fixture_tax", as_of=date(2024, 8, 1)) == []


def test_ngay_het_hieu_luc_cua_doan_sau_van_ban_bi_tu_choi(client, payload):
    payload["chunks"][0]["expiry_date"] = "2026-01-01"
    with pytest.raises(ValidationError, match="expiry_date"):
        ImportInput.model_validate(payload)

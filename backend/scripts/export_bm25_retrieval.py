"""Run backend BM25 against the legal registry and export results for Recall@10."""

import argparse
import json
from pathlib import Path
from tempfile import mkstemp

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.schemas.ingestion import legal_date
from app.schemas.matter import TaxType
from app.services.source_service import search


FILTERABLE_TAX_TYPES = {tax_type.value for tax_type in TaxType}


def benchmark_search_options(case: dict) -> dict:
    category = case.get("category")
    if category not in FILTERABLE_TAX_TYPES | {"TAX_ADMIN", "E_INVOICE", None}:
        raise ValueError("category không hợp lệ.")
    return {
        "doc_type": case.get("doc_type"),
        "as_of": legal_date(case.get("research_as_of")),
        "tax_period": case.get("tax_period"),
        "tax_type": category if category in FILTERABLE_TAX_TYPES else None,
    }


def retrieve_benchmark(db: Session, benchmark: dict) -> list[dict]:
    results = []
    for case in benchmark["cases"]:
        if case["answerability"] != "answerable":
            continue

        case_id = case["case_id"]
        try:
            rows = search(db, case["question"], limit=10, **benchmark_search_options(case))
        except ValueError as exc:
            raise ValueError(f"{case_id}: {exc}") from exc

        results.append({
            "case_id": case_id,
            "retrieved_passage_ids": [str(chunk.id) for chunk, _score in rows],
        })
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--benchmark", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.benchmark.resolve() == args.output.resolve():
        parser.error("Hãy chọn tệp đầu ra khác tệp benchmark.")

    try:
        benchmark = json.loads(args.benchmark.read_text(encoding="utf-8-sig"))
        with SessionLocal.begin() as db:
            if db.get_bind().dialect.name == "postgresql":
                # Use a single corpus snapshot even if ingestion runs during the export.
                db.execute(text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY"))
            results = retrieve_benchmark(db, benchmark)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        fd, temp_name = mkstemp(dir=args.output.parent)
        temporary = Path(temp_name)
        try:
            with open(fd, "w", encoding="utf-8") as output:
                json.dump(results, output, ensure_ascii=False, indent=2)
                output.write("\n")
            temporary.replace(args.output)
        finally:
            temporary.unlink(missing_ok=True)
    except (OSError, KeyError, TypeError, ValueError) as exc:
        parser.exit(1, f"{exc}\n")


if __name__ == "__main__":
    main()

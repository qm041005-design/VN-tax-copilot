"""Import one reviewed parser export into the configured legal registry."""

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from app.core.database import SessionLocal
from app.services.legal_ingestion_service import ingest_legal_document


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    args = parser.parse_args()

    try:
        payload = json.loads(args.input.read_text(encoding="utf-8-sig"))
        with SessionLocal.begin() as db:
            receipt = ingest_legal_document(db, payload)
    except (OSError, ValueError) as exc:
        parser.exit(1, f"{exc}\n")

    print(json.dumps(asdict(receipt), ensure_ascii=False))


if __name__ == "__main__":
    main()

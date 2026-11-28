"""Build a fresh SQLite registry for the bundled retrieval benchmark."""
import argparse
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory

from sqlalchemy import URL, create_engine
from sqlalchemy.orm import Session

from app.core.database import Base
from app.models import LegalChunk, LegalDocument, LegalDocumentTaxScope
from app.services.legal_ingestion_service import ingest_legal_document
from data_pipeline.parser.chunker import chunk_legal_document


def build_snapshot(output: Path):
    sources = json.loads(Path(__file__).with_name("sources.json").read_text(encoding="utf-8"))
    tables = [LegalDocument.__table__, LegalChunk.__table__, LegalDocumentTaxScope.__table__]
    output.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(dir=output.parent) as folder:
        temporary = Path(folder) / "registry.sqlite3"
        engine = create_engine(URL.create("sqlite", database=str(temporary)))
        try:
            Base.metadata.create_all(engine, tables=tables)
            with Session(engine) as db, db.begin():
                for source in sources:
                    document = source["document"]
                    chunks = []
                    for page in source["pages"]:
                        parsed = chunk_legal_document(
                            page["text"], document["doc_code"], document["hierarchy_level"],
                            page["source_page"], document,
                        )
                        if not parsed:
                            raise ValueError(f"Page without passages: {document['doc_code']} / {page['source_page']}")
                        chunks.extend(parsed)
                    ingest_legal_document(db, {
                        "document": document, "chunks": chunks,
                        "tax_types": [source["tax_type"]], "as_of": "2026-11-20",
                    })
        finally:
            engine.dispose()
        # Publish only a complete registry. An existing destination is preserved.
        os.link(temporary, output)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path, help="New SQLite database path")
    build_snapshot(parser.parse_args().output)

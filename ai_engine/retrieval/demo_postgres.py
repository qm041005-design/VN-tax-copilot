import os
from json import dumps

import psycopg
from psycopg.rows import dict_row

from .bm25 import BM25Retriever


def prepare_demo(connection):
    connection.execute("CREATE EXTENSION IF NOT EXISTS vector")
    connection.execute("CREATE SCHEMA IF NOT EXISTS retrieval_demo")
    connection.execute("""
        CREATE TABLE IF NOT EXISTS retrieval_demo.passages (
            passage_id integer PRIMARY KEY,
            legal_identifier text NOT NULL,
            text text NOT NULL,
            embedding vector(3) NOT NULL
        )
    """)
    passages = [
        (1, "01/2099/NĐ-CP", "Hoàn thuế GTGT cho hàng xuất khẩu", "[1,0,0]"),
        (2, "02/2099/NĐ-CP", "Hồ sơ đề nghị hoàn thuế GTGT", "[0.8,0.2,0]"),
        (3, "03/2099/TT-BTC", "Đăng ký sử dụng hóa đơn điện tử", "[0,1,0]"),
    ]
    with connection.cursor() as cursor:
        cursor.executemany("""
            INSERT INTO retrieval_demo.passages
                (passage_id, legal_identifier, text, embedding)
            VALUES (%s, %s, %s, %s::vector)
            ON CONFLICT (passage_id) DO UPDATE SET
                legal_identifier = EXCLUDED.legal_identifier,
                text = EXCLUDED.text,
                embedding = EXCLUDED.embedding
        """, passages)


def search_vector(connection, query_vector, limit=10):
    return connection.execute("""
        SELECT passage_id, legal_identifier, text,
               embedding <=> %s::vector AS distance
        FROM retrieval_demo.passages
        ORDER BY distance, passage_id
        LIMIT %s
    """, (dumps(query_vector, allow_nan=False), limit)).fetchall()


def main():
    with psycopg.connect(
        host="127.0.0.1",
        port=5432,
        dbname="vntax_copilot",
        user=os.getenv("VNTAX_DEMO_DB_USER") or "postgres",
        password=os.getenv("VNTAX_DEMO_DB_PASSWORD"),
        connect_timeout=5,
        row_factory=dict_row,
    ) as connection:
        prepare_demo(connection)
        passages = connection.execute("""
            SELECT passage_id, legal_identifier, text
            FROM retrieval_demo.passages
            ORDER BY passage_id
        """).fetchall()

        bm25_hits = BM25Retriever(passages).search("02/2099/NĐ-CP")
        vector_hits = search_vector(connection, [1, 0, 0], limit=2)

    print("BM25:", [hit["passage_id"] for hit in bm25_hits])
    print("pgvector:", [hit["passage_id"] for hit in vector_hits])


if __name__ == "__main__":
    main()

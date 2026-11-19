import os
from json import dumps
from pathlib import Path

import psycopg
from fastembed import TextEmbedding
from psycopg.rows import dict_row

from .demo_postgres import prepare_demo

MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
EXACT_QUERY = "Đăng ký sử dụng hóa đơn điện tử"
PARAPHRASED_QUERY = "Làm sao nhận lại tiền VAT đã nộp khi bán hàng ra nước ngoài?"


def vector_parameter(embedding):
    return dumps(embedding.tolist(), allow_nan=False)


def save_embeddings(connection, encoder, passages):
    connection.execute("""
        CREATE TABLE IF NOT EXISTS retrieval_demo.passage_embeddings (
            passage_id integer REFERENCES retrieval_demo.passages(passage_id)
                ON DELETE CASCADE,
            model_name text NOT NULL,
            embedding vector(384) NOT NULL,
            PRIMARY KEY (passage_id, model_name)
        )
    """)
    embeddings = encoder.embed([passage["text"] for passage in passages])
    rows = [
        (passage["passage_id"], MODEL, vector_parameter(embedding))
        for passage, embedding in zip(passages, embeddings, strict=True)
    ]
    with connection.cursor() as cursor:
        cursor.executemany("""
            INSERT INTO retrieval_demo.passage_embeddings
                (passage_id, model_name, embedding)
            VALUES (%s, %s, %s::vector)
            ON CONFLICT (passage_id, model_name) DO UPDATE
            SET embedding = EXCLUDED.embedding
        """, rows)


def search_semantic(connection, encoder, question, limit=2):
    query_vector = next(encoder.embed(question))
    return connection.execute("""
        SELECT p.passage_id, p.legal_identifier, p.text,
               e.embedding <=> %s::vector AS distance
        FROM retrieval_demo.passage_embeddings AS e
        JOIN retrieval_demo.passages AS p USING (passage_id)
        WHERE e.model_name = %s
        ORDER BY distance, p.passage_id
        LIMIT %s
    """, (vector_parameter(query_vector), MODEL, limit)).fetchall()


def main():
    cache_dir = Path.cwd().parent / "VN-tax-model-cache"
    print(f"Đang nạp model. Thư mục cache: {cache_dir}", flush=True)
    encoder = TextEmbedding(model_name=MODEL, cache_dir=str(cache_dir))

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
            SELECT passage_id, text
            FROM retrieval_demo.passages
            ORDER BY passage_id
        """).fetchall()

        save_embeddings(connection, encoder, passages)
        exact_hits = search_semantic(connection, encoder, EXACT_QUERY, limit=1)
        semantic_hits = search_semantic(connection, encoder, PARAPHRASED_QUERY)

    print(f"Đã lưu {len(passages)} embedding, mỗi vector có {encoder.embedding_size} chiều.")
    for query, hits in ((EXACT_QUERY, exact_hits), (PARAPHRASED_QUERY, semantic_hits)):
        print(f"\nTruy vấn: {query}")
        for hit in hits:
            print(f"  {hit['passage_id']} | {hit['text']} | distance={hit['distance']:.4f}")


if __name__ == "__main__":
    main()

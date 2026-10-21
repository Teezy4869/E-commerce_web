"""Persistent content-hash cache for embeddings from a configured image encoder."""

import json


class VisualEmbeddingRepository:
    def __init__(self, catalog_repository):
        self.catalog = catalog_repository
        with self.catalog._connect() as db:
            db.execute("""CREATE TABLE IF NOT EXISTS image_embeddings (
                encoder_id TEXT NOT NULL,
                content_sha256 TEXT NOT NULL,
                embedding_json TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (encoder_id, content_sha256)
            )""")

    def get(self, encoder_id, digest):
        with self.catalog._connect() as db:
            row = db.execute("SELECT embedding_json FROM image_embeddings WHERE encoder_id = ? AND content_sha256 = ?",
                             (encoder_id, digest)).fetchone()
            return json.loads(row["embedding_json"]) if row else None

    def put(self, encoder_id, digest, embedding):
        with self.catalog._connect() as db:
            db.execute("""INSERT OR REPLACE INTO image_embeddings (encoder_id, content_sha256, embedding_json)
                VALUES (?, ?, ?)""", (encoder_id, digest, json.dumps(embedding)))

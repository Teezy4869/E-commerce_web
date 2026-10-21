"""Persistent customer preferences and atomic AI request limits."""

import json
import sqlite3
import time
from contextlib import contextmanager


class ShoppingAIRepository:
    def __init__(self, db_path):
        self.db_path = db_path
        with self._connect() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS shopping_preferences (
                    customer_id INTEGER PRIMARY KEY REFERENCES customers(id) ON DELETE CASCADE,
                    style TEXT NOT NULL DEFAULT '', colors_json TEXT NOT NULL DEFAULT '[]',
                    budget_vnd INTEGER NOT NULL DEFAULT 0 CHECK(budget_vnd >= 0),
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS ai_rate_windows (
                    actor TEXT NOT NULL, feature TEXT NOT NULL, window_start INTEGER NOT NULL,
                    count INTEGER NOT NULL, PRIMARY KEY(actor, feature)
                );
            """)

    @contextmanager
    def _connect(self):
        db = sqlite3.connect(self.db_path, timeout=10)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys = ON")
        try:
            yield db
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    def preferences(self, customer_id):
        with self._connect() as db:
            row = db.execute("SELECT style, colors_json, budget_vnd FROM shopping_preferences WHERE customer_id=?", (customer_id,)).fetchone()
        return {"style": row["style"], "colors": json.loads(row["colors_json"]), "budget_vnd": row["budget_vnd"]} if row else {"style": "", "colors": [], "budget_vnd": 0}

    def save_preferences(self, customer_id, preferences):
        with self._connect() as db:
            db.execute("""INSERT INTO shopping_preferences(customer_id,style,colors_json,budget_vnd)
                VALUES (?,?,?,?) ON CONFLICT(customer_id) DO UPDATE SET
                style=excluded.style, colors_json=excluded.colors_json,
                budget_vnd=excluded.budget_vnd, updated_at=CURRENT_TIMESTAMP""",
                (customer_id, preferences["style"], json.dumps(preferences["colors"], ensure_ascii=False), preferences["budget_vnd"]))
        return preferences

    def consume(self, actor, feature, limit, period=60):
        now = int(time.time())
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT window_start,count FROM ai_rate_windows WHERE actor=? AND feature=?", (actor, feature)).fetchone()
            if row and now - row["window_start"] < period:
                if row["count"] >= limit:
                    return False
                db.execute("UPDATE ai_rate_windows SET count=count+1 WHERE actor=? AND feature=?", (actor, feature))
            else:
                db.execute("""INSERT INTO ai_rate_windows(actor,feature,window_start,count) VALUES (?,?,?,1)
                    ON CONFLICT(actor,feature) DO UPDATE SET window_start=excluded.window_start,count=1""", (actor, feature, now))
            if now % 100 == 0:
                db.execute("DELETE FROM ai_rate_windows WHERE window_start < ?", (now - 3600,))
        return True

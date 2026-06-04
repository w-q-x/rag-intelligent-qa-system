import os
import sqlite3
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv

load_dotenv()


class DatabaseManager:
    """SQLite connection and persistence helpers."""

    def __init__(self):
        self.db_path = os.getenv("CONVERSATION_DB_PATH", "data/conversation.db")
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self.conn = None
        self._connect()
        self._create_tables()

    def _connect(self):
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row

    def _create_tables(self):
        cursor = self.conn.cursor()

        cursor.execute(
            '''
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id VARCHAR(36) UNIQUE NOT NULL,
                user_id VARCHAR(128),
                title TEXT,
                status VARCHAR(16) DEFAULT 'active',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            '''
        )

        cursor.execute(
            '''
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id VARCHAR(36) NOT NULL,
                role VARCHAR(16) CHECK(role IN ('user', 'assistant', 'system')) NOT NULL,
                content TEXT NOT NULL,
                turn_number INTEGER,
                metadata TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            '''
        )

        cursor.execute(
            '''
            CREATE TABLE IF NOT EXISTS big_chunks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                big_chunk_id VARCHAR(36) UNIQUE NOT NULL,
                doc_id VARCHAR(36),
                text TEXT NOT NULL,
                token_count INTEGER,
                metadata TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            '''
        )

        cursor.execute('CREATE INDEX IF NOT EXISTS idx_messages_conversation ON messages(conversation_id, turn_number)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_big_chunks_id ON big_chunks(big_chunk_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_big_chunks_doc ON big_chunks(doc_id)')

        cursor.execute(
            '''
            CREATE TABLE IF NOT EXISTS feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id VARCHAR(36) NOT NULL,
                message_id INTEGER NOT NULL,
                rating VARCHAR(16) CHECK(rating IN ('like', 'dislike')) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            '''
        )
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_feedback_conversation ON feedback(conversation_id, message_id)')
        self.conn.commit()

    def add_feedback(self, conversation_id: str, message_id: int, rating: str) -> bool:
        if self.conn is None:
            self._connect()
        self.execute(
            'INSERT OR REPLACE INTO feedback (conversation_id, message_id, rating) VALUES (?, ?, ?)',
            (conversation_id, message_id, rating),
        )
        return True

    def get_feedback(self, conversation_id: str) -> list:
        return self.fetch_all(
            'SELECT * FROM feedback WHERE conversation_id = ? ORDER BY id',
            (conversation_id,),
        )

    def insert_big_chunk(
        self,
        big_chunk_id: str,
        doc_id: str,
        text: str,
        token_count: int,
        metadata: Optional[str] = None,
    ):
        cursor = self.execute(
            '''INSERT OR REPLACE INTO big_chunks
               (big_chunk_id, doc_id, text, token_count, metadata)
               VALUES (?, ?, ?, ?, ?)''',
            (big_chunk_id, doc_id, text, token_count, metadata),
        )
        return cursor.lastrowid

    def insert_big_chunks(self, big_chunks: List[Dict[str, Any]]) -> int:
        if not big_chunks:
            return 0

        if self.conn is None:
            self._connect()

        rows = [
            (
                chunk["big_chunk_id"],
                chunk["doc_id"],
                chunk["text"],
                chunk.get("token_count", 0),
                chunk.get("metadata"),
            )
            for chunk in big_chunks
        ]
        cursor = self.conn.cursor()
        cursor.executemany(
            '''INSERT OR REPLACE INTO big_chunks
               (big_chunk_id, doc_id, text, token_count, metadata)
               VALUES (?, ?, ?, ?, ?)''',
            rows,
        )
        self.conn.commit()
        return len(rows)

    def get_big_chunk(self, big_chunk_id: str) -> Optional[sqlite3.Row]:
        return self.fetch_one(
            'SELECT * FROM big_chunks WHERE big_chunk_id = ?',
            (big_chunk_id,),
        )

    def get_big_chunks_by_ids(self, big_chunk_ids: List[str]) -> list:
        if not big_chunk_ids:
            return []

        placeholders = ",".join(["?"] * len(big_chunk_ids))
        rows = self.fetch_all(
            f'SELECT * FROM big_chunks WHERE big_chunk_id IN ({placeholders})',
            tuple(big_chunk_ids),
        )
        row_map = {row["big_chunk_id"]: row for row in rows}
        return [row_map[chunk_id] for chunk_id in big_chunk_ids if chunk_id in row_map]

    def get_big_chunks_by_doc(self, doc_id: str) -> list:
        return self.fetch_all(
            'SELECT * FROM big_chunks WHERE doc_id = ? ORDER BY id',
            (doc_id,),
        )

    def delete_big_chunks_by_doc(self, doc_id: str):
        self.execute('DELETE FROM big_chunks WHERE doc_id = ?', (doc_id,))

    def clear_big_chunks(self):
        self.execute('DELETE FROM big_chunks')

    def execute(self, sql: str, params: Optional[tuple] = None) -> sqlite3.Cursor:
        if self.conn is None:
            self._connect()

        cursor = self.conn.cursor()
        if params:
            cursor.execute(sql, params)
        else:
            cursor.execute(sql)
        self.conn.commit()
        return cursor

    def fetch_one(self, sql: str, params: Optional[tuple] = None) -> Optional[sqlite3.Row]:
        if self.conn is None:
            self._connect()

        cursor = self.conn.cursor()
        if params:
            cursor.execute(sql, params)
        else:
            cursor.execute(sql)
        return cursor.fetchone()

    def fetch_all(self, sql: str, params: Optional[tuple] = None) -> list:
        if self.conn is None:
            self._connect()

        cursor = self.conn.cursor()
        if params:
            cursor.execute(sql, params)
        else:
            cursor.execute(sql)
        return cursor.fetchall()

    def add_user(self, user_id: str, username: str, password_hash: str) -> bool:
        try:
            self.execute(
                'INSERT INTO users (user_id, username, password_hash) VALUES (?, ?, ?)',
                (user_id, username, password_hash),
            )
            return True
        except Exception:
            return False

    def get_user_by_username(self, username: str):
        return self.fetch_one(
            'SELECT * FROM users WHERE username = ?',
            (username,),
        )

    def get_user_by_id(self, user_id: str):
        return self.fetch_one(
            'SELECT * FROM users WHERE user_id = ?',
            (user_id,),
        )

    def close(self):
        if self.conn:
            self.conn.close()
            self.conn = None


db_manager = DatabaseManager()

__all__ = ["DatabaseManager", "db_manager"]

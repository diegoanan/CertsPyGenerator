from __future__ import annotations

import csv
import os
import sqlite3
from typing import Any, Dict, List


class SubjectRepository:
    def __init__(self, db_path: str = "certs_subjects.db") -> None:
        self.db_path = db_path
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        directory = os.path.dirname(self.db_path)
        if directory:
            os.makedirs(directory, exist_ok=True)
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS subjects (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    C TEXT,
                    ST TEXT,
                    L TEXT,
                    O TEXT,
                    OU TEXT,
                    CN TEXT,
                    email TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

    def add_subject(self, subject: Dict[str, Any]) -> None:
        payload = {
            "name": str(subject.get("name", "")).strip(),
            "C": subject.get("C", ""),
            "ST": subject.get("ST", ""),
            "L": subject.get("L", ""),
            "O": subject.get("O", ""),
            "OU": subject.get("OU", ""),
            "CN": subject.get("CN", ""),
            "email": subject.get("email", "") or subject.get("emailAddress", ""),
        }
        if not payload["name"]:
            raise ValueError("Debe indicar un nombre para el perfil.")

        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO subjects (name, C, ST, L, O, OU, CN, email)
                VALUES (:name, :C, :ST, :L, :O, :OU, :CN, :email)
                """,
                payload,
            )

    def list_subjects(self) -> List[Dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute("SELECT * FROM subjects ORDER BY name").fetchall()
        return [dict(row) for row in rows]

    def get_subject(self, name: str) -> Dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM subjects WHERE name = ?", (name,)).fetchone()
        return dict(row) if row else None

    def delete_subject(self, name: str) -> None:
        with self._connect() as conn:
            conn.execute("DELETE FROM subjects WHERE name = ?", (name,))

    def export_csv(self, output_path: str) -> str:
        rows = self.list_subjects()
        with open(output_path, "w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=["name", "C", "ST", "L", "O", "OU", "CN", "email", "created_at"])
            writer.writeheader()
            writer.writerows(rows)
        return output_path

    def import_csv(self, csv_path: str) -> int:
        imported = 0
        with open(csv_path, "r", newline="", encoding="utf-8") as fh:
            reader = csv.DictReader(fh)
            for row in reader:
                if not row.get("name"):
                    continue
                self.add_subject(row)
                imported += 1
        return imported


class CertificateHistoryRepository:
    def __init__(self, db_path: str = "certs_history.db") -> None:
        self.db_path = db_path
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        directory = os.path.dirname(self.db_path)
        if directory:
            os.makedirs(directory, exist_ok=True)
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    kind TEXT NOT NULL,
                    path TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

    def add_entry(self, name: str, kind: str, path: str, status: str) -> Dict[str, Any]:
        with self._connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO history (name, kind, path, status)
                VALUES (?, ?, ?, ?)
                """,
                (name, kind, path, status),
            )
            row_id = cursor.lastrowid
            row = conn.execute("SELECT * FROM history WHERE id = ?", (row_id,)).fetchone()
        return dict(row)

    def list_entries(self) -> List[Dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute("SELECT * FROM history ORDER BY id DESC").fetchall()
        return [dict(row) for row in rows]

    def list_entries_by_kind(self, kind: str) -> List[Dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute("SELECT * FROM history WHERE kind = ? ORDER BY id DESC", (kind,)).fetchall()
        return [dict(row) for row in rows]

    def update_entry(self, entry_id: int, name: str, kind: str, path: str, status: str) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE history
                SET name = ?, kind = ?, path = ?, status = ?
                WHERE id = ?
                """,
                (name, kind, path, status, entry_id),
            )

    def delete_entry(self, entry_id: int) -> None:
        with self._connect() as conn:
            conn.execute("DELETE FROM history WHERE id = ?", (entry_id,))

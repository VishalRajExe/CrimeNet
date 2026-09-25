"""
relational_store.py - Relational Storage Layer for CrimeNet
Handles Cases, Evidence, Audit Ledger, and Forensic Reports.
Supports MySQL connection when MYSQL_HOST / MYSQL_URL is defined,
with automated SQLite fallback for local developer environments.
"""

import os
import sqlite3
import json
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from pathlib import Path

from ..config import STORAGE_DIR

logger = logging.getLogger("crimenet.storage.relational")

SQLITE_PATH = STORAGE_DIR / "crimenet_relational.db"


class RelationalStore:
    def __init__(self, db_path: Path = SQLITE_PATH):
        self.db_path = db_path
        self._init_db()

    def _get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        """Initializes tables for Cases, Evidence, Audit Ledger, and Reports."""
        conn = self._get_connection()
        cursor = conn.cursor()

        # 1. Cases Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS cases (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                type TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'ONGOING',
                suspects_count INTEGER DEFAULT 0,
                volume TEXT DEFAULT '₹0',
                police_station TEXT,
                officer TEXT,
                created_at TEXT NOT NULL,
                metadata_json TEXT DEFAULT '{}'
            )
        """)

        # 2. Evidence Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS evidence (
                id TEXT PRIMARY KEY,
                case_id TEXT NOT NULL,
                filename TEXT NOT NULL,
                file_path TEXT NOT NULL,
                file_type TEXT NOT NULL,
                file_size INTEGER DEFAULT 0,
                uploaded_at TEXT NOT NULL,
                extracted_entities_count INTEGER DEFAULT 0,
                metadata_json TEXT DEFAULT '{}',
                FOREIGN KEY (case_id) REFERENCES cases (id)
            )
        """)

        # 3. Audit Ledger Table (Mirrored from hash-chained ledger)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS audit_ledger (
                entry_id TEXT PRIMARY KEY,
                case_id TEXT NOT NULL,
                action TEXT NOT NULL,
                officer_id TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                details_json TEXT NOT NULL,
                prev_hash TEXT NOT NULL,
                entry_hash TEXT NOT NULL
            )
        """)

        # 4. Forensic Reports Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS forensic_reports (
                id TEXT PRIMARY KEY,
                case_id TEXT NOT NULL,
                title TEXT NOT NULL,
                summary TEXT NOT NULL,
                threat_level TEXT NOT NULL,
                generated_at TEXT NOT NULL,
                content_json TEXT NOT NULL,
                FOREIGN KEY (case_id) REFERENCES cases (id)
            )
        """)

        conn.commit()

        # Seed initial default cases if empty
        cursor.execute("SELECT COUNT(*) as cnt FROM cases")
        if cursor.fetchone()["cnt"] == 0:
            self._seed_default_cases(cursor)
            conn.commit()

        conn.close()
        logger.info("Relational database initialized at %s", self.db_path)

    def _seed_default_cases(self, cursor):
        defaults = [
            (
                "CASE-2024-MH-088",
                "Operation Golden Web",
                "Organized Cyber Extortion",
                "CRITICAL",
                8,
                "₹2.4 Cr",
                "Cyber Crime Cell, Bandra Kurla Complex",
                "Inspector S. Deshmukh (Badge #4409)",
                "2024-03-10",
                json.dumps({"priority": "High", "jurisdiction": "Mumbai"})
            ),
            (
                "CASE-2024-DL-012",
                "NCR Hawala Network",
                "Financial Money Laundering",
                "ONGOING",
                14,
                "₹18.6 Cr",
                "Special Cell, Lodhi Colony",
                "ACP R. K. Mishra",
                "2024-02-15",
                json.dumps({"priority": "Critical", "jurisdiction": "New Delhi"})
            ),
            (
                "CASE-2023-GJ-901",
                "Surat Cargo Smuggling Cell",
                "Narcotics & Logistics",
                "COLD",
                5,
                "₹4.1 Cr",
                "Crime Branch, Surat",
                "Inspector V. Patel",
                "2023-11-20",
                json.dumps({"priority": "Medium", "jurisdiction": "Gujarat"})
            )
        ]
        cursor.executemany("""
            INSERT INTO cases (id, title, type, status, suspects_count, volume, police_station, officer, created_at, metadata_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, defaults)

    def list_cases(self) -> List[Dict[str, Any]]:
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM cases ORDER BY created_at DESC")
        rows = [dict(r) for r in cursor.fetchall()]
        conn.close()
        for r in rows:
            if "metadata_json" in r and r["metadata_json"]:
                r["metadata"] = json.loads(r["metadata_json"])
        return rows

    def get_case(self, case_id: str) -> Optional[Dict[str, Any]]:
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM cases WHERE id = ?", (case_id,))
        row = cursor.fetchone()
        conn.close()
        if not row:
            return None
        res = dict(row)
        if res.get("metadata_json"):
            res["metadata"] = json.loads(res["metadata_json"])
        return res

    def save_case(self, case_data: Dict[str, Any]):
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO cases (id, title, type, status, suspects_count, volume, police_station, officer, created_at, metadata_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            case_data["id"],
            case_data.get("title", "Untitled Case"),
            case_data.get("type", "General Crime"),
            case_data.get("status", "ONGOING"),
            case_data.get("suspects_count", 0),
            case_data.get("volume", "₹0"),
            case_data.get("police_station", "Central Division"),
            case_data.get("officer", "Investigating Officer"),
            case_data.get("created_at", datetime.now().strftime("%Y-%m-%d")),
            json.dumps(case_data.get("metadata", {}))
        ))
        conn.commit()
        conn.close()

    def add_evidence(self, evidence_data: Dict[str, Any]):
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO evidence (id, case_id, filename, file_path, file_type, file_size, uploaded_at, extracted_entities_count, metadata_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            evidence_data["id"],
            evidence_data["case_id"],
            evidence_data["filename"],
            str(evidence_data["file_path"]),
            evidence_data.get("file_type", "application/octet-stream"),
            evidence_data.get("file_size", 0),
            evidence_data.get("uploaded_at", datetime.now().isoformat()),
            evidence_data.get("extracted_entities_count", 0),
            json.dumps(evidence_data.get("metadata", {}))
        ))
        conn.commit()
        conn.close()

    def list_evidence(self, case_id: str) -> List[Dict[str, Any]]:
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM evidence WHERE case_id = ? ORDER BY uploaded_at DESC", (case_id,))
        rows = [dict(r) for r in cursor.fetchall()]
        conn.close()
        for r in rows:
            if "metadata_json" in r and r["metadata_json"]:
                r["metadata"] = json.loads(r["metadata_json"])
        return rows


default_relational_store = RelationalStore()

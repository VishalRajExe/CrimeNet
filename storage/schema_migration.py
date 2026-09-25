"""CrimeNet Case-Oriented Schema Migration.

Ensures the 10 conceptual domain models are fully supported in MySQL:
1. Case               (existing `cases`, extended with metadata)
2. Evidence           (new `evidence` table, linked to case)
3. Entity             (existing `investigation_entities`, linked to case)
4. Relationship       (existing `entity_relationships`, linked to case)
5. AnalysisResult     (new `analysis_results` table, linked to case)
6. Alert              (new `alerts` table, linked to case)
7. TimelineEvent      (new `timeline_events` table, linked to case)
8. Report             (existing `reports`, linked to case)
9. AuditEvent         (existing `audit_logs`, extended with case_id)
10. Feedback          (new `feedback` table, linked to case)

Preserves ALL existing data in MySQL without breaking any existing columns or FKs.
"""

import os
import pymysql
from dotenv import load_dotenv

load_dotenv()

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", 3306))
DB_NAME = os.getenv("DB_NAME", "crimenet")
DB_USER = os.getenv("DB_USERNAME", "root")
DB_PASS = os.getenv("DB_PASSWORD", "admin")


def run_migration():
    print(f"Connecting to MySQL at {DB_HOST}:{DB_PORT}/{DB_NAME}...")
    conn = pymysql.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASS,
        database=DB_NAME,
        autocommit=True,
        cursorclass=pymysql.cursors.DictCursor
    )

    with conn.cursor() as cur:
        # 1. Inspect existing columns in `cases`
        cur.execute("SHOW COLUMNS FROM cases;")
        case_cols = {row["Field"] for row in cur.fetchall()}
        if "metadata" not in case_cols:
            print("Adding `metadata` column to `cases`...")
            cur.execute("ALTER TABLE cases ADD COLUMN metadata TEXT DEFAULT NULL;")
        else:
            print("`metadata` column already exists in `cases`.")

        # 2. Inspect existing columns in `audit_logs`
        cur.execute("SHOW COLUMNS FROM audit_logs;")
        audit_cols = {row["Field"] for row in cur.fetchall()}
        if "case_id" not in audit_cols:
            print("Adding `case_id` column to `audit_logs`...")
            cur.execute("ALTER TABLE audit_logs ADD COLUMN case_id VARCHAR(36) DEFAULT NULL, ADD KEY idx_audit_case (case_id);")
        else:
            print("`case_id` column already exists in `audit_logs`.")

        # 3. Create `evidence` table
        print("Ensuring `evidence` table exists...")
        cur.execute("""
        CREATE TABLE IF NOT EXISTS evidence (
            id VARCHAR(36) NOT NULL PRIMARY KEY,
            case_id VARCHAR(36) NOT NULL,
            title VARCHAR(200) NOT NULL,
            evidence_type VARCHAR(50) NOT NULL,
            source_ref VARCHAR(255) DEFAULT NULL,
            content LONGTEXT DEFAULT NULL,
            collected_at DATETIME DEFAULT NULL,
            collected_by VARCHAR(36) DEFAULT NULL,
            sha256_hash VARCHAR(64) DEFAULT NULL,
            metadata TEXT DEFAULT NULL,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            KEY idx_evidence_case (case_id),
            KEY idx_evidence_type (evidence_type),
            CONSTRAINT fk_evidence_case FOREIGN KEY (case_id) REFERENCES cases (id) ON DELETE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
        """)

        # Ensure extended evidence columns exist
        cur.execute("SHOW COLUMNS FROM evidence;")
        ev_cols = {row["Field"] for row in cur.fetchall()}
        ev_new_cols = {
            "filename": "VARCHAR(255) DEFAULT NULL",
            "processing_status": "VARCHAR(50) NOT NULL DEFAULT 'Uploaded'",
            "extraction_status": "VARCHAR(50) NOT NULL DEFAULT 'Pending'",
            "description": "TEXT DEFAULT NULL",
            "error_message": "TEXT DEFAULT NULL",
            "entity_count": "INT NOT NULL DEFAULT 0",
            "relation_count": "INT NOT NULL DEFAULT 0",
        }
        for col_name, col_type in ev_new_cols.items():
            if col_name not in ev_cols:
                print(f"Adding `{col_name}` column to `evidence`...")
                cur.execute(f"ALTER TABLE evidence ADD COLUMN `{col_name}` {col_type};")
            else:
                print(f"`{col_name}` column already exists in `evidence`.")

        # 4. Create `analysis_results` table
        print("Ensuring `analysis_results` table exists...")
        cur.execute("""
        CREATE TABLE IF NOT EXISTS analysis_results (
            id VARCHAR(36) NOT NULL PRIMARY KEY,
            case_id VARCHAR(36) NOT NULL,
            task_id VARCHAR(60) NOT NULL,
            algorithm VARCHAR(60) NOT NULL,
            parameters TEXT DEFAULT NULL,
            summary TEXT DEFAULT NULL,
            node_metrics LONGTEXT DEFAULT NULL,
            edge_metrics LONGTEXT DEFAULT NULL,
            executed_by VARCHAR(36) DEFAULT NULL,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            KEY idx_analysis_case (case_id),
            KEY idx_analysis_task (task_id),
            CONSTRAINT fk_analysis_case FOREIGN KEY (case_id) REFERENCES cases (id) ON DELETE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
        """)

        # 5. Create `alerts` table
        print("Ensuring `alerts` table exists...")
        cur.execute("""
        CREATE TABLE IF NOT EXISTS alerts (
            id VARCHAR(36) NOT NULL PRIMARY KEY,
            case_id VARCHAR(36) NOT NULL,
            alert_type VARCHAR(50) NOT NULL,
            severity ENUM('CRITICAL', 'HIGH', 'MEDIUM', 'LOW') NOT NULL DEFAULT 'MEDIUM',
            title VARCHAR(255) NOT NULL,
            explanation TEXT NOT NULL,
            subject VARCHAR(255) DEFAULT NULL,
            related_entities TEXT DEFAULT NULL,
            status ENUM('OPEN', 'REVIEWED', 'DISMISSED', 'ESCALATED') NOT NULL DEFAULT 'OPEN',
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            KEY idx_alerts_case (case_id),
            KEY idx_alerts_severity (severity),
            KEY idx_alerts_status (status),
            CONSTRAINT fk_alerts_case FOREIGN KEY (case_id) REFERENCES cases (id) ON DELETE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
        """)

        # 6. Create `timeline_events` table
        print("Ensuring `timeline_events` table exists...")
        cur.execute("""
        CREATE TABLE IF NOT EXISTS timeline_events (
            id VARCHAR(36) NOT NULL PRIMARY KEY,
            case_id VARCHAR(36) NOT NULL,
            event_type VARCHAR(50) NOT NULL,
            timestamp DATETIME NOT NULL,
            title VARCHAR(255) NOT NULL,
            description TEXT DEFAULT NULL,
            source_ref VARCHAR(100) DEFAULT NULL,
            primary_entity_id VARCHAR(36) DEFAULT NULL,
            secondary_entity_id VARCHAR(36) DEFAULT NULL,
            confidence DOUBLE NOT NULL DEFAULT 1.0,
            location VARCHAR(200) DEFAULT NULL,
            metadata TEXT DEFAULT NULL,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            KEY idx_timeline_case (case_id),
            KEY idx_timeline_ts (timestamp),
            KEY idx_timeline_event_type (event_type),
            CONSTRAINT fk_timeline_case FOREIGN KEY (case_id) REFERENCES cases (id) ON DELETE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
        """)

        # 7. Create `feedback` table (Human-in-the-Loop)
        print("Ensuring `feedback` table exists...")
        cur.execute("""
        CREATE TABLE IF NOT EXISTS feedback (
            id VARCHAR(36) NOT NULL PRIMARY KEY,
            case_id VARCHAR(36) NOT NULL,
            feedback_type VARCHAR(50) NOT NULL,
            target_id VARCHAR(100) NOT NULL,
            action ENUM('ACCEPTED', 'DISMISSED', 'FLAGGED', 'CONFIRMED') NOT NULL,
            notes TEXT DEFAULT NULL,
            user_id VARCHAR(36) DEFAULT NULL,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            KEY idx_feedback_case (case_id),
            KEY idx_feedback_target (target_id),
            KEY idx_feedback_type (feedback_type),
            CONSTRAINT fk_feedback_case FOREIGN KEY (case_id) REFERENCES cases (id) ON DELETE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
        """)

        # Ensure extended feedback columns exist for human-in-the-loop corrections
        cur.execute("SHOW COLUMNS FROM feedback;")
        fb_cols = {row["Field"] for row in cur.fetchall()}
        fb_new_cols = {
            "original_ai_result": "TEXT DEFAULT NULL",
            "corrected_value": "TEXT DEFAULT NULL",
            "reason": "TEXT DEFAULT NULL",
            "source_ref": "VARCHAR(255) DEFAULT NULL",
            "correction_status": "VARCHAR(50) NOT NULL DEFAULT 'PENDING'",
            "audit_id": "VARCHAR(36) DEFAULT NULL"
        }
        for col_name, col_type in fb_new_cols.items():
            if col_name not in fb_cols:
                print(f"Adding `{col_name}` column to `feedback`...")
                cur.execute(f"ALTER TABLE feedback ADD COLUMN `{col_name}` {col_type};")

        # 8. Create `investigation_actions` table (Workflow Actions: Lookout, Freeze, Review, Escalate)
        print("Ensuring `investigation_actions` table exists...")
        cur.execute("""
        CREATE TABLE IF NOT EXISTS investigation_actions (
            id VARCHAR(36) NOT NULL PRIMARY KEY,
            case_id VARCHAR(36) NOT NULL,
            action_type VARCHAR(60) NOT NULL,
            target_entity VARCHAR(255) NOT NULL,
            target_entity_type VARCHAR(50) DEFAULT NULL,
            reason TEXT NOT NULL,
            status VARCHAR(50) NOT NULL DEFAULT 'PENDING_APPROVAL',
            related_evidence VARCHAR(255) DEFAULT NULL,
            investigator_id VARCHAR(36) DEFAULT 'investigator',
            audit_id VARCHAR(36) DEFAULT NULL,
            notes TEXT DEFAULT NULL,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            KEY idx_actions_case (case_id),
            KEY idx_actions_type (action_type),
            KEY idx_actions_status (status),
            CONSTRAINT fk_actions_case FOREIGN KEY (case_id) REFERENCES cases (id) ON DELETE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
        """)

        # 9. Extended columns for `audit_logs` (Court-admissible, append-oriented investigation trail)
        cur.execute("SHOW COLUMNS FROM audit_logs;")
        audit_cols = {row["Field"] for row in cur.fetchall()}
        audit_new_cols = {
            "target": "VARCHAR(255) DEFAULT NULL",
            "old_value": "TEXT DEFAULT NULL",
            "new_value": "TEXT DEFAULT NULL",
            "source_ref": "VARCHAR(255) DEFAULT NULL",
            "result_id": "VARCHAR(64) DEFAULT NULL"
        }
        for col_name, col_type in audit_new_cols.items():
            if col_name not in audit_cols:
                print(f"Adding `{col_name}` column to `audit_logs`...")
                cur.execute(f"ALTER TABLE audit_logs ADD COLUMN `{col_name}` {col_type};")

        # 10. Extended columns for `reports`
        cur.execute("SHOW COLUMNS FROM reports;")
        rep_cols = {row["Field"] for row in cur.fetchall()}
        rep_new_cols = {
            "file_path": "VARCHAR(255) DEFAULT NULL",
            "format": "VARCHAR(20) NOT NULL DEFAULT 'TEXT'",
            "metadata": "TEXT DEFAULT NULL"
        }
        for col_name, col_type in rep_new_cols.items():
            if col_name not in rep_cols:
                print(f"Adding `{col_name}` column to `reports`...")
                cur.execute(f"ALTER TABLE reports ADD COLUMN `{col_name}` {col_type};")

        # 11. Verify all tables
        cur.execute("SHOW TABLES;")
        all_tables = [list(r.values())[0] for r in cur.fetchall()]
        print("\nMigration completed successfully! All tables in `crimenet`:")
        for tbl in sorted(all_tables):
            cur.execute(f"SELECT COUNT(*) AS cnt FROM `{tbl}`;")
            count = cur.fetchone()["cnt"]
            print(f"  - {tbl:<25}: {count} rows")

    conn.close()

if __name__ == "__main__":
    run_migration()

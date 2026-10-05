import sqlite3
from pathlib import Path
from datetime import datetime, timezone


SCHEMA = """
CREATE TABLE IF NOT EXISTS runs (
    run_id TEXT PRIMARY KEY,
    template TEXT NOT NULL,
    config_name TEXT,
    seed INTEGER,
    rows INTEGER,
    created_at TEXT NOT NULL    
);

CREATE TABLE IF NOT EXISTS findings (
    finding_id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL REFERENCES runs(run_id),
    rule_code TEXT NOT NULL,
    severity TEXT NOT NULL,
    row_id TEXT,
    field TEXT,
    observed_value TEXT,
    expected TEXT,
    message TEXT,
    detected_at TEXT
);

CREATE TABLE IF NOT EXISTS metrics (
    run_id TEXT NOT NULL REFERENCES runs(run_id),
    code TEXT NOT NULL,
    true_positives INTEGER,
    false_positives INTEGER,
    false_negatives INTEGER,
    precision REAL,
    recall REAL,
    f1 REAL,
    PRIMARY KEY (run_id, code)
);
"""

# persistence/db.py — añadir
DIMENSION_BY_CODE = {
    "DQ_01": "Completitud",
    "DQ_02": "Unicidad", 
    "DQ_03": "Unicidad",
    "DQ_04": "Validez", 
    "DQ_05": "Validez", 
    "DQ_06": "Validez",
    "DQ_09": "Validez", 
    "DQ_10": "Validez",
    "DQ_07": "Consistencia", 
    "DQ_08": "Consistencia", 
    "DQ_12": "Consistencia",
    "DQ_11": "Continuidad",
    "DQ_13": "Trazabilidad", 
    "DQ_14": "Trazabilidad",
}



def init_db(path: str) -> sqlite3.Connection:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.executescript(SCHEMA)
    return conn

def save_run(conn, run_id: str, template: str, config_name: str, seed: int, rows: int):
    conn.execute(
        "INSERT OR REPLACE INTO runs (run_id, template, config_name, seed, rows, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (run_id, template, config_name, seed, rows, datetime.now(timezone.utc).isoformat()),
    )
    conn.commit()
    
def save_findings(conn, run_id: str, findings: list):
    conn.executemany(
        "INSERT OR REPLACE INTO findings "
        "(finding_id, run_id, rule_code, severity, row_id, field, observed_value, expected, message, detected_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        [
            (
                f.finding_id, 
                run_id, 
                f.rule_code, 
                f.severity, 
                f.row_id, 
                f.field,
                str(f.observed_value) if f.observed_value is not None else None,
                f.expected, 
                f.message, 
                f.detected_at.isoformat()
            )
            for f in findings
        ],
    )
    conn.commit()

def save_metrics(conn, run_id: str, metrics_by_code: list, metrics_global):
    filas = [
        (
            run_id, 
            m.code, 
            m.true_positives, 
            m.false_positives, 
            m.false_negatives,
            m.precision, 
            m.recall, 
            m.f1
        ) 
        for m in metrics_by_code
    ]
    filas.append(
        (
            run_id, 
            "GLOBAL", 
            metrics_global.true_positives, 
            metrics_global.false_positives,
            metrics_global.false_negatives, 
            metrics_global.precision, 
            metrics_global.recall, 
            metrics_global.f1
        )
    )
    conn.executemany(
        "INSERT OR REPLACE INTO metrics "
        "(run_id, code, true_positives, false_positives, false_negatives, precision, recall, f1) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        filas,
    )
    conn.commit()

def list_runs(conn) -> list[dict]:
    cur = conn.execute("SELECT * FROM runs ORDER BY created_at DESC")
    return [dict(zip([d[0] for d in cur.description], row)) for row in cur.fetchall()]


def get_run(conn, run_id: str) -> dict | None:
    cur = conn.execute("SELECT * FROM runs WHERE run_id = ?", (run_id,))
    row = cur.fetchone()
    return dict(zip([d[0] for d in cur.description], row)) if row else None


def get_findings_by_run(conn, run_id: str) -> list[dict]:
    cur = conn.execute("SELECT * FROM findings WHERE run_id = ?", (run_id,))
    return [dict(zip([d[0] for d in cur.description], row)) for row in cur.fetchall()]


def get_metrics_by_run(conn, run_id: str) -> list[dict]:
    cur = conn.execute("SELECT * FROM metrics WHERE run_id = ?", (run_id,))
    return [dict(zip([d[0] for d in cur.description], row)) for row in cur.fetchall()]

def list_runs_summary(conn) -> list[dict]:
    """Runs con su F1 global, para el selector del dashboard."""
    cur = conn.execute("""
        SELECT r.run_id, 
            r.template, 
            r.config_name, 
            r.seed, r.rows, 
            r.created_at,
            m.precision, 
            m.recall, m.f1
        FROM runs r
        LEFT JOIN metrics m ON m.run_id = r.run_id AND m.code = 'GLOBAL'
        ORDER BY r.created_at DESC
    """)
    return [dict(zip([d[0] for d in cur.description], row)) for row in cur.fetchall()]

def get_findings_filtered(conn, run_id: str, rule_code: str = None, severity: str = None) -> list[dict]:
    """Hallazgos de un run, opcionalmente filtrados por código y/o severidad."""
    query = "SELECT * FROM findings WHERE run_id = ?"
    params = [run_id]
    if rule_code:
        query += " AND rule_code = ?"
        params.append(rule_code)
    if severity:
        query += " AND severity = ?"
        params.append(severity)
    cur = conn.execute(query, params)
    return [dict(zip([d[0] for d in cur.description], row)) for row in cur.fetchall()]

def count_findings_by_code(conn, run_id: str) -> list[dict]:
    """Conteo de hallazgos agrupado por código, para la tabla resumen."""
    cur = conn.execute("""
        SELECT rule_code, severity, COUNT(*) as total
        FROM findings WHERE run_id = ?
        GROUP BY rule_code, severity
        ORDER BY rule_code
    """, (run_id,))
    return [dict(zip([d[0] for d in cur.description], row)) for row in cur.fetchall()]
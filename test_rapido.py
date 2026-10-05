# test_rapido.py
from starglob_datalab.persistence.db import init_db, list_runs_summary, get_findings_filtered, count_findings_by_code

conn = init_db("data/starglob.db")

print("--- Runs ---")
for r in list_runs_summary(conn):
    print(r)

run_id = list_runs_summary(conn)[0]["run_id"]

print("\n--- Conteo por código ---")
for c in count_findings_by_code(conn, run_id):
    print(c)

print("\n--- Filtrado por DQ_01 ---")
for f in get_findings_filtered(conn, run_id, rule_code="DQ_01")[:3]:
    print(f)
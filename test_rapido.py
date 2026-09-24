# test_rapido.py
import uuid
from starglob_datalab.configuration import load_config
from starglob_datalab.generation.tickets import generate_tickets
from starglob_datalab.anomalies.injector import inject_anomalies

config = load_config("config/tickets_demo.yaml")
# anomalies:
#   - code: DQ_01
#     count: 5
#     fields: [summary]
#   - code: DQ_02
#     count: 3
#   - code: DQ_03
#     count: 2

df_clean = generate_tickets(config)
df_dirty = df_clean.copy()

df_dirty, entries = inject_anomalies(df_dirty, row_id_col="ticket_id", config=config, run_id="run_test")

print("Filas clean:", len(df_clean), "| Filas dirty:", len(df_dirty))
print("Anomalías totales:", len(entries))

dq03_entries = [e for e in entries if e.code == "DQ_03"]
for e in dq03_entries:
    print(f"row_id (real)={e.row_id} | original={e.original_value} -> altered={e.altered_value}")

duplicados = df_dirty[df_dirty.duplicated(subset="ticket_id", keep=False)]
print("Filas con ticket_id duplicado (DQ02 + DQ03 juntos):", len(duplicados))
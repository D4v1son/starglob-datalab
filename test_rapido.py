from starglob_datalab.configuration import load_config
from starglob_datalab.generation.tickets import generate_tickets
from starglob_datalab.anomalies.injector import inject_anomalies
from starglob_datalab.audit.auditor import audit
from starglob_datalab.evaluation.evaluator import evaluate
from starglob_datalab.persistence.db import (
    init_db, save_run, save_findings, save_metrics,
    get_run, get_findings_by_run, get_metrics_by_run,
)

config = load_config("config/tickets_demo.yaml")
df_clean = generate_tickets(config)
df_dirty, entries = inject_anomalies(
    df_clean.copy(), row_id_col="ticket_id", config=config, run_id="run_test123"
)
findings = audit(df_dirty, row_id_col="ticket_id", template="tickets", run_id="run_test123")
resultado = evaluate(entries, findings, df_clean, row_id_col="ticket_id")

conn = init_db("output/starglob.db")
save_run(conn, run_id="run_test123", template="tickets", config_name="tickets_demo",
          seed=config.seed, rows=config.rows)
save_findings(conn, "run_test123", findings)
save_metrics(conn, "run_test123", resultado["metrics_by_code"], resultado["metrics_global"])

print(get_run(conn, "run_test123"))
print(len(get_findings_by_run(conn, "run_test123")), "hallazgos guardados")
for m in get_metrics_by_run(conn, "run_test123"):
    print(m)

    
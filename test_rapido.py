# test_rapido.py
from starglob_datalab.configuration import GeneratorConfig, Period, AnomalyInjectionConfig
from starglob_datalab.generation.tickets import generate_tickets
from starglob_datalab.anomalies.injector import inject_anomalies

config = GeneratorConfig(
    name="test",
    template="tickets",
    seed=42,
    rows=200,
    period=Period(start_date="2026-01-01", end_date="2026-03-31"),
    output_dir="output/test",
    anomalies=[
        AnomalyInjectionConfig(code="DQ_06", count=5, fields=["satisfaction_score"])
    ],
)

df_clean = generate_tickets(config)
df_dirty, entries = inject_anomalies(
    df_clean.copy(), row_id_col="ticket_id", config=config, run_id="run_test"
)

print("Anomalías:", len(entries))
for e in entries:
    print(f"row_id={e.row_id} original={e.original_value} -> altered={e.altered_value}")
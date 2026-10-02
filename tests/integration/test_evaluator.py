from starglob_datalab.configuration import GeneratorConfig, Period, AnomalyInjectionConfig
from starglob_datalab.generation.tickets import generate_tickets
from starglob_datalab.anomalies.injector import inject_anomalies
from starglob_datalab.audit.auditor import audit
from starglob_datalab.evaluation.evaluator import evaluate

def test_deteccion_perfecta_da_f1_uno():
    config = GeneratorConfig(name="t", template="tickets", seed=1, rows=300,
        period=Period(start_date="2026-01-01", end_date="2026-03-31"),
        output_dir="output/test",
        anomalies=[AnomalyInjectionConfig(code="DQ_01", count=10, fields=["summary"])])
    df_clean = generate_tickets(config)
    df_dirty, entries = inject_anomalies(df_clean.copy(), "ticket_id", config, "run")
    findings = audit(df_dirty, "ticket_id", "tickets", "run")
    r = evaluate(entries, findings, df_clean, "ticket_id")
    assert r["metrics_global"].f1 == 1.0
    assert r["metrics_global"].false_positives == 0
    assert r["metrics_global"].false_negatives == 0
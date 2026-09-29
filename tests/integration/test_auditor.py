import pandas as pd
from starglob_datalab.configuration import GeneratorConfig, Period, AnomalyInjectionConfig
from starglob_datalab.generation.tickets import generate_tickets
from starglob_datalab.generation.backups import generate_backups
from starglob_datalab.anomalies.injector import inject_anomalies
from starglob_datalab.audit.auditor import audit


def _config_tickets(anomalies, rows=300, seed=42):
    return GeneratorConfig(
        name="test", template="tickets", seed=seed, rows=rows,
        period=Period(start_date="2026-01-01", end_date="2026-03-31"),
        output_dir="output/test", anomalies=anomalies,
    )


def _auditar_tickets(anomalies, rows=300, seed=42):
    config = _config_tickets(anomalies, rows, seed)
    df_clean = generate_tickets(config)
    df_dirty, entries = inject_anomalies(
        df_clean.copy(), row_id_col="ticket_id", config=config, run_id="run_gen"
    )
    findings = audit(df_dirty, row_id_col="ticket_id", template="tickets", run_id="run_audit")
    return df_clean, df_dirty, entries, findings


def _config_backups(anomalies, rows=300, seed=42):
    return GeneratorConfig(
        name="test", template="backups", seed=seed, rows=rows,
        period=Period(start_date="2026-01-01", end_date="2026-03-31"),
        output_dir="output/test", anomalies=anomalies,
    )


def _auditar_backups(anomalies, rows=300, seed=42):
    config = _config_backups(anomalies, rows, seed)
    df_clean = generate_backups(config)
    df_dirty, entries = inject_anomalies(
        df_clean.copy(), row_id_col="backup_id", config=config, run_id="run_gen"
    )
    findings = audit(df_dirty, row_id_col="backup_id", template="backups", run_id="run_audit")
    return df_clean, df_dirty, entries, findings


def _por_regla(findings, codigo):
    return [f for f in findings if f.rule_code == codigo]


# --- DQ_01 ---

def test_dq01_detecta_valores_ausentes():
    _, _, entries, findings = _auditar_tickets([
        AnomalyInjectionConfig(code="DQ_01", count=10, fields=["summary"])
    ])
    hallazgos = _por_regla(findings, "DQ_01")
    assert len(hallazgos) == len(entries)
    assert {h.row_id for h in hallazgos} == {e.row_id for e in entries}


# --- DQ_02 ---

def test_dq02_detecta_filas_duplicadas():
    _, _, entries, findings = _auditar_tickets([
        AnomalyInjectionConfig(code="DQ_02", count=5)
    ])
    hallazgos = _por_regla(findings, "DQ_02")
    assert len(hallazgos) == 10  # cada duplicado marca ambas filas (original + copia)


# --- DQ_03 (con la limitación conocida) ---

def test_dq03_detecta_ids_repetidos_aunque_no_coincida_el_row_id():
    _, df_dirty, entries, findings = _auditar_tickets([
        AnomalyInjectionConfig(code="DQ_03", count=3)
    ])
    hallazgos = _por_regla(findings, "DQ_03")
    assert len(hallazgos) == 6  # objetivo + donante, por cada instancia
    ids_manifiesto = {e.altered_value for e in entries if e.code == "DQ_03"}
    ids_detectados = {h.observed_value for h in hallazgos}
    assert ids_manifiesto == ids_detectados  # coinciden por VALOR, no por row_id


# --- DQ_04 ---

def test_dq04_detecta_categoria_invalida():
    _, _, entries, findings = _auditar_tickets([
        AnomalyInjectionConfig(code="DQ_04", count=8, fields=["priority"])
    ])
    hallazgos = _por_regla(findings, "DQ_04")
    assert {h.row_id for h in hallazgos} == {e.row_id for e in entries}


# --- DQ_05 ---

def test_dq05_detecta_tipo_incorrecto():
    _, _, entries, findings = _auditar_tickets([
        AnomalyInjectionConfig(code="DQ_05", count=6, fields=["sla_target_minutes"])
    ])
    hallazgos = _por_regla(findings, "DQ_05")
    assert {h.row_id for h in hallazgos} == {e.row_id for e in entries}


# --- DQ_06 ---

def test_dq06_detecta_valor_fuera_de_rango():
    _, _, entries, findings = _auditar_tickets([
        AnomalyInjectionConfig(code="DQ_06", count=5, fields=["satisfaction_score"])
    ])
    hallazgos = _por_regla(findings, "DQ_06")
    assert {h.row_id for h in hallazgos} == {e.row_id for e in entries}


# --- DQ_07 ---

def test_dq07_detecta_cronologia_imposible():
    _, _, entries, findings = _auditar_tickets([
        AnomalyInjectionConfig(code="DQ_07", count=5, fields=["closed_at", "created_at"])
    ])
    hallazgos = _por_regla(findings, "DQ_07")
    assert {h.row_id for h in hallazgos} == {e.row_id for e in entries}


# --- DQ_08 ---

def test_dq08_detecta_dependencia_incumplida():
    _, _, entries, findings = _auditar_backups([
        AnomalyInjectionConfig(code="DQ_08", count=5, fields=["error_code"])
    ])
    hallazgos = _por_regla(findings, "DQ_08")
    assert {h.row_id for h in hallazgos} == {e.row_id for e in entries}


# --- DQ_09 ---

def test_dq09_detecta_formato_inconsistente():
    _, _, entries, findings = _auditar_tickets([
        AnomalyInjectionConfig(code="DQ_09", count=5, fields=["created_at"])
    ])
    hallazgos = _por_regla(findings, "DQ_09")
    assert {h.row_id for h in hallazgos} == {e.row_id for e in entries}


# --- DQ_10 ---

def test_dq10_detecta_espacios_o_capitalizacion():
    _, _, entries, findings = _auditar_tickets([
        AnomalyInjectionConfig(code="DQ_10", count=5, fields=["priority"])
    ])
    hallazgos = _por_regla(findings, "DQ_10")
    assert {h.row_id for h in hallazgos} == {e.row_id for e in entries}


# --- DQ_11 (con la limitación conocida: row_id=None) ---

def test_dq11_detecta_hueco_temporal():
    _, _, entries, findings = _auditar_backups([
        AnomalyInjectionConfig(code="DQ_11", count=5)
    ], rows=500)
    hallazgos = _por_regla(findings, "DQ_11")
    assert len(hallazgos) >= 1
    assert all(h.row_id is None for h in hallazgos)


# --- DQ_12 ---

def test_dq12_detecta_duracion_extrema():
    _, _, entries, findings = _auditar_backups([
        AnomalyInjectionConfig(code="DQ_12", count=5, fields=["finished_at", "started_at"])
    ])
    hallazgos = _por_regla(findings, "DQ_12")
    assert {h.row_id for h in hallazgos} == {e.row_id for e in entries}


# --- DQ_13 ---

def test_dq13_detecta_referencia_huerfana():
    _, _, entries, findings = _auditar_tickets([
        AnomalyInjectionConfig(code="DQ_13", count=5, fields=["technician_id"])
    ])
    hallazgos = _por_regla(findings, "DQ_13")
    assert {h.row_id for h in hallazgos} == {e.row_id for e in entries}


# --- DQ_14 ---

def test_dq14_detecta_codificacion_danada():
    _, _, entries, findings = _auditar_tickets([
        AnomalyInjectionConfig(code="DQ_14", count=5, fields=["summary"])
    ])
    hallazgos = _por_regla(findings, "DQ_14")
    assert {h.row_id for h in hallazgos} == {e.row_id for e in entries}


# --- Cobertura sobre dataset limpio: no debe haber falsos positivos ---

def test_dataset_limpio_no_genera_hallazgos():
    _, _, _, findings = _auditar_tickets([])
    assert findings == []


def test_dataset_limpio_backups_no_genera_hallazgos():
    _, _, _, findings = _auditar_backups([])
    assert findings == []
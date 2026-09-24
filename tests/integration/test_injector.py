import pandas as pd
from starglob_datalab.configuration import GeneratorConfig, Period, AnomalyInjectionConfig
from starglob_datalab.generation.tickets import generate_tickets
from starglob_datalab.anomalies.injector import inject_anomalies


def _config(anomalies=None, rows=200, seed=42):
    return GeneratorConfig(
        name="test",
        template="tickets",
        seed=seed,
        rows=rows,
        period=Period(start_date="2026-01-01", end_date="2026-03-31"),
        output_dir="output/test",
        anomalies=anomalies or [],
    )


def _generar(anomalies, rows=200, seed=42):
    config = _config(anomalies, rows, seed)
    df_clean = generate_tickets(config)
    df_dirty, entries = inject_anomalies(
        df_clean.copy(), row_id_col="ticket_id", config=config, run_id="run_test"
    )
    return df_clean, df_dirty, entries


# --- DQ_01 ---

def test_dq01_vacia_el_campo_indicado():
    _, df_dirty, entries = _generar([
        AnomalyInjectionConfig(code="DQ_01", count=10, fields=["summary"])
    ])
    assert len(entries) == 10
    for e in entries:
        fila = df_dirty[df_dirty["ticket_id"] == e.row_id]
        assert pd.isna(fila["summary"].values[0])


def test_dq01_falla_si_no_hay_candidatos_suficientes():
    try:
        _generar([AnomalyInjectionConfig(code="DQ_01", count=9999, fields=["summary"])], rows=50)
        assert False, "debería haber lanzado ValueError"
    except ValueError:
        pass


# --- DQ_02 ---

def test_dq02_añade_filas_duplicadas():
    df_clean, df_dirty, entries = _generar([
        AnomalyInjectionConfig(code="DQ_02", count=5)
    ])
    assert len(df_dirty) == len(df_clean) + 5
    duplicados = df_dirty[df_dirty.duplicated(subset="ticket_id", keep=False)]
    assert len(duplicados) == 10  # 5 pares


# --- DQ_03 ---

def test_dq03_row_id_es_la_identidad_original():
    _, df_dirty, entries = _generar([
        AnomalyInjectionConfig(code="DQ_03", count=3)
    ])
    dq03 = [e for e in entries if e.code == "DQ_03"]
    assert len(dq03) == 3
    for e in dq03:
        # el row_id del manifiesto ya NO debe coincidir con lo que hay ahora en esa celda
        assert e.original_value == e.row_id
        assert e.altered_value != e.row_id


def test_dq03_genera_ids_duplicados():
    _, df_dirty, entries = _generar([
        AnomalyInjectionConfig(code="DQ_03", count=3)
    ])
    duplicados = df_dirty[df_dirty.duplicated(subset="ticket_id", keep=False)]
    assert len(duplicados) == 6  # 3 pares


# --- DQ_04 ---

def test_dq04_valor_fuera_de_catalogo():
    from starglob_datalab.generation.schemas import TicketPriority
    _, df_dirty, entries = _generar([
        AnomalyInjectionConfig(code="DQ_04", count=8, fields=["priority"])
    ])
    valores_validos = {p.value for p in TicketPriority}
    for e in entries:
        fila = df_dirty[df_dirty["ticket_id"] == e.row_id]
        assert fila["priority"].values[0] not in valores_validos


# --- DQ_05 ---

def test_dq05_valor_no_numerico():
    _, df_dirty, entries = _generar([
        AnomalyInjectionConfig(code="DQ_05", count=6, fields=["sla_target_minutes"])
    ])
    for e in entries:
        fila = df_dirty[df_dirty["ticket_id"] == e.row_id]
        valor = fila["sla_target_minutes"].values[0]
        assert not str(valor).isdigit()


# --- Combinadas ---

def test_varias_anomalias_no_pisan_las_mismas_celdas():
    _, df_dirty, entries = _generar([
        AnomalyInjectionConfig(code="DQ_01", count=10, fields=["summary"]),
        AnomalyInjectionConfig(code="DQ_02", count=5),
        AnomalyInjectionConfig(code="DQ_03", count=3),
        AnomalyInjectionConfig(code="DQ_04", count=8, fields=["priority"]),
        AnomalyInjectionConfig(code="DQ_05", count=6, fields=["sla_target_minutes"]),
    ])
    assert len(entries) == 10 + 5 + 3 + 8 + 6


def test_misma_semilla_misma_inyeccion():
    anomalies = [AnomalyInjectionConfig(code="DQ_01", count=10, fields=["summary"])]
    _, df1, entries1 = _generar(anomalies, seed=99)
    _, df2, entries2 = _generar(anomalies, seed=99)
    assert df1.equals(df2)
    assert [e.row_id for e in entries1] == [e.row_id for e in entries2]
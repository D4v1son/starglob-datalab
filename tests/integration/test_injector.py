import pandas as pd
from starglob_datalab.configuration import GeneratorConfig, Period, AnomalyInjectionConfig
from starglob_datalab.generation.tickets import generate_tickets
from starglob_datalab.generation.backups import generate_backups
from starglob_datalab.anomalies.injector import inject_anomalies
import re
import pytest
from starglob_datalab.generation.tickets import MAX_TECHNICIAN_ID
from starglob_datalab.anomalies.rules import SECUENCIAS_DANADAS


def _config_tickets(anomalies=None, rows=200, seed=42):
    return GeneratorConfig(
        name="test",
        template="tickets",
        seed=seed,
        rows=rows,
        period=Period(start_date="2026-01-01", end_date="2026-03-31"),
        output_dir="output/test",
        anomalies=anomalies or [],
    )


def _generar_tickets(anomalies, rows=200, seed=42):
    config = _config_tickets(anomalies, rows, seed)
    df_clean = generate_tickets(config)
    df_dirty, entries = inject_anomalies(
        df_clean.copy(), row_id_col="ticket_id", config=config, run_id="run_test"
    )
    return df_clean, df_dirty, entries

def _config_backups(anomalies=None, rows=200, seed=42):
    return GeneratorConfig(
        name="test",
        template="backups",
        seed=seed,
        rows=rows,
        period=Period(start_date="2026-01-01", end_date="2026-03-31"),
        output_dir="output/test",
        anomalies=anomalies or [],
    )


def _generar_backups(anomalies, rows=200, seed=42):
    config = _config_backups(anomalies, rows, seed)
    df_clean = generate_backups(config)
    df_dirty, entries = inject_anomalies(
        df_clean.copy(), row_id_col="backup_id", config=config, run_id="run_test"
    )
    return df_clean, df_dirty, entries

# --- DQ_01 ---

def test_dq01_vacia_el_campo_indicado():
    _, df_dirty, entries = _generar_tickets([
        AnomalyInjectionConfig(code="DQ_01", count=10, fields=["summary"])
    ])
    assert len(entries) == 10
    for e in entries:
        fila = df_dirty[df_dirty["ticket_id"] == e.row_id]
        assert pd.isna(fila["summary"].values[0])


def test_dq01_falla_si_no_hay_candidatos_suficientes():
    try:
        _generar_tickets([AnomalyInjectionConfig(code="DQ_01", count=9999, fields=["summary"])], rows=50)
        assert False, "debería haber lanzado ValueError"
    except ValueError:
        pass


# --- DQ_02 ---

def test_dq02_añade_filas_duplicadas():
    df_clean, df_dirty, entries = _generar_tickets([
        AnomalyInjectionConfig(code="DQ_02", count=5)
    ])
    assert len(df_dirty) == len(df_clean) + 5
    duplicados = df_dirty[df_dirty.duplicated(subset="ticket_id", keep=False)]
    assert len(duplicados) == 10  # 5 pares


# --- DQ_03 ---

def test_dq03_row_id_es_la_identidad_original():
    _, df_dirty, entries = _generar_tickets([
        AnomalyInjectionConfig(code="DQ_03", count=3)
    ])
    dq03 = [e for e in entries if e.code == "DQ_03"]
    assert len(dq03) == 3
    for e in dq03:
        # el row_id del manifiesto ya NO debe coincidir con lo que hay ahora en esa celda
        assert e.original_value == e.row_id
        assert e.altered_value != e.row_id


def test_dq03_genera_ids_duplicados():
    _, df_dirty, entries = _generar_tickets([
        AnomalyInjectionConfig(code="DQ_03", count=3)
    ])
    duplicados = df_dirty[df_dirty.duplicated(subset="ticket_id", keep=False)]
    assert len(duplicados) == 6  # 3 pares


# --- DQ_04 ---

def test_dq04_valor_fuera_de_catalogo():
    from starglob_datalab.generation.schemas import TicketPriority
    _, df_dirty, entries = _generar_tickets([
        AnomalyInjectionConfig(code="DQ_04", count=8, fields=["priority"])
    ])
    valores_validos = {p.value for p in TicketPriority}
    for e in entries:
        fila = df_dirty[df_dirty["ticket_id"] == e.row_id]
        assert fila["priority"].values[0] not in valores_validos


# --- DQ_05 ---

def test_dq05_valor_no_numerico():
    _, df_dirty, entries = _generar_tickets([
        AnomalyInjectionConfig(code="DQ_05", count=6, fields=["sla_target_minutes"])
    ])
    for e in entries:
        fila = df_dirty[df_dirty["ticket_id"] == e.row_id]
        valor = fila["sla_target_minutes"].values[0]
        assert not str(valor).isdigit()


# --- DQ_06 ---

def test_dq06_valor_fuera_de_rango():
    _, df_dirty, entries = _generar_tickets([
        AnomalyInjectionConfig(code="DQ_06", count=5, fields=["satisfaction_score"])
    ])
    assert len(entries) == 5
    for e in entries:
        fila = df_dirty[df_dirty["ticket_id"] == e.row_id]
        valor = fila["satisfaction_score"].values[0]
        assert valor < 1 or valor > 5


def test_dq06_falla_sin_rango_conocido():
    try:
        _generar_tickets([AnomalyInjectionConfig(code="DQ_06", count=1, fields=["client_id"])])
        assert False, "debería haber lanzado ValueError"
    except ValueError:
        pass


# --- DQ_07 ---

def test_dq07_campo_queda_antes_que_referencia():
    _, df_dirty, entries = _generar_tickets([
        AnomalyInjectionConfig(code="DQ_07", count=5, fields=["closed_at", "created_at"])
    ])
    assert len(entries) == 5
    for e in entries:
        assert e.related_fields == ["created_at"]
        fila = df_dirty[df_dirty["ticket_id"] == e.row_id]
        closed = pd.to_datetime(fila["closed_at"].values[0])
        created = pd.to_datetime(fila["created_at"].values[0])
        assert closed < created


def test_dq07_requiere_dos_campos():
    try:
        _generar_tickets([AnomalyInjectionConfig(code="DQ_07", count=1, fields=["closed_at"])])
        assert False, "debería haber lanzado ValueError"
    except ValueError:
        pass


# --- DQ_08 ---

def test_dq08_vacia_solo_bajo_condicion():
    _, df_dirty, entries = _generar_backups([
        AnomalyInjectionConfig(code="DQ_08", count=5, fields=["error_code"])
    ])
    assert len(entries) == 5
    for e in entries:
        fila = df_dirty[df_dirty["backup_id"] == e.row_id]
        assert fila["status"].values[0] in ("failed", "cancelled")
        assert pd.isna(fila["error_code"].values[0])


def test_dq08_falla_sin_dependencia_conocida():
    try:
        _generar_backups([AnomalyInjectionConfig(code="DQ_08", count=1, fields=["job_name"])])
        assert False, "debería haber lanzado ValueError"
    except ValueError:
        pass


# --- DQ_09 ---

def test_dq09_fecha_en_formato_distinto():
    _, df_dirty, entries = _generar_tickets([
        AnomalyInjectionConfig(code="DQ_09", count=5, fields=["created_at"])
    ])
    assert len(entries) == 5
    for e in entries:
        fila = df_dirty[df_dirty["ticket_id"] == e.row_id]
        valor = fila["created_at"].values[0]
        assert "/" in str(valor)  # formato DD/MM/YYYY, no ISO


def test_dq09_conserva_la_misma_fecha_real():
    _, df_dirty, entries = _generar_tickets([
        AnomalyInjectionConfig(code="DQ_09", count=5, fields=["created_at"])
    ])
    for e in entries:
        original = pd.Timestamp(e.original_value)
        alterado = pd.to_datetime(e.altered_value, format="%d/%m/%Y %H:%M:%S")
        assert original == alterado


# --- DQ_10 ---

def test_dq10_altera_pero_conserva_contenido():
    _, df_dirty, entries = _generar_tickets([
        AnomalyInjectionConfig(code="DQ_10", count=5, fields=["summary"])
    ])
    assert len(entries) == 5
    for e in entries:
        fila = df_dirty[df_dirty["ticket_id"] == e.row_id]
        valor = fila["summary"].values[0]
        assert valor != e.original_value
        assert valor.strip().lower() == e.original_value.strip().lower()

# --- DQ_11 ---

def test_dq11_elimina_filas():
    df_clean, df_dirty, entries = _generar_backups([
        AnomalyInjectionConfig(code="DQ_11", count=5)
    ])
    assert len(entries) == 5
    assert len(df_dirty) == len(df_clean) - 5
    for e in entries:
        assert e.row_id in set(df_clean["backup_id"])
        assert e.row_id not in set(df_dirty["backup_id"])
        assert e.related_fields == ["client_id", "job_name"]


def test_dq11_solo_elimina_ejecuciones_intermedias():
    df_clean, _, entries = _generar_backups([
        AnomalyInjectionConfig(code="DQ_11", count=5)
    ])
    for e in entries:
        fila = df_clean[df_clean["backup_id"] == e.row_id].iloc[0]
        mismo_job = df_clean[
            (df_clean["client_id"] == fila["client_id"])
            & (df_clean["job_name"] == fila["job_name"])
        ]
        assert mismo_job["scheduled_at"].min() < fila["scheduled_at"] < mismo_job["scheduled_at"].max()


def test_dq11_solo_aplica_a_backups():
    with pytest.raises(ValueError):
        _generar_tickets([AnomalyInjectionConfig(code="DQ_11", count=1)])


# --- DQ_12 ---

def test_dq12_duracion_desproporcionada():
    _, df_dirty, entries = _generar_backups([
        AnomalyInjectionConfig(code="DQ_12", count=5, fields=["finished_at", "started_at"])
    ])
    assert len(entries) == 5
    for e in entries:
        fila = df_dirty[df_dirty["backup_id"] == e.row_id]
        fin = pd.Timestamp(fila["finished_at"].values[0])
        inicio = pd.Timestamp(fila["started_at"].values[0])
        assert fin > inicio                          # sigue siendo cronológicamente válido
        assert fin - inicio >= pd.Timedelta(days=30)  # pero desproporcionado


def test_dq12_requiere_dos_campos():
    with pytest.raises(ValueError):
        _generar_backups([AnomalyInjectionConfig(code="DQ_12", count=1, fields=["finished_at"])])


# --- DQ_13 ---

def test_dq13_tecnico_inexistente_con_formato_valido():
    _, df_dirty, entries = _generar_tickets([
        AnomalyInjectionConfig(code="DQ_13", count=5, fields=["technician_id"])
    ])
    assert len(entries) == 5
    for e in entries:
        fila = df_dirty[df_dirty["ticket_id"] == e.row_id]
        valor = fila["technician_id"].values[0]
        assert re.fullmatch(r"TEC-\d{3}", valor)               # formato correcto
        assert int(valor.split("-")[1]) > MAX_TECHNICIAN_ID    # pero fuera del rango que existe


def test_dq13_falla_sin_catalogo_de_referencia():
    with pytest.raises(ValueError):
        _generar_tickets([AnomalyInjectionConfig(code="DQ_13", count=1, fields=["client_id"])])


def test_dq13_falla_en_backups():
    with pytest.raises(ValueError):
        _generar_backups([AnomalyInjectionConfig(code="DQ_13", count=1, fields=["client_id"])])


# --- DQ_14 ---

def test_dq14_introduce_caracteres_ilegibles():
    _, df_dirty, entries = _generar_tickets([
        AnomalyInjectionConfig(code="DQ_14", count=5, fields=["summary"])
    ])
    assert len(entries) == 5
    for e in entries:
        fila = df_dirty[df_dirty["ticket_id"] == e.row_id]
        valor = fila["summary"].values[0]
        assert valor != e.original_value
        assert any(secuencia in valor for secuencia in SECUENCIAS_DANADAS)


def test_dq14_falla_en_campo_no_textual():
    with pytest.raises(ValueError):
        _generar_tickets([AnomalyInjectionConfig(code="DQ_14", count=1, fields=["sla_target_minutes"])])

# --- Interacciones entre anomalías ---

def test_dq02_y_dq11_mantienen_indices_unicos():
    for orden in (["DQ_11", "DQ_02"], ["DQ_02", "DQ_11"]):
        _, df_dirty, _ = _generar_backups([
            AnomalyInjectionConfig(code=code, count=5) for code in orden
        ])
        assert df_dirty.index.is_unique


def test_dq11_no_borra_el_donante_de_dq03():
    _, df_dirty, entries = _generar_backups([
        AnomalyInjectionConfig(code="DQ_03", count=5),
        AnomalyInjectionConfig(code="DQ_11", count=5),
    ])
    for e in entries:
        if e.code == "DQ_03":
            # el ID duplicado sigue en el donante (y en el objetivo): al menos 2 filas
            assert (df_dirty["backup_id"] == e.altered_value).sum() >= 2


def test_dq07_y_dq09_no_comparten_celda_created_at():
    _, _, entries = _generar_tickets([
        AnomalyInjectionConfig(code="DQ_09", count=10, fields=["created_at"]),
        AnomalyInjectionConfig(code="DQ_07", count=10, fields=["closed_at", "created_at"]),
    ])
    filas_dq09 = {e.row_id for e in entries if e.code == "DQ_09"}
    filas_dq07 = {e.row_id for e in entries if e.code == "DQ_07"}
    assert filas_dq09.isdisjoint(filas_dq07)

# --- Combinadas ---

def test_varias_anomalias_no_pisan_las_mismas_celdas():
    _, df_dirty, entries = _generar_tickets([
        AnomalyInjectionConfig(code="DQ_01", count=10, fields=["summary"]),
        AnomalyInjectionConfig(code="DQ_02", count=5),
        AnomalyInjectionConfig(code="DQ_03", count=3),
        AnomalyInjectionConfig(code="DQ_04", count=8, fields=["priority"]),
        AnomalyInjectionConfig(code="DQ_05", count=6, fields=["sla_target_minutes"]),
        AnomalyInjectionConfig(code="DQ_06", count=4, fields=["satisfaction_score"]),
        AnomalyInjectionConfig(code="DQ_07", count=4, fields=["closed_at", "created_at"]),
        AnomalyInjectionConfig(code="DQ_09", count=4, fields=["created_at"]),
        AnomalyInjectionConfig(code="DQ_10", count=4, fields=["summary"]),
        AnomalyInjectionConfig(code="DQ_13", count=4, fields=["technician_id"]),
        AnomalyInjectionConfig(code="DQ_14", count=4, fields=["summary"]),
    ])
    assert len(entries) == 10 + 5 + 3 + 8 + 6 + 4 + 4 + 4 + 4 + 4 + 4


def test_varias_anomalias_backups_no_pisan_las_mismas_celdas():
    _, df_dirty, entries = _generar_backups([
        AnomalyInjectionConfig(code="DQ_01", count=10, fields=["job_name"]),
        AnomalyInjectionConfig(code="DQ_02", count=5),
        AnomalyInjectionConfig(code="DQ_03", count=3),
        AnomalyInjectionConfig(code="DQ_08", count=6, fields=["error_code"]),
        AnomalyInjectionConfig(code="DQ_11", count=5),
        AnomalyInjectionConfig(code="DQ_12", count=4, fields=["finished_at", "started_at"]),
        AnomalyInjectionConfig(code="DQ_14", count=4, fields=["job_name"]),
    ])
    assert len(entries) == 10 + 5 + 3 + 6 + 5 + 4 + 4   

def test_misma_semilla_misma_inyeccion():
    anomalies = [AnomalyInjectionConfig(code="DQ_01", count=10, fields=["summary"])]
    _, df1, entries1 = _generar_tickets(anomalies, seed=99)
    _, df2, entries2 = _generar_tickets(anomalies, seed=99)
    assert df1.equals(df2)
    assert [e.row_id for e in entries1] == [e.row_id for e in entries2]


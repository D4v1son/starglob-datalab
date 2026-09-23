import pandas as pd
from starglob_datalab.configuration import GeneratorConfig, Period
from starglob_datalab.generation.backups import generate_backups


def _config(rows=300, seed=42):
    return GeneratorConfig(
        name="test",
        template="backups",
        seed=seed,
        rows=rows,
        period=Period(start_date="2026-01-01", end_date="2026-03-31"),
        output_dir="output/test",
    )

def test_genera_el_numero_de_filas_pedido():
    df = generate_backups(_config(rows=300))
    assert len(df) == 300

def test_misma_semilla_produce_mismo_resultado():
    df1 = generate_backups(_config(seed=99))
    df2 = generate_backups(_config(seed=99))
    assert df1.equals(df2)

def test_ids_son_unicos():
    df = generate_backups(_config())
    assert df["backup_id"].is_unique

def test_mismo_job_tiene_multiples_ejecuciones():
    """Confirma la continuidad temporal --> un job no debería aparecer solo una vez."""
    df = generate_backups(_config())
    conteo_por_job = df.groupby(["client_id", "job_name"]).size()
    assert (conteo_por_job > 1).any()

def test_ejecuciones_de_un_job_estan_espaciados_regularmente():
    df = generate_backups(_config())
    df["scheduled_at"] = pd.to_datetime(df["scheduled_at"]) # por siviene como texto
    grupo = df.groupby(["client_id", "job_name"])
    primer_job = list(grupo.groups.keys())[0]
    fechas = grupo.get_group(primer_job)["scheduled_at"].sort_values()
    diferencias = fechas.diff().dropna().dt.days.unique() # esto es lo que calcula cuantos intervalos de tiempo únicos existen en el dataset (en la generación de backups especificamos 1 0 7 días)
    assert len(diferencias) == 1  # siempre el mismo intervalo
    
def test_fechas_dentro_del_periodo():
    df = generate_backups(_config())
    df["scheduled_at"] = pd.to_datetime(df["scheduled_at"])
    # el inicio y el fin son los que preestablecimos en _config()
    inicio = pd.Timestamp("2026-01-01")
    fin = pd.Timestamp("2026-03-31") + pd.Timedelta(days=1)
    assert (df["scheduled_at"] >= inicio).all()
    assert (df["scheduled_at"] < fin).all()
    
def test_columnas_esperadas_presentes():
    # como este test trabaja con las columnas y no los datos podemos generar menos filas
    df = generate_backups(_config(rows=10))
    columnas_esperadas = {
        "backup_id", "client_id", "job_name", "source_system",
        "scheduled_at", "started_at", "finished_at", "status",
        "bytes_processed", "files_processed", "checksum_verified",
        "error_code", "error_message",
    }
    assert columnas_esperadas.issubset(df.columns)

def test_running_nunca_tiene_finished_at():
    df = generate_backups(_config())
    running = df[df["status"] == "running"]
    assert running["finished_at"].isna().all()


import pandas as pd

from starglob_datalab.configuration import GeneratorConfig, Period
from starglob_datalab.generation.tickets import generate_tickets


def _config(rows=100, seed=42): # aunque sean números mágicos son solo para testear
    return GeneratorConfig(
        name="test",
        template="tickets",
        seed=seed,
        rows=rows,
        period=Period(start_date="2026-01-01", end_date="2026-03-31"),
        output_dir="output/test",
    )

def test_genera_el_numero_de_filas_pedido():
    df = generate_tickets(_config(rows=250))
    assert len(df) == 250


def test_misma_semilla_produce_mismo_resultado():
    df1 = generate_tickets(_config(seed=99))
    df2 = generate_tickets(_config(seed=99))
    assert df1.equals(df2)


def test_semillas_distintas_producen_resultados_distintos():
    df1 = generate_tickets(_config(seed=1))
    df2 = generate_tickets(_config(seed=2))
    assert not df1.equals(df2)

def test_ids_son_unicos():
    df = generate_tickets(_config(rows=500))
    assert df["ticket_id"].is_unique


def test_fechas_dentro_del_periodo():
    df = generate_tickets(_config(rows=500))
    inicio = pd.Timestamp("2026-01-01")
    fin = pd.Timestamp("2026-03-31") + pd.Timedelta(days=1)  # incluye todo el último día
    assert (df["created_at"] >= inicio).all()
    assert (df["created_at"] < fin).all()


def test_columnas_esperadas_presentes():
    df = generate_tickets(_config(rows=10))
    columnas_esperadas = {
        "ticket_id", "client_id", "created_at", "first_response_at",
        "closed_at", "category", "priority", "status", "channel",
        "technician_id", "summary", "sla_target_minutes", "satisfaction_score",
    }
    assert columnas_esperadas.issubset(df.columns)


def test_open_nunca_tiene_first_response():
    df = generate_tickets(_config(rows=1000))
    abiertos = df[df["status"] == "open"]
    assert abiertos["first_response_at"].isna().all()
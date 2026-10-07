import streamlit as st
import pandas as pd
from starglob_datalab.persistence.db import (
    init_db, list_runs_summary, get_metrics_by_run,
    get_findings_filtered, count_findings_by_code,
    DIMENSION_BY_CODE,
)

st.set_page_config(page_title="Starglob DataLab", layout="wide")
st.title("Starglob DataLab - Resultados de auditoría")

conn = init_db("data/starglob.db")
runs = list_runs_summary(conn)

plantillas_disponibles = sorted({r["template"] for r in runs})
filtro_plantilla = st.selectbox("Plantilla", ["(todas)"] + plantillas_disponibles)

runs_filtrados = runs if filtro_plantilla == "(todas)" else [r for r in runs if r["template"] == filtro_plantilla]

if not runs_filtrados:
    st.warning("No hay ejecuciones para esa plantilla.")
    st.stop()

opciones = {f"{r['run_id']} ({r['template']}, F1={r['f1']:.2f})" if r['f1'] is not None
            else f"{r['run_id']} ({r['template']})": r['run_id'] for r in runs_filtrados}
seleccion = st.selectbox("Ejecución (run_id)", list(opciones.keys()))
run_id = opciones[seleccion]

run = next(r for r in runs if r["run_id"] == run_id)

# TENDENCIAS
if len(runs_filtrados) > 1:
    st.subheader("Tendencia de F1 por ejecución")
    df_tendencia = pd.DataFrame(runs_filtrados).sort_values("created_at")
    st.line_chart(df_tendencia.set_index("created_at")["f1"])

st.subheader("Resumen")
col1, col2, col3, col4 = st.columns(4)
col1.metric("Plantilla", run["template"])
col2.metric("Filas", run["rows"])
col3.metric("Precisión global", f"{run['precision']:.2f}" if run["precision"] is not None else "—")
col4.metric("F1 global", f"{run['f1']:.2f}" if run["f1"] is not None else "—")

st.subheader("Métricas por regla")
metricas = get_metrics_by_run(conn, run_id)
st.dataframe([m for m in metricas if m["code"] != "GLOBAL"], use_container_width=True)

st.subheader("Calidad por dimensión")

conteo = count_findings_by_code(conn, run_id)
filtro_gravedad_calidad = st.selectbox("Filtrar gravedad (Calidad)", ["(todas)"] + sorted({c["severity"] for c in conteo}))
conteo_filtrado = conteo if filtro_gravedad_calidad == "(todas)" else [c for c in conteo if c["severity"] == filtro_gravedad_calidad]

por_dimension = {}
for c in conteo_filtrado:
    dim = DIMENSION_BY_CODE.get(c["rule_code"], "Otra")
    por_dimension[dim] = por_dimension.get(dim, 0) + c["total"]

st.bar_chart(por_dimension)

if run["template"] == "backups":
    st.subheader("Continuidad - huecos detectados")
    huecos = get_findings_filtered(conn, run_id, rule_code="DQ_11")
    if huecos:
        df_huecos = pd.DataFrame(huecos)
        df_huecos["fecha_faltante"] = pd.to_datetime(df_huecos["observed_value"])
        df_huecos["cliente_trabajo"] = df_huecos["row_id"]
        st.dataframe(df_huecos[["cliente_trabajo", "fecha_faltante", "message"]], use_container_width=True)
        st.bar_chart(df_huecos.set_index("fecha_faltante")["cliente_trabajo"].astype(str).value_counts())
    else:
        st.info("Sin huecos detectados en esta ejecución.")

st.subheader("Hallazgos")
codigos_disponibles = sorted({c["rule_code"] for c in count_findings_by_code(conn, run_id)})
severidades_disponibles = sorted({c["severity"] for c in count_findings_by_code(conn, run_id)})

col_a, col_b = st.columns(2)
filtro_codigo = col_a.selectbox("Filtrar por código", ["(todos)"] + codigos_disponibles)
filtro_severidad = col_b.selectbox("Filtrar por severidad", ["(todas)"] + severidades_disponibles)

hallazgos = get_findings_filtered(
    conn, run_id,
    rule_code=None if filtro_codigo == "(todos)" else filtro_codigo,
    severity=None if filtro_severidad == "(todas)" else filtro_severidad,
)
st.write(f"{len(hallazgos)} hallazgos")
st.dataframe(hallazgos, use_container_width=True)
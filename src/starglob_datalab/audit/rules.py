import pandas as pd
import re

# reutilizamos los mismos catálogos que ya usa el inyector (DQ_04/DQ_06),
# en vez de duplicar qué valores/rangos son válidos en un tercer sitio
from starglob_datalab.anomalies.rules import (FIELD_ENUMS_BY_TEMPLATE, 
                                              RANGES_BY_TEMPLATE,
                                              DEPENDENCES_BY_TEMPLATE,
                                              REFERENCES_BY_TEMPLATE,
                                              DAMAGED_SECUENCES)


# Campos obligatorios por plantilla (los que en schemas.py NO son Optional)
REQUIRED_FIELDS_BY_TEMPLATE = {
    "tickets": [
        "ticket_id",
        "client_id",
        "created_at",
        "category",
        "priority",
        "status",
        "channel",
        "summary",
        "sla_target_minutes",
    ],
    "backups": [
        "backup_id",
        "client_id",
        "job_name",
        "source_system",
        "scheduled_at",
        "status",
    ],
}

NUMERIC_FIELDS_BY_TEMPLATE = {
    "tickets": ["sla_target_minutes", "satisfaction_score"],
    "backups": ["bytes_processed", "files_processed"],
}

# pares (campo, referencia) conocidos por plantilla, donde campo debe ser
# posterior a referencia - mismo criterio que ya usa el inyector en DQ_07
CHRONOLOGY_PAIRS_BY_TEMPLATE = {
    "tickets": [("closed_at", "created_at"), ("first_response_at", "created_at")],
    "backups": [("started_at", "scheduled_at"), ("finished_at", "started_at")],
}

DATE_FIELDS_BY_TEMPLATE = {
    "tickets": ["created_at", "first_response_at", "closed_at"],
    "backups": ["scheduled_at", "started_at", "finished_at"],
}

TEXT_FIELDS_BY_TEMPLATE = {
    "tickets": ["summary"],
    "backups": ["job_name", "error_message"],
}

EXTREME_DURATION_THRESHOLD_DAYS = 10  # umbral de "desproporcionado", distinto del rango del inyector

def check_required_fields(df: pd.DataFrame, row_id_col: str, campos_requeridos: list[str]):
    """DQ_01 — Completitud: detecta valores obligatorios ausentes."""
    for idx in df.index:
        row_id = df.at[idx, row_id_col]
        for campo in campos_requeridos:
            if pd.isna(df.at[idx, campo]):
                yield {
                    "severity": "error",
                    "row_id": row_id,
                    "field": campo,
                    "observed_value": None,
                    "expected": f"'{campo}' debe tener un valor",
                    "message": f"Falta un valor obligatorio en el campo '{campo}'",
                }

def check_exact_duplicates(df: pd.DataFrame, row_id_col: str):
    """DQ_02 - Unicidad: detecta filas completamente duplicadas (todos los campos iguales)."""
    duplicadas = df[df.duplicated(keep=False)]
    for idx in duplicadas.index:
        row_id = df.at[idx, row_id_col]
        yield {
            "severity": "error",
            "row_id": row_id,
            "field": None,
            "observed_value": None,
            "expected": "cada fila debe ser única",
            "message": "Fila completamente duplicada (todos los campos coinciden con otra)",
        }


def check_duplicate_id(df: pd.DataFrame, row_id_col: str):
    """DQ_03 - Unicidad: detecta IDs repetidos entre filas que NO son duplicados exactos."""
    # excluye las filas ya cubiertas por DQ_02, para no contar dos veces el mismo problema
    no_exactas = df[~df.duplicated(keep=False)]
    ids_repetidos = no_exactas[no_exactas.duplicated(subset=row_id_col, keep=False)]
    for idx in ids_repetidos.index:
        valor = df.at[idx, row_id_col]
        yield {
            "severity": "critical",
            "row_id": valor,
            "field": row_id_col,
            "observed_value": valor,
            "expected": f"'{row_id_col}' debe ser único",
            "message": f"Identificador '{valor}' repetido en más de una fila",
        }

def check_valid_category(df: pd.DataFrame, row_id_col: str, template: str):
    """DQ_04 - Validez: detecta valores fuera del catálogo permitido en campos categóricos."""
    campos_enum = FIELD_ENUMS_BY_TEMPLATE.get(template, {})
    for campo, enum_cls in campos_enum.items():
        valores_validos = {e.value for e in enum_cls}
        for idx in df.index:
            valor = df.at[idx, campo]
            if pd.notna(valor) and valor not in valores_validos:
                yield {
                    "severity": "error",
                    "row_id": df.at[idx, row_id_col],
                    "field": campo,
                    "observed_value": valor,
                    "expected": f"uno de {sorted(valores_validos)}",
                    "message": f"Valor '{valor}' no está en el catálogo permitido de '{campo}'",
                }


def check_valid_type(df: pd.DataFrame, row_id_col: str, template: str):
    """DQ_05 - Validez: detecta valores no numéricos en campos que deberían serlo."""
    campos_numericos = NUMERIC_FIELDS_BY_TEMPLATE.get(template, [])
    for campo in campos_numericos:
        for idx in df.index:
            valor = df.at[idx, campo]
            if pd.isna(valor):
                continue
            try:
                float(valor)
            except (ValueError, TypeError):
                yield {
                    "severity": "error",
                    "row_id": df.at[idx, row_id_col],
                    "field": campo,
                    "observed_value": valor,
                    "expected": "un valor numérico",
                    "message": f"Valor '{valor}' no es numérico en el campo '{campo}'",
                }


def check_value_range(df: pd.DataFrame, row_id_col: str, template: str):
    """DQ_06 - Validez: detecta valores numéricos fuera del rango conocido."""
    rangos = RANGES_BY_TEMPLATE.get(template, {})
    for campo, (minimo, maximo) in rangos.items():
        for idx in df.index:
            valor = df.at[idx, campo]
            if pd.isna(valor):
                continue
            try:
                valor_num = float(valor)
            except (ValueError, TypeError):
                continue  # ya lo cubre check_valid_type, no lo dupliques aquí
            if not (minimo <= valor_num <= maximo):
                yield {
                    "severity": "warning",
                    "row_id": df.at[idx, row_id_col],
                    "field": campo,
                    "observed_value": valor,
                    "expected": f"entre {minimo} y {maximo}",
                    "message": f"Valor {valor} fuera del rango [{minimo}, {maximo}] en '{campo}'",
                }

def check_chronology(df: pd.DataFrame, row_id_col: str, template: str):
    """DQ_07 - Consistencia: detecta relaciones temporales imposibles entre dos campos."""
    pares = CHRONOLOGY_PAIRS_BY_TEMPLATE.get(template, [])
    for campo, referencia in pares:
        for idx in df.index:
            valor = df.at[idx, campo]
            valor_ref = df.at[idx, referencia]
            if pd.isna(valor) or pd.isna(valor_ref):
                continue
            try:
                fecha = pd.Timestamp(valor)
                fecha_ref = pd.Timestamp(valor_ref)
            except (ValueError, TypeError):
                continue  # formato inválido: lo cubre check_date_format (DQ_09), no aquí
            if fecha < fecha_ref:
                yield {
                    "severity": "error",
                    "row_id": df.at[idx, row_id_col],
                    "field": campo,
                    "observed_value": str(valor),
                    "expected": f"posterior o igual a '{referencia}' ({valor_ref})",
                    "message": f"'{campo}' es anterior a '{referencia}', cronología imposible",
                }


def check_dependency(df: pd.DataFrame, row_id_col: str, template: str):
    """DQ_08 - Consistencia: detecta campos obligatorios bajo una condición que no se cumplen."""
    dependencias = DEPENDENCES_BY_TEMPLATE.get(template, {})
    for campo, dependencia in dependencias.items():
        disparador = dependencia["campo_disparador"]
        valores_disparadores = dependencia["valores_disparadores"]
        for idx in df.index:
            if df.at[idx, disparador] in valores_disparadores and pd.isna(df.at[idx, campo]):
                yield {
                    "severity": "error",
                    "row_id": df.at[idx, row_id_col],
                    "field": campo,
                    "observed_value": None,
                    "expected": f"'{campo}' presente cuando {disparador}='{df.at[idx, disparador]}'",
                    "message": f"Falta '{campo}', obligatorio cuando {disparador}='{df.at[idx, disparador]}'",
                }

def check_date_format(df: pd.DataFrame, row_id_col: str, template: str):
    """DQ_09 - Validez: detecta fechas que no siguen el formato ISO 8601 esperado."""
    campos_fecha = DATE_FIELDS_BY_TEMPLATE.get(template, [])
    patron_iso = re.compile(r"^\d{4}-\d{2}-\d{2}([ T]\d{2}:\d{2}:\d{2})?")

    for campo in campos_fecha:
        for idx in df.index:
            valor = df.at[idx, campo]
            if pd.isna(valor):
                continue
            if not patron_iso.match(str(valor)):
                yield {
                    "severity": "warning",
                    "row_id": df.at[idx, row_id_col],
                    "field": campo,
                    "observed_value": str(valor),
                    "expected": "formato ISO 8601 (YYYY-MM-DD...)",
                    "message": f"'{campo}' no sigue el formato de fecha esperado",
                }

def check_text_hygiene(df: pd.DataFrame, row_id_col: str, template: str):
    """DQ_10 - Validez: detecta espacios sobrantes o capitalización inconsistente en campos categóricos."""
    campos_enum = FIELD_ENUMS_BY_TEMPLATE.get(template, {})
    for campo, enum_cls in campos_enum.items():
        valores_validos = {e.value for e in enum_cls}
        for idx in df.index:
            valor = df.at[idx, campo]
            if pd.isna(valor) or not isinstance(valor, str):
                continue
            limpio = valor.strip().lower()
            if valor not in valores_validos and limpio in valores_validos:
                yield {
                    "severity": "info",
                    "row_id": df.at[idx, row_id_col],
                    "field": campo,
                    "observed_value": valor,
                    "expected": f"'{limpio}' sin espacios ni capitalización distinta",
                    "message": f"Valor '{valor}' tiene formato inconsistente (¿'{limpio}'?)",
                }

def check_continuity(df: pd.DataFrame, row_id_col: str, template: str):
    """DQ_11 - Continuidad: detecta huecos en trabajos recurrentes (backups)."""
    if template != "backups":
        return  # no aplica a tickets, igual que en el inyector

    df_temp = df.copy()
    df_temp["_scheduled"] = pd.to_datetime(df_temp["scheduled_at"], errors="coerce")

    for (client_id, job_name), grupo in df_temp.groupby(["client_id", "job_name"]):
        grupo = grupo.dropna(subset=["_scheduled"]).sort_values("_scheduled")
        if len(grupo) < 3:
            continue  # no hay suficiente historial para inferir un patrón fiable

        # la frecuencia esperada es la más común entre ejecuciones consecutivas
        deltas = grupo["_scheduled"].diff().dropna().dt.days
        frecuencia_esperada = deltas.mode().iloc[0]
        if frecuencia_esperada <= 0:
            continue

        fechas = grupo["_scheduled"].tolist()
        for anterior, siguiente in zip(fechas, fechas[1:]):
            hueco_dias = (siguiente - anterior).days
            # un hueco es múltiplo de la frecuencia esperada, pero mayor a 1 ocurrencia
            if hueco_dias >= frecuencia_esperada * 2:
                yield {
                    "severity": "warning",
                    "row_id": None,  # la fila que faltaría no existe, no hay row_id que dar
                    "field": "scheduled_at",
                    "observed_value": f"hueco de {hueco_dias} días entre {anterior.date()} y {siguiente.date()}",
                    "expected": f"ejecución cada {frecuencia_esperada} días para client_id={client_id}, job_name={job_name}",
                    "message": f"Falta al menos una ejecución esperada entre {anterior.date()} y {siguiente.date()}",
                }

def check_extreme_duration(df: pd.DataFrame, row_id_col: str, template: str):
    """DQ_12 - Validez: detecta duraciones desproporcionadamente largas entre dos campos."""
    pares = CHRONOLOGY_PAIRS_BY_TEMPLATE.get(template, [])
    for campo, referencia in pares:
        for idx in df.index:
            valor = df.at[idx, campo]
            valor_ref = df.at[idx, referencia]
            if pd.isna(valor) or pd.isna(valor_ref):
                continue
            try:
                duracion = pd.Timestamp(valor) - pd.Timestamp(valor_ref)
            except (ValueError, TypeError):
                continue
            if duracion.days >= EXTREME_DURATION_THRESHOLD_DAYS:
                yield {
                    "severity": "warning",
                    "row_id": df.at[idx, row_id_col],
                    "field": campo,
                    "observed_value": f"{duracion.days} días desde '{referencia}'",
                    "expected": f"menos de {EXTREME_DURATION_THRESHOLD_DAYS} días",
                    "message": f"Duración desproporcionada entre '{referencia}' y '{campo}'",
                }

def check_orphan_reference(df: pd.DataFrame, row_id_col: str, template: str):
    """DQ_13 - Trazabilidad: detecta referencias con formato válido pero fuera del rango conocido."""
    referencias = REFERENCES_BY_TEMPLATE.get(template, {})
    for campo, (prefijo, primero, ultimo) in referencias.items():
        for idx in df.index:
            valor = df.at[idx, campo]
            if pd.isna(valor):
                continue
            match = re.fullmatch(rf"{prefijo}-(\d+)", str(valor))
            if match and not (primero <= int(match.group(1)) <= ultimo):
                yield {
                    "severity": "error",
                    "row_id": df.at[idx, row_id_col],
                    "field": campo,
                    "observed_value": valor,
                    "expected": f"'{prefijo}-{primero:03d}' a '{prefijo}-{ultimo:03d}'",
                    "message": f"Referencia '{valor}' fuera del rango de valores existentes",
                }

def check_encoding(df: pd.DataFrame, row_id_col: str, template: str):
    """DQ_14 - Trazabilidad: detecta secuencias de caracteres típicas de mala codificación."""
    campos_texto = TEXT_FIELDS_BY_TEMPLATE.get(template, [])
    for campo in campos_texto:
        for idx in df.index:
            valor = df.at[idx, campo]
            if not isinstance(valor, str):
                continue
            if any(secuencia in valor for secuencia in DAMAGED_SECUENCES):
                yield {
                    "severity": "warning",
                    "row_id": df.at[idx, row_id_col],
                    "field": campo,
                    "observed_value": valor,
                    "expected": "texto sin caracteres de codificación dañada",
                    "message": f"Se detectaron caracteres ilegibles en '{campo}'",
                }
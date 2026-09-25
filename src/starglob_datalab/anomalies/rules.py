import pandas as pd
from starglob_datalab.anomalies.manifest import ManifestEntry
from starglob_datalab.generation.schemas import (
    TicketCategory, TicketPriority, TicketStatus, TicketChannel,
    BackupSourceSystem, BackupStatus,
)


FIELD_ENUMS_BY_TEMPLATE = {
    "tickets": {
        "category": TicketCategory,
        "priority": TicketPriority,
        "status": TicketStatus,
        "channel": TicketChannel,
    },
    "backups": {
        "source_system": BackupSourceSystem,
        "status": BackupStatus,
    },
}

VALORES_INVALIDOS_CANDIDATOS = ["urgent", "n/a", "unknown", "pendiente", "xx", "critical!!"]

RANGES_BY_TEMPLATE = {
    "tickets": {
        "satisfaction_score": (1, 5),
    },
    "backups": {
        # de momento no hay campos con rango cerrado conocido en backups
    },
}

DEPENDENCES_BY_TEMPLATE = {
    "backups": {
        "error_code": {"campo_disparador": "status", "valores_disparadores": ["failed", "cancelled"]},
        "bytes_processed": {"campo_disparador": "status", "valores_disparadores": ["success"]},
        "files_processed": {"campo_disparador": "status", "valores_disparadores": ["success"]},
    },
    "tickets": {
        "closed_at": {"campo_disparador": "status", "valores_disparadores": ["closed"]},
    },
}


def _generar_valor_invalido(campo: str, ctx) -> str:
    enums_plantilla = FIELD_ENUMS_BY_TEMPLATE.get(ctx.template, {})
    enum_cls = enums_plantilla.get(campo)
    valores_validos = {e.value for e in enum_cls} if enum_cls else set()
    candidatos = [v for v in VALORES_INVALIDOS_CANDIDATOS if v not in valores_validos]
    return ctx.rng.choice(candidatos)

def _resolve_count(anomaly_cfg, total_rows: int) -> int:
    """Traduce 'rate' (%) o 'count' (nº absoluto) a un número concreto de filas"""
    if anomaly_cfg.count is not None:
        return anomaly_cfg.count
    return max(1, round(anomaly_cfg.rate * total_rows))

def apply_dq01(df: pd.DataFrame, row_id_col: str, cfg, ctx) -> list[ManifestEntry]:
    """DQ_01 - Valor obligatorio ausente: vacía un campo obligatorio en filas elegidas al azar."""
    if not cfg.fields:
        raise ValueError("DQ_01 requiere especificar 'fields' con el campo a vaciar")
    
    # De momento solo soportamos un campo por instancia de DQ_01
    campo = cfg.fields[0]
    
    n = _resolve_count(cfg, len(df)) # nº de filas con las que trabajamos
    
    # Solo son candidatas las filas donde el campo aún tiene valor
    # (no tiene sentido "vaciar" algo que ya está vacío) y cuya celda
    # (row_id, campo) no haya sido tocada ya por otra anomalía
    candidatos = [
        idx for idx in df.index
        if idx in ctx.frozen_ids
        and pd.notna(df.at[idx, campo])
        and (ctx.frozen_ids[idx], campo) not in ctx.used_cells
        and ctx.frozen_ids[idx] not in ctx.used_rows
    ]
    
    # Si no hay suficientes candidatos, falla explícitamente en vez de
    # aplicar menos anomalías de las pedidas en silencio
    if len(candidatos) < n:
        raise ValueError(
            f"DQ_01: solo hay {len(candidatos)} candidatos disponibles "
            f"para {n} solicitados en el campo '{campo}'"
        )
    
    elegidos = ctx.rng.sample(candidatos, n)
    
    entries = []
    for idx in elegidos:
        row_id = ctx.frozen_ids[idx]
        original = df.at[idx, campo]  # se guarda antes de borrarlo, para el manifiesto
        
        # La alteración en sí: vaciar el campo
        df.at[idx, campo] = None
        ctx.used_cells.add((row_id, campo))  # marcamos la celda como ya usada
        
        # Cada anomalía inyectada genera una entrada de manifiesto,
        # con un id y un orden secuencial únicos para toda la ejecución
        order, anomaly_id = ctx.next_entry_ids()
        entries.append(ManifestEntry(
            run_id=ctx.run_id,
            anomaly_id=anomaly_id,
            code="DQ_01",
            row_id=row_id,
            field=campo,
            original_value=str(original),
            altered_value=None,
            seed=ctx.seed,
            injected_order=order,
        ))
    return df, entries

# rules.py

def apply_dq02(df: pd.DataFrame, row_id_col: str, cfg, ctx) -> list[ManifestEntry]:
    """DQ_02 - Duplicado exacto: añade una copia idéntica de filas existentes."""
    n = _resolve_count(cfg, len(df))

    # Candidatas: filas que no tengan ninguna alteración previa (ni de
    # campo ni de fila completa), para no mezclar anomalías
    candidatos = [
        idx for idx in df.index
        if df.at[idx, row_id_col] not in ctx.used_rows
        and not any(rid == df.at[idx, row_id_col] for rid, _ in ctx.used_cells)
    ]
    if len(candidatos) < n:
        raise ValueError(
            f"DQ_02: solo hay {len(candidatos)} candidatos disponibles para {n} solicitados"
        )

    elegidos = ctx.rng.sample(candidatos, n)
    entries = []
    nuevas_filas = []

    for idx in elegidos:
        fila_original = df.loc[idx]
        row_id = ctx.frozen_ids[idx]

        nuevas_filas.append(fila_original.copy())  # copia exacta, se añade al final
        ctx.used_rows.add(row_id)

        order, anomaly_id = ctx.next_entry_ids()
        entries.append(ManifestEntry(
            run_id=ctx.run_id,
            anomaly_id=anomaly_id,
            code="DQ_02",
            row_id=row_id,
            field=None,
            original_value=None,
            altered_value=None,
            seed=ctx.seed,
            injected_order=order,
        ))

    # Se añaden todas las copias de golpe al final, no dentro del bucle,
    # para no alterar los índices mientras se itera sobre 'candidatos'
    df_nuevas = pd.DataFrame(nuevas_filas)
    # ignore_index=True asigna índices nuevos y únicos a las filas duplicadas,
    # en vez de que conserven el mismo índice que la fila original — evitando
    # índices duplicados en el DataFrame, que romperían df.at[]/df.loc[] con
    # ambigüedad en cualquier anomalía posterior que use ese índice
    df = pd.concat([df, df_nuevas], ignore_index=True)

    return df, entries

def apply_dq03(df: pd.DataFrame, row_id_col: str, cfg, ctx):
    """DQ_03 - Identificador duplicado: sobrescribe el ID de una fila con el de otra."""
    n = _resolve_count(cfg, len(df))

    candidatos = [
        idx for idx in df.index
        if idx in ctx.frozen_ids
        and (ctx.frozen_ids[idx], row_id_col) not in ctx.used_cells
        and ctx.frozen_ids[idx] not in ctx.used_rows
    ]
    if len(candidatos) < n * 2:  # cada instancia necesita una fila "objetivo" y una "donante"
        raise ValueError(
            f"DQ_03: solo hay {len(candidatos)} candidatos disponibles, "
            f"se necesitan {n * 2} (2 por cada instancia solicitada)"
        )

    entries = []
    for _ in range(n):
        objetivo_idx, donante_idx = ctx.rng.sample(candidatos, 2)
        candidatos.remove(objetivo_idx) # no reutilizar ni como objetivo ni como donante otra vez
        candidatos.remove(donante_idx)

        row_id = ctx.frozen_ids[objetivo_idx]           # identidad real, para el manifiesto
        id_original = df.at[objetivo_idx, row_id_col]   # valor visible antes de la alteración
        id_duplicado = ctx.frozen_ids[donante_idx]      # el ID que ahora quedará repetido

        df.at[objetivo_idx, row_id_col] = id_duplicado
        ctx.used_cells.add((row_id, row_id_col))

        order, anomaly_id = ctx.next_entry_ids()
        entries.append(ManifestEntry(
            run_id=ctx.run_id,
            anomaly_id=anomaly_id,
            code="DQ_03",
            row_id=row_id,
            field=row_id_col,
            original_value=id_original,
            altered_value=id_duplicado,
            seed=ctx.seed,
            injected_order=order,
        ))
    return df, entries

def apply_dq04(df: pd.DataFrame, row_id_col: str, cfg, ctx):
    """DQ_04 - Categoría no permitida: sustituye un valor por otro fuera del catálogo válido."""
    if not cfg.fields:
        raise ValueError("DQ_04 requiere especificar 'fields' con el campo a corromper")
    campo = cfg.fields[0]
    n = _resolve_count(cfg, len(df))

    candidatos = [
        idx for idx in df.index
        if idx in ctx.frozen_ids
        and (ctx.frozen_ids[idx], campo) not in ctx.used_cells
        and ctx.frozen_ids[idx] not in ctx.used_rows
    ]
    if len(candidatos) < n:
        raise ValueError(
            f"DQ_04: solo hay {len(candidatos)} candidatos disponibles "
            f"para {n} solicitados en el campo '{campo}'"
        )

    elegidos = ctx.rng.sample(candidatos, n)
    entries = []
    for idx in elegidos:
        row_id = ctx.frozen_ids[idx]
        original = df.at[idx, campo]
        valor_invalido = _generar_valor_invalido(campo, ctx)

        df.at[idx, campo] = valor_invalido
        ctx.used_cells.add((row_id, campo))

        order, anomaly_id = ctx.next_entry_ids()
        entries.append(ManifestEntry(
            run_id=ctx.run_id,
            anomaly_id=anomaly_id,
            code="DQ_04",
            row_id=row_id,
            field=campo,
            original_value=original,
            altered_value=valor_invalido,
            seed=ctx.seed,
            injected_order=order,
        ))
    return df, entries

def apply_dq05(df: pd.DataFrame, row_id_col: str, cfg, ctx):
    """DQ_05 - Tipo incorrecto: sustituye un valor numérico por texto no convertible."""
    if not cfg.fields:
        raise ValueError("DQ_05 requiere especificar 'fields' con el campo a corromper")
    campo = cfg.fields[0]
    n = _resolve_count(cfg, len(df))

    candidatos = [
        idx for idx in df.index
        if idx in ctx.frozen_ids
        and pd.notna(df.at[idx, campo])
        and (ctx.frozen_ids[idx], campo) not in ctx.used_cells
        and ctx.frozen_ids[idx] not in ctx.used_rows
    ]
    if len(candidatos) < n:
        raise ValueError(
            f"DQ_05: solo hay {len(candidatos)} candidatos disponibles "
            f"para {n} solicitados en el campo '{campo}'"
        )

    valores_invalidos = ["muchos", "N/D", "varios", "error", "??"]

    df[campo] = df[campo].astype(object) # antes de la asignación, para permitir mezclar tipos
    
    elegidos = ctx.rng.sample(candidatos, n)
    entries = []
    for idx in elegidos:
        row_id = ctx.frozen_ids[idx]
        original = df.at[idx, campo]
        valor_invalido = ctx.rng.choice(valores_invalidos)

        df.at[idx, campo] = valor_invalido
        ctx.used_cells.add((row_id, campo))

        order, anomaly_id = ctx.next_entry_ids()
        entries.append(ManifestEntry(
            run_id=ctx.run_id,
            anomaly_id=anomaly_id,
            code="DQ_05",
            row_id=row_id,
            field=campo,
            original_value=original,
            altered_value=valor_invalido,
            seed=ctx.seed,
            injected_order=order,
        ))
    return df, entries

def apply_dq06(df: pd.DataFrame, row_id_col: str, cfg, ctx):
    """DQ_06 - Valor fuera de rango: sustituye un valor por otro fuera del rango válido."""
    if not cfg.fields:
        raise ValueError("DQ_06 requiere especificar 'fields' con el campo a corromper")
    campo = cfg.fields[0]
    
    rango = RANGES_BY_TEMPLATE.get(ctx.template, {}).get(campo)
    if rango is None:
        raise ValueError(f"DQ_06: no hay rango conocido definido para el campo '{campo}'")
    minimo, maximo = rango
    
    n = _resolve_count(cfg, len(df))
    
    candidatos = [
        idx for idx in df.index
        if idx in ctx.frozen_ids
        and pd.notna(df.at[idx, campo])
        and (ctx.frozen_ids[idx], campo) not in ctx.used_cells
        and ctx.frozen_ids[idx] not in ctx.used_rows
    ]
    if len(candidatos) < n:
        raise ValueError(
            f"DQ_06: solo hay {len(candidatos)} candidatos disponibles "
            f"para {n} solicitados en el campo '{campo}'"
        )
    
    elegidos = ctx.rng.sample(candidatos, n)
    entries = []
    for idx in elegidos:
        row_id = ctx.frozen_ids[idx]
        original = df.at[idx, campo]
        
        # por encima o por debajo del rango, con la misma probabilidad
        if ctx.rng.random() < 0.5:
            valor_invalido = maximo + ctx.rng.randint(1, 5)
        else:
            valor_invalido = minimo - ctx.rng.randint(1, 5)
        
        df.at[idx, campo] = valor_invalido
        ctx.used_cells.add((row_id, campo))

        order, anomaly_id = ctx.next_entry_ids()
        entries.append(ManifestEntry(
            run_id=ctx.run_id,
            anomaly_id=anomaly_id,
            code="DQ_06",
            row_id=row_id,
            field=campo,
            original_value=original,
            altered_value=valor_invalido,
            seed=ctx.seed,
            injected_order=order,
        ))
    return df, entries

def apply_dq07(df: pd.DataFrame, row_id_col: str, cfg, ctx):
    """DQ_07 - Cronología imposible: un campo de fecha queda anterior a su referencia."""
    if not cfg.fields or len(cfg.fields) != 2:
        raise ValueError("DQ_07 requiere 'fields: [campo_a_corromper, campo_de_referencia]'")
    campo, referencia = cfg.fields
    n = _resolve_count(cfg, len(df))

    candidatos = [
        idx for idx in df.index
        if idx in ctx.frozen_ids
        and pd.notna(df.at[idx, campo])
        and pd.notna(df.at[idx, referencia])
        and (ctx.frozen_ids[idx], campo) not in ctx.used_cells
        and ctx.frozen_ids[idx] not in ctx.used_rows
    ]
    if len(candidatos) < n:
        raise ValueError(
            f"DQ_07: solo hay {len(candidatos)} candidatos disponibles "
            f"para {n} solicitados en '{campo}' vs '{referencia}'"
        )
    
    elegidos = ctx.rng.sample(candidatos, n)
    entries = []
    for idx in elegidos:
        row_id = ctx.frozen_ids[idx]
        original = df.at[idx, campo]
        fecha_referencia = df.at[idx, referencia]
        
        # el campo corrompido queda entre 1 minuto y 3 horas ANTES de la referencia
        delta_minutos = ctx.rng.randint(1, 180)
        valor_invalido = pd.Timestamp(fecha_referencia) - pd.Timedelta(minutes=delta_minutos)

        df.at[idx, campo] = valor_invalido
        ctx.used_cells.add((row_id, campo))
        
        order, anomaly_id = ctx.next_entry_ids()
        entries.append(ManifestEntry(
            run_id=ctx.run_id,
            anomaly_id=anomaly_id,
            code="DQ_07",
            row_id=row_id,
            field=campo,
            original_value=str(original),
            altered_value=str(valor_invalido),
            related_fields=[referencia],
            seed=ctx.seed,
            injected_order=order,
        ))
    return df, entries

def apply_dq08(df: pd.DataFrame, row_id_col: str, cfg, ctx):
    """DQ_08 - Dependencia incumplida: vacía un campo obligatorio solo bajo cierta condición."""
    if not cfg.fields:
        raise ValueError("DQ_08 requiere 'fields' con el campo dependiente a vaciar")
    campo = cfg.fields[0]

    dependencia = DEPENDENCES_BY_TEMPLATE.get(ctx.template, {}).get(campo)
    if dependencia is None:
        raise ValueError(f"DQ_08: no hay dependencia conocida definida para el campo '{campo}'")
    disparador = dependencia["campo_disparador"]
    valores_disparadores = dependencia["valores_disparadores"]

    n = _resolve_count(cfg, len(df))

    candidatos = [
        idx for idx in df.index
        if idx in ctx.frozen_ids
        and df.at[idx, disparador] in valores_disparadores  # solo filas donde SÍ aplicaría la obligación
        and pd.notna(df.at[idx, campo])
        and (ctx.frozen_ids[idx], campo) not in ctx.used_cells
        and ctx.frozen_ids[idx] not in ctx.used_rows
    ]
    if len(candidatos) < n:
        raise ValueError(
            f"DQ_08: solo hay {len(candidatos)} candidatos disponibles para {n} solicitados "
            f"en '{campo}' (condición {disparador} in {valores_disparadores})"
        )

    elegidos = ctx.rng.sample(candidatos, n)
    entries = []
    for idx in elegidos:
        row_id = ctx.frozen_ids[idx]
        original = df.at[idx, campo]

        df.at[idx, campo] = None
        ctx.used_cells.add((row_id, campo))

        order, anomaly_id = ctx.next_entry_ids()
        entries.append(ManifestEntry(
            run_id=ctx.run_id,
            anomaly_id=anomaly_id,
            code="DQ_08",
            row_id=row_id,
            field=campo,
            original_value=str(original),
            altered_value=None,
            related_fields=[disparador],
            seed=ctx.seed,
            injected_order=order,
        ))
    return df, entries

def apply_dq09(df: pd.DataFrame, row_id_col: str, cfg, ctx):
    """DQ_09 - Formato inconsistente: reescribe una fecha en un formato distinto al estándar (ISO)."""
    if not cfg.fields:
        raise ValueError("DQ_09 requiere 'fields' con el campo de fecha a corromper")
    campo = cfg.fields[0]
    n = _resolve_count(cfg, len(df))

    candidatos = [
        idx for idx in df.index
        if idx in ctx.frozen_ids
        and pd.notna(df.at[idx, campo])
        and (ctx.frozen_ids[idx], campo) not in ctx.used_cells
        and ctx.frozen_ids[idx] not in ctx.used_rows
    ]
    if len(candidatos) < n:
        raise ValueError(
            f"DQ_09: solo hay {len(candidatos)} candidatos disponibles "
            f"para {n} solicitados en el campo '{campo}'"
        )

    # necesario para poder mezclar texto (fecha mal formateada) en una
    # columna que hasta ahora era de tipo fecha/datetime
    df[campo] = df[campo].astype(object)

    elegidos = ctx.rng.sample(candidatos, n)
    entries = []
    for idx in elegidos:
        row_id = ctx.frozen_ids[idx]
        original = df.at[idx, campo]

        # mismo valor de fecha, pero en DD/MM/YYYY en vez del ISO estándar
        fecha = pd.Timestamp(original)
        valor_invalido = fecha.strftime("%d/%m/%Y %H:%M:%S")

        df.at[idx, campo] = valor_invalido
        ctx.used_cells.add((row_id, campo))

        order, anomaly_id = ctx.next_entry_ids()
        entries.append(ManifestEntry(
            run_id=ctx.run_id,
            anomaly_id=anomaly_id,
            code="DQ_09",
            row_id=row_id,
            field=campo,
            original_value=str(original),
            altered_value=valor_invalido,
            seed=ctx.seed,
            injected_order=order,
        ))
    return df, entries

def apply_dq10(df: pd.DataFrame, row_id_col: str, cfg, ctx):
    """DQ_10 — Espacios o capitalización: añade ruido superficial a un valor de texto/categórico."""
    if not cfg.fields:
        raise ValueError("DQ_10 requiere 'fields' con el campo de texto a corromper")
    campo = cfg.fields[0]
    n = _resolve_count(cfg, len(df))

    candidatos = [
        idx for idx in df.index
        if idx in ctx.frozen_ids
        and pd.notna(df.at[idx, campo])
        and (ctx.frozen_ids[idx], campo) not in ctx.used_cells
        and ctx.frozen_ids[idx] not in ctx.used_rows
    ]
    if len(candidatos) < n:
        raise ValueError(
            f"DQ_10: solo hay {len(candidatos)} candidatos disponibles "
            f"para {n} solicitados en el campo '{campo}'"
        )

    df[campo] = df[campo].astype(object)

    def _ensuciar(valor: str, rng) -> str:
        variantes = [
            f"  {valor}",           # espacio al principio
            f"{valor}  ",           # espacio al final
            valor.upper(),          # todo mayúsculas
            valor.capitalize(),     # solo primera letra en mayúscula
        ]
        return rng.choice(variantes)

    elegidos = ctx.rng.sample(candidatos, n)
    entries = []
    for idx in elegidos:
        row_id = ctx.frozen_ids[idx]
        original = df.at[idx, campo]
        valor_invalido = _ensuciar(str(original), ctx.rng)

        df.at[idx, campo] = valor_invalido
        ctx.used_cells.add((row_id, campo))

        order, anomaly_id = ctx.next_entry_ids()
        entries.append(ManifestEntry(
            run_id=ctx.run_id,
            anomaly_id=anomaly_id,
            code="DQ_10",
            row_id=row_id,
            field=campo,
            original_value=original,
            altered_value=valor_invalido,
            seed=ctx.seed,
            injected_order=order,
        ))
    return df, entries
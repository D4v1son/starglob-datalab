import pandas as pd
from pydantic import BaseModel
from typing import Optional


class MatchResult(BaseModel):
    code: str
    row_id: Optional[str] = None
    field: Optional[str] = None
    kind: str  # "true_positive" | "false_positive" | "false_negative"

class CodeMetrics(BaseModel):
    code: str
    true_positives: int
    false_positives: int
    false_negatives: int
    precision: float
    recall: float
    f1: float
    
def _f1(precision:float, recall:float) -> float:
    if precision + recall == 0:
        return 0.0
    return 2 * precision * recall / (precision + recall)

def _precision_recall(tp: int, fp: int, fn: int) -> tuple[float, float]:
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    return precision, recall

def _claves_manifiesto(entries: list, df_clean, row_id_col: str) -> dict[tuple, list]:
    """
    Construye, para cada código, el conjunto de claves de emparejamiento
    esperadas según el manifiesto. La mayoría usa (row_id, field); DQ_03 y
    DQ_11 usan una clave distinta, coherente con lo que el auditor puede ver.
    """
    claves_por_codigo: dict[str, set] = {}
    
    for entry in entries:
        claves_por_codigo.setdefault(entry.code, set())

        if entry.code == "DQ_03":
            # el auditor solo ve el valor duplicado, no la identidad original
            claves_por_codigo[entry.code].add((str(entry.altered_value).strip(), entry.field))
        
        elif entry.code == "DQ_11":
            # recupera client_id/job_name desde clean.csv usando el row_id congelado
            fila = df_clean[df_clean[row_id_col] == entry.row_id]
            if fila.empty:
                continue
            
            # Normalizamos client_id (upper + strip) para alinearlo con el auditor
            client_id = str(fila["client_id"].values[0]).strip().upper()
            job_name = str(fila["job_name"].values[0]).strip()
            
            # Normalizamos la fecha a objeto date
            fecha_eliminada = pd.Timestamp(entry.original_value).date()
            
            claves_por_codigo[entry.code].add((f"{client_id}|{job_name}", fecha_eliminada))

        else:
            claves_por_codigo[entry.code].add((entry.row_id, entry.field))

    return claves_por_codigo

def evaluate(entries: list, findings: list, df_clean, row_id_col: str) -> dict:
    """
    Compara manifiesto (entries) contra hallazgos (findings) y calcula
    verdaderos/falsos positivos, falsos negativos y métricas por código y
    globales. Requiere df_clean para resolver el emparejamiento especial
    de DQ_11 (cliente + trabajo, no row_id).
    """
    claves_manifiesto = _claves_manifiesto(entries, df_clean, row_id_col)
    codigos = set(claves_manifiesto) | {f.rule_code for f in findings}
    
    matches: list[MatchResult] = []
    metricas_por_codigo: list[CodeMetrics] = []
    tp_total = fp_total = fn_total = 0
    
    for codigo in sorted(codigos):
        esperadas = claves_manifiesto.get(codigo, set())
        hallazgos_codigo = [f for f in findings if f.rule_code == codigo]
        
        tp = fp = 0
        esperadas_cubiertas = set()
        
        for finding in hallazgos_codigo:
            if codigo == "DQ_03":
                clave = (str(finding.row_id).strip(), finding.field)    # row_id del hallazgo = valor duplicado
                acierto = clave in esperadas
                if acierto:
                    esperadas_cubiertas.add(clave)
            elif codigo == "DQ_11":
                # Convertimos la fecha del hallazgo a .date()
                try:
                    fecha_hallazgo = pd.Timestamp(finding.observed_value).date()
                except Exception:
                    fecha_hallazgo = finding.observed_value

                # Normalizamos el row_id del hallazgo
                row_id_hallazgo = str(finding.row_id).strip().upper()
                clave = (row_id_hallazgo, fecha_hallazgo)

                acierto = clave in esperadas
                if acierto:
                    esperadas_cubiertas.add(clave)
            else:
                clave = (finding.row_id, finding.field)
                acierto = clave in esperadas
                if acierto:
                    esperadas_cubiertas.add(clave)
            if acierto:
                tp += 1
                matches.append(
                    MatchResult(
                        code=codigo,
                        row_id=str(finding.row_id),
                        field=finding.field,
                        kind="true_positive",
                    )
                )
            else:
                fp += 1
                matches.append(
                    MatchResult(
                        code=codigo,
                        row_id=str(finding.row_id),
                        field=finding.field,
                        kind="false_positive",
                    )
                )
        
        fn = len(esperadas - esperadas_cubiertas)
        for clave_faltante in esperadas - esperadas_cubiertas:
            matches.append(
                MatchResult(
                    code=codigo,
                    row_id=str(clave_faltante[0]),
                    field=str(clave_faltante[1]),
                    kind="false_negative",
                )
            )

        precision, recall = _precision_recall(tp, fp, fn)
        metricas_por_codigo.append(
            CodeMetrics(
                code=codigo,
                true_positives=tp,
                false_positives=fp,
                false_negatives=fn,
                precision=precision,
                recall=recall,
                f1=_f1(precision, recall),
            )
        )
        
        tp_total += tp
        fp_total += fp
        fn_total += fn

    precision_global, recall_global = _precision_recall(tp_total, fp_total, fn_total)
    metricas_globales = CodeMetrics(
        code="GLOBAL", 
        true_positives=tp_total, 
        false_positives=fp_total, 
        false_negatives=fn_total,
        precision=precision_global, 
        recall=recall_global, 
        f1=_f1(precision_global, recall_global),
    )
    
    return {
        "matches": matches,
        "metrics_by_code": metricas_por_codigo,
        "metrics_global": metricas_globales,
    }
        

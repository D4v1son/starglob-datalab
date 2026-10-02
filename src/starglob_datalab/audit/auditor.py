from starglob_datalab.audit.finding import Finding
from starglob_datalab.audit import rules as audit_rules
from functools import partial

def _reglas_por_template(template):
    return {
        "DQ_01": partial(
            audit_rules.check_required_fields,
            campos_requeridos=audit_rules.REQUIRED_FIELDS_BY_TEMPLATE[template],
        ),
        "DQ_02": audit_rules.check_exact_duplicates,
        "DQ_03": audit_rules.check_duplicate_id,
        "DQ_04": partial(audit_rules.check_valid_category, template=template),
        "DQ_05": partial(audit_rules.check_valid_type, template=template),
        "DQ_06": partial(audit_rules.check_value_range, template=template),
        "DQ_07": partial(audit_rules.check_chronology, template=template),
        "DQ_08": partial(audit_rules.check_dependency, template=template),
        "DQ_09": partial(audit_rules.check_date_format, template=template),
        "DQ_10": partial(audit_rules.check_text_hygiene, template=template),
        "DQ_11": partial(audit_rules.check_continuity, template=template),
        "DQ_12": partial(audit_rules.check_extreme_duration, template=template),
        "DQ_13": partial(audit_rules.check_orphan_reference, template=template),
        "DQ_14": partial(audit_rules.check_encoding, template=template),
    }


RULES_BY_TEMPLATE = {
    "tickets": _reglas_por_template("tickets"),
    "backups": _reglas_por_template("backups"),
}

def audit(df, row_id_col: str, template: str, run_id: str) -> list[Finding]:
    """
    Ejecuta todas las reglas de auditoría registradas para 'template' sobre
    'df'. No modifica el DataFrame ni conoce el manifiesto: solo ve los datos.
    """
    reglas = RULES_BY_TEMPLATE.get(template)
    if reglas is None:
        raise NotImplementedError(f"No hay reglas de auditoría para la plantilla '{template}'")

    findings = []
    contador = 0
    for rule_code, funcion_regla in reglas.items():
        for hallazgo_parcial in funcion_regla(df, row_id_col):
            contador += 1
            findings.append(Finding(
                finding_id=f"find_{contador:06d}",
                run_id=run_id,
                rule_code=rule_code,
                **hallazgo_parcial,
            ))
    return findings
import argparse
import uuid
import json
import pandas as pd
from pathlib import Path

from importlib.metadata import version as pkg_version
from starglob_datalab.configuration import load_config
from starglob_datalab.generation.tickets import generate_tickets
from starglob_datalab.generation.backups import generate_backups
from starglob_datalab.anomalies.injector import inject_anomalies
from starglob_datalab.anomalies.manifest import write_manifest, ManifestEntry
from starglob_datalab.audit.auditor import audit
from starglob_datalab.audit.finding import write_findings
from starglob_datalab.evaluation.evaluator import evaluate


ROW_ID_COL_BY_TEMPLATE = {
    "tickets": "ticket_id",
    "backups": "backup_id",
}


def cmd_generate(args):
    config = load_config(args.config)

    if config.template == "tickets":
        df_clean = generate_tickets(config)
        row_id_col = "ticket_id"
    elif config.template == "backups":
        df_clean = generate_backups(config)
        row_id_col = "backup_id"
    else:
        raise NotImplementedError(f"Plantilla '{config.template}' aún no implementada")
    
    output_dir = Path(config.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    clean_path = output_dir / "clean.csv"
    df_clean.to_csv(clean_path, index=False)
    print(f"Generadas {len(df_clean)} filas en {clean_path}")
    
    if config.anomalies:
        # Cada ejecución, sin importar la semilla, tendrá un identificador único
        # Esto no afecta a la reproducibilidad del dirty_csv ni el manifiesto
        run_id = f"run_{uuid.uuid4().hex[:8]}"
        df_dirty, entries = inject_anomalies(
            df_clean.copy(), # El generador de anomalías travbaja con una copia para no alterar el original
            row_id_col=row_id_col,
            config=config,
            run_id=run_id
        )

        dirty_path = output_dir / "dirty.csv"
        df_dirty.to_csv(dirty_path, index=False)
        print(f"Generadas {len(df_dirty)} filas sucias en {dirty_path}")
        
        manifest_path = output_dir / "truth_manifest.jsonl"
        write_manifest(entries, str(manifest_path))
        print(f"{len(entries)} anomalías inyectadas, manifiesto en {manifest_path}")
        
    # output_path = output_dir / f"{config.template}_clean.csv"
    # df.to_csv(output_path, index=False)
    # 
    # print(f"Generadas {len(df)} filas en {output_path}")

def cmd_audit(args):
    row_id_col = ROW_ID_COL_BY_TEMPLATE.get(args.template)
    if row_id_col is None:
        raise ValueError(f"Plantilla desconocida: '{args.template}'")

    # sin parse_dates: el auditor necesita las fechas como texto (DQ_09)
    df = pd.read_csv(args.input)

    run_id = f"run_{uuid.uuid4().hex[:8]}"
    findings = audit(df, row_id_col=row_id_col, template=args.template, run_id=run_id)

    output_path = args.output or str(Path(args.input).parent / "audit_results.json")
    write_findings(findings, output_path)

    print(f"{len(findings)} hallazgos detectados, guardados en {output_path}")

def cmd_evaluate(args):
    df_clean = pd.read_csv(args.clean)
    df_dirty = pd.read_csv(args.dirty)
    with open(args.manifest) as f:
        entries = [ManifestEntry(**json.loads(l)) for l in f]

    row_id_col = ROW_ID_COL_BY_TEMPLATE[args.template]
    findings = audit(df_dirty, row_id_col=row_id_col, template=args.template, run_id="run_audit")
    resultado = evaluate(entries, findings, df_clean, row_id_col=row_id_col)

    with open(args.output or "evaluation_results.json", "w") as f:
        json.dump({
            "metrics_by_code": [m.model_dump() for m in resultado["metrics_by_code"]],
            "metrics_global": resultado["metrics_global"].model_dump(),
        }, f, indent=2)
    print(f"F1 global: {resultado['metrics_global'].f1:.2f}")


def main():
    parser = argparse.ArgumentParser(prog="starglob_datalab")
    parser.add_argument("--version", action="version", version=f"starglob_datalab {pkg_version('starglob-datalab')}")
    subparsers = parser.add_subparsers(dest="command", required=True)
    
    # comando generate, crea nuevos datos sintéticos
    generate_parser = subparsers.add_parser("generate", help="Genera un dataset limmpio")
    generate_parser.add_argument("--config", required=True, help="Ruta al YAML de configuración")
    generate_parser.set_defaults(func=cmd_generate)
    
    # comando audit, auditor de datos (no necesariamente sintéticos)
    audit_parser = subparsers.add_parser("audit", help="Audita un dataset y genera hallazgos")
    audit_parser.add_argument("--input", required=True, help="Ruta al CSV a auditar (clean o dirty)")
    audit_parser.add_argument("--template", required=True, choices=["tickets", "backups"])
    audit_parser.add_argument("--output", help="Ruta de salida (por defecto, junto al input)")
    audit_parser.set_defaults(func=cmd_audit)
    
    # comando evaluate, compara los resultados de audit con manifest y los csv
    evaluate_parser = subparsers.add_parser("evaluate", help="Evalúa hallazgos contra el manifiesto")
    evaluate_parser.add_argument("--clean", required=True)
    evaluate_parser.add_argument("--dirty", required=True)
    evaluate_parser.add_argument("--manifest", required=True)
    evaluate_parser.add_argument("--template", required=True, choices=["tickets", "backups"])
    evaluate_parser.add_argument("--output")
    evaluate_parser.set_defaults(func=cmd_evaluate)
    
    args = parser.parse_args()
    args.func(args)
    
if __name__ == "__main__":
    main()
import argparse
import uuid
import json
import pandas as pd
from pathlib import Path
import logging
logger = logging.getLogger("starglob_datalab")

from importlib.metadata import version as pkg_version
from starglob_datalab.configuration import load_config
from starglob_datalab.generation.tickets import generate_tickets
from starglob_datalab.generation.backups import generate_backups
from starglob_datalab.anomalies.injector import inject_anomalies
from starglob_datalab.anomalies.manifest import write_manifest, ManifestEntry
from starglob_datalab.audit.auditor import audit
from starglob_datalab.audit.finding import write_findings, write_findings_csv
from starglob_datalab.evaluation.evaluator import evaluate, write_metrics_csv
from starglob_datalab.persistence.db import init_db, save_run, save_findings, save_metrics, get_run
from starglob_datalab.logging_config import setup_logging


ROW_ID_COL_BY_TEMPLATE = {
    "tickets": "ticket_id",
    "backups": "backup_id",
}

DEFAULT_EVAL_NAME = "evaluation_results"

def cmd_generate(args):
    config = load_config(args.config)
    run_id = args.run_id or f"run_{uuid.uuid4().hex[:8]}"

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
    logger.info(f"Generadas {len(df_clean)} filas en {clean_path}")
    
    conn = init_db("data/starglob.db")
    save_run(conn, run_id, config.template, config.name, config.seed, config.rows)
    
    if config.anomalies:
        # Cada ejecución, sin importar la semilla, tendrá un identificador único
        # Esto no afecta a la reproducibilidad del dirty_csv ni el manifiesto
        df_dirty, entries = inject_anomalies(
            df_clean.copy(), # El generador de anomalías travbaja con una copia para no alterar el original
            row_id_col = row_id_col,
            config = config,
            run_id = run_id
        )

        dirty_path = output_dir / "dirty.csv"
        df_dirty.to_csv(dirty_path, index=False)
        logger.info(f"Generadas {len(df_dirty)} filas sucias en {dirty_path}")
        
        manifest_path = output_dir / "truth_manifest.jsonl"
        write_manifest(entries, str(manifest_path))
        logger.info(f"{len(entries)} anomalías inyectadas, manifiesto en {manifest_path}")
    
    # output_path = output_dir / f"{config.template}_clean.csv"
    # df.to_csv(output_path, index=False)
    # 
    # logger.info(f"Generadas {len(df)} filas en {output_path}")

def cmd_audit(args):
    row_id_col = ROW_ID_COL_BY_TEMPLATE.get(args.template)
    if row_id_col is None:
        raise ValueError(f"Plantilla desconocida: '{args.template}'")

    # sin parse_dates: el auditor necesita las fechas como texto (DQ_09)
    df = pd.read_csv(args.input)

    if args.run_id: # en caso de querer enlazarlo con un manifiesto externo
        run_id = args.run_id
    else: # si queremos relacionarlo con las ejecuiones del manifiesto que hemos generado
        manifest_path = Path(args.input).parent / "truth_manifest.jsonl"
        if manifest_path.exists():
            with open(manifest_path, encoding="utf-8") as f:
                run_id = json.loads(f.readline())["run_id"]
        else:
            run_id = f"run_{uuid.uuid4().hex[:8]}"
    
    findings = audit(df, row_id_col=row_id_col, template=args.template, run_id=run_id)

    output_path = args.output or str(Path(args.input).parent / "audit_results.json")
    write_findings(findings, output_path)
    write_findings_csv(findings, output_path.replace(".json", ".csv"))
    
    conn = init_db("data/starglob.db")
    if get_run(conn, run_id) is None:
        save_run(conn, run_id, args.template, Path(args.input).stem, None, len(df))
    save_findings(conn, run_id, findings)

    logger.info(f"{len(findings)} hallazgos detectados, guardados en {output_path}")

def cmd_evaluate(args):
    df_clean = pd.read_csv(args.clean)
    df_dirty = pd.read_csv(args.dirty)
    with open(args.manifest) as f:
        entries = [ManifestEntry(**json.loads(l)) for l in f]
    if args.run_id:
        run_id = args.run_id
    else:
        with open(args.manifest, encoding="utf-8") as f:
            run_id = json.loads(f.readline())["run_id"]

    row_id_col = ROW_ID_COL_BY_TEMPLATE[args.template]
    findings = audit(df_dirty, row_id_col=row_id_col, template=args.template, run_id=run_id)
    resultado = evaluate(entries, findings, df_clean, row_id_col=row_id_col)

    with open(args.output or DEFAULT_EVAL_NAME+".json", "w") as f:
        json.dump({
            "metrics_by_code": [m.model_dump() for m in resultado["metrics_by_code"]],
            "metrics_global": resultado["metrics_global"].model_dump(),
        }, f, indent=2)
    logger.info(f"F1 global: {resultado['metrics_global'].f1:.2f}")
    
    conn = init_db("data/starglob.db")
    save_metrics(conn, run_id, resultado["metrics_by_code"], resultado["metrics_global"])
    write_metrics_csv(resultado["metrics_by_code"], resultado["metrics_global"], (args.output or DEFAULT_EVAL_NAME)+".csv")
    

def main():
    setup_logging()
    parser = argparse.ArgumentParser(prog="starglob_datalab")
    parser.add_argument("--version", action="version", version=f"starglob_datalab {pkg_version('starglob-datalab')}")
    subparsers = parser.add_subparsers(dest="command", required=True)
    
    # comando generate, crea nuevos datos sintéticos
    generate_parser = subparsers.add_parser("generate", help="Genera un dataset limmpio")
    generate_parser.add_argument("--config", required=True, help="Ruta al YAML de configuración")
    generate_parser.add_argument("--run-id", dest="run_id")
    generate_parser.set_defaults(func=cmd_generate)
    
    # comando audit, auditor de datos (no necesariamente sintéticos)
    audit_parser = subparsers.add_parser("audit", help="Audita un dataset y genera hallazgos")
    audit_parser.add_argument("--input", required=True, help="Ruta al CSV a auditar (clean o dirty)")
    audit_parser.add_argument("--template", required=True, choices=["tickets", "backups"])
    audit_parser.add_argument("--output", help="Ruta de salida (por defecto, junto al input)")
    audit_parser.add_argument("--run-id", dest="run_id", help="Vincula esta auditoría a una ejecución existente (opcional)") # esto es util si queremos auditar csv no artificiales
    audit_parser.set_defaults(func=cmd_audit)
    
    # comando evaluate, compara los resultados de audit con manifest y los csv
    evaluate_parser = subparsers.add_parser("evaluate", help="Evalúa hallazgos contra el manifiesto")
    evaluate_parser.add_argument("--clean", required=True)
    evaluate_parser.add_argument("--dirty", required=True)
    evaluate_parser.add_argument("--manifest", required=True)
    evaluate_parser.add_argument("--template", required=True, choices=["tickets", "backups"])
    evaluate_parser.add_argument("--output")
    evaluate_parser.add_argument("--run-id", dest="run_id")
    evaluate_parser.set_defaults(func=cmd_evaluate)
    
    args = parser.parse_args()
    try:
        args.func(args)
    except Exception:
        logger.exception("Error no controlado durante la ejecución")
        raise
    
if __name__ == "__main__":
    main()
import argparse
import uuid
from pathlib import Path

from importlib.metadata import version as pkg_version
from starglob_datalab.configuration import load_config
from starglob_datalab.generation.tickets import generate_tickets
from starglob_datalab.generation.backups import generate_backups
from starglob_datalab.anomalies.injector import inject_anomalies
from starglob_datalab.anomalies.manifest import write_manifest


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



def main():
    parser = argparse.ArgumentParser(prog="starglob_datalab")
    parser.add_argument("--version", action="version", version=f"starglob_datalab {pkg_version('starglob-datalab')}")
    subparsers = parser.add_subparsers(dest="command", required=True)
    
    generate_parser = subparsers.add_parser("generate", help="Genera un dataset limmpio")
    generate_parser.add_argument("--config", required=True, help="Ruta al YAML de configuración")
    generate_parser.set_defaults(func=cmd_generate)
    
    args = parser.parse_args()
    args.func(args)
    
if __name__ == "__main__":
    main()
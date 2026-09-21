import argparse
from pathlib import Path

from starglob_datalab.configuration import load_config
from starglob_datalab.generation.tickets import generate_tickets
from starglob_datalab.generation.backups import generate_backups


def cmd_generate(args):
    config = load_config(args.config)

    if config.template == "tickets":
        df = generate_tickets(config)
    elif config.template == "backups":
        df = generate_backups(config)
    else:
        raise NotImplementedError(f"Plantilla '{config.template}' aún no implementada")
    
    output_dir = Path(config.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    output_path = output_dir / f"{config.template}_clean.csv"
    df.to_csv(output_path, index=False)
    
    print(f"Generadas {len(df)} filas en {output_path}")

def main():
    parser = argparse.ArgumentParser(prog="starglob_datalab")
    subparsers = parser.add_subparsers(dest="command", required=True)
    
    generate_parser = subparsers.add_parser("generate", help="Genera un dataset limmpio")
    generate_parser.add_argument("--config", required=True, help="Ruta al YAML de configuración")
    generate_parser.set_defaults(func=cmd_generate)
    
    args = parser.parse_args()
    args.func(args)
    
if __name__ == "__main__":
    main()
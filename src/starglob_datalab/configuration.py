from datetime import date
from pathlib import Path
import yaml
from pydantic import BaseModel

class Period(BaseModel):
    start_date: date
    end_date: date

class GeneratorConfig(BaseModel):
    name: str
    template: str   # tickets o backups
    seed: int
    rows: int
    period: Period
    output_dir: str
    
def load_config(path: str) -> GeneratorConfig:
    contenido = Path(path).read_text(encoding="utf-8") # lo necesitamos para caracteres especiales como la Ñ
    datos = yaml.safe_load(contenido)
    return GeneratorConfig(**datos)

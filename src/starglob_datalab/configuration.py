from datetime import date
from pathlib import Path
import yaml
from pydantic import BaseModel, model_validator
from typing import Optional


class Period(BaseModel):
    start_date: date
    end_date: date

class AnomalyInjectionConfig(BaseModel):
    code: str
    rate: Optional[float] = None
    count: Optional[int] = None
    fields: Optional[list[str]] = None
    
    @model_validator(mode="after")
    def check_rate_or_count(self):
        if self.rate is None and self.count is None:
            raise ValueError(f"{self.code}: hay que indicar 'rate' o 'count'")
        if self.rate is not None and self.count is not None:
            raise ValueError(f"{self.code}: 'rate' y 'count' son excluyentes, no ambos")
        return self

class GeneratorConfig(BaseModel):
    name: str
    template: str   # tickets o backups
    seed: int
    rows: int
    period: Period
    output_dir: str
    anomalies: Optional[list[AnomalyInjectionConfig]] = None

def load_config(path: str) -> GeneratorConfig:
    contenido = Path(path).read_text(encoding="utf-8") # lo necesitamos para caracteres especiales como la Ñ
    datos = yaml.safe_load(contenido)
    return GeneratorConfig(**datos)

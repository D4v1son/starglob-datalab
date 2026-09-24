from typing import Any, Optional
from pydantic import BaseModel, model_validator


class ManifestEntry(BaseModel):
    run_id: str
    anomaly_id: str
    code: str
    row_id: str
    field: Optional[str] = None
    original_value: Optional[Any] = None
    altered_value: Optional[Any] = None
    related_fields: list[str] = []
    seed: int
    injected_order: int
    
    @model_validator(mode="after")
    def check_field_consistency(self):
        if self.field is not None and self.original_value is None and self.altered_value is None:
            raise ValueError("Si 'field' está presente, debe existir original_value o altered_value")
        return self

def write_manifest(entries: list[ManifestEntry], path: str) -> None:
    """Escribe el manifiesto como JSONL: una línea JSON por anomalía."""
    with open(path, "w", encoding="utf-8") as f:
        for entry in entries:
            f.write(entry.model_dump_json() + "\n")
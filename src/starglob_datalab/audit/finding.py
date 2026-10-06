import json
import csv

from datetime import datetime, timezone
from typing import Any, Optional
from pydantic import BaseModel


class Finding(BaseModel):
    finding_id: str
    run_id: str
    rule_code: str  # coincide con el código DQ_XX que detecta
    severity: str   # info | warning | error | critical
    row_id: Optional[str] = None    # es opcional ya que en DQ_11 devolvemos row_id = None
    field: Optional[str] = None
    observed_value: Optional[Any] = None
    expected: str
    message: str
    detected_at: datetime = None
    
    def model_post_init(self, __context):
        if self.detected_at is None:
            self.detected_at = datetime.now(timezone.utc)
    
    
def write_findings(findings: list[Finding], path:str) -> None:
    """Escribe los hallazgos como JSON: una lista de objetos."""
    with open(path, "w", encoding="utf-8") as f:
        json.dump([f.model_dump(mode="json") for f in findings], f, indent=2, ensure_ascii=False)

def write_findings_csv(findings: list, path: str) -> None:
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=Finding.model_fields.keys())
        writer.writeheader()
        for finding in findings:
            writer.writerow(finding.model_dump(mode="json"))
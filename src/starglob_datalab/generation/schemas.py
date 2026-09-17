"""
Aquí se establecen los esquemas definidos por las plantillas.
Los definimos con la librería de pydantic, que es muy estricta.
Cuando desarrolle la parte de 'inyectar anomalias' lo ideal es montar los datos con dataframes de pandas.
"""

from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, field_validator, model_validator

SLA_BY_PRIORITY = {"critical": 60, "high": 240, "medium": 1440, "low": 4320}

class TicketCategory(str, Enum):
    HARDWARE = "hardware"
    SOFTWARE = "software"
    NETWORK = "network"
    EMAIL = "email"
    SECURITY = "security"
    BILLING = "billing"
    OTHER = "other"
    
class TicketPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"
    
class TicketStatus(str, Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    PENDING_CLIENT = "pending_client"
    RESOLVED = "resolved"
    CLOSED = "closed"
    
class TicketChannel(str, Enum):
    EMAIL = "email"
    PHONE = "phone"
    WEB = "web"
    MONITORING = "monitoring"
    
class Ticket(BaseModel):
    ticket_id: str
    client_id: str
    created_at: datetime
    first_response_at: Optional[datetime] = None
    closed_at: Optional[datetime] = None
    category: TicketCategory
    priority: TicketPriority
    status: TicketStatus
    channel: TicketChannel
    technician_id: Optional[str] = None
    summary: str
    sla_target_minutes: int
    satisfaction_score: Optional[int] = None
    
    @field_validator("summary")
    @classmethod # para no utilizar self ya que lo estamos ejecutando al construir la clase
    def summary_length(cls, v):
        if not (15 <= len(v) <= 180):
            raise ValueError("summary debe tener entre 15 y 180 caracteres")
        return v
    
    @model_validator (mode="after") # validamos después de crear el modelo
    def check_dependencies(self):   # como ya esta creado si podemos usar self
        if self.first_response_at and self.first_response_at < self.created_at:
            raise ValueError("first_response_at debe ser >= created_at")
        if self.status == TicketStatus.CLOSED and self.closed_at is None:
            raise ValueError("closed_at es obligatorio cuando status=closed")
        if self.closed_at and self.closed_at <= self.created_at:
            raise ValueError("closed_at debe ser posterior a created_at")
        if self.status != TicketStatus.CLOSED and self.satisfaction_score is not None:
            raise ValueError("satisfaction_score solo aplica a tickets closed")
        expected_sla = SLA_BY_PRIORITY[self.priority.value]
        if self.sla_target_minutes != expected_sla: # incluso si llegamos a signar el tiempo de espera de forma automática, necesitamos poder comprobarlo para las auditorías
            raise ValueError(f"sla_target_minutes debe ser {expected_sla} para priority={self.priority}")
        return self
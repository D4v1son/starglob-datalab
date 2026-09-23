import pandas as pd
from faker import Faker
from datetime import timedelta

from starglob_datalab.configuration import GeneratorConfig
from starglob_datalab.generation.schemas import (
    Ticket, TicketCategory, TicketPriority, TicketStatus, TicketChannel,
    SLA_BY_PRIORITY,
)


TECID_CHANCE_ON_OPEN = 80

def generate_tickets(config: GeneratorConfig) -> pd.DataFrame:
    """
    Genera un dataset limpio de tickets de soporte, reproducible por semilla.
    
    Args:
        config: configuración cargada desde el YAML (semilla, filas, periodo).

    Returns:
        DataFrame con una fila por ticket, columnas según el schema Ticket.
    """
    
    fake = Faker()
    fake.seed_instance(config.seed)
    
    dias_periodo = (config.period.end_date - config.period.start_date).days
    
    tickets = []
    for i in range(1, config.rows + 1):
        ticket_id = f"TCK-{config.period.start_date.year}-{i:05d}"  # TCK-AÑO-XXXXX
        client_id = f"CLI-{fake.random_int(min=1, max=999):04d}"    # CLI-XXXX
        
        offset_dias = fake.random_int(min=0, max=dias_periodo)
        created_at = pd.Timestamp(config.period.start_date) + timedelta(days=offset_dias)
        created_at += timedelta(
            hours=fake.random_int(min=0, max=23),
            minutes=fake.random_int(min=0, max=59),
        )
        
        priority = fake.random_element(list(TicketPriority))
        status = fake.random_element(list(TicketStatus))
        
        # first_response_at: solo si ya hubo interacción real (no open)
        first_response_at = None
        technician_id = None
        if status != TicketStatus.OPEN:
            first_response_at = created_at + timedelta(minutes=fake.random_int(5, 480))
            technician_id = f"TEC-{fake.random_int(min=1, max=50):03d}"
        elif fake.boolean(chance_of_getting_true=TECID_CHANCE_ON_OPEN):
            # open, pero ya asignado preventivamente (sin responder aún)
            technician_id = f"TEC-{fake.random_int(min=1, max=50):03d}"
        
        closed_at = None
        satisfaction_score = None
        if status == TicketStatus.CLOSED:
            # first_response_at siempre existe en este caso si no tendríamos un error
            closed_at = first_response_at + timedelta(hours=fake.random_int(min=1, max=72))
            satisfaction_score = fake.random_int(min=1, max=5)
        
        ticket = Ticket(
            ticket_id=ticket_id,
            client_id=client_id,
            created_at=created_at,
            first_response_at=first_response_at,
            closed_at=closed_at,
            category=fake.random_element(list(TicketCategory)),
            priority=priority,
            status=status,
            channel=fake.random_element(list(TicketChannel)),
            technician_id=technician_id,
            summary=fake.sentence(nb_words=10),
            sla_target_minutes=SLA_BY_PRIORITY[priority.value],
            satisfaction_score=satisfaction_score,
        )
        tickets.append(ticket.model_dump()) # model_dump() convierte nuestro modelo ticket en un dataframe, para pandas en este caso
    
    return pd.DataFrame(tickets)
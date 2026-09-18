import pytest
from datetime import datetime
from starglob_datalab.generation.schemas import Ticket, BackupJob

#
# TICKET TESTS
#

def test_ticket_valido_se_crea():
    t = Ticket(
        ticket_id="TCK-2026-00001",
        client_id="CLI-0042",
        created_at=datetime(2026, 9, 18, 9, 0),
        closed_at=datetime(2026, 9, 18, 11, 0),
        category="software",
        priority="high",
        status="closed",
        channel="email",
        summary="El cliente no puede acceder al correo corporativo",
        sla_target_minutes=240,
        satisfaction_score=4,
    )
    assert t.ticket_id == "TCK-2026-00001"

def test_ticket_summary_muy_corto_falla():
    with pytest.raises(Exception):
        Ticket(
        ticket_id="TCK-2026-00001",
        client_id="CLI-0042",
        created_at=datetime(2026, 9, 18, 9, 0),
        closed_at=datetime(2026, 9, 18, 11, 0),
        category="software",
        priority="high",
        status="closed",
        channel="email",
        summary="",
        sla_target_minutes=240,
        satisfaction_score=4,
    )

def test_ticket_summary_muy_largo_falla():
    with pytest.raises(Exception):
        Ticket(
        ticket_id="TCK-2026-00001",
        client_id="CLI-0042",
        created_at=datetime(2026, 9, 18, 9, 0),
        closed_at=datetime(2026, 9, 18, 11, 0),
        category="software",
        priority="high",
        status="closed",
        channel="email",
        summary="Este summary tiene que spbrepasar los 180 caracteres, así que ahí van 200: aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        sla_target_minutes=240,
        satisfaction_score=4,
    )

def test_ticket_first_response_antes_de_created_falla():
    with pytest.raises(Exception):
        Ticket(
        ticket_id="TCK-2026-00001",
        client_id="CLI-0042",
        created_at=datetime(2026, 9, 18, 9, 0),
        first_response_at=datetime(2026, 9, 18, 8, 0),
        closed_at=datetime(2026, 9, 18, 11, 0),
        category="software",
        priority="high",
        status="closed",
        channel="email",
        summary="El cliente no puede acceder al correo corporativo",
        sla_target_minutes=240,
        satisfaction_score=4,
    )

def test_ticket_closed_sin_closed_at_falla():
    with pytest.raises(Exception):
        Ticket(
            ticket_id="TCK-2026-00001",
            client_id="CLI-0042",
            created_at=datetime(2026, 9, 18, 9, 0),
            category="software",
            priority="high",
            status="open",
            channel="email",
            summary="El cliente no puede acceder al correo corporativo",
            sla_target_minutes=240,
            satisfaction_score=4,   # presente aunque no está closed
        )

def test_ticket_closed_at_anterior_a_created_falla():
    with pytest.raises(Exception):
        Ticket(
            ticket_id="TCK-2026-00001",
            client_id="CLI-0042",
            created_at=datetime(2026, 9, 18, 9, 0),
            closed_at=datetime(2026, 9, 18, 8, 0),
            category="software",
            priority="high",
            status="closed",
            channel="email",
            summary="El cliente no puede acceder al correo corporativo",
            sla_target_minutes=240,
            satisfaction_score=4,
        )

def test_ticket_satisfaction_score_sin_closed_falla():
    with pytest.raises(Exception):
        Ticket(
            ticket_id="TCK-2026-00001",
            client_id="CLI-0042",
            created_at=datetime(2026, 9, 18, 9, 0),
            category="software",
            priority="high",
            status="open",
            channel="email",
            summary="El cliente no puede acceder al correo corporativo",
            sla_target_minutes=240,
            satisfaction_score=4,
        )

def test_ticket_sla_incorrecto_para_priority_falla():
    with pytest.raises(Exception):
        Ticket(
            ticket_id="TCK-2026-00001",
            client_id="CLI-0042",
            created_at=datetime(2026, 9, 18, 9, 0),
            closed_at=datetime(2026, 9, 18, 11, 0),
            category="software",
            priority="high",
            status="closed",
            channel="email",
            summary="El cliente no puede acceder al correo corporativo",
            sla_target_minutes=0,
            satisfaction_score=4,
        )

def test_ticket_category_invalida_falla():
    with pytest.raises(Exception):
        Ticket(
            ticket_id="TCK-2026-00001",
            client_id="CLI-0042",
            created_at=datetime(2026, 9, 18, 9, 0),
            closed_at=datetime(2026, 9, 18, 11, 0),
            category="plátano",
            priority="high",
            status="closed",
            channel="email",
            summary="El cliente no puede acceder al correo corporativo",
            sla_target_minutes=240,
            satisfaction_score=4,
        )

#
# BACKUP TESTS
#

def test_backup_valido_se_crea():
    b = BackupJob(
        backup_id="BCK-20260918-0001",
        client_id="CLI-0042",
        job_name="backup_diario_db",
        source_system="database",
        scheduled_at=datetime(2026, 9, 18, 2, 0),
        started_at=datetime(2026, 9, 18, 2, 5),
        finished_at=datetime(2026, 9, 18, 2, 30),
        status="success",
        bytes_processed=1024000,
        files_processed=42,
    )
    assert b.backup_id == "BCK-20260918-0001"

def test_backup_started_at_anterior_a_scheduled_falla():
    with pytest.raises(Exception):
        BackupJob(
            backup_id="BCK-20260918-0002",
            client_id="CLI-0042",
            job_name="backup_diario_db",
            source_system="database",
            scheduled_at=datetime(2026, 9, 18, 2, 0),
            started_at=datetime(2026, 9, 18, 1, 50),  # antes de lo previsto
            status="running",
        )

def test_backup_started_at_dentro_de_tolerancia_pasa():
    b = BackupJob(
        backup_id="BCK-20260918-0005",
        client_id="CLI-0042",
        job_name="backup_diario_db",
        source_system="database",
        scheduled_at=datetime(2026, 9, 18, 2, 0),
        started_at=datetime(2026, 9, 18, 2, 10),  # 10 min después, dentro del margen
        status="running",
    )
    assert b.started_at == datetime(2026, 9, 18, 2, 10)

def test_backup_started_at_supera_tolerancia_falla():
    with pytest.raises(Exception):
        BackupJob(
            backup_id="BCK-20260918-0006",
            client_id="CLI-0042",
            job_name="backup_diario_db",
            source_system="database",
            scheduled_at=datetime(2026, 9, 18, 2, 0),
            started_at=datetime(2026, 9, 18, 2, 20),  # 20 min después, fuera del margen
            status="running",
        )

def test_backup_finished_at_anterior_a_started_falla():
    with pytest.raises(Exception):
        BackupJob(
            backup_id="BCK-20260918-0001",
            client_id="CLI-0042",
            job_name="backup_diario_db",
            source_system="database",
            scheduled_at=datetime(2026, 9, 18, 2, 0),
            started_at=datetime(2026, 9, 18, 2, 5),
            finished_at=datetime(2026, 9, 18, 1, 30),
            status="success",
            bytes_processed=1024000,
            files_processed=42,
        )

def test_backup_finished_at_igual_a_started_falla():
    with pytest.raises(Exception):
        BackupJob(
            backup_id="BCK-20260918-0001",
            client_id="CLI-0042",
            job_name="backup_diario_db",
            source_system="database",
            scheduled_at=datetime(2026, 9, 18, 2, 0),
            started_at=datetime(2026, 9, 18, 2, 5),
            finished_at=datetime(2026, 9, 18, 2, 5),
            status="success",
            bytes_processed=1024000,
            files_processed=42,
        )

def test_backup_success_sin_bytes_processed_falla():
    with pytest.raises(Exception):
        BackupJob(
            backup_id="BCK-20260918-0003",
            client_id="CLI-0042",
            job_name="backup_diario_db",
            source_system="filesystem",
            scheduled_at=datetime(2026, 9, 18, 2, 0),
            status="success",
            # bytes_processed y files_processed ausentes a propósito
        )

def test_backup_success_sin_files_processed_falla():
    with pytest.raises(Exception):
        BackupJob(
            backup_id="BCK-20260918-0001",
            client_id="CLI-0042",
            job_name="backup_diario_db",
            source_system="database",
            scheduled_at=datetime(2026, 9, 18, 2, 0),
            started_at=datetime(2026, 9, 18, 2, 5),
            finished_at=datetime(2026, 9, 18, 2, 30),
            status="success",
            bytes_processed=1024000,
            # falta files_processed
        )
        

def test_backup_failed_sin_error_code_falla():
    with pytest.raises(Exception):
        BackupJob(
            backup_id="BCK-20260918-0004",
            client_id="CLI-0042",
            job_name="backup_diario_db",
            source_system="filesystem",
            scheduled_at=datetime(2026, 9, 18, 2, 0),
            status="failed",
            # error_code ausente a propósito
        )

def test_backup_cancelled_sin_error_code_falla():
    with pytest.raises(Exception):
        BackupJob(
            backup_id="BCK-20260918-0001",
            client_id="CLI-0042",
            job_name="backup_diario_db",
            source_system="database",
            scheduled_at=datetime(2026, 9, 18, 2, 0),
            status="cancelled",
            # falta error_code; error_message no es obligatorio
        )
        
def test_backup_source_system_invalido_falla():
    with pytest.raises(Exception):
        BackupJob(
        backup_id="BCK-20260918-0001",
        client_id="CLI-0042",
        job_name="backup_diario_db",
        source_system="plátano",
        scheduled_at=datetime(2026, 9, 18, 2, 0),
        started_at=datetime(2026, 9, 18, 2, 5),
        finished_at=datetime(2026, 9, 18, 2, 30),
        status="success",
        bytes_processed=1024000,
        files_processed=42,
    )
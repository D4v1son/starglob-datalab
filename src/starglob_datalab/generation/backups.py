import pandas as pd
from datetime import timedelta
from faker import Faker
from collections import OrderedDict # Faker exige usar este OrderedDict para el diccionario con pesos que usamos para generar las frecuencias

from starglob_datalab.configuration import GeneratorConfig
from starglob_datalab.generation.schemas import BackupJob, BackupSourceSystem, BackupStatus


MIN_NJOBS  = 3  # no es buena idea bajarlo más, se generaran demasiadas instancias independientes
MEAN_NJOBS = 30 # cambialo si quieres ajustar la cantidad de trabajos que tendrá cada cliente

STATUS_WEIGHTS = OrderedDict([
    (BackupStatus.SUCCESS, 80),
    (BackupStatus.WARNING, 8),
    (BackupStatus.FAILED, 7),
    (BackupStatus.CANCELLED, 3),
    (BackupStatus.RUNNING, 2),
])   # si no se cambia la generación siempre tendrá la misma proporción de backups exitosos...


def _elegir_status(fake: Faker):
    return fake.random_elements(elements=STATUS_WEIGHTS, length=1)[0]

def _generar_trabajos(fake: Faker, n_jobs):
    """Crea trabajos de backup recurrentes (cliente + nombre + frecuencia)."""
    frecuencias_dias = [1, 1, 1, 7] # más probabilidad de diario que semanal
    return [
        {
            "client_id": f"CLI-{fake.random_int(min=1, max=999):04d}",
            "job_name": f"backup_{fake.word()}_{i:03d}",
            "source_system": fake.random_element(list(BackupSourceSystem)),
            "frecuencia_dias": fake.random_element(frecuencias_dias),
        }
        for i in range(n_jobs)
    ]

def _generar_ejecuciones(trabajos, period, fake: Faker):
    """Expande cada trabajo en sus ejecuciones programadas dentro del periodo."""
    fin_periodo = pd.Timestamp(period.end_date)
    ejecuciones = []
    for trabajo in trabajos:
        fecha = pd.Timestamp(period.start_date) + timedelta(
            hours=fake.random_int(0, 5),
            minutes=fake.random_int(0, 59)
        )
        while fecha < fin_periodo:
            ejecuciones.append({**trabajo, "scheduled_at": fecha})
            fecha += timedelta(days=trabajo["frecuencia_dias"])
    return ejecuciones


def generate_backups(config: GeneratorConfig) -> pd.DataFrame:
    """
    Genera un dataset limpio de copias de seguridad, con continuidad temporal:
    cada trabajo (cliente + job_name) se ejecuta periódicamente (diario o
    semanal) a lo largo del periodo configurado, en vez de filas sueltas
    independientes.
    """
    fake = Faker()
    fake.seed_instance(config.seed)
    
    n_jobs = max(MIN_NJOBS, config.rows // MEAN_NJOBS)
    trabajos = _generar_trabajos(fake, n_jobs)
    ejecuciones = _generar_ejecuciones(trabajos, config.period, fake)
    ejecuciones.sort(key=lambda e: e["scheduled_at"])
    
    if len(ejecuciones) < config.rows:
        raise ValueError(
            f"Solo se generaron {len(ejecuciones)} ejecuciones para {config.rows} "
            "filas pedidas; aumenta el nº de trabajos o reduce 'rows'."
        )
    
    contador_por_fecha = {}
    backups = []
    for ejecucion in ejecuciones:
        fecha_str = ejecucion["scheduled_at"].strftime("%Y%m%d")
        contador_por_fecha[fecha_str] = contador_por_fecha.get(fecha_str, 0) + 1
        backup_id = f"BCK-{fecha_str}-{contador_por_fecha[fecha_str]:04d}"

        status = _elegir_status(fake)
        scheduled_at = ejecucion["scheduled_at"]

        started_at = finished_at = None
        bytes_processed = files_processed = checksum_verified = None
        error_code = error_message = None

        if status != BackupStatus.RUNNING:
            started_at = scheduled_at + timedelta(minutes=fake.random_int(0, 15))

        if status in (BackupStatus.SUCCESS, BackupStatus.WARNING):
            finished_at = started_at + timedelta(minutes=fake.random_int(5, 180))
            bytes_processed = fake.random_int(min=1_000_000, max=500_000_000)
            files_processed = fake.random_int(min=1, max=50_000)
            checksum_verified = fake.boolean(
                chance_of_getting_true=90 if status == BackupStatus.SUCCESS else 60
            )
        elif status in (BackupStatus.FAILED, BackupStatus.CANCELLED):
            if started_at:
                finished_at = started_at + timedelta(minutes=fake.random_int(1, 30))
            error_code = f"ERR-{fake.random_int(min=100, max=599)}"
            error_message = fake.sentence(nb_words=8)

        backup = BackupJob(
            backup_id=backup_id,
            client_id=ejecucion["client_id"],
            job_name=ejecucion["job_name"],
            source_system=ejecucion["source_system"],
            scheduled_at=scheduled_at,
            started_at=started_at,
            finished_at=finished_at,
            status=status,
            bytes_processed=bytes_processed,
            files_processed=files_processed,
            checksum_verified=checksum_verified,
            error_code=error_code,
            error_message=error_message,
        )
        backups.append(backup.model_dump())

    return pd.DataFrame(backups)
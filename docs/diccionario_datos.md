# Diccionario de datos - Starglob DataLab

## Catálogos (enums)

| Catálogo | Valores |
|---|---|
| category (tickets) | hardware, software, network, email, security, billing, other |
| priority (tickets) | low, medium, high, critical |
| status (tickets) | open, in_progress, pending_client, resolved, closed |
| channel (tickets) | email, phone, web, monitoring |
| source_system (backups) | filesystem, database, virtual_machine, application |
| status (backups) | success, warning, failed, cancelled, running |

## Decisiones propias (no especificadas en el encargo)

- **Zona horaria**: UTC para toda generación y exportación (ISO 8601 con sufijo Z).
- **sla_target_minutes por prioridad**: critical=60, high=240, medium=1440, low=4320.
- **technician_id / first_response_at**: siempre van juntos, excepto en tickets
  `open`, donde technician_id puede existir por asignación preventiva con
  probabilidad `TECID_CHANCE_ON_OPEN`, pero first_response_at nunca.
- **Tolerancia backups**: started_at puede ser hasta 15 min posterior a scheduled_at.

## Tickets de soporte

| Campo | Tipo | Obligatorio | Regla |
|---|---|---|---|
| ticket_id | string | Sí | Único. `TCK-YYYY-NNNNN` |
| client_id | string | Sí | `CLI-NNNN` |
| created_at | datetime | Sí | ISO 8601 |
| first_response_at | datetime | No | ≥ created_at |
| closed_at | datetime | Condicional | Obligatorio si status=closed. > created_at |
| category | enum | Sí | ver catálogo |
| priority | enum | Sí | ver catálogo |
| status | enum | Sí | ver catálogo |
| channel | enum | Sí | ver catálogo |
| technician_id | string | No | `TEC-NNN` |
| summary | string | Sí | 15–180 caracteres |
| sla_target_minutes | integer | Sí | positivo, derivado de priority |
| satisfaction_score | integer | Condicional | 1–5, solo si status=closed |

## Copias de seguridad

| Campo | Tipo | Obligatorio | Regla |
|---|---|---|---|
| backup_id | string | Sí | Único. `BCK-YYYYMMDD-NNNN` |
| client_id | string | Sí | `CLI-NNNN` |
| job_name | string | Sí | — |
| source_system | enum | Sí | ver catálogo |
| scheduled_at | datetime | Sí | ISO 8601 |
| started_at | datetime | No | ≥ scheduled_at (± tolerancia) |
| finished_at | datetime | No | > started_at si existe |
| status | enum | Sí | ver catálogo |
| bytes_processed | integer | Condicional | ≥0, obligatorio si status=success |
| files_processed | integer | Condicional | ≥0, obligatorio si status=success |
| checksum_verified | boolean | No | puede ser null si failed |
| error_code | string | Condicional | obligatorio si failed/cancelled |
| error_message | string | No | — |
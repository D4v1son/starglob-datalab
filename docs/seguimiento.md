# Seguimiento - Starglob DataLab

## Día 1 - 2026-09-17

**Horas**: ~5h

**Completado**: Entorno venv, repositorio GitHub creado con primer commit,
dudas planteadas y resueltas con el tutor, diseño inicial (arquitectura y
backlog) documentado en el README. [COMMIT](https://github.com/D4v1son/starglob-datalab/commit/3b6ebd289afef7a948b68516762bab79d7f4bce8)

**Decisiones**: Repositorio en GitHub (privado) en vez de Bitbucket.

**Bloqueos**: Ninguno.

**Siguiente paso**: Modelado de esquemas y diccionario de datos (Día 2).

---

## Día 2 - [2026-09-18]

**Horas**: ~5h

**Completado**: Esquemas `Ticket` y `BackupJob` (pydantic) con reglas de
dependencia. Diccionario de datos en el README. Tests unitarios
(`tests/unit/test_schemas.py`) cubriendo casos válidos, inválidos y límite.
[COMMIT](https://github.com/D4v1son/starglob-datalab/commit/45fd78f151de858a5e0cbb95bd6f05cb9e33fb2a)

**Decisiones**: `sla_target_minutes` derivado de `priority` (valores propios,
no especificados en el encargo). Tolerancia de `started_at` sobre
`scheduled_at` en backups: 15 min (decisión propia).

**Bloqueos**: Error de sintaxis y de lógica en tests corregidos durante
revisión. `BackupJob` definido por error como `Enum` en vez de `BaseModel`,
corregido.

**Siguiente paso**: Generador de tickets (Día 3).

---

## Día 3 - [2026-09-21]

**Horas**: ~5h

**Completado**: `configuration.py` (carga y valida YAML). Generador de
tickets con Faker y semilla reproducible. CLI (`generate`) con export a CSV.
Tests de integración del generador (unicidad de IDs, fechas dentro de
periodo, reproducibilidad). Documentación de uso en el README. 
[COMMIT](https://github.com/D4v1son/starglob-datalab/commit/fccefcde20035f51a5327abeae3dc76e877359c7)

**Decisiones**: `technician_id` y `first_response_at` siempre van juntos,
salvo asignación preventiva en tickets `open` (prob. `TECID_CHANCE_ON_OPEN`).
`closed_at` se calcula sobre `first_response_at`, no sobre `created_at`, para
garantizar orden cronológico correcto.

**Bloqueos**: Ninguno bloqueante. Bug menor detectado y corregido
(`first_response_at`/`technician_id` podían generarse de forma inconsistente).

**Siguiente paso**: Generador de backups con continuidad temporal (Día 4).

---

## Día 4 - [2026-09-22]

**Horas**: ~5h

**Completado**: Generador de backups (`generate_backups`) con continuidad
temporal (trabajos recurrentes diarios/semanales por cliente+job_name).
CLI actualizado para soportar plantilla `backups`. Tests de integración
(unicidad de IDs, número de filas, reproducibilidad, espaciado regular
entre ejecuciones de un mismo trabajo). Diccionario de datos actualizado.
[COMMIT]()

**Decisiones**: Frecuencia de trabajos 75% diaria / 25% semanal.
Distribución de status: 80% success, 8% warning, 7% failed, 3% cancelled,
2% running. Selección de trabajos completos (no fechas sueltas) hasta
alcanzar `rows`, en orden barajado por semilla, para evitar sesgo hacia
el inicio del periodo y hacia los primeros trabajos generados.

**Bloqueos**: Varios errores menores corregidos durante el desarrollo
(sintaxis en construcción de diccionario, typo en clave de frecuencia,
`OrderedDict` requerido por Faker para pesos, typo en nombre de columna
en test). Bug de diseño detectado y corregido: el truncado inicial por
fecha rompía la continuidad temporal al concentrar filas en el inicio
del periodo.

**Siguiente paso**: Primera revisión (Día 5). Refactorizar, probar
configuración y generadores, preparar demostración de 10 minutos.
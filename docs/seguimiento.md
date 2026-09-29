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
[COMMIT](https://github.com/D4v1son/starglob-datalab/commit/840e4d9ca6779f7929407b8bfa3623125dfb8eae)

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

---

## Día 5 - [2026-09-23]

**Horas**: ~5h

**Completado**: Refactor según criterios del Anexo D (nombres de constantes,
docstrings, tipos correctos). Validación con volumen real (10000 filas en
ambas plantillas, CA02). Prueba de instalación limpia desde repositorio
recién clonado (CA01). README corregido con el paso de instalación de
dependencias de desarrollo.
[COMMIT](https://github.com/D4v1son/starglob-datalab/commit/bc9821ac4854eff0b202ed375732dbf3a0ddd0b6)

**Decisiones**: Versión del proyecto actualizada a 0.3.0 en pyproject.toml,
marcando el cierre de Hito H1.

**Bloqueos**: Bug real detectado y corregido - `fin_periodo` en el generador
de backups excluía el último día del periodo configurado (comparación
estricta sin margen).

**Siguiente paso**: Día 6. Primera anomalía del catálogo (Semana 2).

---

## Día 6 - [2026-09-24]

**Horas**: ~5h

**Completado**: Estructura del manifiesto (`ManifestEntry`) y 
extensión de `configuration.py` con `AnomalyInjectionConfig`.
Inyector (`injector.py`) con `InjectionContext` compartido, y las 5
primeras anomalías del catálogo implementadas en `rules.py`: DQ01
(valor obligatorio ausente), DQ02 (duplicado exacto), DQ03 (identificador
duplicado), DQ04 (categoría no permitida), DQ05 (tipo incorrecto).
Documentación en `docs/catalogo_anomalias.md` y nueva sección en el
README. Tests de integración cubriendo las 5 reglas por separado y en
combinación. 
[COMMIT](https://github.com/D4v1son/starglob-datalab/commit/3f0ff44251f1de16126e1d4dc70b815f197c823b)

**Decisiones**: `row_id` del manifiesto se toma de una copia congelada
de los IDs (`frozen_ids`) tomada antes de inyectar nada, para que
sobreviva a anomalías que corrompen el propio campo de ID (DQ03).
`used_cells`/`used_rows` en el contexto evitan mezclar anomalías
distintas en la misma celda o fila. Filas añadidas por DQ02 (duplicados)
quedan excluidas como candidatas de otras anomalías posteriores (no
están en `frozen_ids`). DQ04 resuelve el catálogo de valores válidos
según la plantilla (tickets/backups), necesario por la ambigüedad del
campo `status`. `rate`/`count` en la configuración de anomalías son
mutuamente excluyentes (validado).

**Bloqueos**: Bug de índices duplicados en `pd.concat` (DQ02) corregido
con `ignore_index=True`, causaba comparaciones ambiguas de Series en
anomalías posteriores. Error de indentación en DQ05 (asignación fuera
del bucle). `KeyError` en `frozen_ids` para filas nuevas de DQ02,
resuelto excluyéndolas como candidatas.

**Siguiente paso**: Día 7, anomalías lógicas DQ06 a DQ10.

---

## Día 7 - [2026-09-25]

**Horas**: ~5h

**Completado**: DQ06-DQ10 implementadas en `rules.py` (valor fuera de
rango, cronología imposible, dependencia incumplida, formato
inconsistente, espacios/capitalización). CLI (`cmd_generate`) conectado
por fin al inyector: ahora `generate` produce `clean.csv`, `dirty.csv` y
`truth_manifest.jsonl` cuando el YAML incluye anomalías. Tests de
integración cubriendo las 10 anomalías por separado y en combinación,
para tickets y backups. Catálogo y README actualizados. 
[COMMIT](https://github.com/D4v1son/starglob-datalab/commit/7a6edec24180603db87f9ebf93fddd1ac7ae91e2)

**Decisiones**: `RANGES_BY_TEMPLATE`/`DEPENDENCIAS_BY_TEMPLATE` amplían
el patrón de `FIELD_ENUMS_BY_TEMPLATE` para rangos y dependencias por
plantilla. DQ08 y DQ09 no se combinan con DQ07/DQ01 respectivamente en 
el mismo YAML cuando comparten candidatos potenciales (mismo campo 
disparador).

**Bloqueos**: `generate` no invocaba el inyector pese a existir desde
Día 6 (conectado hoy).

**Siguiente paso**: Día 8, DQ11 a DQ14 (continuidad, valor extremo,
referencia huérfana, codificación dañada) y resolver interacciones entre
anomalías.

---

## Día 8 - [2026-09-28]

**Horas**: ~5h

**Completado**: DQ11-DQ14 implementadas (hueco temporal, valor extremo,
referencia huérfana, codificación dañada): catálogo mínimo completo,
DQ01-DQ14. Revisión de interacciones entre anomalías: comprobación
común `fila_libre`, bloqueo de celdas de referencia y de filas
donantes, índices nuevos propios para DQ02. Tests de las cuatro
anomalías nuevas, de las interacciones y combinados para ambas
plantillas. YAML de demo actualizados con todas las anomalías
aplicables. Catálogo actualizado.
[COMMIT](https://github.com/D4v1son/starglob-datalab/commit/8711ac86f86f7edba0969a0bf8be00a4e91d3b00)

**Decisiones**: Granularidad por celda (no por fila) para las
interacciones. DQ11 solo sobre ejecuciones intermedias de backups y
con emparejamiento posterior por cliente + trabajo + fecha. DQ13
define huérfano por rango de IDs, con `MAX_TECHNICIAN_ID` compartida
con el generador. DQ12 y DQ14 acotadas (duraciones y texto).

**Bloqueos**: Ninguno bloqueante. Se detectó que DQ02 comprobaba
`used_rows` con el ID en vivo, que DQ03 puede haber cambiado
(corregido con `frozen_ids`), y que `ignore_index=True` en DQ02
desalinearía `frozen_ids` con DQ11 (sustituido por `next_index`).

**Siguiente paso**: Día 9 - auditor: interfaz común de reglas,
hallazgos y resúmenes, auditando ambos esquemas
(`audit_results.json`).

---

## Día 9 - [2026-09-29]

**Horas**: ~5h

**Completado**: Interfaz común del auditor (`Finding`, patrón de
registro de reglas con `partial`, `audit()`). Catálogo completo de
reglas de auditoría DQ01-DQ14, independientes del inyector y aplicables
a cualquier CSV compatible. Tests de integración (una regla por
código, más cobertura sobre dataset limpio sin falsos positivos).
Documentación del catálogo de auditoría y ampliación del README.
[COMMIT](https://github.com/D4v1son/starglob-datalab/commit/c819dce88731db8a09e8d48f3e77de3715b570a0)

**Decisiones**: `rule_code` coincide con el código `DQ_XX` para permitir
comparación con el manifiesto. Fechas cargadas como texto para el
auditor. Varias reglas (DQ_04, DQ_06, DQ_07, DQ_08, DQ_13, DQ_14)
reutilizan los mismos catálogos de negocio que ya usa el inyector, para
no definir la misma regla tres veces. DQ_11 y DQ_12 del auditor usan
criterios propios (frecuencia inferida, umbral de 10 días) distintos de
los parámetros usados por el inyector.

**Bloqueos**: `Finding.row_id` definido como obligatorio,
corregido a opcional para soportar DQ_11.

**Siguiente paso**: Día 10 - evaluación: comparar hallazgos contra el
manifiesto, calcular métricas (precisión, recall, F1) y resolver el
emparejamiento especial de DQ_03 y DQ_11.
# Catálogo de anomalías &rarr; Starglob DataLab

Cada anomalía se identifica por un código `DQ_XX`. El manifiesto
(`truth_manifest.jsonl`) registra una línea por cada instancia inyectada,
con la estructura definida en el Anexo B del encargo.

| Código | Nombre | Ejemplo | Estado |
|---|---|---|---|
| DQ_01 | Valor obligatorio ausente | `created_at` vacío | <ul><li>- [x] Implementado</li></ul> |
| DQ_02 | Duplicado exacto | Dos registros idénticos | <ul><li>- [x] Implementado</li></ul> |
| DQ_03 | Identificador duplicado | `ticket_id` repetido | <ul><li>- [x] Implementado</li></ul> |
| DQ_04 | Categoría no permitida | `priority = "urgent"` | <ul><li>- [x] Implementado</li></ul> |
| DQ_05 | Tipo incorrecto | `files_processed = "muchos"` | <ul><li>- [x] Implementado</li></ul> |
| DQ_06 | Valor fuera de rango | `satisfaction_score = 9` | <ul><li>- [ ] Pendiente</li></ul> |
| DQ_07 | Cronología imposible | `closed_at` anterior a `created_at` | <ul><li>- [ ] Pendiente</li></ul> |
| DQ_08 | Dependencia incumplida | `failed` sin `error_code` | <ul><li>- [ ] Pendiente</li></ul> |
| DQ_09 | Formato inconsistente | Fecha en `DD/MM/YYYY` | <ul><li>- [ ] Pendiente</li></ul> |
| DQ_10 | Espacios o capitalización | `status` con espacios extra | <ul><li>- [ ] Pendiente</li></ul> |
| DQ_11 | Hueco temporal | Día esperado sin copia | <ul><li>- [ ] Pendiente</li></ul> |
| DQ_12 | Valor extremo | Duración desproporcionada | <ul><li>- [ ] Pendiente</li></ul> |
| DQ_13 | Referencia huérfana | `technician_id` inexistente | <ul><li>- [ ] Pendiente</li></ul> |
| DQ_14 | Codificación dañada | Caracteres ilegibles | <ul><li>- [ ] Pendiente</li></ul> |

## Decisiones propias

- **Validación de configuración de anomalías**: cada anomalía en el YAML
  debe indicar exactamente uno de `rate` (porcentaje) o `count` (cantidad
  absoluta), nunca ambos ni ninguno. El documento menciona que puede
  indicarse "una cantidad absoluta o un porcentaje", pero no especifica
  que sean mutuamente excluyentes; se ha añadido esta validación explícita
  en `AnomalyInjectionConfig` para evitar configuraciones ambiguas.
- **row_id congelado en anomalías**: se captura una copia de los IDs
  (`frozen_ids`) antes de inyectar cualquier anomalía, para que el
  manifiesto siga rastreando la fila correcta aunque DQ03 corrompa el
  propio campo de ID visible en `dirty.csv`.
- **Anomalías no se mezclan en la misma fila/celda**: `used_cells` evita
  tocar dos veces el mismo (fila, campo); `used_rows` evita que una
  anomalía de fila completa (DQ02) afecte a una fila ya tocada por
  cualquier otra, y viceversa.
- **Filas duplicadas por DQ02 no son candidatas de otras anomalías**:
  al no existir en `frozen_ids` (que solo contiene las filas del dataset
  limpio original), quedan excluidas automáticamente de DQ01/03/04/05.
- **DQ04 depende de la plantilla**: el catálogo de valores válidos para
  comparar (`FIELD_ENUMS_BY_TEMPLATE`) se resuelve según
  `tickets`/`backups`, ya que campos como `status` tienen significados
  distintos en cada una.
- **Rangos y dependencias por plantilla (DQ06, DQ08)**: igual que
  `FIELD_ENUMS_BY_TEMPLATE` (DQ04), se definen diccionarios
  (`RANGES_BY_TEMPLATE`, `DEPENDENCIAS_BY_TEMPLATE`) con el conocimiento
  de negocio necesario por plantilla. Solo cubren los campos usados
  hasta ahora; aplicar estas anomalías a un campo nuevo requiere
  añadirlo primero al diccionario correspondiente, o falla
  explícitamente.
- **DQ10 no descarta colisiones con el valor original**: en campos con
  capitalización natural (texto libre), una variante podría coincidir
  por casualidad con el original; se acepta como caso límite poco
  probable con los campos usados actualmente.
- **Interacciones entre anomalías**: se mantiene la granularidad por
  celda (varias anomalías pueden coexistir en una fila si tocan campos
  distintos). Se descartó bloquear por fila entera porque el documento
  solo pide evitar la misma celda, y permite probar filas con varios
  errores. Si el emparejamiento en la evaluación (Día 10) da problemas,
  bastaría con cambiar la comprobación de candidatos.
- **Bloqueo de celdas de referencia** (DQ_07, DQ_08, DQ_12): además de
  su campo principal, marcan como usada la celda de la que dependen.
- **DQ_11 solo elimina ejecuciones intermedias y solo en backups**: un
  hueco al principio o al final de un trabajo no se distingue de un
  trabajo que empezó más tarde o terminó antes. El emparejamiento en la
  evaluación será por cliente + trabajo + fecha, no por `row_id`.
- **DQ_12 solo cubre duraciones** (30-180 días de desproporción). Los
  valores numéricos extremos quedan fuera por ahora.
- **DQ_13 define "huérfano" por rango de IDs**: sin tabla maestra de
  técnicos, el catálogo lo fija el propio generador
  (`MAX_TECHNICIAN_ID`, constante compartida).
- **DQ_14 simula la mala codificación** sustituyendo caracteres por
  secuencias ilegibles conocidas, en vez de recodificar texto (el texto
  generado es ASCII y no cambiaría).
- **DQ_11 y DQ_12 no se aplican a tickets, y DQ_13 tampoco a backups**,
  por no tener sentido de negocio en esa plantilla.

## Detalle por anomalía

### DQ_01 &rarr; Valor obligatorio ausente
Vacía (pone a `null`) el valor de un campo obligatorio en un número de
filas elegido al azar (reproducible por semilla). El campo afectado se
especifica en la configuración (`fields: [nombre_campo]`); de momento
solo se soporta un campo por instancia de la anomalía. Falla
explícitamente si no hay suficientes filas candidatas (con valor no nulo
y celda no usada por otra anomalía) para la cantidad solicitada.

### DQ_02 &rarr; Duplicado exacto

Añade una copia idéntica de filas completas elegidas al azar (sin alterar
ningún campo). El `row_id` del manifiesto apunta al identificador que
queda duplicado en el dataset; `field`, `original_value` y
`altered_value` quedan en `null`, ya que la anomalía afecta a la fila
entera, no a un campo concreto. No se duplican filas que ya tengan otra
anomalía aplicada (de campo o de fila completa), para evitar mezclar
anomalías distintas en una misma fila.

### DQ_03 &rarr; Identificador duplicado

Sobrescribe el identificador (`ticket_id`/`backup_id`) de una fila
"objetivo" con el de otra fila "donante", elegidas ambas al azar sin
solapar con otras anomalías. El `row_id` del manifiesto es la identidad
real de la fila objetivo (capturada antes de la alteración), no el valor
duplicado que ahora aparece en `dirty.csv`. Requiere el doble de
candidatos que instancias solicitadas (una fila objetivo + una donante
por cada duplicado).

### DQ_04 &rarr; Categoría no permitida

Sustituye el valor de un campo categórico (`priority`, `status`,
`category`, `channel`, `source_system`) por un valor fuera del catálogo
válido definido en el schema (por ejemplo, `priority = "urgent"`, que no
existe en `TicketPriority`). Los valores inválidos candidatos se filtran
para excluir cualquiera que coincidiera por casualidad con un valor real
del enum. La resolución del catálogo correcto depende de la plantilla
(`tickets` o `backups`), necesario porque campos como `status` significan
cosas distintas en cada una.

### DQ_05 &rarr; Tipo incorrecto

Sustituye el valor de un campo numérico (por ejemplo, `files_processed`)
por un texto no convertible a número (`"muchos"`, `"N/D"`, `"varios"`).
Nota: al mezclar texto en una columna numérica, pandas puede convertir el
tipo de la columna entera a `object` al exportar/releer el CSV. El
auditor no debe asumir el tipo de una columna solo por su `dtype`.

### DQ_06 &rarr; Valor fuera de rango

Sustituye un valor numérico por otro fuera del rango válido conocido
(`RANGES_BY_TEMPLATE`), con la misma probabilidad de quedar por encima o
por debajo del límite, desviado entre 1 y 5 unidades. Solo soporta
campos con un rango cerrado explícitamente definido (actualmente,
`satisfaction_score` en tickets).

### DQ_07 &rarr; Cronología imposible

Adelanta un campo de fecha para que quede antes que su campo de
referencia (entre 1 minuto y 3 horas antes), rompiendo una relación
temporal esperada (p. ej. `closed_at` antes de `created_at`). Requiere
`fields: [campo_a_corromper, campo_de_referencia]`. Es la única
anomalía, junto a DQ08, que usa `related_fields` en el manifiesto para
señalar el campo con el que se relaciona el problema.

### DQ_08 &rarr; Dependencia incumplida

Vacía un campo que solo es obligatorio bajo cierta condición de negocio
(`DEPENDENCIAS_BY_TEMPLATE`), y únicamente en las filas donde esa
condición se cumple (p. ej. solo vacía `error_code` en backups cuyo
`status` ya es `failed`/`cancelled`). Es la inversión programática de
las reglas de dependencia ya definidas en `schemas.py`.

### DQ_09 &rarr; Formato inconsistente

Reescribe una fecha válida en un formato distinto al estándar (ISO
8601) usado por el resto del dataset. Por ejemplo, `DD/MM/YYYY` en vez
del formato habitual. A diferencia de DQ05, no pierde información: el
valor sigue siendo la misma fecha real, solo cambia su representación
textual, simulando un problema de origen/formato de datos en vez de un
dato corrupto.

### DQ_10 &rarr; Espacios o capitalización

Añade ruido superficial a un valor de texto o categórico: espacios al
inicio/final, o cambios de capitalización (mayúsculas, solo primera
letra). El valor sigue siendo semánticamente el mismo para un lector
humano, pero rompe comparaciones exactas de texto. No se comprueba si
la variante generada coincide por casualidad con el valor original.

### DQ_11 — Hueco temporal

Elimina ejecuciones **intermedias** de trabajos recurrentes (nunca la
primera ni la última de un trabajo, para que el hueco tenga una
ejecución antes y otra después). Solo aplica a `backups`; con otra
plantilla falla con mensaje explícito. La estructura de los trabajos
se calcula sobre el dataset limpio original (`ctx.original_df`), no
sobre el dataset en curso, porque otras anomalías (DQ01, DQ10) pueden
haber alterado `job_name`.

En el manifiesto, `row_id` es la fila eliminada (tomada de
`frozen_ids`), `field` es `scheduled_at`, `original_value` es la fecha
eliminada y `related_fields` es `["client_id", "job_name"]`.
**Consecuencia para el auditor y el evaluador:** esa fila ya no existe
en `dirty.csv`, así que el auditor solo puede detectar el hueco (fecha
esperada sin ejecución en un trabajo recurrente), y el evaluador debe
emparejar DQ_11 por cliente + trabajo + fecha, recuperando cliente y
trabajo desde `clean.csv` a partir del `row_id`.

### DQ_12 — Valor extremo

Alarga una duración hasta un valor desproporcionado: el campo de fin
queda entre 30 y 180 días después del campo de inicio
(`EXTREME_DURATION_DAYS`). Requiere `fields: [campo_fin, campo_inicio]`.
La duración sigue siendo cronológicamente válida (fin posterior a
inicio), lo que la distingue de DQ_07. El "criterio" del catálogo es
este umbral, reconstruible desde `original_value`, `altered_value` y
`related_fields`. De momento solo cubre duraciones, no valores
numéricos extremos.

### DQ_13 — Referencia huérfana

Sustituye un identificador de referencia por otro con formato válido
pero inexistente (por ejemplo, `TEC-051` a `TEC-999` cuando los
técnicos válidos son `TEC-001` a `TEC-050`). Solo soporta campos con un
catálogo de referencia definido (`REFERENCIAS_BY_TEMPLATE`,
actualmente solo `technician_id` en tickets); `client_id` no tiene
tabla maestra, así que no puede ser huérfano. El rango válido
(`MAX_TECHNICIAN_ID`) se comparte con el generador para no duplicar el
número.

### DQ_14 — Codificación dañada

Sustituye entre 1 y 3 caracteres de un campo de texto por secuencias
típicas de mala codificación (`Ã©`, `Ã±`, `â€™`, `�`...). Es una
simulación, no un mojibake real: los textos de Faker son ASCII, y la
conversión real no cambiaría nada. El texto ilegible resultante queda
en `altered_value` del manifiesto como evidencia. Solo aplica a campos
de texto.

## Interacciones entre anomalías

- **Granularidad por celda:** dos anomalías pueden tocar campos
  distintos de la misma fila, pero nunca la misma celda. Las anomalías
  de fila completa (DQ_02, DQ_11) solo eligen filas que ninguna otra
  anomalía haya tocado, y viceversa (`ctx.fila_libre`).
- **Celdas de referencia:** DQ_07, DQ_08 y DQ_12 comprueban y bloquean
  también su celda de referencia (`created_at`, `status`,
  `started_at`), para que otra anomalía no la reformatee o altere
  después.
- **Filas donantes (DQ_03):** la fila cuyo ID se copia queda bloqueada,
  para que DQ_11 no la elimine ni DQ_02 la duplique.
- **Índices nuevos (DQ_02):** las filas duplicadas reciben índices
  desde un contador propio (`ctx.next_index`), sin renumerar las
  existentes ni reutilizar el índice de una fila eliminada por DQ_11.
- **Orden:** el resultado no depende del orden en que aparezcan las
  anomalías en el YAML.
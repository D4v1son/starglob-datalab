# Catálogo de anomalías — Starglob DataLab

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
  absoluta), nunca ambos ni ninguno — el documento menciona que puede
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
tipo de la columna entera a `object` al exportar/releer el CSV — el
auditor no debe asumir el tipo de una columna solo por su `dtype`.

*(se rellena al implementarla)*
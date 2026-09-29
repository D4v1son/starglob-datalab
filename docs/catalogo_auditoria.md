# Catálogo de reglas de auditoría - Starglob DataLab

El auditor es independiente del inyector: no conoce el manifiesto, solo
analiza los datos. Cada regla se identifica con el mismo código `DQ_XX`
de la anomalía que detecta, para que los hallazgos puedan compararse
contra el manifiesto en la evaluación.

El auditor recibe las fechas como texto (sin `parse_dates`), para poder
detectar formatos inconsistentes (DQ_09) antes de que pandas los
"corrija" silenciosamente al convertirlos.

| Código | Regla | Severidad | Estado |
|---|---|---|---|
| DQ_01 | Valor obligatorio ausente | error | <ul><li>- [x] Implementado</li></ul> |
| DQ_02 | Fila completamente duplicada | error | <ul><li>- [x] Implementado</li></ul> |
| DQ_03 | Identificador repetido | critical | <ul><li>- [x] Implementado</li></ul> (ver limitación) |
| DQ_04 | Valor fuera del catálogo | error | <ul><li>- [x] Implementado</li></ul> |
| DQ_05 | Valor no numérico | error | <ul><li>- [x] Implementado</li></ul> |
| DQ_06 | Valor fuera de rango | warning | <ul><li>- [x] Implementado</li></ul> |
| DQ_07 | Cronología imposible | error | <ul><li>- [x] Implementado</li></ul> |
| DQ_08 | Dependencia incumplida | error | <ul><li>- [x] Implementado</li></ul> |
| DQ_09 | Formato de fecha inconsistente | warning | <ul><li>- [x] Implementado</li></ul> |
| DQ_10 | Espacios o capitalización | info | <ul><li>- [x] Implementado</li></ul> |
| DQ_11 | Hueco temporal | warning | <ul><li>- [x] Implementado</li></ul> (ver limitación) |
| DQ_12 | Duración desproporcionada | warning | <ul><li>- [x] Implementado</li></ul> |
| DQ_13 | Referencia huérfana | error | <ul><li>- [x] Implementado</li></ul> |
| DQ_14 | Codificación dañada | warning | <ul><li>- [x] Implementado</li></ul> |

## Limitaciones conocidas (pendientes de resolver en la evaluación)

- **DQ_03**: el auditor no puede saber cuál de las dos filas con ID
  repetido era la "objetivo" originalmente (esa información solo la
  tiene el manifiesto, vía `frozen_ids`). El `row_id` del hallazgo es el
  propio ID duplicado, no la identidad original de la fila objetivo. El
  emparejamiento en el evaluador deberá hacerse por **valor duplicado**,
  no por `row_id`.
- **DQ_11**: al detectar una *ausencia* de ejecución, no hay una fila
  concreta que señalar. El hallazgo se emite con `row_id=None`; el
  emparejamiento deberá hacerse por (cliente, trabajo, fecha esperada).

## Decisiones propias

- **`rule_code` del auditor = código `DQ_XX`**: necesario para que la
  evaluación pueda comparar hallazgos contra el manifiesto por regla.
- **El auditor recibe fechas como texto**, sin `parse_dates`, para
  poder detectar DQ_09 (formato inconsistente) antes de que pandas
  normalice el valor al leer el CSV.
- **`Finding.row_id` es opcional**: DQ_11 (hueco temporal) detecta una
  ausencia, no una fila concreta.
- **DQ_07/DQ_12 del auditor comprueban pares de campos fijos**
  (`CHRONOLOGY_PAIRS_BY_TEMPLATE`), no los que se hayan usado realmente
  al inyectar - el auditor es más exhaustivo que la instancia concreta
  de la anomalía inyectada.
- **`EXTREME_DURATION_THRESHOLD_DAYS` (auditor) es independiente del
  rango 30-180 días del inyector (DQ_12)**: el auditor aplica su propio
  criterio de negocio, no "sabe" cómo se generó la anomalía.
- **DQ_11 del auditor infiere la frecuencia esperada** por trabajo
  (moda de los intervalos entre ejecuciones), en vez de asumir un valor
  fijo, y requiere al menos 3 ejecuciones para tener un patrón fiable.

## Detalle por regla

### DQ_01 - Valor obligatorio ausente
Recorre los campos obligatorios de la plantilla
(`REQUIRED_FIELDS_BY_TEMPLATE`) y marca cualquier valor nulo.

### DQ_02 - Fila completamente duplicada
Usa `df.duplicated(keep=False)` sobre todas las columnas; marca ambas
filas implicadas en cada duplicado.

### DQ_03 - Identificador repetido
Excluye las filas ya cubiertas por DQ_02 (duplicados exactos), y marca
los IDs que se repiten entre filas que, por lo demás, son distintas.

### DQ_04 - Valor fuera del catálogo
Reutiliza `FIELD_ENUMS_BY_TEMPLATE` (el mismo catálogo que usa el
inyector) para comprobar que cada valor categórico pertenece al enum.

### DQ_05 - Valor no numérico
Intenta convertir a `float` los campos de `NUMERIC_FIELDS_BY_TEMPLATE`;
cualquier fallo de conversión es un hallazgo.

### DQ_06 - Valor fuera de rango
Reutiliza `RANGES_BY_TEMPLATE` del inyector. Omite valores no numéricos
(ya cubiertos por DQ_05) para no duplicar el hallazgo.

### DQ_07 - Cronología imposible
Comprueba pares fijos de campos por plantilla
(`CHRONOLOGY_PAIRS_BY_TEMPLATE`), no los que se hayan usado realmente
al inyectar - por eso puede detectar cronologías imposibles aunque se
hayan originado en un par de campos distinto al usado en DQ_07 del
inyector.

### DQ_08 - Dependencia incumplida
Reutiliza `DEPENDENCES_BY_TEMPLATE` del inyector: comprueba, para cada
dependencia conocida, que el campo exista cuando el disparador tiene el
valor correspondiente.

### DQ_09 - Formato de fecha inconsistente
Comprueba con una expresión regular que cada fecha (como texto) siga el
formato ISO 8601. Requiere que el DataFrame se cargue sin `parse_dates`.

### DQ_10 - Espacios o capitalización
Para campos categóricos: si el valor no coincide con el catálogo pero,
tras limpiar espacios y pasar a minúsculas, sí coincide, se marca como
formato inconsistente (nunca se solapa con DQ_04).

### DQ_11 - Hueco temporal
Solo aplica a `backups`. Para cada trabajo recurrente (cliente +
job_name) con al menos 3 ejecuciones, infiere la frecuencia esperada
(el intervalo más común entre ejecuciones consecutivas) y marca
cualquier hueco de al menos el doble de esa frecuencia.

### DQ_12 - Duración desproporcionada
Usa los mismos pares de `CHRONOLOGY_PAIRS_BY_TEMPLATE`, marcando
duraciones de 10 días o más (`EXTREME_DURATION_THRESHOLD_DAYS`). Este
umbral es una decisión propia del auditor, deliberadamente distinta del
rango 30-180 días que usa el inyector para generar la anomalía.

### DQ_13 - Referencia huérfana
Reutiliza `REFERENCIAS_BY_TEMPLATE`: comprueba que el número dentro de
un ID con formato válido esté dentro del rango que el generador
realmente usa.

### DQ_14 - Codificación dañada
Comprueba, en campos de texto, la presencia de cualquiera de las
secuencias típicas de mala codificación que también usa el inyector
para simularla.
# Starglob DataLab

Generador y auditor de datos sintéticos para pruebas de software.

## Diseño inicial

### Arquitectura
Módulos separados por responsabilidad, siguiendo el flujo:

Configuración → Generador → Inyector → Auditor → Evaluador → Persistencia → Presentación

- **configuration.py**: carga y valida el YAML (esquema con pydantic).
- **generation/**: crea datasets válidos (tickets, backups) con semilla.
- **anomalies/**: aplica anomalías sobre una copia y escribe el manifiesto.
- **audit/**: aplica reglas de calidad y emite hallazgos normalizados.
- **evaluation/**: compara hallazgos vs manifiesto, calcula métricas.
- **persistence/**: guarda ejecuciones, hallazgos y métricas en SQLite.
- **reporting/**: exportaciones (CSV, JSON, Excel opcional).
- **app/dashboard.py**: interfaz Streamlit, consume solo datos persistidos.
- **cli.py**: comandos `generate`, `audit`, `evaluate`.

### Modelos de datos
Dos plantillas: `tickets` (incidencias de soporte) y `backups` (copias de seguridad). Ambas requieren identificadores únicos reproducibles por semilla y relaciones temporales coherentes (p. ej. `closed_at` posterior a `created_at`). Como parte de la documentación hay un [catálogo](./docs/diccionario_datos.md) con el schema de los datos representados visualmente.

### Backlog (siguiendo la planificación de 75h)
- **Semana 1**: configuración + generador de ambas plantillas + reproducibilidad
- **Semana 2**: catálogo de anomalías (DQ01–DQ14) + auditor + evaluador
- **Semana 3**: persistencia SQLite + dashboard + documentación + entrega

## Anomalías y auditoría

El dataset limpio (`clean.csv`) se copia y se le inyectan anomalías controladas 
para producir un dataset "sucio" (`dirty.csv`), junto con un manifiesto 
(`truth_manifest.jsonl`) que registra exactamente qué se alteró, dónde y por qué. 
Este manifiesto es la "verdad conocida" contra la que se evalúa después el 
auditor.

El identificador de fila (`row_id`) usado en el manifiesto se toma como
una copia congelada del ID original (`ticket_id`/`backup_id`) antes de
inyectar nada, de forma que sigue siendo trazable incluso si la propia
anomalía corrompe ese campo (ver DQ03).

Consulta el [catálogo de anomalías](./docs/catalogo_anomalias.md) para el
detalle de cada código implementado, su definición y ejemplo.

El auditor (`audit/auditor.py`) es independiente del inyector: analiza
cualquier CSV compatible con las plantillas, sin conocer el manifiesto,
y emite hallazgos normalizados (`Finding`) con la misma estructura
`row_id`/`field`/`severity`. Cada regla de auditoría usa el mismo código 
`DQ_XX` que la anomalía que detecta, para poder compararse contra el 
manifiesto en la evaluación.

Consulta el [catálogo de reglas de auditoría](./docs/catalogo_auditoria.md)
para el detalle de cada regla y sus limitaciones conocidas.

## Instalación

```powershell
git clone https://github.com/D4v1son/starglob-datalab.git StarGlob_DataLab
cd StarGlob_DataLab
python -m venv venv
venv\Scripts\activate # Alternativamente: .\venv\Scripts\Activate.ps1
pip install -e .
```
Para poder utilizar las **herramientas de desarrollador**, primero debes instalar 
las dependencias de forma separada:
```powershell
pip install -e ".[dev]"

# Actualmente nos permite ejecutar tests
pytest -v
```
En caso de querer cambiar de **entorno** de ejecución recuerda salir primero del que
te encuentres:
```powershell
deactivate
```
## Uso

### Comprobar versión del programa:
```powershell
python -m starglob_datalab --version
```

### Generar un dataset limpio:
```powershell
python -m starglob_datalab generate --config config/<dataset>.yaml

# ejemplo:
python -m starglob_datalab generate --config config/tickets_demo.yaml
python -m starglob_datalab generate --config config/backups_demo.yaml
```

Esto crea `output/tickets_demo/clean.csv`, reproducible: la misma
configuración y semilla siempre produce el mismo resultado. Además, de haber 
añadido anomalías a la generación, se generará un archivo
`output/tickets_demo/dirty.csv` y un manifesto con los cambios de cada 
anomalía en `output/tickets_demo/truth_manifest.jsonl`.

### Auditar un dataset:
```powershell
python -m starglob_datalab audit --input output/<dataset>/dirty.csv --template <tickets|backups> [--output <direccion/nombre>.json] [--run-id <run_id>]

# ejemplo:
python -m starglob_datalab audit --input output/tickets_demo/dirty.csv --template tickets [--output <direccion/nombre>.json] [--run-id <run_id>]
python -m starglob_datalab audit --input output/backups_demo/dirty.csv --template backups [--output <direccion/nombre>.json] [--run-id <run_id>]
```
Con este comando se genera `output/tickets_demo/audit_results.json` con
las anomalías que el auditor haya encontrado. **CLI `audit` usa `--template` 
en vez de `--rules`**: nuestras reglas de auditoría están fijas por plantilla 
en código (`RULES_BY_TEMPLATE`). Actualmente solo existen dos plantillas:
`tickets` y `backups`. Es posible especificar una nueva ruta y nombre para 
el archivo mediante `--output`. Por defecto se genera en el nuevo archivo en 
el mismo directorio que el input.

Por defecto, la ejecución del auditor está ligada al manifiesto mediante un `run_id`, 
de esta forma es más fácil comparar los resultados y almacenarlos sin que se 
crucen con otras ejecuciones. Como es posible especificar un ``run_id`` para cada 
ejecución concreta con el comando ``--run-id``. En caso de no especificar un nuevo
identificador o de existir un manifiesto, se generará un nuevo identificador.

### Evaluar los resultados:
```powershell
python -m starglob_datalab evaluate --clean output/<dataset>/clean.csv --dirty output/<dataset>/dirty.csv --manifest output/<dataset>/truth_manifest.jsonl --template <tickets|backups> [--output <nombre>.json]

# ejemplo:
python -m starglob_datalab evaluate --clean output/tickets_demo/clean.csv --dirty output/tickets_demo/dirty.csv --manifest output/tickets_demo/truth_manifest.jsonl --template tickets [--output <nombre>.json]
python -m starglob_datalab evaluate --clean output/backups_demo/clean.csv --dirty output/backups_demo/dirty.csv --manifest output/backups_demo/truth_manifest.jsonl --template backups [--output <nombre>.json]
```

Por defecto, se generará el autput como `evaluation_results.json`, pero
se puede modificar con `--output`. El archivo se genera en la carpeta desde 
la que se ejecute el comando.
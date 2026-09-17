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
Dos plantillas: `tickets` (incidencias de soporte) y `backups` (copias de seguridad). Ambas requieren identificadores únicos reproducibles por semilla y relaciones temporales coherentes (p. ej. `closed_at` posterior
a `created_at`).

### Backlog (siguiendo la planificación de 75h)
- **Semana 1**: configuración + generador de ambas plantillas + reproducibilidad
- **Semana 2**: catálogo de anomalías (DQ01–DQ14) + auditor + evaluador
- **Semana 3**: persistencia SQLite + dashboard + documentación + entrega

## Instalación

*(pendiente, se documentará cuando el entorno esté probado de principio a fin)*
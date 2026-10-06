# Rendimiento - RNF03

Objetivo de referencia del encargo: generar y auditar 100.000 filas en
menos de 3 minutos.

## Resultado - [2026-10-06]

**Equipo:** Intel Core i7-13620H (13ª gen), 16 GB RAM. Ejecutado 
con `config/tickets_bench.yaml` y `config/backups_bench.yaml` 
(100.000 filas, con una muestra representativa de anomalías, 
no las 14 completas).

| Plantilla | Generar + inyectar | Auditar | Total |
|---|---|---|---|
| Tickets   | 11.5s | 40.8s | 52.3s |
| Backups   | 10.1s | 35.0s | 45.1s |

**Objetivo cumplido** con amplio margen: ambas plantillas completan el
ciclo generar + inyectar + auditar en menos de 1 minuto, muy por debajo
del límite de 3 minutos.

## Notas

- Auditar tarda 3-4× más que generar en ambas plantillas, por recorrer
  el DataFrame fila a fila en cada una de las 14 reglas, sin
  vectorizar - margen de optimización si algún día hiciera falta, pero
  no es necesario dado el resultado actual.
- Medido con `Measure-Command` en PowerShell, por comando por separado
  (no el pipeline completo de una sola vez).

```powershell
Measure-Command { python -m starglob_datalab generate --config config/tickets_bench.yaml --run-id bench_tickets }

Measure-Command { python -m starglob_datalab audit --input output/bench_tickets/dirty.csv --template tickets }

Measure-Command { python -m starglob_datalab generate --config config/backups_bench.yaml --run-id bench_backups }

Measure-Command { python -m starglob_datalab audit --input output/bench_backups/dirty.csv --template backups }
```
import random
import pandas as pd
from starglob_datalab.anomalies.manifest import ManifestEntry
from starglob_datalab.anomalies import rules


class InjectionContext:
    """Estado compartido entre todas las anomalías de una misma ejecución."""
    
    def __init__(self, seed: int, run_id: str, frozen_ids: dict, template: str):
        self.rng = random.Random(seed)
        self.seed = seed
        self.run_id = run_id
        self._order = 0
        self.used_cells = set()         # (row_id, field) ya alterados, para no repetir celda
        self.used_rows = set()          # filas usadas, en caso de no querer repetir filas
        self.frozen_ids = frozen_ids    # {índice de fila: row_id original}
        self.template = template        # para saber si tratamos con Tockets o Backups
        
    def next_entry_ids(self):
        self._order += 1
        return self._order, f"anom_{self._order:06d}"

APPLICATORS = {
    "DQ_01": rules.apply_dq01,
    "DQ_02": rules.apply_dq02,
    "DQ_03": rules.apply_dq03,
    "DQ_04": rules.apply_dq04,
    "DQ_05": rules.apply_dq05,
    "DQ_06": rules.apply_dq06,
    "DQ_07": rules.apply_dq07,
    "DQ_08": rules.apply_dq08,
    "DQ_09": rules.apply_dq09,
    "DQ_10": rules.apply_dq10,
    # se irán añadiendo aquí conforme implementemos cada anomalía
}

# injector.py

def inject_anomalies(df, row_id_col: str, config, run_id: str):
    """
    Aplica sobre 'df' (debe ser ya una copia del dataset limpio) todas las
    anomalías listadas en config.anomalies. Devuelve (df_actualizado, entries).
    """
    frozen_ids = dict(zip(df.index, df[row_id_col]))  # foto fija ANTES de tocar nada
    ctx = InjectionContext(
        seed=config.seed,
        run_id=run_id,
        frozen_ids=frozen_ids,
        template=config.template
    )
        
    entries = []
    for anomaly_cfg in (config.anomalies or []):
        aplicar = APPLICATORS.get(anomaly_cfg.code)
        if aplicar is None:
            raise NotImplementedError(f"Anomalía '{anomaly_cfg.code}' aún no implementada")
        df, nuevas_entries = aplicar(df, row_id_col, anomaly_cfg, ctx)
        entries.extend(nuevas_entries)
    return df, entries
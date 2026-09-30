import random
import pandas as pd
from starglob_datalab.anomalies.manifest import ManifestEntry
from starglob_datalab.anomalies import rules


class InjectionContext:
    """Estado compartido entre todas las anomalías de una misma ejecución."""
    
    def __init__(self, seed: int, run_id: str, frozen_ids: dict, template: str, original_df):
        self.rng = random.Random(seed)
        self.seed = seed
        self.run_id = run_id
        self._order = 0
        self.used_cells = set()                 # (row_id, field) ya alterados, para no repetir celda
        self.used_rows = set()                  # filas usadas, en caso de no querer repetir filas
        self.frozen_ids = frozen_ids            # {índice de fila: row_id original}
        self.next_index = max(frozen_ids) + 1   # siguiente índice libre para filas nuevas (DQ02)
        self.template = template                # para saber si tratamos con Tockets o Backups
        self.original_df = original_df          # copia del dataset limpio, nunca se modifica
        
    def next_entry_ids(self):
        self._order += 1
        return self._order, f"anom_{self._order:06d}"
    
    def fila_libre(self, row_id) -> bool:
        """True si ninguna anomalía ha tocado la fila (ni entera ni ninguna celda)."""
        return row_id not in self.used_rows and not any(rid == row_id for rid, _ in self.used_cells)

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
    "DQ_11": rules.apply_dq11,
    "DQ_12": rules.apply_dq12,
    "DQ_13": rules.apply_dq13,
    "DQ_14": rules.apply_dq14,
}

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
        template=config.template,
        original_df=df.copy(),
    )
        
    entries = []
    for anomaly_cfg in (config.anomalies or []):
        aplicar = APPLICATORS.get(anomaly_cfg.code)
        if aplicar is None:
            raise NotImplementedError(f"Anomalía '{anomaly_cfg.code}' aún no implementada")
        df, nuevas_entries = aplicar(df, row_id_col, anomaly_cfg, ctx)
        entries.extend(nuevas_entries)
    return df, entries
    
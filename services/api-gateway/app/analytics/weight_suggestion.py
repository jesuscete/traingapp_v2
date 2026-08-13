"""Sugerencia de peso historico para prellenar una serie de rutina.

Regla (estudio de rutinas, seccion 5): al prellenar un `routine_set`, buscar
el ultimo peso registrado en `set_entry` para ese `exercise_id` y, si es
posible, el mismo `set_number`; si no hay coincidencia exacta de numero de
serie, usar el ultimo peso registrado para ese ejercicio en general.

La funcion es pura e aislada para poder testearla sin base de datos.
Notas de coherencia con el catalogo:
- Ejercicios unilaterales: el peso se registra por lado en cada `set_entry`
  (`side`). La sugerencia devuelve el peso tal y como se registro (un lado);
  el llamado decide si duplicarlo o mostrarlo por lado.
- Peso corporal (`uses_bodyweight`): no hay peso que sugerir; el llamado
  debe saltarse la sugerencia (devolver `None`).
"""

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class WeightRecord:
    """Un peso real registrado (una fila de `set_entry` normal)."""

    set_number: int
    weight: float
    performed_at: datetime


def suggest_weight(records: list[WeightRecord], set_number: int) -> float | None:
    """Ultimo peso para el mismo set_number; si no hay, el ultimo del ejercicio.

    Si no hay ningun registro historico, devuelve `None` (sin sugerencia).
    """
    if not records:
        return None
    by_set = [record for record in records if record.set_number == set_number]
    source = by_set if by_set else records
    return max(source, key=lambda record: record.performed_at).weight

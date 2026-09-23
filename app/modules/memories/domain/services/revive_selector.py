"""Como se eligen los recuerdos que se vuelven a mostrar (capacidad CP-05).

El PRD deja abierto el mecanismo de "revivir" (pendiente P15). Este servicio
concentra la regla provisional en un solo sitio, sin base de datos de por medio,
para que cambiarla sea cambiar esta funcion:

  1. si hay recuerdos de este mismo dia en anos anteriores, se muestran esos;
  2. si no, se muestra una seleccion al azar de recuerdos antiguos.
"""

from dataclasses import dataclass
from enum import StrEnum

from app.modules.memories.domain.entities.memory import Memory


class ReviveReason(StrEnum):
    ON_THIS_DAY = "on_this_day"
    RANDOM = "random"
    NONE = "none"


@dataclass(frozen=True, slots=True)
class ReviveSelection:
    memories: list[Memory]
    reason: ReviveReason


def choose_revive_memories(
    on_this_day: list[Memory], fallback: list[Memory], limit: int
) -> ReviveSelection:
    if on_this_day:
        return ReviveSelection(memories=on_this_day[:limit], reason=ReviveReason.ON_THIS_DAY)
    if fallback:
        return ReviveSelection(memories=fallback[:limit], reason=ReviveReason.RANDOM)
    return ReviveSelection(memories=[], reason=ReviveReason.NONE)

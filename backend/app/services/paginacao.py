"""Paginação das listagens que podem crescer."""

from dataclasses import dataclass
from typing import Generic, TypeVar

T = TypeVar("T")

POR_PAGINA_PADRAO = 30
POR_PAGINA_MAXIMO = 100


@dataclass(frozen=True)
class Pagina(Generic[T]):
    itens: list[T]
    total: int
    pagina: int
    por_pagina: int


def limite_e_deslocamento(pagina: int, por_pagina: int) -> tuple[int, int, int, int]:
    """Devolve (pagina, por_pagina, limite, deslocamento) dentro dos limites aceitos."""
    pagina = max(1, pagina)
    por_pagina = min(max(1, por_pagina), POR_PAGINA_MAXIMO)
    return pagina, por_pagina, por_pagina, (pagina - 1) * por_pagina

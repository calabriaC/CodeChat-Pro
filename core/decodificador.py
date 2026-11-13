"""Decodificador por mayoría para el código de repetición de longitud n."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

import numpy as np

from core.matematicas import validar_bits, validar_longitud

BIT_AMBIGUO = -1


class PoliticaDesempate(str, Enum):
    """Qué hacer cuando un bloque de longitud par tiene tantos unos como ceros."""

    AMBIGUO = "ambiguo"
    CERO = "cero"
    UNO = "uno"
    ALEATORIO = "aleatorio"

    @property
    def etiqueta(self) -> str:
        return {
            PoliticaDesempate.AMBIGUO: "Marcar como ambiguo",
            PoliticaDesempate.CERO: "Seleccionar 0",
            PoliticaDesempate.UNO: "Seleccionar 1",
            PoliticaDesempate.ALEATORIO: "Decisión aleatoria",
        }[self]


@dataclass(frozen=True)
class ResultadoDecodificacion:
    """Resultado de la decodificación por mayoría.

    bits: arreglo int8 con 0, 1 o BIT_AMBIGUO (-1) por cada bit de información.
    """

    bits: np.ndarray
    votos_uno: np.ndarray  # cantidad de unos recibidos en cada bloque
    empates: np.ndarray  # True en los bloques con empate (resueltos o no)
    ambiguos: np.ndarray  # True en los bloques que quedaron sin decidir
    n: int
    politica: PoliticaDesempate

    @property
    def num_empates(self) -> int:
        return int(self.empates.sum())

    @property
    def num_ambiguos(self) -> int:
        return int(self.ambiguos.sum())

    @property
    def hay_ambiguos(self) -> bool:
        return bool(self.ambiguos.any())

    def bits_resueltos(self) -> np.ndarray:
        """Bits 0/1 decodificados. Lanza ValueError si queda algún bit ambiguo."""
        if self.hay_ambiguos:
            raise ValueError(f"Hay {self.num_ambiguos} bit(s) ambiguo(s): el mensaje no puede reconstruirse.")
        return self.bits.astype(np.uint8)


def decodificar(
    recibidos,
    n: int,
    politica: PoliticaDesempate = PoliticaDesempate.AMBIGUO,
    generador: np.random.Generator | None = None,
) -> ResultadoDecodificacion:
    """Decodifica por mayoría cada bloque de n bits recibidos.

    * Si hay más unos que ceros se decide 1; si hay más ceros se decide 0.
    * Si hay empate (solo posible con n par) se aplica la política indicada.
    """
    recibidos = validar_bits(recibidos)
    n = validar_longitud(n)
    politica = PoliticaDesempate(politica)
    if recibidos.size % n:
        raise ValueError(f"La longitud recibida ({recibidos.size}) no es múltiplo de n = {n}.")

    bloques = recibidos.reshape(-1, n)
    votos_uno = bloques.sum(axis=1, dtype=np.int64)
    votos_cero = n - votos_uno
    bits = (votos_uno > votos_cero).astype(np.int8)
    empates = votos_uno == votos_cero
    ambiguos = np.zeros_like(empates)

    if empates.any():
        if politica is PoliticaDesempate.AMBIGUO:
            bits[empates] = BIT_AMBIGUO
            ambiguos = empates.copy()
        elif politica is PoliticaDesempate.CERO:
            bits[empates] = 0
        elif politica is PoliticaDesempate.UNO:
            bits[empates] = 1
        else:  # ALEATORIO
            rng = generador if generador is not None else np.random.default_rng()
            bits[empates] = rng.integers(0, 2, size=int(empates.sum()), dtype=np.int8)

    return ResultadoDecodificacion(
        bits=bits, votos_uno=votos_uno, empates=empates, ambiguos=ambiguos, n=n, politica=politica
    )

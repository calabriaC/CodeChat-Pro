"""Canal binario simétrico (BSC, Binary Symmetric Channel).

Cada bit transmitido se invierte de forma independiente con probabilidad p y
llega intacto con probabilidad 1 - p.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from core.matematicas import validar_bits, validar_probabilidad


@dataclass(frozen=True)
class ResultadoCanal:
    """Resultado de pasar una secuencia de bits por el canal."""

    transmitidos: np.ndarray
    recibidos: np.ndarray
    mascara_errores: np.ndarray  # True donde el canal invirtió el bit
    probabilidad: float  # p teórica configurada

    @property
    def posiciones_alteradas(self) -> np.ndarray:
        return np.flatnonzero(self.mascara_errores)

    @property
    def num_errores(self) -> int:
        return int(self.mascara_errores.sum())

    @property
    def proporcion_errores(self) -> float:
        """Proporción OBSERVADA de bits invertidos (estimación empírica de p)."""
        total = self.transmitidos.size
        return self.num_errores / total if total else 0.0


class CanalBSC:
    """Canal binario simétrico con probabilidad de inversión p (0 <= p <= 0.5)."""

    def __init__(self, probabilidad: float, generador: np.random.Generator | None = None):
        self.probabilidad = validar_probabilidad(probabilidad)
        self.generador = generador if generador is not None else np.random.default_rng()

    def transmitir(self, bits) -> ResultadoCanal:
        transmitidos = validar_bits(bits)
        # random() devuelve valores en [0, 1): con p = 0 nunca hay error y con
        # p = 0.5 cada bit se invierte con probabilidad exactamente 1/2.
        mascara = self.generador.random(transmitidos.size) < self.probabilidad
        recibidos = transmitidos ^ mascara.astype(np.uint8)
        return ResultadoCanal(
            transmitidos=transmitidos.copy(),
            recibidos=recibidos,
            mascara_errores=mascara,
            probabilidad=self.probabilidad,
        )

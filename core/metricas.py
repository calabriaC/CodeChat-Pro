"""Métricas de desempeño: BER, recuperación, tasa y estadística de los experimentos.

Se miden siempre dos escenarios con el mismo canal BSC(p):

* Escenario A — sin código: los k bits útiles se transmiten directamente.
* Escenario B — con código de repetición: se transmiten k·n bits y se decodifica por mayoría.

Vocabulario:
* BER del canal: proporción de bits TRANSMITIDOS que el canal invirtió (estima p).
* BER residual: proporción de bits ÚTILES que quedan incorrectos al final.
  Sin código, ambas coinciden; con código, la BER residual es la que mide la protección.
* Los bits ambiguos (empates no resueltos) se cuentan aparte: no son errores
  confirmados, pero tampoco aciertos.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from core.decodificador import BIT_AMBIGUO

Z_95 = 1.959963984540054


def intervalo_wilson(exitos: int, ensayos: int, z: float = Z_95) -> tuple[float, float]:
    """Intervalo de confianza de Wilson (95 % por defecto) para una proporción."""
    if ensayos <= 0:
        raise ValueError("El número de ensayos debe ser positivo.")
    if not 0 <= exitos <= ensayos:
        raise ValueError("El número de éxitos debe estar entre 0 y el número de ensayos.")
    phat = exitos / ensayos
    z2 = z * z
    denominador = 1.0 + z2 / ensayos
    centro = (phat + z2 / (2 * ensayos)) / denominador
    margen = z * math.sqrt(phat * (1 - phat) / ensayos + z2 / (4 * ensayos * ensayos)) / denominador
    bajo = 0.0 if exitos == 0 else max(0.0, centro - margen)
    alto = 1.0 if exitos == ensayos else min(1.0, centro + margen)
    return bajo, alto


def comparar_bits(originales, decididos) -> tuple[int, int]:
    """Compara bit a bit. Devuelve (incorrectos, ambiguos).

    `decididos` puede contener BIT_AMBIGUO (-1); esos bits no cuentan como error ni como acierto.
    """
    originales = np.asarray(originales).tolist()
    decididos = np.asarray(decididos).tolist()
    if len(originales) != len(decididos):
        raise ValueError("Las secuencias a comparar deben tener la misma longitud.")
    incorrectos = 0
    ambiguos = 0
    for original, decidido in zip(originales, decididos):
        if decidido == BIT_AMBIGUO:
            ambiguos += 1
        elif decidido != original:
            incorrectos += 1
    return incorrectos, ambiguos


@dataclass(frozen=True)
class MetricasEsquema:
    """Métricas de un esquema de transmisión (con o sin código) sobre k bits útiles."""

    nombre: str
    bits_utiles: int
    bits_transmitidos: int
    errores_introducidos: int  # bits invertidos por el canal
    errores_residuales: int  # bits útiles incorrectos al final
    ambiguos: int = 0  # bits útiles sin decidir

    @property
    def tasa(self) -> float:
        """Bits útiles por bit transmitido (1 sin código, 1/n con repetición)."""
        return self.bits_utiles / self.bits_transmitidos if self.bits_transmitidos else 0.0

    @property
    def redundancia_por_bit(self) -> float:
        return (self.bits_transmitidos - self.bits_utiles) / self.bits_utiles if self.bits_utiles else 0.0

    @property
    def ber_canal(self) -> float:
        return self.errores_introducidos / self.bits_transmitidos if self.bits_transmitidos else 0.0

    @property
    def ber_residual(self) -> float:
        return self.errores_residuales / self.bits_utiles if self.bits_utiles else 0.0

    @property
    def bits_recuperados(self) -> int:
        """Bits útiles recuperados con certeza (ni erróneos ni ambiguos)."""
        return self.bits_utiles - self.errores_residuales - self.ambiguos

    @property
    def porcentaje_recuperacion(self) -> float:
        return 100.0 * self.bits_recuperados / self.bits_utiles if self.bits_utiles else 100.0

    @property
    def mensaje_integro(self) -> bool:
        return self.errores_residuales == 0 and self.ambiguos == 0

    def a_diccionario(self) -> dict:
        return {
            "bits_utiles": self.bits_utiles,
            "bits_transmitidos": self.bits_transmitidos,
            "errores_introducidos": self.errores_introducidos,
            "errores_residuales": self.errores_residuales,
            "ambiguos": self.ambiguos,
            "ber_canal": self.ber_canal,
            "ber_residual": self.ber_residual,
            "porcentaje_recuperacion": self.porcentaje_recuperacion,
            "tasa": self.tasa,
        }

"""Codificador del código de repetición binario de longitud n."""

from __future__ import annotations

import numpy as np

from core.matematicas import texto_a_bits, validar_bits, validar_longitud


def codificar(bits, n: int) -> np.ndarray:
    """Repite cada bit exactamente n veces.

    Ejemplo: codificar([1, 0], 3) -> [1, 1, 1, 0, 0, 0]
    """
    return np.repeat(validar_bits(bits), validar_longitud(n))


def codificar_texto(texto: str, n: int) -> tuple[np.ndarray, np.ndarray]:
    """Convierte el texto a bits UTF-8 y los codifica. Devuelve (bits, codificados)."""
    bits = texto_a_bits(texto)
    return bits, codificar(bits, n)

"""Codificador del código de repetición binario de longitud n (implementación propia).

Código de repetición R_n: cada bit de información b se transforma en la palabra
de código b b ... b (n veces). Parámetros: k = 1, M = 2, d = n, R = 1/n.

Ejemplo: mensaje 101 con n = 3  ->  111 000 111
"""

from __future__ import annotations

import numpy as np

from core.matematicas import texto_a_bits, validar_bits, validar_longitud


def codificar(bits, n: int) -> np.ndarray:
    """Repite cada bit del mensaje exactamente n veces.

    Algoritmo:
      1. Validar que n esté en 1..21 y que cada elemento sea 0 o 1.
      2. Para cada bit b del mensaje, agregar b a la salida n veces.
    La salida tiene longitud len(bits) * n.
    """
    n = validar_longitud(n)
    mensaje = validar_bits(bits)

    palabra_codigo: list[int] = []
    for bit in mensaje.tolist():          # recorrer los bits de información
        for _ in range(n):                # repetir el bit n veces
            palabra_codigo.append(bit)

    # NumPy solo se usa como contenedor del resultado (tarea auxiliar).
    return np.array(palabra_codigo, dtype=np.uint8)


def codificar_texto(texto: str, n: int) -> tuple[np.ndarray, np.ndarray]:
    """Convierte el texto a bits (UTF-8) y los codifica. Devuelve (bits, codificados)."""
    bits = texto_a_bits(texto)
    return bits, codificar(bits, n)

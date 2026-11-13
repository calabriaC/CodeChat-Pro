"""Fundamentos matemáticos de CodeChat Pro.

Contiene las conversiones texto <-> bits (UTF-8), los parámetros del código de
repetición binario de longitud n, la entropía binaria, la capacidad del canal
binario simétrico (BSC) y las probabilidades teóricas de error residual de la
decodificación por mayoría.

Este módulo no depende de la interfaz gráfica.
"""

from __future__ import annotations

import math
from numbers import Integral

import numpy as np

N_MIN = 1
N_MAX = 21
P_MIN = 0.0
P_MAX = 0.5


# ---------------------------------------------------------------------------
# Validaciones
# ---------------------------------------------------------------------------
def validar_longitud(n: int) -> int:
    """Comprueba que n sea un entero en [N_MIN, N_MAX] y lo devuelve como int."""
    if isinstance(n, bool) or not isinstance(n, Integral):
        raise TypeError(f"La longitud del código debe ser un entero, se recibió {n!r}.")
    if not N_MIN <= n <= N_MAX:
        raise ValueError(f"La longitud del código debe estar entre {N_MIN} y {N_MAX}; se recibió {n}.")
    return int(n)


def validar_probabilidad(p: float) -> float:
    """Comprueba que 0 <= p <= 0.5 (dominio del canal en la aplicación)."""
    try:
        p = float(p)
    except (TypeError, ValueError) as exc:
        raise TypeError(f"La probabilidad debe ser numérica, se recibió {p!r}.") from exc
    if math.isnan(p) or not P_MIN <= p <= P_MAX:
        raise ValueError(f"La probabilidad de error debe cumplir 0 <= p <= 0.5; se recibió {p}.")
    return p


def _validar_probabilidad_unitaria(p: float) -> float:
    p = float(p)
    if math.isnan(p) or not 0.0 <= p <= 1.0:
        raise ValueError(f"La probabilidad debe estar en [0, 1]; se recibió {p}.")
    return p


def validar_bits(bits) -> np.ndarray:
    """Convierte una secuencia de bits en un arreglo 1-D uint8 con valores 0/1."""
    arreglo = np.asarray(bits)
    if arreglo.ndim != 1:
        raise ValueError("La secuencia de bits debe ser unidimensional.")
    if arreglo.size and not np.isin(arreglo, (0, 1)).all():
        raise ValueError("La secuencia solo puede contener los valores 0 y 1.")
    return arreglo.astype(np.uint8, copy=False)


# ---------------------------------------------------------------------------
# Conversión texto <-> bits (UTF-8, bit más significativo primero)
# ---------------------------------------------------------------------------
def texto_a_bits(texto: str) -> np.ndarray:
    """Codifica el texto en UTF-8 y devuelve sus bits (MSB primero)."""
    if not isinstance(texto, str):
        raise TypeError("El mensaje debe ser una cadena de texto.")
    datos = np.frombuffer(texto.encode("utf-8"), dtype=np.uint8)
    return np.unpackbits(datos)


def bits_a_bytes(bits) -> bytes:
    """Agrupa los bits de 8 en 8 (MSB primero) y devuelve los bytes."""
    bits = validar_bits(bits)
    if bits.size % 8:
        raise ValueError("La cantidad de bits debe ser múltiplo de 8 para formar bytes.")
    return np.packbits(bits).tobytes()


def bits_a_texto(bits) -> str:
    """Decodifica bits a texto UTF-8 de forma estricta (lanza UnicodeDecodeError)."""
    return bits_a_bytes(bits).decode("utf-8")


def bits_a_texto_tolerante(bits) -> tuple[str, bool]:
    """Decodifica bits a texto. Devuelve (texto, es_utf8_valido).

    Si los bytes no forman UTF-8 válido, las secuencias inválidas se muestran con
    el carácter de reemplazo U+FFFD y el indicador es False.
    """
    datos = bits_a_bytes(bits)
    try:
        return datos.decode("utf-8"), True
    except UnicodeDecodeError:
        return datos.decode("utf-8", errors="replace"), False


def bits_a_cadena(bits) -> str:
    """Representa una secuencia de bits como cadena '0101...'."""
    return "".join("1" if b else "0" for b in validar_bits(bits).tolist())


def cadena_a_bits(cadena: str) -> np.ndarray:
    """Convierte una cadena '0101...' en arreglo de bits."""
    if any(c not in "01" for c in cadena):
        raise ValueError("La cadena solo puede contener los caracteres '0' y '1'.")
    return np.fromiter((c == "1" for c in cadena), dtype=np.uint8, count=len(cadena))


# ---------------------------------------------------------------------------
# Parámetros del código de repetición binario R_n = {0^n, 1^n}
# ---------------------------------------------------------------------------
def distancia_minima(n: int) -> int:
    """d_min = n: las dos palabras código 00...0 y 11...1 difieren en n posiciones."""
    return validar_longitud(n)


def capacidad_correccion(n: int) -> int:
    """t = floor((n - 1) / 2): errores por bloque que se corrigen con garantía."""
    return (validar_longitud(n) - 1) // 2


def capacidad_deteccion(n: int) -> int:
    """d_min - 1 = n - 1: errores por bloque que se detectan con garantía."""
    return validar_longitud(n) - 1


def tasa_codigo(n: int) -> float:
    """R = k / n = 1 / n (un bit de información por bloque de n bits)."""
    return 1.0 / validar_longitud(n)


def redundancia(n: int) -> int:
    """n - 1 bits redundantes por cada bit de información."""
    return validar_longitud(n) - 1


def parametros_codigo(n: int) -> dict:
    """Parámetros (n, k, M, d) del código de repetición y sus consecuencias.

    * k = 1 bit de información por bloque; M = 2^k = 2 palabras código.
    * d = n; corrige t = floor((d-1)/2) y detecta d - 1 errores por bloque.
    """
    n = validar_longitud(n)
    return {
        "n": n,
        "k": 1,
        "M": 2,
        "d": distancia_minima(n),
        "t": capacidad_correccion(n),
        "detecta": capacidad_deteccion(n),
        "R": tasa_codigo(n),
        "redundancia": redundancia(n),
    }


# ---------------------------------------------------------------------------
# Teoría de la información: entropía binaria y capacidad del BSC
# ---------------------------------------------------------------------------
def entropia_binaria(p: float) -> float:
    """H2(p) = -p log2 p - (1-p) log2 (1-p), con el convenio 0·log2(0) = 0."""
    p = _validar_probabilidad_unitaria(p)
    if p in (0.0, 1.0):
        return 0.0
    return -p * math.log2(p) - (1.0 - p) * math.log2(1.0 - p)


def capacidad_bsc(p: float) -> float:
    """C = 1 - H2(p) bits por uso del canal. C(0) = 1 y C(0.5) = 0."""
    return 1.0 - entropia_binaria(p)


# ---------------------------------------------------------------------------
# Probabilidades teóricas de la decodificación por mayoría
# ---------------------------------------------------------------------------
def _termino_binomial(n: int, k: int, p: float) -> float:
    """C(n,k) p^k (1-p)^(n-k): probabilidad de exactamente k errores en n bits."""
    return math.comb(n, k) * p**k * (1.0 - p) ** (n - k)


def probabilidad_error_mayoria_estricta(n: int, p: float) -> float:
    """P(más de la mitad de los n bits del bloque se invierten).

    Es la probabilidad de que la mayoría apunte al bit equivocado.
    """
    n = validar_longitud(n)
    p = validar_probabilidad(p)
    return math.fsum(_termino_binomial(n, k, p) for k in range(n // 2 + 1, n + 1))


def probabilidad_empate(n: int, p: float) -> float:
    """P(exactamente n/2 errores). Solo es posible para n par; para n impar vale 0."""
    n = validar_longitud(n)
    p = validar_probabilidad(p)
    if n % 2:
        return 0.0
    return _termino_binomial(n, n // 2, p)


def probabilidad_error_bit(n: int, p: float) -> float:
    """Probabilidad de error residual por bit de información.

    * n impar:  sum_{k=(n+1)/2}^{n} C(n,k) p^k (1-p)^(n-k)
    * n par (desempate aleatorio):
                sum_{k=n/2+1}^{n} C(n,k) p^k (1-p)^(n-k) + 0.5 C(n,n/2) p^(n/2) (1-p)^(n/2)

    Para una fuente con bits equiprobables, las políticas "elegir 0" y
    "elegir 1" producen en promedio la misma probabilidad que el desempate
    aleatorio.
    """
    return probabilidad_error_mayoria_estricta(n, p) + 0.5 * probabilidad_empate(n, p)


def probabilidad_fallo_mensaje(n: int, p: float, k_bits: int, empates_como_fallo: bool = False) -> float:
    """Probabilidad de que un mensaje de k_bits bits NO se recupere por completo.

    Suponiendo bloques independientes: P_fallo = 1 - (1 - q)^k_bits, donde q es
    la probabilidad de que un bit de información no se recupere:

    * empates_como_fallo=False -> q = P_error_bit (desempate aleatorio).
    * empates_como_fallo=True  -> q = P(mayoría errónea) + P(empate)
      (política "marcar como ambiguo": un empate impide recuperar el mensaje).
    """
    if isinstance(k_bits, bool) or not isinstance(k_bits, Integral) or k_bits < 0:
        raise ValueError("k_bits debe ser un entero no negativo.")
    if empates_como_fallo:
        q = probabilidad_error_mayoria_estricta(n, p) + probabilidad_empate(n, p)
    else:
        q = probabilidad_error_bit(n, p)
    return _uno_menos_potencia(q, k_bits)


def probabilidad_fallo_sin_codigo(p: float, k_bits: int) -> float:
    """Sin código, el mensaje falla si al menos uno de sus k bits se invierte: 1 - (1-p)^k."""
    p = validar_probabilidad(p)
    if isinstance(k_bits, bool) or not isinstance(k_bits, Integral) or k_bits < 0:
        raise ValueError("k_bits debe ser un entero no negativo.")
    return _uno_menos_potencia(p, k_bits)


def _uno_menos_potencia(q: float, k: int) -> float:
    """1 - (1 - q)^k calculado de forma numéricamente estable."""
    if k == 0 or q == 0.0:
        return 0.0
    if q >= 1.0:
        return 1.0
    return -math.expm1(k * math.log1p(-q))

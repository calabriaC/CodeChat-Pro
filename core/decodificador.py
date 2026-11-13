"""Decodificador por mayoría para el código de repetición de longitud n (implementación propia).

Para cada bloque de n bits recibidos:
  1. Contar los ceros.
  2. Contar los unos.
  3. Comparar las cantidades.
  4. Recuperar el bit predominante (si hay empate, aplicar la política elegida).
  5. Registrar el resultado.

Con n impar nunca hay empate. Con n par hay empate cuando llegan exactamente
n/2 unos y n/2 ceros.

Detección frente a corrección: el receptor NO conoce el mensaje original. Lo
único que puede observar es si un bloque recibido es una palabra del código
(00...0 o 11...1). Si no lo es, sabe que hubo al menos un error en el bloque
(detección), pero no sabe cuántos. La decisión por mayoría devuelve el bit
correcto siempre que el bloque tenga como máximo t = floor((n-1)/2) errores.
"""

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

    bits: int8 con 0, 1 o BIT_AMBIGUO (-1) por cada bit de información.
    """

    bits: np.ndarray
    votos_cero: np.ndarray  # ceros contados en cada bloque
    votos_uno: np.ndarray  # unos contados en cada bloque
    empates: np.ndarray  # True en los bloques con empate (resueltos o no)
    ambiguos: np.ndarray  # True en los bloques que quedaron sin decidir
    bloques_no_codigo: np.ndarray  # True si el bloque recibido no es 0^n ni 1^n (error detectado)
    n: int
    politica: PoliticaDesempate

    @property
    def num_empates(self) -> int:
        return int(self.empates.sum())

    @property
    def num_ambiguos(self) -> int:
        return int(self.ambiguos.sum())

    @property
    def num_bloques_detectados(self) -> int:
        """Bloques en los que el receptor detecta que hubo al menos un error."""
        return int(self.bloques_no_codigo.sum())

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
    """Decodifica por mayoría cada bloque de n bits recibidos."""
    n = validar_longitud(n)
    politica = PoliticaDesempate(politica)
    secuencia = validar_bits(recibidos).tolist()
    if len(secuencia) % n != 0:
        raise ValueError(f"La longitud recibida ({len(secuencia)}) no es divisible entre n = {n}.")
    rng = generador if generador is not None else np.random.default_rng()

    bits, ceros_por_bloque, unos_por_bloque = [], [], []
    empates, ambiguos, no_codigo = [], [], []

    for inicio in range(0, len(secuencia), n):
        bloque = secuencia[inicio:inicio + n]

        # 1-2. Contar ceros y unos del bloque.
        ceros = 0
        unos = 0
        for bit in bloque:
            if bit == 1:
                unos += 1
            else:
                ceros += 1

        # 3-4. Comparar y decidir.
        empate = False
        ambiguo = False
        if unos > ceros:
            decision = 1
        elif ceros > unos:
            decision = 0
        else:  # empate: solo posible con n par (unos = ceros = n/2)
            empate = True
            if politica is PoliticaDesempate.CERO:
                decision = 0
            elif politica is PoliticaDesempate.UNO:
                decision = 1
            elif politica is PoliticaDesempate.ALEATORIO:
                decision = int(rng.integers(0, 2))
            else:  # AMBIGUO: no se inventa el bit
                decision = BIT_AMBIGUO
                ambiguo = True

        # 5. Registrar el resultado del bloque.
        bits.append(decision)
        ceros_por_bloque.append(ceros)
        unos_por_bloque.append(unos)
        empates.append(empate)
        ambiguos.append(ambiguo)
        no_codigo.append(ceros != 0 and unos != 0)  # el bloque no es 00...0 ni 11...1

    return ResultadoDecodificacion(
        bits=np.array(bits, dtype=np.int8),
        votos_cero=np.array(ceros_por_bloque, dtype=np.int64),
        votos_uno=np.array(unos_por_bloque, dtype=np.int64),
        empates=np.array(empates, dtype=bool),
        ambiguos=np.array(ambiguos, dtype=bool),
        bloques_no_codigo=np.array(no_codigo, dtype=bool),
        n=n,
        politica=politica,
    )

"""Orquestación de la transmisión completa y simulaciones Monte Carlo.

Flujo: texto -> bits UTF-8 -> codificación (repetición n) -> canal BSC(p)
       -> decodificación por mayoría -> bits -> texto UTF-8.
"""

from __future__ import annotations

import random
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

import numpy as np

from core import matematicas as mat
from core.canal_bsc import CanalBSC, ResultadoCanal
from core.codificador import codificar
from core.decodificador import PoliticaDesempate, ResultadoDecodificacion, decodificar

VERSION_ESQUEMA = 1


class EstadoTransmision(str, Enum):
    EXITO = "exito"  # mensaje recuperado idéntico al original
    ERROR = "error"  # se reconstruyó un mensaje, pero difiere del original
    AMBIGUO = "ambiguo"  # quedaron bits ambiguos: no se reconstruye el mensaje

    @property
    def etiqueta(self) -> str:
        return {
            EstadoTransmision.EXITO: "Recuperado correctamente",
            EstadoTransmision.ERROR: "Mensaje con errores",
            EstadoTransmision.AMBIGUO: "Ambiguo (no recuperable)",
        }[self]


def nueva_semilla() -> int:
    """Semilla aleatoria de 31 bits, para registrar y poder repetir el experimento."""
    return random.SystemRandom().randrange(2**31)


def crear_generador(semilla: int | None) -> tuple[int, np.random.Generator]:
    """Devuelve (semilla_usada, generador). Si semilla es None se genera una."""
    if semilla is None:
        semilla = nueva_semilla()
    if isinstance(semilla, bool) or not isinstance(semilla, int) or semilla < 0:
        raise ValueError("La semilla debe ser un entero no negativo.")
    return semilla, np.random.default_rng(semilla)


@dataclass
class ResultadoTransmision:
    """Toda la información de una transmisión de mensaje de extremo a extremo."""

    mensaje_original: str
    n: int
    p: float
    semilla: int
    politica: PoliticaDesempate
    bits_originales: np.ndarray
    bits_codificados: np.ndarray
    canal: ResultadoCanal
    decodificacion: ResultadoDecodificacion
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    fecha_hora: str = field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))

    # --- métricas derivadas -------------------------------------------------
    @property
    def errores_introducidos(self) -> int:
        return self.canal.num_errores

    @property
    def ambiguedades(self) -> int:
        return self.decodificacion.num_ambiguos

    @property
    def mascara_errores_residuales(self) -> np.ndarray:
        """True en los bits de información decididos (no ambiguos) que son incorrectos."""
        dec = self.decodificacion
        return (~dec.ambiguos) & (dec.bits != self.bits_originales.astype(np.int8))

    @property
    def errores_residuales(self) -> int:
        return int(self.mascara_errores_residuales.sum())

    @property
    def bloques_con_errores(self) -> int:
        """Bloques de n bits en los que el canal alteró al menos un bit."""
        if self.bits_originales.size == 0:
            return 0
        return int(self.canal.mascara_errores.reshape(-1, self.n).any(axis=1).sum())

    @property
    def bloques_corregidos(self) -> int:
        """Bloques alterados por el canal cuyo bit se decodificó correctamente."""
        if self.bits_originales.size == 0:
            return 0
        alterados = self.canal.mascara_errores.reshape(-1, self.n).any(axis=1)
        correctos = (~self.decodificacion.ambiguos) & ~self.mascara_errores_residuales
        return int((alterados & correctos).sum())

    @property
    def estado(self) -> EstadoTransmision:
        if self.ambiguedades:
            return EstadoTransmision.AMBIGUO
        if self.errores_residuales:
            return EstadoTransmision.ERROR
        return EstadoTransmision.EXITO

    @property
    def mensaje_recuperado(self) -> str | None:
        """Texto reconstruido, o None si hay bits ambiguos (no se inventa nada)."""
        if self.ambiguedades:
            return None
        return mat.bits_a_texto_tolerante(self.decodificacion.bits_resueltos())[0]

    @property
    def utf8_valido(self) -> bool | None:
        if self.ambiguedades:
            return None
        return mat.bits_a_texto_tolerante(self.decodificacion.bits_resueltos())[1]

    # --- persistencia -------------------------------------------------------
    def a_registro(self) -> dict:
        """Diccionario serializable a JSON con los datos del experimento."""
        return {
            "version_esquema": VERSION_ESQUEMA,
            "id": self.id,
            "fecha_hora": self.fecha_hora,
            "mensaje_original": self.mensaje_original,
            "longitud_codigo": self.n,
            "probabilidad_error": self.p,
            "semilla": self.semilla,
            "politica_desempate": self.politica.value,
            "bits_informacion": int(self.bits_originales.size),
            "bits_originales": mat.bits_a_cadena(self.bits_originales),
            "bits_transmitidos": mat.bits_a_cadena(self.canal.transmitidos),
            "bits_recibidos": mat.bits_a_cadena(self.canal.recibidos),
            "posiciones_alteradas": self.canal.posiciones_alteradas.tolist(),
            "errores_introducidos": self.errores_introducidos,
            "proporcion_errores_observada": self.canal.proporcion_errores,
            "errores_residuales": self.errores_residuales,
            "empates": self.decodificacion.num_empates,
            "ambiguedades": self.ambiguedades,
            "mensaje_recuperado": self.mensaje_recuperado,
            "utf8_valido": self.utf8_valido,
            "resultado": self.estado.value,
            "tasa_codigo": mat.tasa_codigo(self.n),
            "distancia_minima": mat.distancia_minima(self.n),
            "capacidad_correccion": mat.capacidad_correccion(self.n),
            "capacidad_canal": mat.capacidad_bsc(self.p),
            "probabilidad_error_bit_teorica": mat.probabilidad_error_bit(self.n, self.p),
        }


def transmitir_mensaje(
    texto: str,
    n: int,
    p: float,
    semilla: int | None = None,
    politica: PoliticaDesempate = PoliticaDesempate.AMBIGUO,
) -> ResultadoTransmision:
    """Ejecuta la cadena completa de transmisión de un mensaje."""
    n = mat.validar_longitud(n)
    p = mat.validar_probabilidad(p)
    politica = PoliticaDesempate(politica)
    semilla, rng = crear_generador(semilla)

    bits = mat.texto_a_bits(texto)
    codificados = codificar(bits, n)
    res_canal = CanalBSC(p, rng).transmitir(codificados)
    res_dec = decodificar(res_canal.recibidos, n, politica, rng)
    return ResultadoTransmision(
        mensaje_original=texto,
        n=n,
        p=p,
        semilla=semilla,
        politica=politica,
        bits_originales=bits,
        bits_codificados=codificados,
        canal=res_canal,
        decodificacion=res_dec,
    )


# ---------------------------------------------------------------------------
# Simulación Monte Carlo de la tasa de error de bit (BER)
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class ResultadoMonteCarlo:
    n: int
    p: float
    num_bits: int  # bits de información simulados
    errores_canal: int  # bits invertidos por el canal (de num_bits * n)
    errores_residuales: int  # bits de información decididos incorrectamente
    ambiguos: int  # bits sin decidir (solo con política AMBIGUO)

    @property
    def ber_canal(self) -> float:
        """BER observada del canal (antes de decodificar)."""
        return self.errores_canal / (self.num_bits * self.n)

    @property
    def ber_residual(self) -> float:
        """BER observada después de decodificar."""
        return self.errores_residuales / self.num_bits

    @property
    def intervalo_95(self) -> tuple[float, float]:
        return mat.intervalo_wilson(self.errores_residuales, self.num_bits)


def simular_ber(
    n: int,
    p: float,
    num_bits: int,
    semilla: int | None = None,
    politica: PoliticaDesempate = PoliticaDesempate.ALEATORIO,
    generador: np.random.Generator | None = None,
) -> ResultadoMonteCarlo:
    """Estima la BER residual transmitiendo num_bits bits aleatorios equiprobables.

    Usa exactamente el mismo codificador, canal y decodificador que la
    transmisión de mensajes. Por defecto los empates se resuelven al azar, que es
    la política para la que vale la fórmula teórica de n par.
    """
    if num_bits <= 0:
        raise ValueError("num_bits debe ser positivo.")
    n = mat.validar_longitud(n)
    p = mat.validar_probabilidad(p)
    rng = generador if generador is not None else crear_generador(semilla)[1]

    bits = rng.integers(0, 2, size=num_bits, dtype=np.uint8)
    res_canal = CanalBSC(p, rng).transmitir(codificar(bits, n))
    res_dec = decodificar(res_canal.recibidos, n, politica, rng)
    incorrectos = (~res_dec.ambiguos) & (res_dec.bits != bits.astype(np.int8))
    return ResultadoMonteCarlo(
        n=n,
        p=p,
        num_bits=int(num_bits),
        errores_canal=res_canal.num_errores,
        errores_residuales=int(incorrectos.sum()),
        ambiguos=res_dec.num_ambiguos,
    )

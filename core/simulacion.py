"""Transmisión de extremo a extremo y experimentos repetidos (Monte Carlo).

Flujo con código (escenario B):
    texto -> bits UTF-8 -> codificador (repetición n) -> BSC(p) -> decodificador -> bits -> texto
Flujo sin código (escenario A):
    texto -> bits UTF-8 -> BSC(p) -> bits -> texto
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
from core.decodificador import BIT_AMBIGUO, PoliticaDesempate, ResultadoDecodificacion, decodificar
from core.metricas import MetricasEsquema, comparar_bits, intervalo_wilson

VERSION_ESQUEMA = 2


class EstadoTransmision(str, Enum):
    EXITO = "exito"  # mensaje recuperado idéntico al original
    ERROR = "error"  # quedan bits incorrectos (el mensaje no es el original)
    AMBIGUO = "ambiguo"  # quedaron bits sin decidir: no se reconstruye el mensaje

    @property
    def etiqueta(self) -> str:
        return {
            EstadoTransmision.EXITO: "Recuperado correctamente",
            EstadoTransmision.ERROR: "Recuperación fallida",
            EstadoTransmision.AMBIGUO: "Ambiguo (no recuperable)",
        }[self]


def nueva_semilla() -> int:
    """Semilla aleatoria de 31 bits; se registra para poder repetir el experimento."""
    return random.SystemRandom().randrange(2**31)


def crear_generador(semilla: int | None) -> tuple[int, np.random.Generator]:
    """Devuelve (semilla_usada, generador). Si semilla es None se genera una."""
    if semilla is None:
        semilla = nueva_semilla()
    if isinstance(semilla, bool) or not isinstance(semilla, int) or semilla < 0:
        raise ValueError("La semilla debe ser un entero no negativo.")
    return semilla, np.random.default_rng(semilla)


@dataclass(frozen=True)
class TextoRecuperado:
    """Resultado de convertir bits recuperados en texto, sin reemplazos silenciosos."""

    texto: str | None  # None si hay bits ambiguos o los bytes no son UTF-8 válido
    bytes_hex: str | None  # bytes recibidos en hexadecimal (None si hay ambigüedad)
    utf8_valido: bool | None  # None si no se pudo formar la secuencia de bytes

    @property
    def vista_previa(self) -> str | None:
        """Representación aproximada con U+FFFD; usar SOLO rotulada como no válida."""
        if self.bytes_hex is None:
            return None
        return bytes.fromhex(self.bytes_hex).decode("utf-8", errors="replace")


def recuperar_texto(bits) -> TextoRecuperado:
    bits = np.asarray(bits)
    if (bits == BIT_AMBIGUO).any():
        return TextoRecuperado(texto=None, bytes_hex=None, utf8_valido=None)
    datos = mat.bits_a_bytes(bits.astype(np.uint8))
    try:
        return TextoRecuperado(texto=datos.decode("utf-8"), bytes_hex=datos.hex(), utf8_valido=True)
    except UnicodeDecodeError:
        return TextoRecuperado(texto=None, bytes_hex=datos.hex(), utf8_valido=False)


@dataclass
class ResultadoTransmision:
    """Una transmisión del mismo mensaje con código (B) y sin código (A)."""

    mensaje_original: str
    n: int
    p: float
    semilla: int
    politica: PoliticaDesempate
    bits_originales: np.ndarray
    bits_codificados: np.ndarray
    canal: ResultadoCanal  # escenario B: palabra de código por el BSC
    decodificacion: ResultadoDecodificacion
    sin_codigo: ResultadoCanal  # escenario A: bits originales por el BSC
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    fecha_hora: str = field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))

    def __post_init__(self) -> None:
        self.politica = PoliticaDesempate(self.politica)

    # --- escenario B (con código) -------------------------------------------
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
        """Bloques alterados por el canal (dato del simulador, el receptor no lo conoce)."""
        if self.bits_originales.size == 0:
            return 0
        return int(self.canal.mascara_errores.reshape(-1, self.n).any(axis=1).sum())

    @property
    def bloques_corregidos(self) -> int:
        """Bloques alterados cuyo bit se decodificó correctamente (dato del simulador)."""
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
    def recuperado(self) -> TextoRecuperado:
        return recuperar_texto(self.decodificacion.bits)

    @property
    def mensaje_recuperado(self) -> str | None:
        """Texto reconstruido, o None si hay ambigüedad o los bytes no son UTF-8 válido."""
        return self.recuperado.texto

    @property
    def utf8_valido(self) -> bool | None:
        return self.recuperado.utf8_valido

    # --- escenario A (sin código) -------------------------------------------
    @property
    def recuperado_sin_codigo(self) -> TextoRecuperado:
        return recuperar_texto(self.sin_codigo.recibidos)

    # --- métricas comparables ------------------------------------------------
    @property
    def metricas_con_codigo(self) -> MetricasEsquema:
        return MetricasEsquema(
            nombre=f"Repetición n = {self.n}",
            bits_utiles=int(self.bits_originales.size),
            bits_transmitidos=int(self.bits_codificados.size),
            errores_introducidos=self.errores_introducidos,
            errores_residuales=self.errores_residuales,
            ambiguos=self.ambiguedades,
        )

    @property
    def metricas_sin_codigo(self) -> MetricasEsquema:
        errores = self.sin_codigo.num_errores
        return MetricasEsquema(
            nombre="Sin código",
            bits_utiles=int(self.bits_originales.size),
            bits_transmitidos=int(self.bits_originales.size),
            errores_introducidos=errores,
            errores_residuales=errores,  # sin código, todo error del canal queda en el mensaje
        )

    # --- persistencia --------------------------------------------------------
    def a_registro(self) -> dict:
        """Diccionario serializable a JSON con los datos del experimento."""
        rec = self.recuperado
        decodificados = "".join("?" if b == BIT_AMBIGUO else str(int(b)) for b in self.decodificacion.bits.tolist())
        return {
            "version_esquema": VERSION_ESQUEMA,
            "id": self.id,
            "fecha_hora": self.fecha_hora,
            "mensaje_original": self.mensaje_original,
            "longitud_codigo": self.n,
            "probabilidad_error": self.p,
            "semilla": self.semilla,
            "politica_desempate": self.politica.value,
            "bits_originales": mat.bits_a_cadena(self.bits_originales),
            "bits_codificados": mat.bits_a_cadena(self.bits_codificados),
            "bits_recibidos": mat.bits_a_cadena(self.canal.recibidos),
            "bits_decodificados": decodificados,
            "posiciones_alteradas": self.canal.posiciones_alteradas.tolist(),
            "errores_introducidos": self.errores_introducidos,
            "proporcion_errores_observada": self.canal.proporcion_errores,
            "bloques_detectados": self.decodificacion.num_bloques_detectados,
            "errores_residuales": self.errores_residuales,
            "empates": self.decodificacion.num_empates,
            "ambiguedades": self.ambiguedades,
            "mensaje_recuperado": rec.texto,
            "utf8_valido": rec.utf8_valido,
            "resultado": self.estado.value,
            "tasa_codigo": mat.tasa_codigo(self.n),
            "distancia_minima": mat.distancia_minima(self.n),
            "capacidad_correccion": mat.capacidad_correccion(self.n),
            "capacidad_canal": mat.capacidad_bsc(self.p),
            "probabilidad_error_bit_teorica": mat.probabilidad_error_bit(self.n, self.p),
            "sin_codigo": self.metricas_sin_codigo.a_diccionario(),
        }


def transmitir_mensaje(
    texto: str,
    n: int,
    p: float,
    semilla: int | None = None,
    politica: PoliticaDesempate = PoliticaDesempate.AMBIGUO,
) -> ResultadoTransmision:
    """Transmite el mensaje con código (B) y sin código (A) por el mismo BSC(p)."""
    n = mat.validar_longitud(n)
    p = mat.validar_probabilidad(p)
    politica = PoliticaDesempate(politica)
    semilla, rng = crear_generador(semilla)

    bits = mat.texto_a_bits(texto)
    codificados = codificar(bits, n)
    canal = CanalBSC(p, rng)
    res_canal = canal.transmitir(codificados)
    res_dec = decodificar(res_canal.recibidos, n, politica, rng)
    res_sin_codigo = canal.transmitir(bits)
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
        sin_codigo=res_sin_codigo,
    )


# ---------------------------------------------------------------------------
# Experimentos repetidos: con y sin código
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class ResultadoExperimento:
    """Totales de `ensayos` mensajes aleatorios de `bits_por_ensayo` bits."""

    n: int
    p: float
    ensayos: int
    bits_por_ensayo: int
    semilla: int
    politica: PoliticaDesempate
    sin_codigo: MetricasEsquema
    con_codigo: MetricasEsquema
    mensajes_ok_sin_codigo: int
    mensajes_ok_con_codigo: int

    @property
    def bits_totales(self) -> int:
        return self.ensayos * self.bits_por_ensayo

    @property
    def intervalo_ber_con_codigo(self) -> tuple[float, float]:
        return intervalo_wilson(self.con_codigo.errores_residuales, self.bits_totales)

    @property
    def intervalo_ber_sin_codigo(self) -> tuple[float, float]:
        return intervalo_wilson(self.sin_codigo.errores_residuales, self.bits_totales)

    # --- valores teóricos correspondientes ---------------------------------
    @property
    def ber_teorica_con_codigo(self) -> float:
        """Errores confirmados esperados por bit. Con política AMBIGUO, el empate no es error."""
        if self.politica is PoliticaDesempate.AMBIGUO:
            return mat.probabilidad_error_mayoria_estricta(self.n, self.p)
        return mat.probabilidad_error_bit(self.n, self.p)

    @property
    def ambiguedad_teorica(self) -> float:
        if self.politica is PoliticaDesempate.AMBIGUO:
            return mat.probabilidad_empate(self.n, self.p)
        return 0.0

    @property
    def exito_mensaje_teorico_con_codigo(self) -> float:
        return 1.0 - mat.probabilidad_fallo_mensaje(
            self.n, self.p, self.bits_por_ensayo,
            empates_como_fallo=self.politica is PoliticaDesempate.AMBIGUO,
        )

    @property
    def exito_mensaje_teorico_sin_codigo(self) -> float:
        return 1.0 - mat.probabilidad_fallo_sin_codigo(self.p, self.bits_por_ensayo)


def experimento_con_sin_codigo(
    n: int,
    p: float,
    bits_por_ensayo: int,
    ensayos: int,
    semilla: int | None = None,
    politica: PoliticaDesempate = PoliticaDesempate.ALEATORIO,
) -> ResultadoExperimento:
    """Repite `ensayos` veces: genera un mensaje aleatorio y lo envía sin código y con código.

    Ambos escenarios usan el mismo canal BSC(p) y la misma secuencia de mensajes,
    de modo que la comparación es justa.
    """
    n = mat.validar_longitud(n)
    p = mat.validar_probabilidad(p)
    politica = PoliticaDesempate(politica)
    if bits_por_ensayo <= 0 or ensayos <= 0:
        raise ValueError("bits_por_ensayo y ensayos deben ser positivos.")
    semilla, rng = crear_generador(semilla)
    canal = CanalBSC(p, rng)

    err_canal_a = err_canal_b = residuales_b = ambiguos_b = 0
    ok_a = ok_b = 0
    for _ in range(ensayos):
        mensaje = rng.integers(0, 2, size=bits_por_ensayo, dtype=np.uint8)

        # Escenario A: sin código
        rec_a = canal.transmitir(mensaje)
        err_canal_a += rec_a.num_errores
        ok_a += rec_a.num_errores == 0

        # Escenario B: con código de repetición
        rec_b = canal.transmitir(codificar(mensaje, n))
        dec_b = decodificar(rec_b.recibidos, n, politica, rng)
        incorrectos, ambiguos = comparar_bits(mensaje, dec_b.bits)
        err_canal_b += rec_b.num_errores
        residuales_b += incorrectos
        ambiguos_b += ambiguos
        ok_b += incorrectos == 0 and ambiguos == 0

    total = ensayos * bits_por_ensayo
    return ResultadoExperimento(
        n=n, p=p, ensayos=ensayos, bits_por_ensayo=bits_por_ensayo, semilla=semilla, politica=politica,
        sin_codigo=MetricasEsquema("Sin código", total, total, err_canal_a, err_canal_a),
        con_codigo=MetricasEsquema(f"Repetición n = {n}", total, total * n, err_canal_b, residuales_b, ambiguos_b),
        mensajes_ok_sin_codigo=int(ok_a),
        mensajes_ok_con_codigo=int(ok_b),
    )


# ---------------------------------------------------------------------------
# Estimación de la BER residual para un punto (n, p)
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
        return intervalo_wilson(self.errores_residuales, self.num_bits)


def simular_ber(
    n: int,
    p: float,
    num_bits: int,
    semilla: int | None = None,
    politica: PoliticaDesempate = PoliticaDesempate.ALEATORIO,
    generador: np.random.Generator | None = None,
) -> ResultadoMonteCarlo:
    """Estima la BER residual transmitiendo num_bits bits aleatorios equiprobables.

    Usa el mismo codificador, canal y decodificador que la transmisión de
    mensajes. Por defecto los empates se resuelven al azar, la política para la
    que vale la fórmula teórica de n par.
    """
    if num_bits <= 0:
        raise ValueError("num_bits debe ser positivo.")
    n = mat.validar_longitud(n)
    p = mat.validar_probabilidad(p)
    rng = generador if generador is not None else crear_generador(semilla)[1]

    bits = rng.integers(0, 2, size=num_bits, dtype=np.uint8)
    res_canal = CanalBSC(p, rng).transmitir(codificar(bits, n))
    res_dec = decodificar(res_canal.recibidos, n, politica, rng)
    incorrectos, ambiguos = comparar_bits(bits, res_dec.bits)
    return ResultadoMonteCarlo(
        n=n,
        p=p,
        num_bits=int(num_bits),
        errores_canal=res_canal.num_errores,
        errores_residuales=incorrectos,
        ambiguos=ambiguos,
    )

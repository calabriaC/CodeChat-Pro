import itertools

import numpy as np
import pytest

from core.codificador import codificar
from core.decodificador import BIT_AMBIGUO, PoliticaDesempate, decodificar
from core.matematicas import capacidad_correccion


@pytest.mark.parametrize("n", range(1, 22))
def test_decodificacion_sin_errores(n):
    bits = np.array([0, 1, 1, 0, 1], dtype=np.uint8)
    res = decodificar(codificar(bits, n), n)
    assert np.array_equal(res.bits_resueltos(), bits)
    assert res.num_ambiguos == 0 and res.num_empates == 0


@pytest.mark.parametrize("n", range(1, 22))
def test_corrige_todos_los_patrones_hasta_t_errores(n):
    """Toda configuración de hasta t errores en un bloque se corrige."""
    t = capacidad_correccion(n)
    for bit in (0, 1):
        palabra = codificar([bit], n)
        for k in range(t + 1):
            # Para n grandes basta con muestrear patrones; para n <= 9, todos.
            patrones = itertools.combinations(range(n), k)
            for i, posiciones in enumerate(patrones):
                if i > 200:
                    break
                recibido = palabra.copy()
                recibido[list(posiciones)] ^= 1
                assert decodificar(recibido, n).bits.tolist() == [bit]


@pytest.mark.parametrize("n", [1, 3, 5, 7, 21])
def test_mas_de_la_mitad_de_errores_produce_error(n):
    """Con k > n/2 errores la mayoría elige el bit equivocado (impares)."""
    palabra = codificar([1], n)
    recibido = palabra.copy()
    recibido[: n // 2 + 1] ^= 1
    assert decodificar(recibido, n).bits.tolist() == [0]


def test_t_mas_uno_errores_en_n_par_produce_empate():
    # n = 4, t = 1: con 2 errores hay empate (no es corregible).
    recibido = np.array([1, 1, 0, 0], dtype=np.uint8)
    res = decodificar(recibido, 4)
    assert res.empates.tolist() == [True]
    assert res.bits.tolist() == [BIT_AMBIGUO]


def test_deteccion_de_empates_y_politica_ambiguo_por_defecto():
    recibido = np.array([1, 0, 1, 1, 0, 0, 1, 1], dtype=np.uint8)  # n=4: [1,0,1,1] y [0,0,1,1]
    res = decodificar(recibido, 4)
    assert res.politica is PoliticaDesempate.AMBIGUO
    assert res.bits.tolist() == [1, BIT_AMBIGUO]
    assert res.num_empates == 1 and res.num_ambiguos == 1
    with pytest.raises(ValueError):
        res.bits_resueltos()


@pytest.mark.parametrize(
    "politica, esperado",
    [(PoliticaDesempate.CERO, 0), (PoliticaDesempate.UNO, 1)],
)
def test_politicas_deterministas(politica, esperado):
    res = decodificar([1, 0, 0, 1], 4, politica)
    assert res.bits.tolist() == [esperado]
    assert res.num_empates == 1 and res.num_ambiguos == 0


def test_politica_aleatoria_es_reproducible_y_equilibrada():
    empates = np.tile([1, 0], 10_000)  # 10 000 bloques empatados de n = 2
    a = decodificar(empates, 2, PoliticaDesempate.ALEATORIO, np.random.default_rng(7))
    b = decodificar(empates, 2, PoliticaDesempate.ALEATORIO, np.random.default_rng(7))
    assert np.array_equal(a.bits, b.bits)
    assert a.num_ambiguos == 0 and a.num_empates == 10_000
    assert 0.47 < a.bits.mean() < 0.53


def test_n_uno_no_corrige():
    assert decodificar([0, 1, 1], 1).bits.tolist() == [0, 1, 1]


def test_longitud_no_multiplo_de_n():
    with pytest.raises(ValueError):
        decodificar([1, 1, 1, 0], 3)


def test_ejemplo_manual_conteo_por_bloque():
    """111 000 111 con un error en cada bloque: 101 010 110 -> se recupera 101."""
    res = decodificar([1, 0, 1, 0, 1, 0, 1, 1, 0], 3)
    assert res.votos_uno.tolist() == [2, 1, 2]
    assert res.votos_cero.tolist() == [1, 2, 1]
    assert res.bits.tolist() == [1, 0, 1]
    assert res.bloques_no_codigo.tolist() == [True, True, True]  # el receptor detecta los 3 bloques


def test_dos_errores_en_n3_engañan_al_decodificador():
    """Con 2 > t = 1 errores el bloque 111 llega como 001: se decide 0 (error residual)."""
    res = decodificar([0, 0, 1], 3)
    assert res.bits.tolist() == [0]
    assert res.bloques_no_codigo.tolist() == [True]  # se detecta, pero se corrige mal


def test_n_errores_convierten_en_otra_palabra_y_no_se_detectan():
    """Si se invierten los n bits, llega la otra palabra código: ni se detecta ni se corrige."""
    res = decodificar([0, 0, 0, 0, 0], 5)
    assert res.bits.tolist() == [0]
    assert res.bloques_no_codigo.tolist() == [False]


@pytest.mark.parametrize("n", [2, 3, 4, 5, 6, 7])
def test_deteccion_garantizada_hasta_n_menos_1_errores(n):
    palabra = codificar([1], n)
    for k in range(1, n):
        recibido = palabra.copy()
        recibido[:k] ^= 1
        assert decodificar(recibido, n).bloques_no_codigo.tolist() == [True]

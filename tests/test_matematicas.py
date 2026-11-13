import math

import pytest

from core import matematicas as mat
from core.decodificador import PoliticaDesempate
from core.simulador import simular_ber


@pytest.mark.parametrize("n", range(1, 22))
def test_parametros_del_codigo(n):
    assert mat.distancia_minima(n) == n
    assert mat.capacidad_correccion(n) == (n - 1) // 2
    assert mat.capacidad_deteccion(n) == n - 1
    assert mat.tasa_codigo(n) == pytest.approx(1 / n)
    assert mat.redundancia(n) == n - 1


def test_capacidad_correccion_valores_concretos():
    assert [mat.capacidad_correccion(n) for n in (1, 2, 3, 4, 5, 7, 21)] == [0, 0, 1, 1, 2, 3, 10]


def test_entropia_casos_limite():
    assert mat.entropia_binaria(0.0) == 0.0
    assert mat.entropia_binaria(1.0) == 0.0
    assert mat.entropia_binaria(0.5) == 1.0


def test_capacidad_bsc():
    assert mat.capacidad_bsc(0.0) == 1.0
    assert mat.capacidad_bsc(0.5) == 0.0
    assert mat.capacidad_bsc(0.1) == pytest.approx(0.531004406, abs=1e-9)
    # H2(0.11) = 0.350287 + 0.149629 = 0.499916  ->  C ~ 0.500084
    assert mat.capacidad_bsc(0.11) == pytest.approx(0.500084, abs=1e-6)
    # Simetría H(p) = H(1-p)
    assert mat.entropia_binaria(0.2) == pytest.approx(mat.entropia_binaria(0.8))


def test_probabilidad_error_valores_calculados_a_mano():
    # n = 3: 3 p^2 (1-p) + p^3
    assert mat.probabilidad_error_bit(3, 0.1) == pytest.approx(0.028)
    # n = 5: 10 p^3 (1-p)^2 + 5 p^4 (1-p) + p^5
    assert mat.probabilidad_error_bit(5, 0.1) == pytest.approx(0.00856)
    # n = 4 con desempate aleatorio: 4p^3(1-p) + p^4 + 0.5 * 6 p^2 (1-p)^2
    assert mat.probabilidad_error_bit(4, 0.1) == pytest.approx(0.0037 + 0.0243)


@pytest.mark.parametrize("p", [0.0, 0.01, 0.1, 0.25, 0.5])
def test_casos_limite_probabilidad_error(p):
    assert mat.probabilidad_error_bit(1, p) == pytest.approx(p)
    assert mat.probabilidad_error_bit(2, p) == pytest.approx(p)  # n = 2 no mejora a n = 1
    assert mat.probabilidad_error_bit(7, 0.5) == pytest.approx(0.5)
    assert mat.probabilidad_error_bit(7, 0.0) == 0.0


@pytest.mark.parametrize("m", range(1, 11))
@pytest.mark.parametrize("p", [0.05, 0.2, 0.4])
def test_codigo_par_equivale_al_impar_anterior(m, p):
    """Con desempate aleatorio, P_e(2m) = P_e(2m - 1): el bit extra no ayuda."""
    assert mat.probabilidad_error_bit(2 * m, p) == pytest.approx(mat.probabilidad_error_bit(2 * m - 1, p))


@pytest.mark.parametrize("p", [0.01, 0.1, 0.3])
def test_error_decrece_con_n_impar(p):
    valores = [mat.probabilidad_error_bit(n, p) for n in range(1, 22, 2)]
    assert all(a > b for a, b in zip(valores, valores[1:]))


def test_probabilidades_suman_uno():
    n, p = 6, 0.3
    total = math.fsum(math.comb(n, k) * p**k * (1 - p) ** (n - k) for k in range(n + 1))
    assert total == pytest.approx(1.0)
    acierto_estricto = 1 - mat.probabilidad_error_mayoria_estricta(n, p) - mat.probabilidad_empate(n, p)
    assert 0 < acierto_estricto < 1


def test_probabilidad_fallo_mensaje():
    q = mat.probabilidad_error_bit(3, 0.1)
    assert mat.probabilidad_fallo_mensaje(3, 0.1, 40) == pytest.approx(1 - (1 - q) ** 40)
    assert mat.probabilidad_fallo_mensaje(3, 0.0, 40) == 0.0
    assert mat.probabilidad_fallo_mensaje(3, 0.1, 0) == 0.0
    # Con política "ambiguo", el empate cuenta como fallo: la probabilidad aumenta.
    assert mat.probabilidad_fallo_mensaje(4, 0.1, 8, empates_como_fallo=True) > mat.probabilidad_fallo_mensaje(
        4, 0.1, 8
    )


def test_intervalo_wilson():
    bajo, alto = mat.intervalo_wilson(50, 100)
    assert bajo < 0.5 < alto
    assert mat.intervalo_wilson(0, 1000)[0] == 0.0


@pytest.mark.parametrize("n", [1, 2, 3, 4, 5, 7])
@pytest.mark.parametrize("p", [0.05, 0.2])
def test_monte_carlo_coincide_con_la_teoria(n, p):
    """La BER residual simulada debe caer cerca del valor teórico (±5 sigmas)."""
    num_bits = 200_000
    res = simular_ber(n, p, num_bits, semilla=2026, politica=PoliticaDesempate.ALEATORIO)
    teorico = mat.probabilidad_error_bit(n, p)
    sigma = math.sqrt(teorico * (1 - teorico) / num_bits)
    assert abs(res.ber_residual - teorico) < 5 * sigma + 1e-12
    # La BER del canal es otra magnitud: estima p, no P_e.
    assert abs(res.ber_canal - p) < 5 * math.sqrt(p * (1 - p) / (num_bits * n))

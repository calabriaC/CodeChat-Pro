import numpy as np
import pytest

from core.canal_bsc import CanalBSC


def test_canal_sin_ruido_no_altera():
    bits = np.random.default_rng(1).integers(0, 2, 10_000, dtype=np.uint8)
    res = CanalBSC(0.0, np.random.default_rng(2)).transmitir(bits)
    assert np.array_equal(res.recibidos, bits)
    assert res.num_errores == 0 and res.proporcion_errores == 0.0
    assert res.posiciones_alteradas.size == 0


def test_canal_p_medio_invierte_la_mitad():
    bits = np.zeros(200_000, dtype=np.uint8)
    res = CanalBSC(0.5, np.random.default_rng(3)).transmitir(bits)
    # Desviación típica = sqrt(0.25/200000) ~ 0.0011; tolerancia de ~5 sigmas.
    assert abs(res.proporcion_errores - 0.5) < 0.006


@pytest.mark.parametrize("p", [0.01, 0.1, 0.3])
def test_proporcion_observada_cercana_a_p(p):
    total = 200_000
    res = CanalBSC(p, np.random.default_rng(4)).transmitir(np.ones(total, dtype=np.uint8))
    sigma = (p * (1 - p) / total) ** 0.5
    assert abs(res.proporcion_errores - p) < 5 * sigma


def test_posiciones_alteradas_coinciden_con_diferencias():
    bits = np.random.default_rng(5).integers(0, 2, 5_000, dtype=np.uint8)
    res = CanalBSC(0.2, np.random.default_rng(6)).transmitir(bits)
    assert np.array_equal(res.posiciones_alteradas, np.flatnonzero(res.recibidos != bits))
    assert res.num_errores == res.posiciones_alteradas.size


def test_semilla_reproduce_el_experimento():
    bits = np.ones(1_000, dtype=np.uint8)
    a = CanalBSC(0.1, np.random.default_rng(42)).transmitir(bits)
    b = CanalBSC(0.1, np.random.default_rng(42)).transmitir(bits)
    assert np.array_equal(a.recibidos, b.recibidos)


def test_no_modifica_la_entrada():
    bits = np.ones(100, dtype=np.uint8)
    CanalBSC(0.5, np.random.default_rng(0)).transmitir(bits)
    assert bits.all()


@pytest.mark.parametrize("p", [-0.1, 0.51, 1.0, float("nan")])
def test_probabilidad_fuera_de_rango(p):
    with pytest.raises(ValueError):
        CanalBSC(p)

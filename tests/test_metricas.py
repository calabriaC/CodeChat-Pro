import pytest

from core.decodificador import BIT_AMBIGUO
from core.metricas import MetricasEsquema, comparar_bits, intervalo_wilson


def test_comparar_bits_separa_errores_y_ambiguos():
    assert comparar_bits([0, 1, 1, 0], [0, 1, 1, 0]) == (0, 0)
    assert comparar_bits([0, 1, 1, 0], [1, 1, BIT_AMBIGUO, 0]) == (1, 1)
    with pytest.raises(ValueError):
        comparar_bits([0, 1], [0])


def test_metricas_esquema_calculadas_a_mano():
    # 100 bits útiles con n = 3: 300 transmitidos, 30 invertidos, 2 erróneos, 1 ambiguo.
    m = MetricasEsquema("n=3", bits_utiles=100, bits_transmitidos=300, errores_introducidos=30,
                        errores_residuales=2, ambiguos=1)
    assert m.tasa == pytest.approx(1 / 3)
    assert m.redundancia_por_bit == pytest.approx(2.0)
    assert m.ber_canal == pytest.approx(0.1)
    assert m.ber_residual == pytest.approx(0.02)
    assert m.bits_recuperados == 97
    assert m.porcentaje_recuperacion == pytest.approx(97.0)
    assert not m.mensaje_integro


def test_intervalo_wilson():
    bajo, alto = intervalo_wilson(50, 100)
    assert bajo < 0.5 < alto
    assert intervalo_wilson(0, 1000)[0] == 0.0
    assert intervalo_wilson(1000, 1000)[1] == 1.0
    with pytest.raises(ValueError):
        intervalo_wilson(5, 0)

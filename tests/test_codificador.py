import numpy as np
import pytest

from core.codificador import codificar, codificar_texto
from core.matematicas import bits_a_texto, texto_a_bits


@pytest.mark.parametrize("n", range(1, 22))
def test_cada_bit_se_repite_n_veces(n):
    bits = np.array([1, 0, 1, 1, 0], dtype=np.uint8)
    codificados = codificar(bits, n)
    assert codificados.size == bits.size * n
    assert np.array_equal(codificados.reshape(-1, n), np.repeat(bits[:, None], n, axis=1))


def test_ejemplos_del_enunciado():
    assert codificar([1], 5).tolist() == [1, 1, 1, 1, 1]
    assert codificar([1], 4).tolist() == [1, 1, 1, 1]
    assert codificar([1, 0], 3).tolist() == [1, 1, 1, 0, 0, 0]


def test_n_igual_a_uno_no_modifica():
    bits = np.array([0, 1, 1, 0], dtype=np.uint8)
    assert np.array_equal(codificar(bits, 1), bits)


@pytest.mark.parametrize("n", [0, 22, -3])
def test_longitud_fuera_de_rango(n):
    with pytest.raises(ValueError):
        codificar([1, 0], n)


@pytest.mark.parametrize("n", [3.0, "3", True])
def test_longitud_no_entera(n):
    with pytest.raises(TypeError):
        codificar([1, 0], n)


def test_bits_invalidos():
    with pytest.raises(ValueError):
        codificar([0, 2, 1], 3)


@pytest.mark.parametrize("texto", ["Hola", "Teoría de Códigos ñ", "€ 😀 漢字", ""])
def test_conversion_utf8_ida_y_vuelta(texto):
    bits = texto_a_bits(texto)
    assert bits.size == 8 * len(texto.encode("utf-8"))
    assert bits_a_texto(bits) == texto


def test_conversion_utf8_msb_primero():
    # 'A' = 0x41 = 01000001
    assert texto_a_bits("A").tolist() == [0, 1, 0, 0, 0, 0, 0, 1]


def test_codificar_texto():
    bits, cod = codificar_texto("Hi", 3)
    assert bits.size == 16 and cod.size == 48

import json

import pytest

from core.decodificador import PoliticaDesempate
from core.simulador import EstadoTransmision, transmitir_mensaje


def test_canal_sin_ruido_recupera_el_mensaje():
    res = transmitir_mensaje("Teoría de Códigos 😀", 3, 0.0, semilla=1)
    assert res.estado is EstadoTransmision.EXITO
    assert res.mensaje_recuperado == "Teoría de Códigos 😀"
    assert res.errores_introducidos == 0 and res.errores_residuales == 0


def test_misma_semilla_mismo_resultado():
    a = transmitir_mensaje("Hola mundo", 5, 0.2, semilla=123)
    b = transmitir_mensaje("Hola mundo", 5, 0.2, semilla=123)
    assert a.canal.posiciones_alteradas.tolist() == b.canal.posiciones_alteradas.tolist()
    assert a.mensaje_recuperado == b.mensaje_recuperado


def test_semilla_generada_se_registra():
    res = transmitir_mensaje("x", 3, 0.1)
    assert isinstance(res.semilla, int) and res.semilla >= 0
    repetido = transmitir_mensaje("x", 3, 0.1, semilla=res.semilla)
    assert repetido.canal.recibidos.tolist() == res.canal.recibidos.tolist()


def test_ambiguedad_no_inventa_mensaje():
    # Con n = 2 y p = 0.5 es prácticamente seguro que aparezca algún empate.
    res = transmitir_mensaje("Mensaje largo para forzar empates", 2, 0.5, semilla=9)
    assert res.ambiguedades > 0
    assert res.estado is EstadoTransmision.AMBIGUO
    assert res.mensaje_recuperado is None
    assert res.utf8_valido is None


def test_errores_residuales_con_n_uno():
    res = transmitir_mensaje("abcdefghij" * 5, 1, 0.3, semilla=4)
    assert res.errores_residuales == res.errores_introducidos > 0
    assert res.estado is EstadoTransmision.ERROR
    assert res.mensaje_recuperado is not None


def test_politica_aleatoria_no_deja_ambiguos():
    res = transmitir_mensaje("abc", 4, 0.4, semilla=3, politica=PoliticaDesempate.ALEATORIO)
    assert res.ambiguedades == 0
    assert res.mensaje_recuperado is not None


def test_contabilidad_de_bloques():
    res = transmitir_mensaje("Probando bloques", 5, 0.15, semilla=8)
    assert res.bloques_con_errores > 0
    assert res.bloques_corregidos <= res.bloques_con_errores
    assert res.bloques_con_errores - res.bloques_corregidos == res.errores_residuales + res.ambiguedades


def test_registro_es_serializable_y_completo():
    registro = transmitir_mensaje("Hola", 3, 0.1, semilla=5).a_registro()
    json.dumps(registro)  # no debe fallar
    for campo in (
        "id", "fecha_hora", "mensaje_original", "longitud_codigo", "probabilidad_error", "semilla",
        "bits_transmitidos", "bits_recibidos", "errores_introducidos", "errores_residuales",
        "ambiguedades", "mensaje_recuperado", "resultado", "tasa_codigo", "distancia_minima",
        "capacidad_canal",
    ):
        assert campo in registro
    assert registro["tasa_codigo"] == pytest.approx(1 / 3)
    assert registro["distancia_minima"] == 3
    assert len(registro["bits_transmitidos"]) == 3 * 32


def test_parametros_invalidos():
    with pytest.raises(ValueError):
        transmitir_mensaje("x", 3, 0.7)
    with pytest.raises(ValueError):
        transmitir_mensaje("x", 0, 0.1)

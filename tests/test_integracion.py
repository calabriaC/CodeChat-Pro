"""Pruebas de extremo a extremo: mensaje -> codificador -> BSC -> decodificador -> métrica."""

import json
import math

import pytest

from core import matematicas as mat
from core.decodificador import PoliticaDesempate
from core.simulacion import EstadoTransmision, experimento_con_sin_codigo, transmitir_mensaje


def test_canal_sin_ruido_recupera_el_mensaje():
    res = transmitir_mensaje("Teoría de Códigos 😀", 3, 0.0, semilla=1)
    assert res.estado is EstadoTransmision.EXITO
    assert res.mensaje_recuperado == "Teoría de Códigos 😀"
    assert res.errores_introducidos == 0 and res.errores_residuales == 0
    assert res.sin_codigo.num_errores == 0
    assert res.recuperado_sin_codigo.texto == "Teoría de Códigos 😀"


def test_misma_semilla_mismo_resultado():
    a = transmitir_mensaje("Hola mundo", 5, 0.2, semilla=123)
    b = transmitir_mensaje("Hola mundo", 5, 0.2, semilla=123)
    assert a.canal.posiciones_alteradas.tolist() == b.canal.posiciones_alteradas.tolist()
    assert a.sin_codigo.posiciones_alteradas.tolist() == b.sin_codigo.posiciones_alteradas.tolist()
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


def test_utf8_invalido_no_se_reemplaza_en_silencio():
    # 'ñ' = C3 B1. Si el canal invierte el bit más significativo de B1 -> 31, la
    # secuencia C3 31 deja de ser UTF-8 válido. Se busca una semilla que lo produzca.
    for semilla in range(500):
        res = transmitir_mensaje("ñññññ", 1, 0.2, semilla=semilla)
        if res.utf8_valido is False:
            break
    else:
        pytest.fail("No se encontró una transmisión con UTF-8 inválido")
    assert res.estado is EstadoTransmision.ERROR
    assert res.mensaje_recuperado is None  # no hay texto "recuperado" inventado
    assert res.recuperado.bytes_hex  # pero sí se conservan los bytes recibidos
    assert "�" in res.recuperado.vista_previa
    assert res.a_registro()["mensaje_recuperado"] is None


def test_n_uno_equivale_a_no_codificar():
    res = transmitir_mensaje("abcdefghij" * 5, 1, 0.3, semilla=4)
    assert res.errores_residuales == res.errores_introducidos > 0
    assert res.estado is EstadoTransmision.ERROR


def test_politica_aleatoria_no_deja_ambiguos():
    res = transmitir_mensaje("abc", 4, 0.4, semilla=3, politica=PoliticaDesempate.ALEATORIO)
    assert res.ambiguedades == 0


def test_contabilidad_de_bloques():
    res = transmitir_mensaje("Probando bloques", 5, 0.15, semilla=8)
    assert res.bloques_con_errores > 0
    assert res.bloques_corregidos <= res.bloques_con_errores
    assert res.bloques_con_errores - res.bloques_corregidos == res.errores_residuales + res.ambiguedades
    # El receptor detecta todo bloque alterado que no quedó convertido en otra palabra código.
    assert res.decodificacion.num_bloques_detectados <= res.bloques_con_errores


def test_metricas_con_y_sin_codigo_de_una_transmision():
    res = transmitir_mensaje("Hola", 3, 0.1, semilla=5)
    con, sin = res.metricas_con_codigo, res.metricas_sin_codigo
    assert con.bits_utiles == sin.bits_utiles == 32
    assert con.bits_transmitidos == 96 and sin.bits_transmitidos == 32
    assert con.tasa == pytest.approx(1 / 3) and sin.tasa == 1.0
    assert sin.errores_residuales == sin.errores_introducidos


def test_registro_es_serializable_y_completo():
    registro = transmitir_mensaje("Hola", 3, 0.1, semilla=5).a_registro()
    json.dumps(registro)  # no debe fallar
    for campo in (
        "id", "fecha_hora", "mensaje_original", "longitud_codigo", "probabilidad_error", "semilla",
        "politica_desempate", "bits_originales", "bits_codificados", "bits_recibidos", "bits_decodificados",
        "errores_introducidos", "errores_residuales", "ambiguedades", "tasa_codigo", "capacidad_canal",
        "resultado", "sin_codigo",
    ):
        assert campo in registro
    assert registro["tasa_codigo"] == pytest.approx(1 / 3)
    assert registro["distancia_minima"] == 3
    assert len(registro["bits_originales"]) == 32
    assert len(registro["bits_codificados"]) == len(registro["bits_recibidos"]) == 96
    assert len(registro["bits_decodificados"]) == 32


def test_bits_decodificados_marcan_ambiguos():
    registro = transmitir_mensaje("Mensaje largo para forzar empates", 2, 0.5, semilla=9).a_registro()
    assert "?" in registro["bits_decodificados"]
    assert registro["bits_decodificados"].count("?") == registro["ambiguedades"]


def test_parametros_invalidos():
    with pytest.raises(ValueError):
        transmitir_mensaje("x", 3, 0.7)
    with pytest.raises(ValueError):
        transmitir_mensaje("x", 0, 0.1)


# --- experimentos repetidos con y sin código -----------------------------------
@pytest.mark.parametrize("n", [3, 5, 7])
def test_experimento_con_codigo_mejora_y_coincide_con_la_teoria(n):
    p = 0.1
    exp = experimento_con_sin_codigo(n, p, bits_por_ensayo=100, ensayos=400, semilla=2026)
    total = exp.bits_totales
    # Sin código la BER residual estima p; con código estima P_e(n, p).
    sigma_a = math.sqrt(p * (1 - p) / total)
    assert abs(exp.sin_codigo.ber_residual - p) < 5 * sigma_a
    teo = exp.ber_teorica_con_codigo
    sigma_b = math.sqrt(teo * (1 - teo) / total)
    assert abs(exp.con_codigo.ber_residual - teo) < 5 * sigma_b
    # La codificación reduce la BER, a costa de transmitir n veces más bits.
    assert exp.con_codigo.ber_residual < exp.sin_codigo.ber_residual
    assert exp.con_codigo.bits_transmitidos == n * exp.sin_codigo.bits_transmitidos
    assert exp.mensajes_ok_con_codigo > exp.mensajes_ok_sin_codigo


def test_experimento_sin_ruido():
    exp = experimento_con_sin_codigo(3, 0.0, bits_por_ensayo=50, ensayos=20, semilla=1)
    assert exp.mensajes_ok_con_codigo == exp.mensajes_ok_sin_codigo == 20
    assert exp.con_codigo.ber_residual == exp.sin_codigo.ber_residual == 0.0


def test_experimento_n_par_distingue_ambiguos():
    amb = experimento_con_sin_codigo(4, 0.2, 100, 200, semilla=3, politica=PoliticaDesempate.AMBIGUO)
    ale = experimento_con_sin_codigo(4, 0.2, 100, 200, semilla=3, politica=PoliticaDesempate.ALEATORIO)
    assert amb.con_codigo.ambiguos > 0 and ale.con_codigo.ambiguos == 0
    total = amb.bits_totales
    sigma = math.sqrt(amb.ambiguedad_teorica * (1 - amb.ambiguedad_teorica) / total)
    assert abs(amb.con_codigo.ambiguos / total - amb.ambiguedad_teorica) < 5 * sigma
    assert amb.ber_teorica_con_codigo == pytest.approx(mat.probabilidad_error_mayoria_estricta(4, 0.2))
    assert ale.ber_teorica_con_codigo == pytest.approx(mat.probabilidad_error_bit(4, 0.2))


def test_exito_teorico_de_mensajes():
    exp = experimento_con_sin_codigo(3, 0.05, bits_por_ensayo=40, ensayos=300, semilla=11)
    assert exp.exito_mensaje_teorico_sin_codigo == pytest.approx(0.95**40)
    teo = exp.exito_mensaje_teorico_con_codigo
    obs = exp.mensajes_ok_con_codigo / exp.ensayos
    assert abs(obs - teo) < 5 * math.sqrt(teo * (1 - teo) / exp.ensayos)

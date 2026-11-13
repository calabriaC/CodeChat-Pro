import json

import pytest

from almacenamiento.gestor_json import ErrorHistorial, GestorHistorial
from core.simulador import transmitir_mensaje


@pytest.fixture
def gestor(tmp_path):
    return GestorHistorial(tmp_path / "data" / "historial.json")


def test_archivo_inexistente_devuelve_lista_vacia(gestor):
    assert gestor.cargar() == []
    assert gestor.aviso is None


def test_guardar_y_leer(gestor):
    registro = transmitir_mensaje("Hola ñandú", 5, 0.1, semilla=1).a_registro()
    gestor.agregar(registro)
    leidos = gestor.cargar()
    assert leidos == [registro]
    # El archivo es JSON válido y conserva caracteres UTF-8 legibles.
    texto = gestor.ruta.read_text(encoding="utf-8")
    assert "ñandú" in texto
    assert json.loads(texto)[0]["id"] == registro["id"]


def test_no_quedan_temporales(gestor):
    for i in range(3):
        gestor.agregar(transmitir_mensaje(f"m{i}", 3, 0.1, semilla=i).a_registro())
    archivos = sorted(p.name for p in gestor.ruta.parent.iterdir())
    assert archivos == ["historial.json"]
    assert len(gestor.cargar()) == 3


def test_no_duplica_registros(gestor):
    registro = transmitir_mensaje("a", 3, 0.1, semilla=1).a_registro()
    gestor.agregar(registro)
    with pytest.raises(ErrorHistorial):
        gestor.agregar(registro)


def test_archivo_corrupto_se_respalda(gestor):
    gestor.ruta.parent.mkdir(parents=True)
    gestor.ruta.write_text('[{"id": "a", ', encoding="utf-8")
    assert gestor.cargar() == []
    assert gestor.aviso is not None
    respaldos = list(gestor.ruta.parent.glob("historial.corrupto-*.json"))
    assert len(respaldos) == 1
    # Después de recuperarse se puede seguir guardando.
    gestor.agregar(transmitir_mensaje("b", 3, 0.0, semilla=1).a_registro())
    assert len(gestor.cargar()) == 1


def test_filtrar_e_indicadores(gestor):
    registros = [
        transmitir_mensaje("hola", 3, 0.0, semilla=1).a_registro(),
        transmitir_mensaje("adiós", 5, 0.0, semilla=2).a_registro(),
        transmitir_mensaje("ruido" * 10, 1, 0.3, semilla=3).a_registro(),
    ]
    for r in registros:
        gestor.agregar(r)
    todos = gestor.cargar()
    assert len(GestorHistorial.filtrar(todos, texto="HOLA")) == 1
    assert len(GestorHistorial.filtrar(todos, n=5)) == 1
    assert len(GestorHistorial.filtrar(todos, resultado="exito")) == 2

    ind = GestorHistorial.indicadores(todos)
    assert ind["total"] == 3 and ind["exitosas"] == 2
    assert ind["errores_introducidos"] == sum(r["errores_introducidos"] for r in registros)
    assert ind["porcentaje_recuperados"] == pytest.approx(200 / 3)
    assert GestorHistorial.indicadores([])["porcentaje_recuperados"] is None


def test_exportar_y_eliminar(gestor, tmp_path):
    registro = transmitir_mensaje("x", 3, 0.0, semilla=1).a_registro()
    gestor.agregar(registro)
    destino = tmp_path / "export" / "exportado.json"
    GestorHistorial.exportar(gestor.cargar(), destino)
    assert json.loads(destino.read_text(encoding="utf-8"))[0]["id"] == registro["id"]
    assert gestor.eliminar(registro["id"]) is True
    assert gestor.eliminar(registro["id"]) is False
    assert gestor.cargar() == []

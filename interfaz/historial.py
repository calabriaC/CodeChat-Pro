"""Historial de experimentos: consulta, filtrado, detalle, eliminación y exportación JSON."""

from __future__ import annotations

import html
import json
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QHeaderView,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from almacenamiento.gestor_json import GestorHistorial
from core import matematicas as mat
from interfaz import estilos as e
from interfaz.componentes import Aviso, Panel, etiqueta, fila, pagina_desplazable

RESULTADOS = {"exito": ("Éxito", e.VERDE), "error": ("Con errores", e.ROJO), "ambiguo": ("Ambiguo", e.NARANJA)}
COLUMNAS = ["Fecha y hora", "Mensaje", "n", "p", "Semilla", "Errores canal", "Errores residuales",
            "Ambiguos", "Resultado"]


class DialogoDetalle(QDialog):
    def __init__(self, registro: dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Experimento {registro.get('id', '')[:8]}")
        self.resize(760, 600)
        lay = QVBoxLayout(self)
        texto = QPlainTextEdit(json.dumps(registro, ensure_ascii=False, indent=2))
        texto.setReadOnly(True)
        texto.setStyleSheet(f"font-family:{e.FUENTE_MONO}; font-size:9.5pt;")
        botones = QDialogButtonBox(QDialogButtonBox.Close)
        botones.rejected.connect(self.reject)
        lay.addWidget(texto)
        lay.addWidget(botones)


class PaginaHistorial(QWidget):
    historial_cambiado = Signal()

    def __init__(self, gestor: GestorHistorial, parent=None):
        super().__init__(parent)
        self.gestor = gestor
        self._registros: list[dict] = []
        self._filtrados: list[dict] = []

        area, lay = pagina_desplazable(
            "Historial de experimentos",
            f"Transmisiones guardadas localmente en {html.escape(str(gestor.ruta.name))}. "
            "Filtre, consulte el detalle completo de cada registro o exporte los resultados.",
        )
        raiz = QVBoxLayout(self)
        raiz.setContentsMargins(0, 0, 0, 0)
        raiz.addWidget(area)

        filtros = Panel()
        self.txt_buscar = QLineEdit()
        self.txt_buscar.setPlaceholderText("Buscar en mensaje original, recuperado o id…")
        self.cmb_n = QComboBox()
        self.cmb_n.addItem("Todas las n", None)
        for n in range(mat.N_MIN, mat.N_MAX + 1):
            self.cmb_n.addItem(f"n = {n}", n)
        self.cmb_resultado = QComboBox()
        self.cmb_resultado.addItem("Todos los resultados", None)
        for clave, (nombre, _) in RESULTADOS.items():
            self.cmb_resultado.addItem(nombre, clave)
        self.txt_buscar.textChanged.connect(self._aplicar_filtros)
        self.cmb_n.currentIndexChanged.connect(self._aplicar_filtros)
        self.cmb_resultado.currentIndexChanged.connect(self._aplicar_filtros)
        filtros.cuerpo.addLayout(fila(self.txt_buscar, self.cmb_n, self.cmb_resultado))

        self.btn_detalle = QPushButton("Ver detalle")
        self.btn_eliminar = QPushButton("Eliminar")
        self.btn_exportar = QPushButton("Exportar filtrados a JSON")
        self.btn_exportar.setObjectName("primario")
        btn_recargar = QPushButton("Recargar")
        self.btn_detalle.clicked.connect(self._ver_detalle)
        self.btn_eliminar.clicked.connect(self._eliminar)
        self.btn_exportar.clicked.connect(self._exportar)
        btn_recargar.clicked.connect(self.actualizar)
        self.lbl_conteo = etiqueta("", "secundario", ajustar=False)
        acciones = fila(self.lbl_conteo, espaciado=8, estirar_final=True)
        for b in (btn_recargar, self.btn_detalle, self.btn_eliminar, self.btn_exportar):
            acciones.addWidget(b)
        filtros.cuerpo.addLayout(acciones)
        lay.addWidget(filtros)

        self.aviso = Aviso()
        lay.addWidget(self.aviso)

        self.tabla = QTableWidget(0, len(COLUMNAS))
        self.tabla.setHorizontalHeaderLabels(COLUMNAS)
        self.tabla.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tabla.setSelectionMode(QAbstractItemView.SingleSelection)
        self.tabla.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tabla.setAlternatingRowColors(True)
        self.tabla.verticalHeader().setVisible(False)
        self.tabla.setMinimumHeight(420)
        cab = self.tabla.horizontalHeader()
        cab.setSectionResizeMode(QHeaderView.ResizeToContents)
        cab.setSectionResizeMode(1, QHeaderView.Stretch)
        self.tabla.doubleClicked.connect(self._ver_detalle)
        self.tabla.itemSelectionChanged.connect(self._actualizar_botones)
        lay.addWidget(self.tabla, 1)

        self.actualizar()

    # ------------------------------------------------------------------
    def actualizar(self) -> None:
        self._registros = self.gestor.cargar()
        if self.gestor.aviso:
            self.aviso.mostrar("advertencia", html.escape(self.gestor.aviso))
        else:
            self.aviso.ocultar()
        self._aplicar_filtros()

    def _aplicar_filtros(self) -> None:
        self._filtrados = list(reversed(GestorHistorial.filtrar(
            self._registros,
            texto=self.txt_buscar.text(),
            n=self.cmb_n.currentData(),
            resultado=self.cmb_resultado.currentData(),
        )))
        self.tabla.setRowCount(len(self._filtrados))
        for i, r in enumerate(self._filtrados):
            mensaje = r.get("mensaje_original", "").replace("\n", " ")
            nombre, color = RESULTADOS.get(r.get("resultado"), (str(r.get("resultado")), e.TEXTO))
            valores = [
                str(r.get("fecha_hora", "")).replace("T", " "),
                mensaje if len(mensaje) <= 60 else mensaje[:60] + "…",
                r.get("longitud_codigo"),
                r.get("probabilidad_error"),
                r.get("semilla"),
                r.get("errores_introducidos"),
                r.get("errores_residuales"),
                r.get("ambiguedades"),
                nombre,
            ]
            for j, v in enumerate(valores):
                item = QTableWidgetItem("" if v is None else str(v))
                if j >= 2 and j < 8:
                    item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                if j == 8:
                    item.setForeground(QColor(color))
                self.tabla.setItem(i, j, item)
        self.lbl_conteo.setText(f"{len(self._filtrados)} de {len(self._registros)} registros")
        self.btn_exportar.setEnabled(bool(self._filtrados))
        self._actualizar_botones()

    def _seleccionado(self) -> dict | None:
        filas = self.tabla.selectionModel().selectedRows()
        return self._filtrados[filas[0].row()] if filas else None

    def _actualizar_botones(self) -> None:
        hay = self._seleccionado() is not None
        self.btn_detalle.setEnabled(hay)
        self.btn_eliminar.setEnabled(hay)

    def _ver_detalle(self) -> None:
        registro = self._seleccionado()
        if registro:
            DialogoDetalle(registro, self).exec()

    def _eliminar(self) -> None:
        registro = self._seleccionado()
        if not registro:
            return
        respuesta = QMessageBox.question(
            self, "Eliminar experimento",
            f"¿Eliminar el experimento del {str(registro.get('fecha_hora', '')).replace('T', ' ')}?\n"
            "Esta acción no se puede deshacer.",
        )
        if respuesta != QMessageBox.Yes:
            return
        try:
            self.gestor.eliminar(registro["id"])
        except OSError as exc:
            self.aviso.mostrar("error", f"No se pudo eliminar: {html.escape(str(exc))}")
            return
        self.actualizar()
        self.historial_cambiado.emit()

    def _exportar(self) -> None:
        sugerido = Path.home() / f"codechat_historial_{datetime.now():%Y%m%d_%H%M%S}.json"
        ruta, _ = QFileDialog.getSaveFileName(self, "Exportar historial", str(sugerido), "JSON (*.json)")
        if not ruta:
            return
        try:
            GestorHistorial.exportar(self._filtrados, ruta)
        except OSError as exc:
            self.aviso.mostrar("error", f"No se pudo exportar: {html.escape(str(exc))}")
            return
        self.aviso.mostrar("exito", f"Se exportaron {len(self._filtrados)} registros a {html.escape(ruta)}.")

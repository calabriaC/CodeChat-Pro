"""Componentes visuales reutilizables por los distintos módulos de la interfaz."""

from __future__ import annotations

import html

import numpy as np
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg, NavigationToolbar2QT
from matplotlib.figure import Figure
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QSizePolicy,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from interfaz import estilos as e

# Límite de bloques que se dibujan en los visores de bits (los totales y el
# historial siempre usan el mensaje completo).
MAX_BLOQUES_VISIBLES = 96


def pagina_desplazable(titulo: str, subtitulo: str) -> tuple[QScrollArea, QVBoxLayout]:
    """Crea una página con encabezado y área desplazable. Devuelve (página, layout de contenido)."""
    contenido = QWidget()
    contenido.setObjectName("pagina")
    layout = QVBoxLayout(contenido)
    layout.setContentsMargins(28, 24, 28, 24)
    layout.setSpacing(16)
    lbl_titulo = QLabel(titulo)
    lbl_titulo.setObjectName("titulo")
    lbl_sub = QLabel(subtitulo)
    lbl_sub.setObjectName("subtitulo")
    lbl_sub.setWordWrap(True)
    layout.addWidget(lbl_titulo)
    layout.addWidget(lbl_sub)

    area = QScrollArea()
    area.setWidgetResizable(True)
    area.setWidget(contenido)
    area.setFrameShape(QFrame.NoFrame)
    area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)  # el contenido se adapta al ancho
    return area, layout


class Panel(QFrame):
    """Contenedor con fondo de panel, bordes redondeados y título opcional."""

    def __init__(self, titulo: str | None = None, parent=None):
        super().__init__(parent)
        self.setObjectName("panel")
        self.cuerpo = QVBoxLayout(self)
        self.cuerpo.setContentsMargins(18, 16, 18, 16)
        self.cuerpo.setSpacing(10)
        if titulo:
            lbl = QLabel(titulo)
            lbl.setObjectName("seccion")
            self.cuerpo.addWidget(lbl)


class Tarjeta(QFrame):
    """Tarjeta de indicador: título, valor grande y nota."""

    def __init__(self, titulo: str, color: str = e.TEXTO, parent=None):
        super().__init__(parent)
        self.setObjectName("tarjeta")
        self.setMinimumWidth(170)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 14, 16, 14)
        lay.setSpacing(2)
        barra = QFrame()
        barra.setFixedSize(28, 3)
        barra.setStyleSheet(f"background:{color}; border-radius:1px;")
        self.lbl_titulo = QLabel(titulo)
        self.lbl_titulo.setObjectName("tarjetaTitulo")
        self.lbl_valor = QLabel("—")
        self.lbl_valor.setObjectName("tarjetaValor")
        self.lbl_nota = QLabel("")
        self.lbl_nota.setObjectName("tarjetaNota")
        self.lbl_nota.setWordWrap(True)
        for w in (barra, self.lbl_titulo, self.lbl_valor, self.lbl_nota):
            lay.addWidget(w)

    def establecer(self, valor: str, nota: str = "") -> None:
        self.lbl_valor.setText(valor)
        self.lbl_nota.setText(nota)


class Aviso(QLabel):
    """Banda de mensaje de estado (éxito, advertencia, error o información)."""

    COLORES = {"exito": e.VERDE, "advertencia": e.NARANJA, "error": e.ROJO, "info": e.CIAN}
    ICONOS = {"exito": "✓", "advertencia": "!", "error": "×", "info": "i"}

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWordWrap(True)
        self.setTextFormat(Qt.RichText)
        self.hide()

    def mostrar(self, tipo: str, texto: str) -> None:
        color = self.COLORES[tipo]
        c = QColor(color)
        self.setStyleSheet(
            f"background: rgba({c.red()}, {c.green()}, {c.blue()}, 30); border:1px solid {color};"
            " border-radius:8px; padding:10px 12px;"
        )
        self.setText(f"<b style='color:{color}'>{self.ICONOS[tipo]}</b>&nbsp; {texto}")
        self.show()

    def ocultar(self) -> None:
        self.hide()


class VisorBits(QTextBrowser):
    """Muestra bits agrupados por bloques, resaltando posiciones alteradas o ambiguas."""

    def __init__(self, alto_minimo: int = 90, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(alto_minimo)
        self.setMaximumHeight(alto_minimo * 2)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        self.setOpenLinks(False)

    def mostrar_bits(
        self,
        bits: np.ndarray,
        tam_bloque: int = 8,
        marcados: np.ndarray | None = None,
        color_marcado: str = e.ROJO,
        ambiguos: np.ndarray | None = None,
    ) -> None:
        """bits: valores 0/1 (o -1 = ambiguo). marcados/ambiguos: máscaras booleanas."""
        if bits.size == 0:
            self.setHtml(f"<span style='color:{e.TEXTO_3}'>(sin bits)</span>")
            return
        limite = min(bits.size, MAX_BLOQUES_VISIBLES * tam_bloque)
        partes = []
        for inicio in range(0, limite, tam_bloque):
            bloque = []
            for i in range(inicio, min(inicio + tam_bloque, limite)):
                if ambiguos is not None and ambiguos[i]:
                    bloque.append(f"<span style='color:{e.FONDO};background:{e.NARANJA}'>?</span>")
                elif marcados is not None and marcados[i]:
                    bloque.append(
                        f"<span style='color:{e.FONDO};background:{color_marcado};font-weight:700'>{bits[i]}</span>"
                    )
                else:
                    bloque.append(str(int(bits[i])))
            partes.append("".join(bloque))
        cuerpo = " ".join(partes)
        nota = ""
        if limite < bits.size:
            nota = (
                f"<br><span style='color:{e.TEXTO_3};font-family:Segoe UI'>… se muestran {limite} de "
                f"{bits.size} bits. Los conteos usan el mensaje completo.</span>"
            )
        self.setHtml(
            f"<div style='font-family:{html.escape(e.FUENTE_MONO)};font-size:10.5pt;"
            f"color:{e.TEXTO};line-height:150%'>{cuerpo}{nota}</div>"
        )


class LienzoGrafica(QWidget):
    """Figura de Matplotlib integrada con su barra de herramientas (zoom, guardar...)."""

    def __init__(self, alto: float = 4.6, parent=None):
        super().__init__(parent)
        self.figura = Figure(figsize=(8, alto), layout="constrained")
        self.canvas = FigureCanvasQTAgg(self.figura)
        self.canvas.setMinimumHeight(int(alto * 80))
        self.canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        barra = NavigationToolbar2QT(self.canvas, self)
        barra.setStyleSheet(f"background:{e.PANEL}; border:none;")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(barra)
        lay.addWidget(self.canvas)

    def nuevo_eje(self):
        self.figura.clear()
        return self.figura.add_subplot(111)

    def dibujar(self) -> None:
        self.canvas.draw_idle()


def fila(*widgets, espaciado: int = 10, estirar_final: bool = False) -> QHBoxLayout:
    lay = QHBoxLayout()
    lay.setSpacing(espaciado)
    for w in widgets:
        if isinstance(w, QWidget):
            lay.addWidget(w)
        else:
            lay.addLayout(w)
    if estirar_final:
        lay.addStretch(1)
    return lay


def etiqueta(texto: str, nombre: str | None = None, ajustar: bool = True) -> QLabel:
    lbl = QLabel(texto)
    if nombre:
        lbl.setObjectName(nombre)
    lbl.setWordWrap(ajustar)
    return lbl

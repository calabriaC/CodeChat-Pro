"""Ventana principal con navegación lateral y páginas apiladas."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QButtonGroup,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from almacenamiento.gestor_json import GestorHistorial
from interfaz.dashboard import PaginaDashboard
from interfaz.estadisticas import PaginaEstadisticas
from interfaz.historial import PaginaHistorial
from interfaz.laboratorio import PaginaLaboratorio
from interfaz.transmision import PaginaTransmision


class VentanaPrincipal(QMainWindow):
    def __init__(self, gestor: GestorHistorial):
        super().__init__()
        self.setWindowTitle("CodeChat Pro — Códigos de repetición sobre un canal BSC")
        self.resize(1280, 820)
        self.setMinimumSize(960, 640)

        self.dashboard = PaginaDashboard(gestor)
        self.transmision = PaginaTransmision(gestor)
        self.laboratorio = PaginaLaboratorio()
        self.estadisticas = PaginaEstadisticas()
        self.historial = PaginaHistorial(gestor)

        self.paginas = {
            "dashboard": ("Dashboard", self.dashboard),
            "transmision": ("Transmisión", self.transmision),
            "laboratorio": ("Laboratorio matemático", self.laboratorio),
            "estadisticas": ("Estadísticas y gráficas", self.estadisticas),
            "historial": ("Historial", self.historial),
        }

        self.pila = QStackedWidget()
        barra = QFrame()
        barra.setObjectName("barraLateral")
        barra.setFixedWidth(230)
        lay_barra = QVBoxLayout(barra)
        lay_barra.setContentsMargins(14, 22, 14, 18)
        lay_barra.setSpacing(4)
        marca = QLabel("◉ CodeChat Pro")
        marca.setObjectName("marca")
        sub = QLabel("CÓDIGOS DE REPETICIÓN · BSC")
        sub.setObjectName("marcaSub")
        lay_barra.addWidget(marca)
        lay_barra.addWidget(sub)
        lay_barra.addSpacing(22)

        self.botones: dict[str, QPushButton] = {}
        grupo = QButtonGroup(self)
        grupo.setExclusive(True)
        for clave, (texto, pagina) in self.paginas.items():
            self.pila.addWidget(pagina)
            boton = QPushButton(texto)
            boton.setObjectName("nav")
            boton.setCheckable(True)
            boton.clicked.connect(lambda _=False, c=clave: self.mostrar(c))
            grupo.addButton(boton)
            lay_barra.addWidget(boton)
            self.botones[clave] = boton
        lay_barra.addStretch(1)
        pie = QLabel("Teoría de Códigos · Tema 6\nProyecto final 2026")
        pie.setObjectName("tarjetaNota")
        lay_barra.addWidget(pie)

        raiz = QWidget()
        raiz.setObjectName("raiz")
        lay = QHBoxLayout(raiz)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        lay.addWidget(barra)
        lay.addWidget(self.pila, 1)
        self.setCentralWidget(raiz)

        # Conexiones entre módulos
        self.dashboard.ir_a.connect(self.mostrar)
        self.transmision.historial_cambiado.connect(self._historial_cambiado)
        self.historial.historial_cambiado.connect(self.dashboard.actualizar)

        self.mostrar("dashboard")

    def mostrar(self, clave: str) -> None:
        pagina = self.paginas[clave][1]
        if clave == "dashboard":
            self.dashboard.actualizar()
        elif clave == "historial":
            self.historial.actualizar()
        self.pila.setCurrentWidget(pagina)
        self.botones[clave].setChecked(True)

    def _historial_cambiado(self) -> None:
        self.dashboard.actualizar()
        self.historial.actualizar()

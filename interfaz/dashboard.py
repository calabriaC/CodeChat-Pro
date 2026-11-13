"""Dashboard principal: indicadores reales calculados a partir del historial JSON."""

from __future__ import annotations

import html

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QGridLayout, QPushButton, QVBoxLayout, QWidget

from almacenamiento.gestor_json import GestorHistorial
from interfaz import estilos as e
from interfaz.componentes import Aviso, Panel, Tarjeta, etiqueta, pagina_desplazable


class PaginaDashboard(QWidget):
    ir_a = Signal(str)  # clave del módulo de destino

    def __init__(self, gestor: GestorHistorial, parent=None):
        super().__init__(parent)
        self.gestor = gestor
        area, lay = pagina_desplazable(
            "CodeChat Pro",
            "Sistema interactivo de transmisión confiable de mensajes mediante códigos de repetición "
            "y análisis de errores en un canal binario simétrico (BSC).",
        )
        raiz = QVBoxLayout(self)
        raiz.setContentsMargins(0, 0, 0, 0)
        raiz.addWidget(area)

        intro = Panel()
        intro.cuerpo.addWidget(etiqueta(
            "Un emisor envía un mensaje digital por un canal ruidoso que invierte cada bit con probabilidad "
            "<b>p</b>. El código de repetición envía cada bit <b>n</b> veces y el receptor decide por "
            "<b>mayoría</b>. Más redundancia reduce el error residual, pero también reduce la tasa "
            "<b>R = 1/n</b>. Este aplicativo permite medir ese compromiso y compararlo con la capacidad "
            "de Shannon <b>C = 1 − H₂(p)</b>."
        ))
        lay.addWidget(intro)

        self.aviso = Aviso()
        lay.addWidget(self.aviso)

        rejilla = QGridLayout()
        rejilla.setSpacing(14)
        self.tarjetas = {
            "total": Tarjeta("Transmisiones guardadas", e.CIAN),
            "exitosas": Tarjeta("Transmisiones exitosas", e.VERDE),
            "porcentaje": Tarjeta("Mensajes recuperados", e.AZUL),
            "introducidos": Tarjeta("Errores introducidos por el canal", e.NARANJA),
            "residuales": Tarjeta("Errores residuales tras decodificar", e.ROJO),
            "ambiguedades": Tarjeta("Bits ambiguos (empates sin resolver)", e.NARANJA),
        }
        for i, tarjeta in enumerate(self.tarjetas.values()):
            rejilla.addWidget(tarjeta, i // 3, i % 3)
        lay.addLayout(rejilla)

        accesos = Panel("Accesos rápidos")
        fila_accesos = QGridLayout()
        fila_accesos.setSpacing(10)
        for i, (clave, texto, desc) in enumerate(
            [
                ("transmision", "Transmitir un mensaje", "Codificar, enviar por el BSC y decodificar."),
                ("laboratorio", "Laboratorio BSC", "Experimentos repetidos con y sin código (n = 3, 5, 7)."),
                ("resultados", "Resultados", "Error frente a tasa, capacidad de Shannon y fundamento."),
                ("historial", "Historial de experimentos", "Consultar, filtrar y exportar en JSON."),
            ]
        ):
            boton = QPushButton(texto)
            boton.setObjectName("primario" if i == 0 else "")
            boton.clicked.connect(lambda _=False, c=clave: self.ir_a.emit(c))
            fila_accesos.addWidget(boton, 0, i)
            fila_accesos.addWidget(etiqueta(desc, "tarjetaNota"), 1, i)
        accesos.cuerpo.addLayout(fila_accesos)
        lay.addWidget(accesos)

        self.panel_recientes = Panel("Últimas transmisiones")
        self.lbl_recientes = etiqueta("")
        self.panel_recientes.cuerpo.addWidget(self.lbl_recientes)
        lay.addWidget(self.panel_recientes)
        lay.addStretch(1)

        self.actualizar()

    def actualizar(self) -> None:
        registros = self.gestor.cargar()
        if self.gestor.aviso:
            self.aviso.mostrar("advertencia", html.escape(self.gestor.aviso))
        else:
            self.aviso.ocultar()
        ind = GestorHistorial.indicadores(registros)
        total = ind["total"]
        self.tarjetas["total"].establecer(str(total), "Experimentos almacenados en data/historial.json")
        self.tarjetas["exitosas"].establecer(
            str(ind["exitosas"]), f"Con errores: {ind['con_errores']} · Ambiguas: {ind['ambiguas']}"
        )
        if ind["porcentaje_recuperados"] is None:
            self.tarjetas["porcentaje"].establecer("—", "Aún no hay transmisiones guardadas")
        else:
            self.tarjetas["porcentaje"].establecer(
                f"{ind['porcentaje_recuperados']:.1f} %", "Mensajes idénticos al original"
            )
        self.tarjetas["introducidos"].establecer(f"{ind['errores_introducidos']:,}".replace(",", "."), "Bits invertidos en el BSC")
        self.tarjetas["residuales"].establecer(f"{ind['errores_residuales']:,}".replace(",", "."), "Bits de información incorrectos")
        self.tarjetas["ambiguedades"].establecer(str(ind["ambiguedades"]), "Nunca se cuentan como aciertos")

        if not registros:
            self.lbl_recientes.setText(
                f"<span style='color:{e.TEXTO_2}'>Todavía no hay experimentos. Vaya a <b>Transmisión</b>, ejecute "
                "una transmisión y pulse <b>Guardar en historial</b>.</span>"
            )
            return
        colores = {"exito": e.VERDE, "error": e.ROJO, "ambiguo": e.NARANJA}
        nombres = {"exito": "Éxito", "error": "Con errores", "ambiguo": "Ambiguo"}
        lineas = []
        for r in reversed(registros[-5:]):
            mensaje = r.get("mensaje_original", "")
            mensaje = mensaje if len(mensaje) <= 40 else mensaje[:40] + "…"
            res = r.get("resultado", "")
            lineas.append(
                f"<span style='color:{e.TEXTO_3}'>{html.escape(r.get('fecha_hora', '').replace('T', ' '))}</span>"
                f" &nbsp; n = {r.get('longitud_codigo')} · p = {r.get('probabilidad_error')} &nbsp; "
                f"<b style='color:{colores.get(res, e.TEXTO)}'>{nombres.get(res, res)}</b> &nbsp; "
                f"“{html.escape(mensaje)}”"
            )
        self.lbl_recientes.setText("<br>".join(lineas))

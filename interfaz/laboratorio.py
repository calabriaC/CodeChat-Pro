"""Laboratorio BSC: experimentos repetidos con y sin código (Monte Carlo)."""

from __future__ import annotations

import html
from datetime import datetime
from pathlib import Path

import numpy as np
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QGridLayout,
    QHeaderView,
    QProgressBar,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from almacenamiento.gestor_json import GestorHistorial
from core import matematicas as mat
from core.decodificador import PoliticaDesempate
from core.simulacion import ResultadoExperimento, experimento_con_sin_codigo
from interfaz import estilos as e
from interfaz.componentes import (
    Aviso,
    LienzoGrafica,
    Panel,
    TareaSegundoPlano,
    etiqueta,
    fila,
    pagina_desplazable,
)

COLUMNAS = [
    "n", "p", "Ensayos × bits", "Política", "BER sin código", "BER con código", "IC 95 % (con código)",
    "P_e teórica", "Ambiguos", "Mensajes íntegros sin código", "Mensajes íntegros con código",
    "Éxito teórico con código", "Tasa R",
]


def _fmt(x: float) -> str:
    if x == 0:
        return "0"
    return f"{x:.4f}" if x >= 1e-3 else f"{x:.3e}"


class PaginaLaboratorio(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._resultados: list[ResultadoExperimento] = []
        self._ultimo_lote: list[ResultadoExperimento] = []
        self._tarea: TareaSegundoPlano | None = None

        area, lay = pagina_desplazable(
            "Laboratorio BSC",
            "Experimentos repetidos: cada ensayo genera un mensaje aleatorio de k bits y lo envía por el "
            "mismo canal BSC(p) sin código y con código de repetición. Los resultados provienen de "
            "simulaciones realmente ejecutadas y se comparan con los valores teóricos.",
        )
        raiz = QVBoxLayout(self)
        raiz.setContentsMargins(0, 0, 0, 0)
        raiz.addWidget(area)

        # --- configuración ---
        conf = Panel("Configuración del experimento")
        self.spin_n = QSpinBox()
        self.spin_n.setRange(mat.N_MIN, mat.N_MAX)
        self.spin_n.setValue(3)
        self.spin_p = QDoubleSpinBox()
        self.spin_p.setRange(mat.P_MIN, mat.P_MAX)
        self.spin_p.setDecimals(4)
        self.spin_p.setSingleStep(0.01)
        self.spin_p.setValue(0.10)
        self.spin_bits = QSpinBox()
        self.spin_bits.setRange(8, 100_000)
        self.spin_bits.setValue(160)
        self.spin_bits.setToolTip("Bits de información por mensaje de prueba (160 bits = 20 caracteres ASCII).")
        self.spin_ensayos = QSpinBox()
        self.spin_ensayos.setRange(1, 100_000)
        self.spin_ensayos.setValue(500)
        self.spin_ensayos.setToolTip("Cantidad de mensajes de prueba transmitidos.")
        self.spin_semilla = QSpinBox()
        self.spin_semilla.setRange(0, 2**31 - 1)
        self.spin_semilla.setValue(2026)
        self.cmb_politica = QComboBox()
        for pol in (PoliticaDesempate.ALEATORIO, PoliticaDesempate.AMBIGUO,
                    PoliticaDesempate.CERO, PoliticaDesempate.UNO):
            self.cmb_politica.addItem(pol.etiqueta, pol.value)
        self.cmb_politica.setToolTip(
            "Solo afecta a n par. 'Decisión aleatoria' es la política de la fórmula teórica; "
            "'Marcar como ambiguo' cuenta los empates aparte (no son errores ni aciertos)."
        )

        rej = QGridLayout()
        rej.setHorizontalSpacing(14)
        rej.setVerticalSpacing(8)
        campos = [
            ("Longitud n", self.spin_n), ("Probabilidad p", self.spin_p), ("Bits por mensaje", self.spin_bits),
            ("Ensayos (mensajes)", self.spin_ensayos), ("Semilla", self.spin_semilla),
            ("Desempate (n par)", self.cmb_politica),
        ]
        for i, (texto, w) in enumerate(campos):
            rej.addWidget(etiqueta(texto), i // 3, 2 * (i % 3))
            rej.addWidget(w, i // 3, 2 * (i % 3) + 1)
        for col in (1, 3, 5):
            rej.setColumnStretch(col, 1)
        conf.cuerpo.addLayout(rej)

        self.btn_ejecutar = QPushButton("▶ Ejecutar experimento")
        self.btn_ejecutar.setObjectName("primario")
        self.btn_ejecutar.clicked.connect(lambda: self.ejecutar([self.spin_n.value()]))
        self.btn_357 = QPushButton("Comparar n = 3, 5 y 7")
        self.btn_357.setObjectName("primario")
        self.btn_357.clicked.connect(lambda: self.ejecutar([3, 5, 7]))
        presets = []
        for n in (3, 5, 7):
            b = QPushButton(f"Preconfigurado n = {n}")
            b.setObjectName("chip")
            b.setToolTip(f"n = {n}, p = 0.1, 500 mensajes de 160 bits, semilla 2026, desempate aleatorio.")
            b.clicked.connect(lambda _=False, m=n: self._preconfigurar(m))
            presets.append(b)
        self.btn_cancelar = QPushButton("Cancelar")
        self.btn_cancelar.setEnabled(False)
        self.btn_cancelar.clicked.connect(self.cancelar)
        acciones = fila(self.btn_ejecutar, self.btn_357, *presets, espaciado=8, estirar_final=True)
        acciones.addWidget(self.btn_cancelar)
        conf.cuerpo.addLayout(acciones)
        self.barra = QProgressBar()
        self.barra.setTextVisible(True)
        self.barra.setFormat("%p %")
        self.barra.setStyleSheet(
            f"QProgressBar {{ background:{e.FONDO}; border:1px solid {e.BORDE}; border-radius:6px; height:16px;"
            f" text-align:center; color:{e.TEXTO}; }} QProgressBar::chunk {{ background:{e.AZUL}; border-radius:6px; }}"
        )
        self.barra.hide()
        conf.cuerpo.addWidget(self.barra)
        lay.addWidget(conf)

        self.aviso = Aviso()
        lay.addWidget(self.aviso)

        # --- resultados ---
        self.panel_conclusion = Panel("Conclusión basada en los datos")
        self.lbl_conclusion = etiqueta("")
        self.panel_conclusion.cuerpo.addWidget(self.lbl_conclusion)
        self.panel_conclusion.hide()
        lay.addWidget(self.panel_conclusion)

        self.panel_grafica = Panel("Con código frente a sin código")
        self.lienzo = LienzoGrafica(alto=4.2)
        self.panel_grafica.cuerpo.addWidget(self.lienzo)
        self.panel_grafica.hide()
        lay.addWidget(self.panel_grafica)

        panel_tabla = Panel("Resultados de la sesión")
        self.tabla = QTableWidget(0, len(COLUMNAS))
        self.tabla.setHorizontalHeaderLabels(COLUMNAS)
        self.tabla.verticalHeader().setVisible(False)
        self.tabla.setEditTriggers(QTableWidget.NoEditTriggers)
        self.tabla.setAlternatingRowColors(True)
        self.tabla.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.tabla.setMinimumHeight(240)
        btn_limpiar = QPushButton("Limpiar")
        btn_limpiar.clicked.connect(self._limpiar)
        self.btn_exportar = QPushButton("Exportar resultados a JSON")
        self.btn_exportar.clicked.connect(self._exportar)
        self.btn_exportar.setEnabled(False)
        panel_tabla.cuerpo.addWidget(self.tabla)
        panel_tabla.cuerpo.addLayout(fila(etiqueta(
            "BER = errores en bits útiles / bits útiles. Los ambiguos (empates sin resolver) se cuentan aparte. "
            "IC 95 %: intervalo de confianza de Wilson de la BER con código.", "secundario"),
            btn_limpiar, self.btn_exportar))
        lay.addWidget(panel_tabla)
        lay.addStretch(1)

    # ------------------------------------------------------------------
    def _preconfigurar(self, n: int) -> None:
        self.spin_n.setValue(n)
        self.spin_p.setValue(0.10)
        self.spin_bits.setValue(160)
        self.spin_ensayos.setValue(500)
        self.spin_semilla.setValue(2026)
        self.cmb_politica.setCurrentIndex(self.cmb_politica.findData(PoliticaDesempate.ALEATORIO.value))
        self.ejecutar([n])

    def _en_ejecucion(self, activo: bool) -> None:
        for w in (self.btn_ejecutar, self.btn_357):
            w.setEnabled(not activo)
        self.btn_cancelar.setEnabled(activo)
        self.barra.setVisible(activo)

    def ejecutar(self, longitudes: list[int]) -> None:
        if self._tarea is not None:
            return
        p = self.spin_p.value()
        bits = self.spin_bits.value()
        ensayos = self.spin_ensayos.value()
        semilla = self.spin_semilla.value()
        politica = PoliticaDesempate(self.cmb_politica.currentData())

        def trabajo(reportar):
            resultados = []
            for i, n in enumerate(longitudes):
                reportar(i, len(longitudes))
                # Misma semilla para cada n: todos los códigos ven los mismos mensajes.
                resultados.append(experimento_con_sin_codigo(n, p, bits, ensayos, semilla, politica))
            reportar(len(longitudes), len(longitudes))
            return resultados

        self.aviso.mostrar("info", f"Simulando {ensayos} mensajes de {bits} bits para n = "
                                   f"{', '.join(map(str, longitudes))} con p = {p:g}…")
        self.barra.setRange(0, len(longitudes))
        self.barra.setValue(0)
        self._en_ejecucion(True)
        self._tarea = TareaSegundoPlano(trabajo, self)
        self._tarea.progreso.connect(lambda hecho, total: self.barra.setValue(hecho))
        self._tarea.terminado.connect(self._terminado)
        self._tarea.fallo.connect(self._fallo)
        self._tarea.finished.connect(self._liberar_tarea)
        self._tarea.start()

    def cancelar(self) -> None:
        if self._tarea is not None:
            self._tarea.cancelar()

    def detener(self) -> None:
        """Cancela y espera la tarea en curso (al cerrar la aplicación)."""
        if self._tarea is not None:
            self._tarea.cancelar()
            self._tarea.wait()

    def _liberar_tarea(self) -> None:
        self._tarea = None
        self._en_ejecucion(False)

    def _fallo(self, mensaje: str) -> None:
        self.aviso.mostrar("advertencia", html.escape(mensaje))

    def _terminado(self, resultados: list[ResultadoExperimento]) -> None:
        self.aviso.ocultar()
        self._ultimo_lote = resultados
        self._resultados.extend(resultados)
        for r in resultados:
            self._agregar_fila(r)
        self.btn_exportar.setEnabled(True)
        self._dibujar(resultados)
        self._concluir(resultados)

    def _agregar_fila(self, r: ResultadoExperimento) -> None:
        bajo, alto = r.intervalo_ber_con_codigo
        valores = [
            r.n, f"{r.p:g}", f"{r.ensayos} × {r.bits_por_ensayo}", r.politica.value,
            _fmt(r.sin_codigo.ber_residual), _fmt(r.con_codigo.ber_residual), f"[{_fmt(bajo)}, {_fmt(alto)}]",
            _fmt(r.ber_teorica_con_codigo), r.con_codigo.ambiguos,
            f"{r.mensajes_ok_sin_codigo}/{r.ensayos} ({100 * r.mensajes_ok_sin_codigo / r.ensayos:.1f} %)",
            f"{r.mensajes_ok_con_codigo}/{r.ensayos} ({100 * r.mensajes_ok_con_codigo / r.ensayos:.1f} %)",
            f"{100 * r.exito_mensaje_teorico_con_codigo:.1f} %", f"1/{r.n}",
        ]
        fila_i = self.tabla.rowCount()
        self.tabla.insertRow(fila_i)
        for j, v in enumerate(valores):
            item = QTableWidgetItem(str(v))
            item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.tabla.setItem(fila_i, j, item)
        self.tabla.scrollToBottom()

    def _dibujar(self, resultados: list[ResultadoExperimento]) -> None:
        ax = self.lienzo.nuevo_eje()
        etiquetas = ["Sin código"] + [f"n = {r.n}" for r in resultados]
        # Sin código: se agregan todos los ensayos del lote (todos usan la misma p).
        total_sin = sum(r.bits_totales for r in resultados)
        err_sin = sum(r.sin_codigo.errores_residuales for r in resultados)
        observados = [err_sin / total_sin] + [r.con_codigo.ber_residual for r in resultados]
        teoricos = [resultados[0].p] + [r.ber_teorica_con_codigo for r in resultados]
        x = np.arange(len(etiquetas))
        piso = 1e-7
        colores = [e.TEXTO_3] + [e.SERIES[i % len(e.SERIES)] for i in range(len(resultados))]
        ax.bar(x, [max(v, piso) for v in observados], width=0.6, color=colores, edgecolor=e.PANEL, linewidth=2,
               label="BER residual observada")
        ax.scatter(x, [max(v, piso) for v in teoricos], marker="_", s=900, color=e.TEXTO, linewidths=2.5, zorder=3,
                   label="Valor teórico (p o P_e)")
        for xi, v in zip(x, observados):
            ax.annotate("0 errores" if v == 0 else _fmt(v), (xi, max(v, piso)), textcoords="offset points",
                        xytext=(0, 6), ha="center", fontsize=8.5, color=e.TEXTO_2)
        ax.set_yscale("log")
        ax.set_ylim(bottom=piso)
        ax.grid(axis="x", visible=False)
        ax.set_axisbelow(True)
        ax.set_xticks(x, etiquetas)
        ax.set_title(f"BER residual con y sin código (p = {resultados[0].p:g}, "
                     f"{resultados[0].ensayos} mensajes de {resultados[0].bits_por_ensayo} bits)")
        ax.set_xlabel("Esquema de transmisión")
        ax.set_ylabel("BER residual por bit útil (escala log)")
        ax.legend(loc="upper right")
        self.lienzo.dibujar()
        self.panel_grafica.show()

    def _concluir(self, resultados: list[ResultadoExperimento]) -> None:
        partes = []
        for r in resultados:
            sin, con = r.sin_codigo, r.con_codigo
            if con.errores_residuales == 0:
                total = f"{r.bits_totales:,}".replace(",", ".")
                mejora = f"no se observó ningún error residual en {total} bits (P_e teórica {_fmt(r.ber_teorica_con_codigo)})"
            else:
                factor = sin.ber_residual / con.ber_residual if con.ber_residual else float("inf")
                mejora = (f"la BER bajó de {_fmt(sin.ber_residual)} a {_fmt(con.ber_residual)} "
                          f"(≈ {factor:.1f} veces menor; teoría: {_fmt(r.p)} → {_fmt(r.ber_teorica_con_codigo)})")
            partes.append(
                f"<b>n = {r.n}:</b> {mejora}; mensajes íntegros {r.mensajes_ok_sin_codigo} → "
                f"{r.mensajes_ok_con_codigo} de {r.ensayos}. Precio: {r.n}× más bits transmitidos "
                f"(R = 1/{r.n} = {1 / r.n:.3f})."
            )
        p = resultados[0].p
        C = mat.capacidad_bsc(p)
        cierre = (
            f"Con p = {p:g} la capacidad del canal es C = {C:.3f}. Cada aumento de n reduce el error, pero "
            "también la tasa: la repetición cambia eficiencia por fiabilidad, mientras que Shannon garantiza "
            "códigos con error arbitrariamente pequeño a cualquier tasa R &lt; C."
            if 0 < p < 0.5 else
            ("Con p = 0 el canal no introduce errores: el código solo añade redundancia." if p == 0 else
             "Con p = 0.5 la salida es independiente de la entrada (C = 0): ningún código puede ayudar.")
        )
        self.lbl_conclusion.setText("<br>".join(partes) + "<br><br>" + cierre)
        self.panel_conclusion.show()

    def _limpiar(self) -> None:
        self._resultados.clear()
        self.tabla.setRowCount(0)
        self.btn_exportar.setEnabled(False)
        self.panel_grafica.hide()
        self.panel_conclusion.hide()

    def _exportar(self) -> None:
        sugerido = Path.home() / f"codechat_laboratorio_{datetime.now():%Y%m%d_%H%M%S}.json"
        ruta, _ = QFileDialog.getSaveFileName(self, "Exportar resultados", str(sugerido), "JSON (*.json)")
        if not ruta:
            return
        datos = [
            {
                "n": r.n, "p": r.p, "ensayos": r.ensayos, "bits_por_ensayo": r.bits_por_ensayo,
                "semilla": r.semilla, "politica_desempate": r.politica.value,
                "sin_codigo": r.sin_codigo.a_diccionario(), "con_codigo": r.con_codigo.a_diccionario(),
                "mensajes_integros_sin_codigo": r.mensajes_ok_sin_codigo,
                "mensajes_integros_con_codigo": r.mensajes_ok_con_codigo,
                "ber_teorica_con_codigo": r.ber_teorica_con_codigo,
                "ambiguedad_teorica": r.ambiguedad_teorica,
                "exito_mensaje_teorico_con_codigo": r.exito_mensaje_teorico_con_codigo,
                "exito_mensaje_teorico_sin_codigo": r.exito_mensaje_teorico_sin_codigo,
                "ic95_ber_con_codigo": list(r.intervalo_ber_con_codigo),
            }
            for r in self._resultados
        ]
        try:
            GestorHistorial.exportar(datos, ruta)
        except OSError as exc:
            self.aviso.mostrar("error", f"No se pudo exportar: {html.escape(str(exc))}")
            return
        self.aviso.mostrar("exito", f"Se exportaron {len(datos)} experimentos a {html.escape(ruta)}.")

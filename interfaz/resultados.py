"""Resultados: gráficas teóricas y experimentales, y fundamento matemático."""

from __future__ import annotations

import html

import numpy as np
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QGridLayout,
    QLineEdit,
    QProgressBar,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from core import matematicas as mat
from core.decodificador import PoliticaDesempate
from core.simulacion import crear_generador, experimento_con_sin_codigo, simular_ber
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
from interfaz.fundamento import PaginaFundamento

GRAFICAS = [
    ("pe_vs_r", "★ Error residual frente a tasa de transmisión R (gráfica principal)"),
    ("con_sin", "Comparación con y sin código"),
    ("exp_vs_teo", "Error teórico frente a error experimental"),
    ("pe_vs_p", "Error residual frente a probabilidad p del canal"),
    ("c_vs_p", "Capacidad de Shannon frente a p"),
    ("r_vs_n", "Tasa frente a longitud n"),
    ("pe_vs_red", "Redundancia frente a fiabilidad"),
    ("t_vs_n", "Capacidad de corrección frente a longitud n"),
]
SIMULABLES = {"pe_vs_r", "con_sin", "exp_vs_teo"}
USAN_P = {"pe_vs_r", "con_sin", "pe_vs_red"}
P_SIMULACION = [0.01, 0.02, 0.05, 0.08, 0.1, 0.15, 0.2, 0.3, 0.4, 0.5]
PISO_LOG = 1e-15  # límite inferior del eje logarítmico


def interpretar_codigos(texto: str) -> list[int]:
    """'3, 5, 7' o '1-21' o '3,9-11' -> lista ordenada de longitudes válidas."""
    valores: set[int] = set()
    try:
        for parte in texto.replace(";", ",").split(","):
            parte = parte.strip()
            if not parte:
                continue
            if "-" in parte:
                a, b = (int(x) for x in parte.split("-", 1))
                valores.update(range(min(a, b), max(a, b) + 1))
            else:
                valores.add(int(parte))
    except ValueError:
        raise ValueError(f"No se entiende la lista de longitudes «{texto}». Use p. ej. 3, 5, 7 o 1-21.") from None
    fuera = [v for v in valores if not mat.N_MIN <= v <= mat.N_MAX]
    if fuera:
        raise ValueError(f"Longitudes fuera de rango ({mat.N_MIN}–{mat.N_MAX}): {sorted(fuera)}")
    if not valores:
        raise ValueError("Indique al menos una longitud de código.")
    return sorted(valores)


def p_umbral(R: float) -> float:
    """p* en [0, 0.5] tal que C(p*) = R (C es decreciente en ese intervalo). Bisección."""
    if R >= 1.0:
        return 0.0
    bajo, alto = 0.0, 0.5
    for _ in range(60):
        medio = (bajo + alto) / 2
        if mat.capacidad_bsc(medio) > R:
            bajo = medio
        else:
            alto = medio
    return (bajo + alto) / 2


def _fmt(x: float) -> str:
    if x == 0:
        return "0"
    return f"{x:.4f}" if x >= 1e-3 else f"{x:.3e}"


class PaginaResultados(QWidget):
    """Contenedor con dos pestañas: gráficas y fundamento matemático."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.graficas = PaginaGraficas()
        self.fundamento = PaginaFundamento()
        pestanas = QTabWidget()
        pestanas.addTab(self.graficas, "Gráficas y métricas")
        pestanas.addTab(self.fundamento, "Fundamento matemático")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 8, 0, 0)
        lay.addWidget(pestanas)

    def detener(self) -> None:
        self.graficas.detener()


class PaginaGraficas(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._simulaciones: dict[str, tuple[tuple, object]] = {}
        self._tarea: TareaSegundoPlano | None = None
        area, lay = pagina_desplazable(
            "Resultados",
            "Curvas teóricas exactas y estimaciones experimentales (Monte Carlo) obtenidas con el mismo "
            "codificador, canal y decodificador del aplicativo. Las líneas son teoría; los puntos con "
            "intervalo de confianza son simulación.",
        )
        raiz = QVBoxLayout(self)
        raiz.setContentsMargins(0, 0, 0, 0)
        raiz.addWidget(area)

        # --- filtros (una franja sobre la gráfica) ---
        controles = Panel()
        self.cmb_grafica = QComboBox()
        for clave, nombre in GRAFICAS:
            self.cmb_grafica.addItem(nombre, clave)
        self.txt_codigos = QLineEdit("3, 5, 7")
        self.txt_codigos.setToolTip("Longitudes separadas por comas o rangos, p. ej. '3, 5, 7' o '1-21'.")
        btn_357 = QPushButton("3 · 5 · 7")
        btn_impares = QPushButton("Impares 1–21")
        btn_todos = QPushButton("Todos 1–21")
        for b, valor in ((btn_357, "3, 5, 7"), (btn_impares, "1,3,5,7,9,11,13,15,17,19,21"), (btn_todos, "1-21")):
            b.setObjectName("chip")
            b.clicked.connect(lambda _=False, v=valor: (self.txt_codigos.setText(v), self.actualizar()))
        self.spin_p = QDoubleSpinBox()
        self.spin_p.setRange(0.001, 0.5)
        self.spin_p.setDecimals(3)
        self.spin_p.setSingleStep(0.01)
        self.spin_p.setValue(0.1)
        self.spin_bits = QSpinBox()
        self.spin_bits.setRange(1_000, 1_000_000)
        self.spin_bits.setSingleStep(10_000)
        self.spin_bits.setValue(20_000)
        self.spin_bits.setToolTip("Bits de información simulados por cada punto experimental.")
        self.spin_semilla = QSpinBox()
        self.spin_semilla.setRange(0, 2**31 - 1)
        self.spin_semilla.setValue(2026)
        self.btn_simular = QPushButton("Ejecutar simulación")
        self.btn_simular.setObjectName("primario")
        self.btn_simular.clicked.connect(self.simular)
        self.btn_cancelar = QPushButton("Cancelar")
        self.btn_cancelar.clicked.connect(self.cancelar)
        self.btn_cancelar.setEnabled(False)
        self.barra = QProgressBar()
        self.barra.setFormat("%p %")
        self.barra.setStyleSheet(
            f"QProgressBar {{ background:{e.FONDO}; border:1px solid {e.BORDE}; border-radius:6px; height:16px;"
            f" text-align:center; color:{e.TEXTO}; }} QProgressBar::chunk {{ background:{e.AZUL}; border-radius:6px; }}"
        )
        self.barra.hide()

        rej = QGridLayout()
        rej.setHorizontalSpacing(12)
        rej.setVerticalSpacing(8)
        rej.addWidget(etiqueta("Gráfica"), 0, 0)
        rej.addWidget(self.cmb_grafica, 0, 1, 1, 3)
        rej.addWidget(etiqueta("Códigos (n)"), 1, 0)
        rej.addWidget(self.txt_codigos, 1, 1)
        rej.addLayout(fila(btn_357, btn_impares, btn_todos, espaciado=6, estirar_final=True), 1, 2, 1, 2)
        self.lbl_p = etiqueta("p del canal")
        rej.addWidget(self.lbl_p, 2, 0)
        rej.addWidget(self.spin_p, 2, 1)
        self.fila_sim = fila(
            etiqueta("Bits por punto", ajustar=False), self.spin_bits,
            etiqueta("Semilla", ajustar=False), self.spin_semilla, self.btn_simular, self.btn_cancelar,
            espaciado=8, estirar_final=True,
        )
        rej.addLayout(self.fila_sim, 3, 0, 1, 4)
        rej.addWidget(self.barra, 4, 0, 1, 4)
        rej.setColumnStretch(1, 1)
        rej.setColumnStretch(3, 1)
        controles.cuerpo.addLayout(rej)
        lay.addWidget(controles)

        self.aviso = Aviso()
        lay.addWidget(self.aviso)

        panel_grafica = Panel()
        self.lienzo = LienzoGrafica(alto=5.0)
        self.lbl_descripcion = etiqueta("", "secundario")
        self.chk_tabla = QCheckBox("Mostrar tabla de datos")
        self.tabla = QTableWidget()
        self.tabla.setAlternatingRowColors(True)
        self.tabla.setEditTriggers(QTableWidget.NoEditTriggers)
        self.tabla.verticalHeader().setVisible(False)
        self.tabla.setMinimumHeight(220)
        self.tabla.hide()
        self.chk_tabla.toggled.connect(self.tabla.setVisible)
        panel_grafica.cuerpo.addWidget(self.lienzo)
        panel_grafica.cuerpo.addWidget(self.lbl_descripcion)
        panel_grafica.cuerpo.addWidget(self.chk_tabla)
        panel_grafica.cuerpo.addWidget(self.tabla)
        lay.addWidget(panel_grafica)
        lay.addStretch(1)

        self.cmb_grafica.currentIndexChanged.connect(self.actualizar)
        self.txt_codigos.editingFinished.connect(self.actualizar)
        self.spin_p.valueChanged.connect(self.actualizar)
        self.actualizar()

    # ------------------------------------------------------------------
    def _clave(self) -> str:
        return self.cmb_grafica.currentData()

    def _parametros(self, clave: str, codigos: list[int]) -> tuple:
        p = self.spin_p.value() if clave in USAN_P else None
        return (tuple(codigos), p, self.spin_bits.value(), self.spin_semilla.value())

    def _simulacion_vigente(self, clave: str, codigos: list[int]):
        guardada = self._simulaciones.get(clave)
        if guardada and guardada[0] == self._parametros(clave, codigos):
            return guardada[1]
        return None

    def actualizar(self) -> None:
        clave = self._clave()
        self.lbl_p.setVisible(clave in USAN_P)
        self.spin_p.setVisible(clave in USAN_P)
        for i in range(self.fila_sim.count()):
            w = self.fila_sim.itemAt(i).widget()
            if w:
                w.setVisible(clave in SIMULABLES)
        try:
            codigos = interpretar_codigos(self.txt_codigos.text())
        except ValueError as exc:
            self.aviso.mostrar("error", html.escape(str(exc)))
            return
        if self._tarea is None:
            self.aviso.ocultar()
        ax = self.lienzo.nuevo_eje()
        encabezados, filas, descripcion = getattr(self, f"_g_{clave}")(ax, codigos)
        self.lienzo.dibujar()
        self.lbl_descripcion.setText(descripcion)
        self._llenar_tabla(encabezados, filas)

    def _llenar_tabla(self, encabezados: list[str], filas: list[list]) -> None:
        self.tabla.clear()
        self.tabla.setColumnCount(len(encabezados))
        self.tabla.setRowCount(len(filas))
        self.tabla.setHorizontalHeaderLabels(encabezados)
        for i, f in enumerate(filas):
            for j, v in enumerate(f):
                texto = f"{v:.6g}" if isinstance(v, float) else str(v)
                item = QTableWidgetItem(texto)
                item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.tabla.setItem(i, j, item)
        self.tabla.resizeColumnsToContents()

    @staticmethod
    def _leyenda(ax, **kw) -> None:
        if ax.get_legend_handles_labels()[0]:
            ax.legend(**kw)

    # --- simulación en segundo plano -------------------------------------
    def simular(self) -> None:
        if self._tarea is not None:
            return
        clave = self._clave()
        try:
            codigos = interpretar_codigos(self.txt_codigos.text())
        except ValueError as exc:
            self.aviso.mostrar("error", html.escape(str(exc)))
            return
        parametros = self._parametros(clave, codigos)
        _, p, num_bits, semilla = parametros

        if clave == "pe_vs_r":
            puntos = [(n, p) for n in codigos]
        elif clave == "exp_vs_teo":
            puntos = [(n, q) for n in codigos for q in P_SIMULACION]
        else:  # con_sin
            puntos = [(n, p) for n in codigos]

        def trabajo(reportar):
            _, rng = crear_generador(semilla)
            datos = []
            for i, (n, q) in enumerate(puntos):
                reportar(i, len(puntos))
                if clave == "con_sin":
                    # 100 mensajes de num_bits/100 bits, con y sin código por el mismo canal.
                    datos.append(experimento_con_sin_codigo(n, q, max(num_bits // 100, 1), 100,
                                                            semilla + i, PoliticaDesempate.ALEATORIO))
                else:
                    datos.append(simular_ber(n, q, num_bits, politica=PoliticaDesempate.ALEATORIO, generador=rng))
            reportar(len(puntos), len(puntos))
            return datos

        self.barra.setRange(0, len(puntos))
        self.barra.setValue(0)
        self.barra.show()
        self.btn_simular.setEnabled(False)
        self.btn_cancelar.setEnabled(True)
        self.aviso.mostrar("info", f"Simulando {len(puntos)} punto(s) con {num_bits:,} bits cada uno…".replace(",", "."))
        self._tarea = TareaSegundoPlano(trabajo, self)
        self._tarea.progreso.connect(lambda hecho, total: self.barra.setValue(hecho))
        self._tarea.terminado.connect(lambda datos: self._simulacion_terminada(clave, parametros, datos))
        self._tarea.fallo.connect(lambda msg: self.aviso.mostrar("advertencia", html.escape(msg)))
        self._tarea.finished.connect(self._liberar_tarea)
        self._tarea.start()

    def _simulacion_terminada(self, clave, parametros, datos) -> None:
        self._simulaciones[clave] = (parametros, datos)
        self.aviso.ocultar()
        if self._clave() == clave:
            self.actualizar()

    def _liberar_tarea(self) -> None:
        self._tarea = None
        self.barra.hide()
        self.btn_simular.setEnabled(True)
        self.btn_cancelar.setEnabled(False)

    def cancelar(self) -> None:
        if self._tarea is not None:
            self._tarea.cancelar()

    def detener(self) -> None:
        if self._tarea is not None:
            self._tarea.cancelar()
            self._tarea.wait()

    def _marcar_experimental(self, ax, x, r, color, marcador, etiqueta_serie=None) -> bool:
        """Dibuja un punto experimental con IC 95 %; si hubo 0 errores, solo la cota superior."""
        bajo, alto = r.intervalo_95
        if r.errores_residuales > 0:
            ax.errorbar([x], [r.ber_residual], yerr=[[r.ber_residual - bajo], [alto - r.ber_residual]],
                        fmt=marcador, color=color, markersize=8, capsize=3, markeredgecolor=e.PANEL,
                        label=etiqueta_serie, zorder=4)
            return True
        ax.plot([x], [alto], marker="v", color=color, markersize=8, markerfacecolor="none", zorder=4)
        return False

    # --- ★ gráfica principal ----------------------------------------------
    def _g_pe_vs_r(self, ax, codigos):
        p = self.spin_p.value()
        C = mat.capacidad_bsc(p)
        ns = list(range(mat.N_MIN, mat.N_MAX + 1, 2))
        ax.plot([mat.tasa_codigo(n) for n in ns], [max(mat.probabilidad_error_bit(n, p), PISO_LOG) for n in ns],
                color=e.TEXTO_3, linewidth=1.2, marker="o", markersize=3, zorder=1,
                label="Teórico: códigos impares n = 1…21")
        filas = []
        sim = self._simulacion_vigente("pe_vs_r", codigos)
        resultados = {r.n: r for r in sim} if sim else {}
        for i, n in enumerate(codigos):
            R, pe = mat.tasa_codigo(n), mat.probabilidad_error_bit(n, p)
            color = e.color_serie(i, len(codigos))
            muchos = len(codigos) > 8
            ax.scatter([R], [max(pe, PISO_LOG)], color=color, marker=e.marcador_serie(i), s=80, zorder=3,
                       edgecolors=e.PANEL, linewidths=1.5, label=None if muchos else f"n = {n} (teórico)")
            if not muchos:
                ax.annotate(f"n={n}", (R, max(pe, PISO_LOG)), textcoords="offset points", xytext=(7, 4),
                            fontsize=8.5, color=e.TEXTO_2)
            fila_datos = [n, R, pe, "sí" if R < C else "no"]
            if n in resultados:
                r = resultados[n]
                self._marcar_experimental(ax, R, r, color, "x")
                bajo, alto = r.intervalo_95
                fila_datos += [r.num_bits, r.errores_residuales, r.ber_residual, bajo, alto,
                               "sí" if bajo <= pe <= alto else "no"]
            filas.append(fila_datos)
        if resultados:
            ax.plot([], [], marker="x", color=e.TEXTO_2, linestyle="none", label="Experimental (IC 95 %)")
            ax.plot([], [], marker="v", color=e.TEXTO_2, linestyle="none", markerfacecolor="none",
                    label="0 errores: cota sup. 95 %")
        ax.axvline(C, color=e.CIAN, linestyle="--", linewidth=1.5, label=f"Capacidad C = {C:.3f}")
        ax.axvspan(0, C, color=e.CIAN, alpha=0.06)
        ax.set_yscale("log")
        ax.set_xlim(0, 1.05)
        ax.set_title(f"Error residual frente a tasa de transmisión (BSC, p = {p:g})")
        ax.set_xlabel("R = 1/n (bits de información por bit transmitido)")
        ax.set_ylabel("P_e = probabilidad de error residual por bit (escala log)")
        self._leyenda(ax, loc="lower right")
        encabezados = ["n", "R", "P_e teórica", "R < C"]
        if resultados:
            encabezados += ["bits simulados", "errores", "BER experimental", "IC95 inf", "IC95 sup", "teórica en IC"]
            filas = [f + [""] * (len(encabezados) - len(f)) for f in filas]
        descripcion = (
            "Cada punto es un código de repetición: a la derecha n = 1 (sin código, R = 1, error = p); hacia la "
            "izquierda n crece, la tasa cae como 1/n y el error residual disminuye. La zona sombreada son las tasas "
            "R &lt; C, donde Shannon garantiza que existen códigos con error tan pequeño como se quiera; la "
            "repetición solo baja el error llevando R hacia 0, por eso su curva nunca llega a la esquina inferior "
            "derecha de esa zona. Cambie p para ver cómo se desplazan la curva y C."
        )
        if not resultados:
            descripcion += " Pulse <b>Ejecutar simulación</b> para añadir puntos experimentales."
        return encabezados, filas, descripcion

    # --- comparación con y sin código ---------------------------------------
    def _g_con_sin(self, ax, codigos):
        p = self.spin_p.value()
        sim = self._simulacion_vigente("con_sin", codigos)
        etiquetas = ["Sin código"] + [f"n = {n}" for n in codigos]
        x = np.arange(len(etiquetas))
        teoricos = [p] + [mat.probabilidad_error_bit(n, p) for n in codigos]
        piso = 1e-7
        ancho = 0.38 if sim else 0.6
        desplazamiento = ancho / 2 if sim else 0
        ax.bar(x - desplazamiento, [max(v, piso) for v in teoricos], width=ancho, color=e.SERIES[0],
               edgecolor=e.PANEL, linewidth=2, label="Teórico")
        filas = []
        if sim:
            total = sum(r.bits_totales for r in sim)
            ber_sin = sum(r.sin_codigo.errores_residuales for r in sim) / total
            observados = [ber_sin] + [r.con_codigo.ber_residual for r in sim]
            ax.bar(x + desplazamiento, [max(v, piso) for v in observados], width=ancho, color=e.SERIES[1],
                   edgecolor=e.PANEL, linewidth=2, label="Experimental")
            for xi, v in zip(x, observados):
                ax.annotate("0 err." if v == 0 else _fmt(v), (xi + desplazamiento, max(v, piso)),
                            textcoords="offset points", xytext=(0, 5), ha="center", fontsize=8, color=e.TEXTO_2)
            ok_sin = sum(r.mensajes_ok_sin_codigo for r in sim)
            filas.append(["sin código", 1.0, p, ber_sin, total, total, f"{ok_sin}/{100 * len(sim)}"])
            for r in sim:
                filas.append([r.n, 1 / r.n, r.ber_teorica_con_codigo, r.con_codigo.ber_residual, r.bits_totales,
                              r.con_codigo.bits_transmitidos, f"{r.mensajes_ok_con_codigo}/{r.ensayos}"])
        else:
            filas = [["sin código", 1.0, p, "", "", "", ""]] + [
                [n, 1 / n, mat.probabilidad_error_bit(n, p), "", "", "", ""] for n in codigos]
        ax.set_yscale("log")
        ax.set_ylim(bottom=piso, top=1)
        ax.grid(axis="x", visible=False)
        ax.set_axisbelow(True)
        ax.set_xticks(x, etiquetas)
        ax.set_title(f"BER residual con y sin código de repetición (p = {p:g})")
        ax.set_xlabel("Esquema de transmisión")
        ax.set_ylabel("BER residual por bit útil (escala log)")
        self._leyenda(ax, loc="upper right")
        descripcion = (
            "Sin código, cada bit útil falla con probabilidad p. Con repetición, el error baja a P_e(n, p), "
            "pero por cada bit útil se transmiten n bits."
        )
        if sim:
            descripcion += (
                f" Experimento: para cada n, 100 mensajes aleatorios de {max(self.spin_bits.value() // 100, 1)} "
                "bits enviados por el mismo canal sin y con código (columna “mensajes íntegros”)."
            )
        else:
            descripcion += " Pulse <b>Ejecutar simulación</b> para medirlo experimentalmente."
        return (["esquema", "R", "BER teórica", "BER experimental", "bits útiles", "bits transmitidos",
                 "mensajes íntegros"], filas, descripcion)

    # --- teórico vs experimental -----------------------------------------------
    def _g_exp_vs_teo(self, ax, codigos):
        ps = np.linspace(0.005, 0.5, 100)
        ax.set_yscale("log")
        ax.set_title("BER residual: teoría (líneas) frente a simulación Monte Carlo (puntos, IC 95 %)")
        ax.set_xlabel("p = probabilidad de inversión de bit del canal")
        ax.set_ylabel("BER residual por bit de información (escala log)")
        ax.set_xlim(0, 0.52)
        sim = self._simulacion_vigente("exp_vs_teo", codigos)
        filas = []
        for i, n in enumerate(codigos):
            color = e.color_serie(i, len(codigos))
            ax.plot(ps, [max(mat.probabilidad_error_bit(n, p), PISO_LOG) for p in ps], color=color, linewidth=1.5,
                    label=f"n = {n} (teórica)")
            if not sim:
                continue
            for r in (r for r in sim if r.n == n):
                teo = mat.probabilidad_error_bit(n, r.p)
                bajo, alto = r.intervalo_95
                self._marcar_experimental(ax, r.p, r, color, e.marcador_serie(i))
                filas.append([n, r.p, r.num_bits, r.errores_canal, r.ber_canal, r.errores_residuales,
                              r.ber_residual, bajo, alto, teo, "sí" if bajo <= teo <= alto else "no"])
        ax.set_ylim(bottom=1e-6, top=1)
        if sim:
            ax.plot([], [], marker="o", color=e.TEXTO_2, linestyle="none", label="Simulación (IC 95 %)")
            ax.plot([], [], marker="v", color=e.TEXTO_2, linestyle="none", markerfacecolor="none",
                    label="0 errores: cota sup. 95 %")
            dentro = sum(1 for f in filas if f[-1] == "sí")
            descripcion = (
                f"Simulación con {self.spin_bits.value():,} bits".replace(",", ".")
                + f" de información por punto y semilla {self.spin_semilla.value()} (empates resueltos al azar). "
                f"{dentro} de {len(filas)} valores teóricos caen dentro del intervalo de confianza del 95 % de la "
                "estimación; por azar se espera que alrededor de 1 de cada 20 quede fuera. Los puntos son "
                "estimaciones aleatorias; las líneas, valores teóricos exactos. La BER del canal (≈ p) y la BER "
                "residual tras decodificar son magnitudes distintas: ver la tabla de datos."
            )
        else:
            descripcion = ("Se muestran solo las curvas teóricas. Pulse <b>Ejecutar simulación</b> para estimar "
                           "experimentalmente la BER residual en varios valores de p.")
        self._leyenda(ax, loc="lower right", ncols=2 if len(codigos) > 4 else 1)
        return (["n", "p", "bits", "errores canal", "BER canal", "errores residuales", "BER residual",
                 "IC95 inf", "IC95 sup", "P_e teórica", "teórica en IC"], filas, descripcion)

    # --- error vs p ---------------------------------------------------------------
    def _g_pe_vs_p(self, ax, codigos):
        ps = np.linspace(0.005, 0.5, 100)
        ax.plot(ps, ps, color=e.TEXTO_2, linestyle="--", linewidth=1.5, label="Sin código: error = p")
        for i, n in enumerate(codigos):
            pe = [mat.probabilidad_error_bit(n, p) for p in ps]
            ax.plot(ps, np.maximum(pe, PISO_LOG), color=e.color_serie(i, len(codigos)), label=f"n = {n}",
                    marker=e.marcador_serie(i), markevery=12, markersize=6)
        filas = [[p] + [mat.probabilidad_error_bit(n, p) for n in codigos] for p in (0.01, 0.05, 0.1, 0.2, 0.3, 0.5)]
        ax.set_yscale("log")
        ax.set_ylim(bottom=max(PISO_LOG, ax.get_ylim()[0]))
        ax.set_xlim(0, 0.5)
        ax.set_title("Error residual tras la decodificación por mayoría (teórico)")
        ax.set_xlabel("p = probabilidad de inversión de bit del canal")
        ax.set_ylabel("P_e = error residual por bit de información (escala log)")
        self._leyenda(ax, loc="lower right", ncols=2 if len(codigos) > 6 else 1)
        return (["p"] + [f"P_e (n={n})" for n in codigos], filas,
                "La línea discontinua es el error sin código. Para 0 &lt; p &lt; 0.5 los códigos impares más largos "
                "reducen el error; en p = 0.5 todas las curvas valen 0.5: ningún código ayuda. Los códigos pares "
                "(desempate aleatorio) coinciden con el impar anterior.")

    # --- capacidad ----------------------------------------------------------------
    def _g_c_vs_p(self, ax, codigos):
        ps = np.linspace(0, 0.5, 201)
        ax.plot(ps, [mat.capacidad_bsc(float(p)) for p in ps], color=e.CIAN, linewidth=2.5, label="C(p) = 1 − H₂(p)")
        filas = []
        for i, n in enumerate(codigos[:8]):
            R = mat.tasa_codigo(n)
            ps_ = p_umbral(R)
            color = e.color_serie(i, min(len(codigos), 8))
            ax.axhline(R, color=color, linestyle="--", linewidth=1.2, label=f"R = 1/{n} (cruza en p* ≈ {ps_:.3f})")
            ax.plot([ps_], [R], marker=e.marcador_serie(i), color=color, markersize=8)
            filas.append([n, R, ps_])
        ax.set_xlim(0, 0.5)
        ax.set_ylim(0, 1.05)
        ax.set_title("Capacidad del canal binario simétrico")
        ax.set_xlabel("p = probabilidad de inversión de bit")
        ax.set_ylabel("C (bits de información por uso del canal)")
        self._leyenda(ax, loc="upper right")
        tabla_c = ", ".join(f"C({q:g}) = {mat.capacidad_bsc(q):.3f}" for q in (0, 0.01, 0.05, 0.1, 0.2, 0.3, 0.5))
        nota = " (se muestran las primeras 8 tasas)" if len(codigos) > 8 else ""
        return (["n", "R = 1/n", "p* tal que C(p*) = R"], filas,
                f"{tabla_c}. La capacidad decrece de 1 a 0 cuando p va de 0 a 0.5. Para cada código, R &lt; C "
                "solo cuando p &lt; p*: a la izquierda del cruce la teoría de Shannon admite comunicación confiable a "
                "esa tasa (con algún código, no necesariamente el de repetición)" + nota + ".")

    # --- tasa vs n ----------------------------------------------------------------
    def _g_r_vs_n(self, ax, codigos):
        ns = np.arange(mat.N_MIN, mat.N_MAX + 1)
        ax.plot(ns, [mat.tasa_codigo(int(n)) for n in ns], color=e.SERIES[0], marker="o", label="R = 1/n")
        ax.scatter(codigos, [mat.tasa_codigo(n) for n in codigos], s=110, facecolors="none", edgecolors=e.CIAN,
                   linewidths=2, zorder=3, label="Códigos seleccionados")
        for n in codigos[:8]:
            ax.annotate(f"{mat.tasa_codigo(n):.3f}", (n, mat.tasa_codigo(n)), textcoords="offset points",
                        xytext=(6, 6), fontsize=8, color=e.TEXTO_2)
        ax.set_xticks(ns)
        ax.set_ylim(0, 1.05)
        ax.set_title("Tasa del código de repetición")
        ax.set_xlabel("n = longitud del código (bits transmitidos por bit de información)")
        ax.set_ylabel("R = 1/n (bits de información por bit transmitido)")
        self._leyenda(ax, loc="upper right")
        filas = [[int(n), mat.tasa_codigo(int(n)), mat.redundancia(int(n))] for n in ns]
        return (["n", "R = 1/n", "Redundancia n−1"], filas,
                "Cuando n crece la tasa cae como 1/n y tiende a 0: con n = 3 solo un tercio de los bits enviados es "
                "información, con n = 7 apenas un séptimo. Toda la mejora en fiabilidad se paga con esta pérdida "
                "de eficiencia.")

    # --- redundancia vs fiabilidad --------------------------------------------------
    def _g_pe_vs_red(self, ax, codigos):
        p = self.spin_p.value()
        ns = np.arange(mat.N_MIN, mat.N_MAX + 1)
        red = ns - 1
        pe = np.array([mat.probabilidad_error_bit(int(n), p) for n in ns])
        impar = ns % 2 == 1
        ax.plot(red, np.maximum(pe, PISO_LOG), color=e.TEXTO_3, linewidth=1, zorder=1)
        ax.scatter(red[impar], np.maximum(pe[impar], PISO_LOG), color=e.SERIES[0], marker="o", s=50, zorder=2,
                   label="n impar")
        ax.scatter(red[~impar], np.maximum(pe[~impar], PISO_LOG), color=e.SERIES[1], marker="s", s=50, zorder=2,
                   label="n par (desempate aleatorio)")
        ax.axhline(p, color=e.TEXTO_2, linestyle="--", linewidth=1.2, label=f"Sin código: p = {p:g}")
        sel = np.array(codigos)
        ax.scatter(sel - 1, [max(mat.probabilidad_error_bit(n, p), PISO_LOG) for n in codigos], s=130,
                   facecolors="none", edgecolors=e.CIAN, linewidths=2, zorder=3, label="Códigos seleccionados")
        ax.set_yscale("log")
        ax.set_xticks(red)
        ax.set_title(f"Fiabilidad frente a redundancia (p = {p:g})")
        ax.set_xlabel("Redundancia n − 1 (bits redundantes por bit de información)")
        ax.set_ylabel("P_e = error residual por bit (escala log)")
        self._leyenda(ax, loc="lower left")
        filas = [[int(n), int(n - 1), float(v)] for n, v in zip(ns, pe)]
        return (["n", "Redundancia", "P_e"], filas,
                "Cada par de bits redundantes adicionales reduce el error residual de forma aproximadamente "
                "exponencial, pero el bit que convierte un código impar en par no aporta mejora.")

    # --- t vs n -------------------------------------------------------------------
    def _g_t_vs_n(self, ax, codigos):
        ns = np.arange(mat.N_MIN, mat.N_MAX + 1)
        ts = [mat.capacidad_correccion(int(n)) for n in ns]
        impares = [n for n in ns if n % 2]
        pares = [n for n in ns if n % 2 == 0]
        ax.plot(ns, ts, color=e.TEXTO_3, linewidth=1, zorder=1)
        ax.scatter(impares, [mat.capacidad_correccion(int(n)) for n in impares], color=e.SERIES[0], marker="o",
                   s=50, zorder=2, label="n impar")
        ax.scatter(pares, [mat.capacidad_correccion(int(n)) for n in pares], color=e.SERIES[1], marker="s",
                   s=50, zorder=2, label="n par (mismo t que n − 1)")
        ax.plot(ns, ns - 1, color=e.SERIES[2], linestyle=":", linewidth=1.5, label="Detección garantizada: d − 1 = n − 1")
        ax.scatter(codigos, [mat.capacidad_correccion(n) for n in codigos], s=130, facecolors="none",
                   edgecolors=e.CIAN, linewidths=2, zorder=3, label="Códigos seleccionados")
        ax.set_xticks(ns)
        ax.set_title("Capacidad de corrección garantizada t = ⌊(n − 1)/2⌋")
        ax.set_xlabel("n = longitud del código (bits)")
        ax.set_ylabel("Errores por bloque (bits)")
        self._leyenda(ax, loc="upper left")
        filas = [[int(n), 1, 2, mat.distancia_minima(int(n)), mat.capacidad_correccion(int(n)),
                  mat.capacidad_deteccion(int(n))] for n in ns]
        return (["n", "k", "M", "d", "t (corrige)", "d−1 (detecta)"], filas,
                "t crece en escalones: pasar de n impar a n par no corrige ningún error adicional, porque con "
                "n/2 errores el bloque queda empatado; la detección garantizada sí crece con cada bit.")

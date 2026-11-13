"""Estadísticas y gráficas: curvas teóricas y verificación Monte Carlo."""

from __future__ import annotations

import numpy as np
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QGridLayout,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from core import matematicas as mat
from core.decodificador import PoliticaDesempate
from core.simulador import crear_generador, simular_ber
from interfaz import estilos as e
from interfaz.componentes import Aviso, LienzoGrafica, Panel, etiqueta, fila, pagina_desplazable

GRAFICAS = [
    ("pe_vs_p", "1 · Probabilidad de error del canal frente a error residual"),
    ("r_vs_n", "2 · Longitud del código frente a tasa"),
    ("t_vs_n", "3 · Longitud del código frente a capacidad de corrección"),
    ("pe_vs_red", "4 · Redundancia frente a error residual"),
    ("c_vs_p", "5 · Probabilidad de error frente a capacidad del canal"),
    ("pe_vs_r", "6 · Error residual frente a tasa (distintos códigos)"),
    ("exp_vs_teo", "7 · Resultados experimentales frente a teóricos (Monte Carlo)"),
]
P_SIMULACION = [0.01, 0.02, 0.05, 0.08, 0.1, 0.15, 0.2, 0.3, 0.4, 0.5]
PISO_LOG = 1e-15  # límite inferior del eje logarítmico


def interpretar_codigos(texto: str) -> list[int]:
    """'3, 5, 7' o '1-21' o '3,9-11' -> lista ordenada de longitudes válidas."""
    valores: set[int] = set()
    for parte in texto.replace(";", ",").split(","):
        parte = parte.strip()
        if not parte:
            continue
        if "-" in parte:
            a, b = (int(x) for x in parte.split("-", 1))
            valores.update(range(min(a, b), max(a, b) + 1))
        else:
            valores.add(int(parte))
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


class PaginaEstadisticas(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._simulacion = None  # (parámetros, resultados) de la última simulación
        area, lay = pagina_desplazable(
            "Estadísticas y gráficas",
            "Compare códigos de repetición: curvas teóricas exactas y estimaciones experimentales "
            "mediante simulación Monte Carlo sobre el mismo codificador, canal y decodificador.",
        )
        raiz = QVBoxLayout(self)
        raiz.setContentsMargins(0, 0, 0, 0)
        raiz.addWidget(area)

        # --- filtros (una sola franja sobre la gráfica) ---
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
        self.spin_p.setToolTip("p fija para las gráficas 4 y 6.")
        self.spin_bits = QSpinBox()
        self.spin_bits.setRange(1_000, 1_000_000)
        self.spin_bits.setSingleStep(10_000)
        self.spin_bits.setValue(50_000)
        self.spin_bits.setToolTip("Bits de información simulados por cada punto (n, p).")
        self.spin_semilla = QSpinBox()
        self.spin_semilla.setRange(0, 2**31 - 1)
        self.spin_semilla.setValue(2026)
        self.btn_simular = QPushButton("Ejecutar simulación")
        self.btn_simular.setObjectName("primario")
        self.btn_simular.clicked.connect(self.simular)

        rej = QGridLayout()
        rej.setHorizontalSpacing(12)
        rej.setVerticalSpacing(8)
        rej.addWidget(etiqueta("Gráfica"), 0, 0)
        rej.addWidget(self.cmb_grafica, 0, 1, 1, 3)
        rej.addWidget(etiqueta("Códigos (n)"), 1, 0)
        rej.addWidget(self.txt_codigos, 1, 1)
        rej.addLayout(fila(btn_357, btn_impares, btn_todos, espaciado=6, estirar_final=True), 1, 2, 1, 2)
        self.lbl_p = etiqueta("p fija")
        rej.addWidget(self.lbl_p, 2, 0)
        rej.addWidget(self.spin_p, 2, 1)
        self.fila_sim = fila(
            etiqueta("Bits por punto", ajustar=False), self.spin_bits,
            etiqueta("Semilla", ajustar=False), self.spin_semilla, self.btn_simular,
            espaciado=8, estirar_final=True,
        )
        rej.addLayout(self.fila_sim, 3, 0, 1, 4)
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
    def actualizar(self) -> None:
        clave = self.cmb_grafica.currentData()
        usa_p = clave in ("pe_vs_red", "pe_vs_r")
        self.lbl_p.setVisible(usa_p)
        self.spin_p.setVisible(usa_p)
        for i in range(self.fila_sim.count()):
            w = self.fila_sim.itemAt(i).widget()
            if w:
                w.setVisible(clave == "exp_vs_teo")
        try:
            codigos = interpretar_codigos(self.txt_codigos.text())
        except ValueError as exc:
            self.aviso.mostrar("error", str(exc))
            return
        self.aviso.ocultar()
        ax = self.lienzo.nuevo_eje()
        metodo = getattr(self, f"_g_{clave}")
        encabezados, filas, descripcion = metodo(ax, codigos)
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

    # --- 1 ------------------------------------------------------------
    def _g_pe_vs_p(self, ax, codigos):
        ps = np.linspace(0.005, 0.5, 100)
        ax.plot(ps, ps, color=e.TEXTO_2, linestyle="--", linewidth=1.5, label="Sin codificar: BER del canal = p")
        filas = []
        for i, n in enumerate(codigos):
            pe = [mat.probabilidad_error_bit(n, p) for p in ps]
            ax.plot(ps, np.maximum(pe, PISO_LOG), color=e.color_serie(i, len(codigos)), label=f"n = {n}",
                    marker=e.marcador_serie(i), markevery=12, markersize=6)
        for p in (0.01, 0.05, 0.1, 0.2, 0.3, 0.5):
            filas.append([p] + [mat.probabilidad_error_bit(n, p) for n in codigos])
        ax.set_yscale("log")
        ax.set_ylim(bottom=max(PISO_LOG, ax.get_ylim()[0]))
        ax.set_xlim(0, 0.5)
        ax.set_title("BER residual tras la decodificación por mayoría (teórica)")
        ax.set_xlabel("p = probabilidad de inversión de bit del canal (BER del canal)")
        ax.set_ylabel("P_e = BER residual por bit de información (escala log)")
        self._leyenda(ax, loc="lower right", ncols=2 if len(codigos) > 6 else 1)
        return (["p"] + [f"P_e (n={n})" for n in codigos], filas,
                "La línea discontinua es la BER del canal (sin codificar). Cada curva es la probabilidad teórica de "
                "error residual por bit tras decodificar. Para p &lt; 0.5 los códigos impares más largos reducen el "
                "error; en p = 0.5 todas las curvas valen 0.5: ningún código ayuda. Los códigos pares (desempate "
                "aleatorio) coinciden con el impar anterior.")

    # --- 2 ------------------------------------------------------------
    def _g_r_vs_n(self, ax, codigos):
        ns = np.arange(mat.N_MIN, mat.N_MAX + 1)
        rs = [mat.tasa_codigo(int(n)) for n in ns]
        ax.plot(ns, rs, color=e.SERIES[0], marker="o", label="R = 1/n")
        sel = [n for n in codigos]
        ax.scatter(sel, [mat.tasa_codigo(n) for n in sel], s=110, facecolors="none", edgecolors=e.CIAN,
                   linewidths=2, zorder=3, label="Códigos seleccionados")
        for n in sel[:8]:
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
                "La tasa cae como 1/n: con n = 3 solo un tercio de los bits enviados es información. "
                "Toda la mejora en confiabilidad se paga con esta pérdida de eficiencia.")

    # --- 3 ------------------------------------------------------------
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
        ax.plot(ns, ns - 1, color=e.SERIES[2], linestyle=":", linewidth=1.5, label="Detección garantizada: n − 1")
        ax.scatter(codigos, [mat.capacidad_correccion(n) for n in codigos], s=130, facecolors="none",
                   edgecolors=e.CIAN, linewidths=2, zorder=3, label="Códigos seleccionados")
        ax.set_xticks(ns)
        ax.set_title("Capacidad de corrección garantizada t = ⌊(n − 1)/2⌋")
        ax.set_xlabel("n = longitud del código (bits)")
        ax.set_ylabel("Errores por bloque (bits)")
        self._leyenda(ax, loc="upper left")
        filas = [[int(n), mat.distancia_minima(int(n)), mat.capacidad_correccion(int(n)),
                  mat.capacidad_deteccion(int(n))] for n in ns]
        return (["n", "d_min", "t (corrige)", "n−1 (detecta)"], filas,
                "t crece en escalones: aumentar n de impar a par no corrige ningún error adicional, porque "
                "d_min = n par permite detectar, pero no corregir, el patrón de n/2 errores (empate).")

    # --- 4 ------------------------------------------------------------
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
        ax.axhline(p, color=e.TEXTO_2, linestyle="--", linewidth=1.2, label=f"Sin codificar: p = {p:g}")
        sel = np.array(codigos)
        ax.scatter(sel - 1, [max(mat.probabilidad_error_bit(n, p), PISO_LOG) for n in codigos], s=130,
                   facecolors="none", edgecolors=e.CIAN, linewidths=2, zorder=3, label="Códigos seleccionados")
        ax.set_yscale("log")
        ax.set_xticks(red)
        ax.set_title(f"Error residual frente a redundancia (p = {p:g})")
        ax.set_xlabel("Redundancia n − 1 (bits redundantes por bit de información)")
        ax.set_ylabel("P_e = BER residual por bit (escala log)")
        self._leyenda(ax, loc="lower left")
        filas = [[int(n), int(n - 1), float(v)] for n, v in zip(ns, pe)]
        return (["n", "Redundancia", "P_e"], filas,
                "Cada par de bits redundantes adicionales reduce el error residual de forma aproximadamente "
                "exponencial, pero el bit que convierte un código impar en par no aporta mejora.")

    # --- 5 ------------------------------------------------------------
    def _g_c_vs_p(self, ax, codigos):
        ps = np.linspace(0, 0.5, 201)
        cs = [mat.capacidad_bsc(float(p)) for p in ps]
        ax.plot(ps, cs, color=e.CIAN, linewidth=2.5, label="C(p) = 1 − H₂(p)")
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
        nota = " (se muestran las primeras 8 tasas)" if len(codigos) > 8 else ""
        return (["n", "R = 1/n", "p* tal que C(p*) = R"], filas,
                "C(0) = 1 y C(0.5) = 0. Para cada código, R &lt; C solo cuando p &lt; p*: a la izquierda del cruce "
                "la teoría de Shannon admite comunicación confiable a esa tasa (con algún código, no necesariamente "
                "el de repetición)" + nota + ".")

    # --- 6 ------------------------------------------------------------
    def _g_pe_vs_r(self, ax, codigos):
        p = self.spin_p.value()
        C = mat.capacidad_bsc(p)
        filas = []
        ns = list(range(mat.N_MIN, mat.N_MAX + 1, 2))
        rs = [mat.tasa_codigo(n) for n in ns]
        pes = [max(mat.probabilidad_error_bit(n, p), PISO_LOG) for n in ns]
        ax.plot(rs, pes, color=e.TEXTO_3, linewidth=1, zorder=1, label="Códigos impares 1–21")
        for i, n in enumerate(codigos):
            R, pe = mat.tasa_codigo(n), mat.probabilidad_error_bit(n, p)
            color = e.color_serie(i, len(codigos))
            ax.scatter([R], [max(pe, PISO_LOG)], color=color, marker=e.marcador_serie(i), s=70, zorder=3,
                       edgecolors=e.PANEL, linewidths=1.5, label=f"n = {n}" if len(codigos) <= 8 else None)
            if len(codigos) <= 8:
                ax.annotate(f"n={n}", (R, max(pe, PISO_LOG)), textcoords="offset points", xytext=(6, 4),
                            fontsize=8, color=e.TEXTO_2)
            filas.append([n, R, pe, "sí" if R < C else "no"])
        ax.axvline(C, color=e.CIAN, linestyle="--", linewidth=1.5, label=f"Capacidad C = {C:.3f}")
        ax.axvspan(0, C, color=e.CIAN, alpha=0.06)
        ax.set_yscale("log")
        ax.set_xlim(0, 1.05)
        ax.set_title(f"Compromiso error–tasa de los códigos de repetición (p = {p:g})")
        ax.set_xlabel("R = tasa del código (bits de información por bit transmitido)")
        ax.set_ylabel("P_e = BER residual por bit (escala log)")
        self._leyenda(ax, loc="lower right")
        return (["n", "R", "P_e", "R < C"], filas,
                "Zona sombreada: tasas por debajo de la capacidad. Shannon garantiza que existen códigos con "
                "error arbitrariamente pequeño en cualquier tasa R &lt; C; los de repetición solo reducen el error "
                "llevando R hacia 0, por eso su curva no alcanza la esquina inferior derecha de esa zona.")

    # --- 7 ------------------------------------------------------------
    def _parametros_simulacion(self, codigos):
        return (tuple(codigos), self.spin_bits.value(), self.spin_semilla.value())

    def simular(self) -> None:
        try:
            codigos = interpretar_codigos(self.txt_codigos.text())
        except ValueError as exc:
            self.aviso.mostrar("error", str(exc))
            return
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            num_bits = self.spin_bits.value()
            _, rng = crear_generador(self.spin_semilla.value())
            resultados = {
                n: [simular_ber(n, p, num_bits, politica=PoliticaDesempate.ALEATORIO, generador=rng)
                    for p in P_SIMULACION]
                for n in codigos
            }
            self._simulacion = (self._parametros_simulacion(codigos), resultados)
        finally:
            QApplication.restoreOverrideCursor()
        self.actualizar()

    def _g_exp_vs_teo(self, ax, codigos):
        ps = np.linspace(0.005, 0.5, 100)
        ax.set_yscale("log")
        ax.set_title("BER residual: teoría (líneas) frente a simulación Monte Carlo (puntos, IC 95 %)")
        ax.set_xlabel("p = probabilidad de inversión de bit del canal")
        ax.set_ylabel("BER residual por bit de información (escala log)")
        ax.set_xlim(0, 0.52)
        vigente = self._simulacion is not None and self._simulacion[0] == self._parametros_simulacion(codigos)
        filas = []
        for i, n in enumerate(codigos):
            color = e.color_serie(i, len(codigos))
            ax.plot(ps, [max(mat.probabilidad_error_bit(n, p), PISO_LOG) for p in ps], color=color, linewidth=1.5,
                    label=f"n = {n} (teórica)")
            if not vigente:
                continue
            for r in self._simulacion[1][n]:
                teo = mat.probabilidad_error_bit(n, r.p)
                bajo, alto = r.intervalo_95
                if r.errores_residuales > 0:
                    ax.errorbar([r.p], [r.ber_residual], yerr=[[r.ber_residual - bajo], [alto - r.ber_residual]],
                                fmt=e.marcador_serie(i), color=color, markersize=7, capsize=3,
                                markeredgecolor=e.PANEL)
                else:
                    # Cero errores observados: solo se conoce una cota superior (IC 95 %).
                    ax.plot([r.p], [alto], marker="v", color=color, markersize=7, markerfacecolor="none")
                filas.append([n, r.p, r.num_bits, r.errores_canal, r.ber_canal, r.errores_residuales,
                              r.ber_residual, bajo, alto, teo, "sí" if bajo <= teo <= alto else "no"])
        ax.set_ylim(bottom=1e-7, top=1)
        if vigente:
            ax.plot([], [], marker="o", color=e.TEXTO_2, linestyle="none", label="Simulación (IC 95 %)")
            ax.plot([], [], marker="v", color=e.TEXTO_2, linestyle="none", markerfacecolor="none",
                    label="0 errores: cota sup. 95 %")
            dentro = sum(1 for f in filas if f[-1] == "sí")
            descripcion = (
                f"Simulación con {self.spin_bits.value():,} bits".replace(",", ".")
                + f" de información por punto y semilla {self.spin_semilla.value()} (empates resueltos al azar). {dentro} de {len(filas)} valores "
                "teóricos caen dentro del intervalo de confianza del 95 % de la estimación; con un 95 % de "
                "confianza se espera que alrededor de 1 de cada 20 quede fuera por azar. Los puntos son "
                "estimaciones aleatorias; las líneas, valores teóricos exactos."
            )
        else:
            descripcion = (
                "Se muestran solo las curvas teóricas. Pulse <b>Ejecutar simulación</b> para estimar "
                "experimentalmente la BER residual transmitiendo bits aleatorios por el canal BSC."
            )
        self._leyenda(ax, loc="lower right", ncols=2 if len(codigos) > 4 else 1)
        return (["n", "p", "bits", "errores canal", "BER canal", "errores residuales", "BER residual",
                 "IC95 inf", "IC95 sup", "P_e teórica", "teórica en IC"], filas, descripcion)

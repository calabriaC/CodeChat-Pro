"""Fundamento matemático: parámetros del código, capacidad del BSC y error residual."""

from __future__ import annotations

import math

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDoubleSpinBox,
    QGridLayout,
    QHeaderView,
    QSlider,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from core import matematicas as mat
from interfaz import estilos as e
from interfaz.componentes import LienzoGrafica, Panel, Tarjeta, etiqueta, fila, pagina_desplazable


def _fmt(x: float) -> str:
    """Formato legible para probabilidades que van de 1 a 1e-30."""
    if x == 0:
        return "0"
    if x >= 1e-3:
        return f"{x:.6f}".rstrip("0").rstrip(".")
    return f"{x:.4e}"


class PaginaFundamento(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        area, lay = pagina_desplazable(
            "Fundamento matemático",
            "Ajuste n y p para calcular los parámetros (n, k, M, d) del código de repetición, la capacidad "
            "del canal y la probabilidad teórica de error tras la decodificación por mayoría. Todos los "
            "valores de esta pestaña son teóricos y exactos.",
        )
        raiz = QVBoxLayout(self)
        raiz.setContentsMargins(0, 0, 0, 0)
        raiz.addWidget(area)

        # --- controles ---
        controles = Panel("Parámetros")
        self.spin_n = QSpinBox()
        self.spin_n.setRange(mat.N_MIN, mat.N_MAX)
        self.spin_n.setValue(5)
        self.slider_n = QSlider(Qt.Horizontal)
        self.slider_n.setRange(mat.N_MIN, mat.N_MAX)
        self.slider_n.setValue(5)
        self.spin_n.valueChanged.connect(self.slider_n.setValue)
        self.slider_n.valueChanged.connect(self.spin_n.setValue)

        self.spin_p = QDoubleSpinBox()
        self.spin_p.setRange(mat.P_MIN, mat.P_MAX)
        self.spin_p.setDecimals(4)
        self.spin_p.setSingleStep(0.01)
        self.spin_p.setValue(0.10)
        self.slider_p = QSlider(Qt.Horizontal)
        self.slider_p.setRange(0, 500)
        self.slider_p.setValue(100)
        self.slider_p.valueChanged.connect(lambda v: self.spin_p.setValue(v / 1000))
        self.spin_p.valueChanged.connect(self._sincronizar_slider_p)

        self.spin_k = QSpinBox()
        self.spin_k.setRange(1, 10_000)
        self.spin_k.setValue(20)
        self.spin_k.setSuffix(" caracteres ASCII")
        self.spin_k.setToolTip("Longitud del mensaje para calcular la probabilidad de fallo del mensaje (8 bits por carácter).")

        rej = QGridLayout()
        rej.setHorizontalSpacing(14)
        rej.addWidget(etiqueta("Longitud n"), 0, 0)
        rej.addWidget(self.spin_n, 0, 1)
        rej.addWidget(self.slider_n, 0, 2)
        rej.addWidget(etiqueta("Probabilidad p"), 1, 0)
        rej.addWidget(self.spin_p, 1, 1)
        rej.addWidget(self.slider_p, 1, 2)
        rej.addWidget(etiqueta("Mensaje de"), 2, 0)
        rej.addWidget(self.spin_k, 2, 1)
        rej.setColumnStretch(2, 1)
        controles.cuerpo.addLayout(rej)
        lay.addWidget(controles)

        # --- tarjetas ---
        self.tarjetas = {
            "dmin": Tarjeta("Distancia mínima d_min", e.CIAN),
            "t": Tarjeta("Corrección garantizada t", e.VERDE),
            "R": Tarjeta("Tasa del código R", e.AZUL),
            "C": Tarjeta("Capacidad del canal C", e.CIAN),
            "pe": Tarjeta("Error residual por bit P_e", e.ROJO),
            "pm": Tarjeta("Fallo del mensaje completo", e.NARANJA),
        }
        rej_t = QGridLayout()
        rej_t.setSpacing(12)
        for i, t in enumerate(self.tarjetas.values()):
            rej_t.addWidget(t, i // 3, i % 3)
        lay.addLayout(rej_t)

        # --- explicaciones ---
        self.panel_codigo = Panel("1 · Parámetros del código de repetición")
        self.lbl_codigo = etiqueta("")
        self.panel_codigo.cuerpo.addWidget(self.lbl_codigo)

        self.panel_canal = Panel("2 · Capacidad del canal binario simétrico")
        self.lbl_canal = etiqueta("")
        self.panel_canal.cuerpo.addWidget(self.lbl_canal)

        self.panel_error = Panel("3 · Probabilidad de error residual (decodificación por mayoría)")
        self.lbl_error = etiqueta("")
        self.grafica = LienzoGrafica(alto=3.4)
        self.panel_error.cuerpo.addWidget(self.lbl_error)
        self.panel_error.cuerpo.addWidget(self.grafica)

        self.panel_rc = Panel("4 · Interpretación: tasa R frente a capacidad C")
        self.lbl_rc = etiqueta("")
        self.panel_rc.cuerpo.addWidget(self.lbl_rc)

        self.panel_tabla = Panel("5 · Tabla de referencia: capacidad y P_e para n = 3, 5 y 7")
        self.tabla_ref = QTableWidget()
        self.tabla_ref.verticalHeader().setVisible(False)
        self.tabla_ref.setEditTriggers(QTableWidget.NoEditTriggers)
        self.tabla_ref.setAlternatingRowColors(True)
        self.tabla_ref.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.tabla_ref.setMinimumHeight(330)
        self.panel_tabla.cuerpo.addWidget(self.tabla_ref)
        self.panel_tabla.cuerpo.addWidget(etiqueta(
            "Lectura: al crecer n la tasa cae (1/3 → 1/5 → 1/7) y P_e disminuye para 0 &lt; p &lt; 0.5; "
            "en p = 0.5 ningún código ayuda (C = 0 y P_e = 0.5). Una casilla “R &lt; C” indica que la "
            "tasa del código está por debajo de la capacidad, no que el error sea pequeño.", "secundario"))
        self._llenar_tabla_referencia()

        for p in (self.panel_codigo, self.panel_canal, self.panel_error, self.panel_rc, self.panel_tabla):
            lay.addWidget(p)
        lay.addStretch(1)

        for w in (self.spin_n, self.spin_p, self.spin_k):
            w.valueChanged.connect(self.actualizar)
        self.actualizar()

    # ------------------------------------------------------------------
    def _llenar_tabla_referencia(self) -> None:
        valores_p = [0.0, 0.01, 0.05, 0.1, 0.2, 0.3, 0.4, 0.5]
        columnas = ["p", "H₂(p)", "C = 1 − H₂(p)", "P_e n=3 (R=0.333)", "P_e n=5 (R=0.2)",
                    "P_e n=7 (R=0.143)", "n ∈ {3,5,7} con R < C"]
        self.tabla_ref.setColumnCount(len(columnas))
        self.tabla_ref.setHorizontalHeaderLabels(columnas)
        self.tabla_ref.setRowCount(len(valores_p))
        for i, p in enumerate(valores_p):
            C = mat.capacidad_bsc(p)
            fila_datos = [f"{p:g}", f"{mat.entropia_binaria(p):.4f}", f"{C:.4f}"]
            fila_datos += [_fmt(mat.probabilidad_error_bit(n, p)) for n in (3, 5, 7)]
            fila_datos.append(", ".join(str(n) for n in (3, 5, 7) if mat.tasa_codigo(n) < C) or "ninguno")
            for j, v in enumerate(fila_datos):
                item = QTableWidgetItem(v)
                item.setTextAlignment(Qt.AlignCenter)
                self.tabla_ref.setItem(i, j, item)

    def _sincronizar_slider_p(self, valor: float) -> None:
        # Sin bloquear señales, el slider (paso 0.001) redondearía el valor escrito.
        self.slider_p.blockSignals(True)
        self.slider_p.setValue(round(valor * 1000))
        self.slider_p.blockSignals(False)

    def actualizar(self) -> None:
        n = self.spin_n.value()
        p = self.spin_p.value()
        k_bits = 8 * self.spin_k.value()

        dmin = mat.distancia_minima(n)
        t = mat.capacidad_correccion(n)
        R = mat.tasa_codigo(n)
        H = mat.entropia_binaria(p)
        C = mat.capacidad_bsc(p)
        pe = mat.probabilidad_error_bit(n, p)
        p_estricta = mat.probabilidad_error_mayoria_estricta(n, p)
        p_empate = mat.probabilidad_empate(n, p)
        pm = mat.probabilidad_fallo_mensaje(n, p, k_bits)
        pm_amb = mat.probabilidad_fallo_mensaje(n, p, k_bits, empates_como_fallo=True)

        self.tarjetas["dmin"].establecer(str(dmin), f"Detecta hasta {mat.capacidad_deteccion(n)} errores por bloque")
        self.tarjetas["t"].establecer(str(t), f"⌊({n} − 1)/2⌋ errores por bloque")
        self.tarjetas["R"].establecer(f"{R:.4f}", f"1/{n} · {mat.redundancia(n)} bits redundantes por bit")
        self.tarjetas["C"].establecer(f"{C:.4f}", f"bits por uso del canal · H₂(p) = {H:.4f}")
        self.tarjetas["pe"].establecer(_fmt(pe), f"Sin codificar sería p = {_fmt(p)}")
        self.tarjetas["pm"].establecer(_fmt(pm), f"Mensaje de {k_bits} bits de información")

        # 1. Código
        self.lbl_codigo.setText(
            f"El código de repetición de longitud n = {n} tiene solo dos palabras código: "
            f"<span style='font-family:Consolas;color:{e.CIAN}'>{'0' * n}</span> y "
            f"<span style='font-family:Consolas;color:{e.CIAN}'>{'1' * n}</span>.<br>"
            f"<b>Parámetros (n, M, d) = ({n}, 2, {dmin})</b>, código lineal [n, k, d] = [{n}, 1, {dmin}]: "
            f"cada bloque lleva k = 1 bit de información y hay M = 2<sup>k</sup> = 2 palabras código.<br>"
            f"<b>Distancia mínima:</b> d<sub>min</sub> = n = <b>{dmin}</b> (las dos palabras difieren en todas las posiciones).<br>"
            f"<b>Detección garantizada:</b> d − 1 = <b>{mat.capacidad_deteccion(n)}</b> errores: con 1 a {n - 1} "
            f"errores el bloque recibido mezcla ceros y unos, así que no es palabra código y el receptor "
            f"<i>detecta</i> que algo falló (sin saber cuántos errores hubo). Con {n} errores llega la otra "
            f"palabra código y el error pasa inadvertido.<br>"
            f"<b>Corrección garantizada:</b> t = ⌊(d<sub>min</sub> − 1)/2⌋ = ⌊({n} − 1)/2⌋ = <b>{t}</b>: "
            f"con hasta {t} error(es) la palabra enviada sigue siendo la más cercana (mayoría), por lo que "
            f"la decodificación por mayoría devuelve el bit correcto con certeza.<br>"
            f"<b>Tasa:</b> R = k/n = 1/{n} = <b>{R:.4f}</b> · <b>Redundancia:</b> {mat.redundancia(n)} bit(s) "
            f"redundantes por cada bit de información (el {100 * (1 - R):.1f} % de lo transmitido es redundancia)."
            + (
                f"<br><span style='color:{e.NARANJA}'>n es par: con exactamente {n // 2} errores el bloque queda "
                f"empatado ({n // 2} unos y {n // 2} ceros) y la mayoría no puede decidir.</span>"
                if n % 2 == 0
                else ""
            )
        )

        # 2. Canal
        if p == 0:
            detalle_h = "Caso límite p = 0: por convenio 0·log₂0 = 0, así que H₂(0) = 0 y el canal es perfecto (C = 1)."
        elif p == 0.5:
            detalle_h = "Caso límite p = 0.5: H₂(0.5) = 1, por lo que C = 0. La salida es independiente de la entrada: no se transmite información."
        else:
            detalle_h = (
                f"H₂({p:g}) = −{p:g}·log₂({p:g}) − {1 - p:g}·log₂({1 - p:g}) = {p * -math.log2(p):.4f} + "
                f"{(1 - p) * -math.log2(1 - p):.4f} = <b>{H:.4f}</b>"
            )
        self.lbl_canal.setText(
            "<span style='font-family:Consolas'>H₂(p) = −p·log₂(p) − (1−p)·log₂(1−p) &nbsp;&nbsp; C = 1 − H₂(p)</span><br>"
            f"{detalle_h}<br>"
            f"<b>Capacidad:</b> C = 1 − {H:.4f} = <b>{C:.4f}</b> bits de información por bit transmitido. "
            "Es el máximo de información confiable que el canal admite por cada uso."
        )

        # 3. Error residual
        if n % 2:
            formula = f"P_e = Σ<sub>k={(n + 1) // 2}</sub><sup>{n}</sup> C({n},k)·p<sup>k</sup>·(1−p)<sup>{n}−k</sup>"
        else:
            formula = (
                f"P_e = Σ<sub>k={n // 2 + 1}</sub><sup>{n}</sup> C({n},k)·p<sup>k</sup>·(1−p)<sup>{n}−k</sup> "
                f"+ ½·C({n},{n // 2})·p<sup>{n // 2}</sup>·(1−p)<sup>{n // 2}</sup> &nbsp;(desempate aleatorio)"
            )
        partes = [
            f"<span style='font-family:Consolas;color:{e.CIAN}'>{formula}</span>",
            f"Para p = {p:g}: <b>P_e = {_fmt(pe)}</b> por bit de información "
            f"(sin codificar el error sería p = {_fmt(p)}"
            + (f"; la codificación lo reduce {p / pe:,.1f} veces)." if pe > 0 and pe < p else ")."),
        ]
        if n % 2 == 0:
            partes.append(
                f"Desglose para n par: P(mayoría errónea) = {_fmt(p_estricta)} y P(empate) = {_fmt(p_empate)}. "
                f"Con desempate aleatorio la mitad de los empates acierta. Observe que P_e(n = {n}) = "
                f"P_e(n = {n - 1}) = {_fmt(mat.probabilidad_error_bit(n - 1, p))}: el bit adicional de un código par no "
                "reduce el error, solo añade la posibilidad de empate."
            )
        partes.append(
            f"<b>Mensaje completo</b> (k = {k_bits} bits, bloques independientes): "
            f"P(fallo) = 1 − (1 − P_e)<sup>k</sup> = <b>{_fmt(pm)}</b>"
            + (
                f"; si los empates se marcan como ambiguos, P(no recuperar) = {_fmt(pm_amb)}."
                if n % 2 == 0
                else "."
            )
            + " La probabilidad de fallo de un mensaje crece con su longitud, aunque P_e por bit sea pequeña."
        )
        self.lbl_error.setText("<br>".join(partes))
        self._dibujar_binomial(n, p)

        # 4. R frente a C
        if R < C:
            estado = (
                f"<b style='color:{e.VERDE}'>R = {R:.4f} &lt; C = {C:.4f}.</b> Por el teorema de codificación de "
                "canal de Shannon existen códigos con tasa R cuya probabilidad de error puede hacerse tan pequeña "
                "como se quiera. Esto <b>no</b> significa que este código de repetición lo logre: su error es "
                f"P_e = {_fmt(pe)} y solo tiende a 0 cuando n → ∞, es decir, cuando R = 1/n → 0."
            )
        elif R == C:
            estado = f"<b style='color:{e.NARANJA}'>R = C = {C:.4f}.</b> Caso frontera del teorema de Shannon."
        else:
            estado = (
                f"<b style='color:{e.ROJO}'>R = {R:.4f} &gt; C = {C:.4f}.</b> Por el inverso del teorema de "
                "codificación de canal, ningún código con esta tasa puede lograr una probabilidad de error "
                "arbitrariamente pequeña en este canal."
            )
        objetivo = 1e-6
        n_necesario = next((m for m in range(1, mat.N_MAX + 1, 2) if mat.probabilidad_error_bit(m, p) <= objetivo), None)
        if 0 < p < 0.5:
            if n_necesario:
                ejemplo = (
                    f"Ejemplo con p = {p:g}: para lograr P_e ≤ 10<sup>−6</sup> la repetición necesita n = "
                    f"{n_necesario}, es decir R = 1/{n_necesario} ≈ {1 / n_necesario:.3f}: aprovecha solo el "
                    f"{100 / n_necesario / C:.0f} % de la capacidad C = {C:.3f}. "
                )
            else:
                ejemplo = (
                    f"Ejemplo con p = {p:g}: ni siquiera n = 21 (R ≈ 0.048) alcanza P_e ≤ 10<sup>−6</sup> "
                    f"(P_e(21) = {_fmt(mat.probabilidad_error_bit(21, p))}), aunque C = {C:.3f}. "
                )
        else:
            ejemplo = ""
        self.lbl_rc.setText(
            estado + "<br><br><b>¿Por qué la repetición no es un buen código según Shannon?</b> "
            + ejemplo
            + "La repetición solo reduce el error haciendo crecer n, y entonces R = 1/n → 0: para que "
            "P_e → 0 hay que renunciar a toda la tasa. El teorema de Shannon garantiza, en cambio, códigos con "
            "P_e tan pequeña como se quiera manteniendo una tasa fija cercana a C. Además, cada bloque solo "
            "protege k = 1 bit: la redundancia no se comparte entre bits. Familias como Hamming, BCH, "
            "Reed-Solomon, LDPC o polares codifican muchos bits a la vez y se acercan mucho más a la capacidad."
        )

    def _dibujar_binomial(self, n: int, p: float) -> None:
        """Distribución del número de errores por bloque, coloreada según el resultado de la decisión."""
        ax = self.grafica.nuevo_eje()
        ks = list(range(n + 1))
        probs = [math.comb(n, k) * p**k * (1 - p) ** (n - k) for k in ks]
        colores, etiquetas = [], []
        for k in ks:
            if 2 * k < n:
                colores.append(e.VERDE)
                etiquetas.append("Corregido (k < n/2)")
            elif 2 * k == n:
                colores.append(e.NARANJA)
                etiquetas.append("Empate (k = n/2)")
            else:
                colores.append(e.ROJO)
                etiquetas.append("Decisión errónea (k > n/2)")
        vistos = set()
        for k, pr, c, et in zip(ks, probs, colores, etiquetas):
            ax.bar(k, pr, color=c, width=0.8, edgecolor=e.PANEL, linewidth=2,
                   label=et if et not in vistos else None)
            vistos.add(et)
        ax.axvline(mat.capacidad_correccion(n) + 0.5, color=e.TEXTO_2, linestyle="--", linewidth=1)
        ax.text(mat.capacidad_correccion(n) + 0.55, ax.get_ylim()[1] * 0.92, f" t = {mat.capacidad_correccion(n)}",
                color=e.TEXTO_2, fontsize=8.5)
        ax.set_title(f"Número de errores por bloque · Binomial(n = {n}, p = {p:g})")
        ax.set_xlabel("k = bits invertidos en un bloque de n bits")
        ax.set_ylabel("Probabilidad P(K = k)")
        ax.set_xticks(ks)
        ax.legend(loc="upper right")
        self.grafica.dibujar()

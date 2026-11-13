"""Módulo de transmisión de mensajes: codificar -> canal BSC -> decodificar -> comparar."""

from __future__ import annotations

import html

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QGridLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from almacenamiento.gestor_json import ErrorHistorial, GestorHistorial
from core import matematicas as mat
from core.canal_bsc import CanalBSC
from core.codificador import codificar
from core.decodificador import PoliticaDesempate, decodificar
from core.simulador import EstadoTransmision, ResultadoTransmision, crear_generador
from interfaz import estilos as e
from interfaz.componentes import Aviso, Panel, VisorBits, etiqueta, fila, pagina_desplazable

MAX_CARACTERES = 1000
PROBABILIDADES_RAPIDAS = (0.0, 0.01, 0.05, 0.10, 0.20, 0.30, 0.50)


def _dato(titulo: str) -> tuple[QLabel, QLabel]:
    t = etiqueta(titulo, "secundario")
    v = QLabel("—")
    v.setStyleSheet("font-weight:600;")
    return t, v


class PaginaTransmision(QWidget):
    historial_cambiado = Signal()

    def __init__(self, gestor: GestorHistorial, parent=None):
        super().__init__(parent)
        self.gestor = gestor
        self._reiniciar_estado()

        area, lay = pagina_desplazable(
            "Transmisión de mensajes",
            "Escriba un mensaje y recorra cada etapa: codificación por repetición, paso por el canal "
            "binario simétrico y decodificación por mayoría.",
        )
        raiz = QVBoxLayout(self)
        raiz.setContentsMargins(0, 0, 0, 0)
        raiz.addWidget(area)

        lay.addWidget(self._crear_configuracion())
        self.aviso = Aviso()
        lay.addWidget(self.aviso)
        lay.addWidget(self._crear_panel_codificacion())
        lay.addWidget(self._crear_panel_canal())
        lay.addWidget(self._crear_panel_decodificacion())
        lay.addWidget(self._crear_panel_resultado())
        lay.addStretch(1)

        self._actualizar_info_codigo()
        self._actualizar_botones()

    # ------------------------------------------------------------------ UI
    def _crear_configuracion(self) -> Panel:
        panel = Panel("Configuración del experimento")

        self.txt_mensaje = QPlainTextEdit()
        self.txt_mensaje.setPlaceholderText("Escriba aquí el mensaje a transmitir (UTF-8: tildes, ñ y emojis admitidos)…")
        self.txt_mensaje.setPlainText("Hola, Teoría de Códigos")
        self.txt_mensaje.setFixedHeight(70)
        self.txt_mensaje.textChanged.connect(lambda: self._invalidar_desde(0))
        panel.cuerpo.addWidget(self.txt_mensaje)

        rejilla = QGridLayout()
        rejilla.setHorizontalSpacing(14)
        rejilla.setVerticalSpacing(8)

        self.spin_n = QSpinBox()
        self.spin_n.setRange(mat.N_MIN, mat.N_MAX)
        self.spin_n.setValue(3)
        self.spin_n.setToolTip("Cada bit se repite n veces (1 ≤ n ≤ 21).")
        self.spin_n.valueChanged.connect(lambda: (self._actualizar_info_codigo(), self._invalidar_desde(0)))
        self.lbl_info_codigo = etiqueta("", "secundario")
        rejilla.addWidget(etiqueta("Longitud del código n"), 0, 0)
        rejilla.addWidget(self.spin_n, 0, 1)
        rejilla.addWidget(self.lbl_info_codigo, 0, 2, 1, 3)

        self.spin_p = QDoubleSpinBox()
        self.spin_p.setRange(mat.P_MIN, mat.P_MAX)
        self.spin_p.setDecimals(4)
        self.spin_p.setSingleStep(0.01)
        self.spin_p.setValue(0.10)
        self.spin_p.setToolTip("Probabilidad teórica de que el canal invierta cada bit (0 ≤ p ≤ 0.5).")
        self.spin_p.valueChanged.connect(self._p_cambiada)
        rejilla.addWidget(etiqueta("Probabilidad de error p"), 1, 0)
        rejilla.addWidget(self.spin_p, 1, 1)
        self.grupo_p = QButtonGroup(self)
        self.grupo_p.setExclusive(True)
        chips = []
        for valor in PROBABILIDADES_RAPIDAS:
            b = QPushButton(f"{valor * 100:g} %")
            b.setObjectName("chip")
            b.setCheckable(True)
            b.clicked.connect(lambda _=False, v=valor: self.spin_p.setValue(v))
            self.grupo_p.addButton(b)
            chips.append(b)
        rejilla.addLayout(fila(*chips, espaciado=6, estirar_final=True), 1, 2, 1, 3)

        self.chk_semilla = QCheckBox("Semilla fija")
        self.chk_semilla.setToolTip("Con semilla fija el experimento se puede repetir exactamente.")
        self.spin_semilla = QSpinBox()
        self.spin_semilla.setRange(0, 2**31 - 1)
        self.spin_semilla.setValue(2026)
        self.spin_semilla.setEnabled(False)
        self.chk_semilla.toggled.connect(self.spin_semilla.setEnabled)
        self.chk_semilla.toggled.connect(lambda: self._invalidar_desde(1))
        self.spin_semilla.valueChanged.connect(lambda: self._invalidar_desde(1))
        rejilla.addWidget(self.chk_semilla, 2, 0)
        rejilla.addWidget(self.spin_semilla, 2, 1)

        self.cmb_politica = QComboBox()
        for pol in PoliticaDesempate:
            self.cmb_politica.addItem(pol.etiqueta, pol)
        self.cmb_politica.setToolTip("Solo actúa con n par, cuando un bloque tiene tantos unos como ceros.")
        self.cmb_politica.currentIndexChanged.connect(lambda: self._invalidar_desde(2))
        rejilla.addWidget(etiqueta("Desempate (n par)"), 2, 2)
        rejilla.addWidget(self.cmb_politica, 2, 3)
        rejilla.setColumnStretch(4, 1)
        panel.cuerpo.addLayout(rejilla)

        self.btn_codificar = QPushButton("1 · Codificar")
        self.btn_transmitir = QPushButton("2 · Transmitir por BSC")
        self.btn_decodificar = QPushButton("3 · Decodificar")
        self.btn_todo = QPushButton("▶ Ejecutar todo")
        self.btn_todo.setObjectName("primario")
        self.btn_guardar = QPushButton("Guardar en historial")
        self.btn_codificar.clicked.connect(self.codificar)
        self.btn_transmitir.clicked.connect(self.transmitir)
        self.btn_decodificar.clicked.connect(self.decodificar)
        self.btn_todo.clicked.connect(self.ejecutar_todo)
        self.btn_guardar.clicked.connect(self.guardar)
        botones = fila(self.btn_codificar, self.btn_transmitir, self.btn_decodificar, self.btn_todo, estirar_final=True)
        botones.addWidget(self.btn_guardar)
        panel.cuerpo.addLayout(botones)
        self._sincronizar_chips()
        return panel

    def _crear_panel_codificacion(self) -> Panel:
        self.panel_cod = Panel("Etapa 1 · Codificación")
        self.lbl_cod_info = etiqueta("", "secundario")
        self.visor_original = VisorBits(60)
        self.visor_codificado = VisorBits(90)
        c = self.panel_cod.cuerpo
        c.addWidget(self.lbl_cod_info)
        c.addWidget(etiqueta("Bits de información (UTF-8, agrupados por byte)", "secundario"))
        c.addWidget(self.visor_original)
        c.addWidget(etiqueta("Bits codificados (agrupados en bloques de n)", "secundario"))
        c.addWidget(self.visor_codificado)
        return self.panel_cod

    def _crear_panel_canal(self) -> Panel:
        self.panel_canal = Panel("Etapa 2 · Canal binario simétrico")
        rejilla = QGridLayout()
        rejilla.setHorizontalSpacing(24)
        self.datos_canal = {}
        for i, (clave, titulo) in enumerate(
            [
                ("p", "Probabilidad configurada p"),
                ("errores", "Errores introducidos"),
                ("proporcion", "Proporción observada"),
                ("semilla", "Semilla usada"),
            ]
        ):
            t, v = _dato(titulo)
            rejilla.addWidget(t, 0, i)
            rejilla.addWidget(v, 1, i)
            self.datos_canal[clave] = v
        self.lbl_posiciones = etiqueta("", "secundario")
        self.visor_recibido = VisorBits(90)
        c = self.panel_canal.cuerpo
        c.addLayout(rejilla)
        c.addWidget(etiqueta(
            "Bits recibidos — en <span style='color:%s'><b>rojo</b></span> los bits invertidos por el canal" % e.ROJO,
            "secundario",
        ))
        c.addWidget(self.visor_recibido)
        c.addWidget(self.lbl_posiciones)
        return self.panel_canal

    def _crear_panel_decodificacion(self) -> Panel:
        self.panel_dec = Panel("Etapa 3 · Decodificación por mayoría")
        rejilla = QGridLayout()
        rejilla.setHorizontalSpacing(24)
        self.datos_dec = {}
        for i, (clave, titulo) in enumerate(
            [
                ("corregidos", "Bloques corregidos"),
                ("residuales", "Errores residuales (bits)"),
                ("empates", "Empates detectados"),
                ("ambiguos", "Bits ambiguos"),
            ]
        ):
            t, v = _dato(titulo)
            rejilla.addWidget(t, 0, i)
            rejilla.addWidget(v, 1, i)
            self.datos_dec[clave] = v
        self.visor_decodificado = VisorBits(60)
        c = self.panel_dec.cuerpo
        c.addLayout(rejilla)
        c.addWidget(etiqueta(
            "Bits decodificados — <span style='color:%s'><b>rojo</b></span>: error residual · "
            "<span style='color:%s'><b>?</b></span>: ambiguo" % (e.ROJO, e.NARANJA),
            "secundario",
        ))
        c.addWidget(self.visor_decodificado)
        return self.panel_dec

    def _crear_panel_resultado(self) -> Panel:
        self.panel_res = Panel("Resultado · comparación de mensajes")
        self.aviso_resultado = Aviso()
        self.lbl_original = etiqueta("")
        self.lbl_recuperado = etiqueta("")
        for lbl in (self.lbl_original, self.lbl_recuperado):
            lbl.setStyleSheet(f"background:{e.FONDO}; border:1px solid {e.BORDE}; border-radius:8px; padding:10px;")
            lbl.setTextFormat(Qt.RichText)
        rejilla = QGridLayout()
        rejilla.addWidget(etiqueta("Mensaje original", "secundario"), 0, 0)
        rejilla.addWidget(etiqueta("Mensaje recuperado", "secundario"), 0, 1)
        rejilla.addWidget(self.lbl_original, 1, 0)
        rejilla.addWidget(self.lbl_recuperado, 1, 1)
        c = self.panel_res.cuerpo
        c.addWidget(self.aviso_resultado)
        c.addLayout(rejilla)
        return self.panel_res

    # -------------------------------------------------------------- estado
    def _reiniciar_estado(self) -> None:
        self._texto = None
        self._bits = None
        self._codificados = None
        self._semilla = None
        self._rng = None
        self._canal = None
        self._resultado: ResultadoTransmision | None = None
        self._guardado = False

    def _etapa(self) -> int:
        if self._resultado is not None:
            return 3
        if self._canal is not None:
            return 2
        if self._codificados is not None:
            return 1
        return 0

    def _invalidar_desde(self, etapa: int) -> None:
        """Descarta los resultados de la etapa indicada en adelante (parámetros cambiados)."""
        if not hasattr(self, "panel_cod"):
            return
        if etapa <= 0:
            self._bits = self._codificados = self._texto = None
        if etapa <= 1:
            self._canal = self._rng = self._semilla = None
        if etapa <= 2:
            self._resultado = None
            self._guardado = False
        self.panel_cod.setVisible(self._codificados is not None)
        self.panel_canal.setVisible(self._canal is not None)
        self.panel_dec.setVisible(self._resultado is not None)
        self.panel_res.setVisible(self._resultado is not None)
        self.aviso.ocultar()
        self._actualizar_botones()

    def _actualizar_botones(self) -> None:
        etapa = self._etapa()
        self.btn_transmitir.setEnabled(etapa >= 1)
        self.btn_decodificar.setEnabled(etapa >= 2)
        self.btn_guardar.setEnabled(etapa == 3 and not self._guardado)
        if etapa == 0:
            self.panel_cod.hide()
            self.panel_canal.hide()
            self.panel_dec.hide()
            self.panel_res.hide()

    def _actualizar_info_codigo(self) -> None:
        n = self.spin_n.value()
        self.lbl_info_codigo.setText(
            f"d<sub>min</sub> = {mat.distancia_minima(n)} · t = {mat.capacidad_correccion(n)} · "
            f"R = 1/{n} = {mat.tasa_codigo(n):.4f} · {mat.redundancia(n)} bits redundantes por bit"
            + (" · <span style='color:%s'>n par: puede haber empates</span>" % e.NARANJA if n % 2 == 0 else "")
        )

    def _p_cambiada(self) -> None:
        self._sincronizar_chips()
        self._invalidar_desde(1)

    def _sincronizar_chips(self) -> None:
        p = self.spin_p.value()
        self.grupo_p.setExclusive(False)
        for b, v in zip(self.grupo_p.buttons(), PROBABILIDADES_RAPIDAS):
            b.setChecked(abs(v - p) < 1e-9)
        self.grupo_p.setExclusive(True)

    # ------------------------------------------------------------- etapas
    def codificar(self) -> bool:
        texto = self.txt_mensaje.toPlainText()
        if not texto:
            self.aviso.mostrar("advertencia", "Escriba un mensaje antes de codificar.")
            return False
        if len(texto) > MAX_CARACTERES:
            self.aviso.mostrar("advertencia", f"El mensaje supera el máximo de {MAX_CARACTERES} caracteres.")
            return False
        self._invalidar_desde(0)
        n = self.spin_n.value()
        self._texto = texto
        self._bits = mat.texto_a_bits(texto)
        self._codificados = codificar(self._bits, n)

        num_bytes = self._bits.size // 8
        self.lbl_cod_info.setText(
            f"{len(texto)} caracteres → {num_bytes} bytes UTF-8 → <b>{self._bits.size}</b> bits de información → "
            f"<b>{self._codificados.size}</b> bits transmitidos (×{n})."
        )
        self.visor_original.mostrar_bits(self._bits, 8)
        self.visor_codificado.mostrar_bits(self._codificados, n)
        self._invalidar_desde(1)
        return True

    def transmitir(self) -> bool:
        if self._codificados is None and not self.codificar():
            return False
        self._invalidar_desde(1)
        semilla = self.spin_semilla.value() if self.chk_semilla.isChecked() else None
        self._semilla, self._rng = crear_generador(semilla)
        p = self.spin_p.value()
        self._canal = CanalBSC(p, self._rng).transmitir(self._codificados)
        n = self.spin_n.value()

        c = self._canal
        self.datos_canal["p"].setText(f"{p:.4f}  ({p * 100:g} %)")
        self.datos_canal["errores"].setText(f"{c.num_errores} de {c.transmitidos.size}")
        self.datos_canal["proporcion"].setText(f"{c.proporcion_errores:.4f}  ({c.proporcion_errores * 100:.2f} %)")
        self.datos_canal["semilla"].setText(str(self._semilla))
        self.visor_recibido.mostrar_bits(c.recibidos, n, marcados=c.mascara_errores)
        posiciones = c.posiciones_alteradas.tolist()
        if posiciones:
            muestra = ", ".join(map(str, posiciones[:40])) + (" …" if len(posiciones) > 40 else "")
            self.lbl_posiciones.setText(f"Posiciones alteradas (desde 0): {muestra}")
        else:
            self.lbl_posiciones.setText("El canal no alteró ningún bit en esta transmisión.")
        self.lbl_posiciones.setToolTip(
            "La proporción observada es una realización aleatoria; solo se aproxima a p cuando "
            "el número de bits es grande (ley de los grandes números)."
        )
        self._invalidar_desde(2)
        return True

    def decodificar(self) -> bool:
        if self._canal is None and not self.transmitir():
            return False
        n = self.spin_n.value()
        politica = PoliticaDesempate(self.cmb_politica.currentData())
        dec = decodificar(self._canal.recibidos, n, politica, self._rng)
        self._resultado = ResultadoTransmision(
            mensaje_original=self._texto,
            n=n,
            p=self._canal.probabilidad,
            semilla=self._semilla,
            politica=politica,
            bits_originales=self._bits,
            bits_codificados=self._codificados,
            canal=self._canal,
            decodificacion=dec,
        )
        self._guardado = False
        self._mostrar_resultado()
        self._invalidar_desde(3)
        return True

    def ejecutar_todo(self) -> None:
        if self.codificar() and self.transmitir():
            self.decodificar()

    def guardar(self) -> None:
        if self._resultado is None:
            return
        try:
            self.gestor.agregar(self._resultado.a_registro())
        except (ErrorHistorial, OSError) as exc:
            self.aviso.mostrar("error", f"No se pudo guardar el experimento: {html.escape(str(exc))}")
            return
        self._guardado = True
        self._actualizar_botones()
        self.aviso.mostrar("exito", f"Experimento guardado en el historial (id {self._resultado.id[:8]}).")
        self.historial_cambiado.emit()

    # ------------------------------------------------------------ resultado
    def _mostrar_resultado(self) -> None:
        r = self._resultado
        dec = r.decodificacion
        self.datos_dec["corregidos"].setText(f"{r.bloques_corregidos} de {r.bloques_con_errores} alterados")
        self.datos_dec["residuales"].setText(str(r.errores_residuales))
        self.datos_dec["empates"].setText(
            f"{dec.num_empates}" + (f" (resueltos: {dec.politica.etiqueta.lower()})" if dec.num_empates and not dec.num_ambiguos else "")
        )
        self.datos_dec["ambiguos"].setText(str(r.ambiguedades))
        for clave, valor, color in (
            ("residuales", r.errores_residuales, e.ROJO),
            ("ambiguos", r.ambiguedades, e.NARANJA),
        ):
            self.datos_dec[clave].setStyleSheet(f"font-weight:600; color:{color if valor else e.TEXTO};")
        self.visor_decodificado.mostrar_bits(
            dec.bits, 8, marcados=r.mascara_errores_residuales, ambiguos=dec.ambiguos
        )

        self.lbl_original.setText(html.escape(r.mensaje_original).replace("\n", "<br>"))
        estado = r.estado
        if estado is EstadoTransmision.AMBIGUO:
            self.lbl_recuperado.setText(
                f"<span style='color:{e.NARANJA}'>No se reconstruye el mensaje: {r.ambiguedades} bit(s) "
                "quedaron ambiguos y el sistema no inventa su valor.</span>"
            )
            self.aviso_resultado.mostrar(
                "advertencia",
                f"<b>Transmisión ambigua.</b> Con n = {r.n} (par) hubo {r.ambiguedades} empate(s) sin resolver. "
                "Elija otra política de desempate o un n impar para obtener una decisión.",
            )
        else:
            recuperado = r.mensaje_recuperado or ""
            self.lbl_recuperado.setText(html.escape(recuperado).replace("\n", "<br>") or "<i>(vacío)</i>")
            if estado is EstadoTransmision.EXITO:
                self.aviso_resultado.mostrar(
                    "exito",
                    f"<b>Mensaje recuperado correctamente.</b> El canal introdujo {r.errores_introducidos} error(es) "
                    f"y la decodificación corrigió todos los bloques afectados.",
                )
            else:
                extra = "" if r.utf8_valido else " Algunos bytes no forman UTF-8 válido y se muestran como �."
                self.aviso_resultado.mostrar(
                    "error",
                    f"<b>El mensaje recuperado NO coincide con el original.</b> Quedaron {r.errores_residuales} "
                    f"bit(s) de información erróneos tras decodificar.{extra}",
                )

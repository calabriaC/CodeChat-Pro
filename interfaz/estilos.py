
"""Identidad visual premium de CodeChat Pro.

Paleta, hoja de estilos Qt y configuración de gráficas Matplotlib.
Aplicación de escritorio para el Tema 6 de Teoría de Códigos.
"""

from __future__ import annotations

import matplotlib as mpl


# ============================================================
# 1. PALETA DE COLORES
# ============================================================

# Fondos
FONDO = "#0B0F19"
PANEL = "#141B28"
PANEL_ALTO = "#1E293B"
BORDE = "#293548"

# Colores principales
AZUL = "#2789D8"
CIAN = "#46CFE4"
ROJO = "#F04452"
VERDE = "#35D49A"
NARANJA = "#F4B860"

# Textos
TEXTO = "#F8FAFC"
TEXTO_2 = "#B2BED0"
TEXTO_3 = "#8191A8"

# Colores auxiliares
SIDEBAR = "#0E1420"
SUPERFICIE = "#101827"
HOVER = "#263449"
ROJO_OSCURO = "#6D1D2A"

# Gráficas
SERIES = [
    "#F04452",
    "#2789D8",
    "#35D49A",
    "#F4B860",
    "#A78BFA",
    "#46CFE4",
    "#F472B6",
    "#94A3B8",
]

MARCADORES = ["o", "s", "^", "D", "v", "P", "X", "h"]

FUENTE_MONO = "Consolas, 'Cascadia Mono', 'Courier New', monospace"


def color_serie(i: int, total: int) -> str:
    """Devuelve un color para una serie de datos."""
    if total <= len(SERIES):
        return SERIES[i % len(SERIES)]

    t = i / max(total - 1, 1)

    return mpl.colors.to_hex(
        mpl.colormaps["viridis"](0.15 + 0.75 * t)
    )


def marcador_serie(i: int) -> str:
    """Devuelve un marcador para identificar una serie."""
    return MARCADORES[i % len(MARCADORES)]


# ============================================================
# 2. HOJA DE ESTILOS PRINCIPAL
# ============================================================

HOJA_ESTILOS = f"""

/* ----------------------------------------------------------
   ESTILO GLOBAL
---------------------------------------------------------- */

* {{
    font-family: 'Segoe UI', 'Arial', sans-serif;
    font-size: 10pt;
    color: {TEXTO};
}}

QMainWindow,
QWidget#raiz,
QWidget#pagina,
QWidget#zonaPrincipal {{
    background-color: {FONDO};
}}

QScrollArea {{
    background: transparent;
    border: none;
}}

QScrollArea > QWidget > QWidget {{
    background: transparent;
}}

QLabel {{
    background: transparent;
}}


/* ----------------------------------------------------------
   TIPOGRAFIA
---------------------------------------------------------- */

QLabel#titulo {{
    font-size: 21pt;
    font-weight: 700;
    color: {TEXTO};
}}

QLabel#subtitulo {{
    color: {TEXTO_2};
    font-size: 10pt;
}}

QLabel#seccion {{
    font-size: 13pt;
    font-weight: 700;
    color: {TEXTO};
}}

QLabel#secundario {{
    color: {TEXTO_2};
    font-size: 9pt;
}}

QLabel#formula {{
    font-family: {FUENTE_MONO};
    color: {CIAN};
    font-size: 10.5pt;
}}


/* ----------------------------------------------------------
   BARRA LATERAL
---------------------------------------------------------- */

QFrame#barraLateral {{
    background-color: {SIDEBAR};
    border-right: 1px solid {BORDE};
}}

QLabel#marca {{
    font-size: 21pt;
    font-weight: 700;
    color: {TEXTO};
}}

QLabel#marcaSub {{
    color: {ROJO};
    font-size: 8pt;
    font-weight: 600;
}}

QPushButton#nav {{
    text-align: left;
    background: transparent;
    color: {TEXTO_2};

    border: none;
    border-radius: 10px;

    padding: 12px 16px;
    font-size: 10pt;
    font-weight: 500;
}}

QPushButton#nav:hover {{
    background-color: {HOVER};
    color: {TEXTO};
}}

QPushButton#nav:checked {{
    background-color: {ROJO_OSCURO};
    color: #FFFFFF;
    font-weight: 700;
    border-left: 3px solid {ROJO};
}}


/* ----------------------------------------------------------
   ENCABEZADO
---------------------------------------------------------- */

QFrame#encabezado {{
    background-color: {SUPERFICIE};
    border-bottom: 1px solid {BORDE};
}}

QFrame#barraEstado {{
    background-color: {SUPERFICIE};
    border-top: 1px solid {BORDE};
}}

QLabel#estadoActivo {{
    color: {VERDE};
    background-color: #12352B;

    border: 1px solid #27674E;
    border-radius: 10px;

    padding: 8px 14px;

    font-size: 9pt;
    font-weight: 700;
}}


/* ----------------------------------------------------------
   PANELES Y TARJETAS
---------------------------------------------------------- */

QFrame#panel,
QFrame#tarjeta {{
    background-color: {PANEL};
    border: 1px solid {BORDE};
    border-radius: 12px;
}}

QLabel#tarjetaValor {{
    font-size: 23pt;
    font-weight: 700;
    color: {TEXTO};
}}

QLabel#tarjetaTitulo {{
    color: {TEXTO_2};
    font-size: 9pt;
    font-weight: 600;
}}

QLabel#tarjetaNota {{
    color: {TEXTO_3};
    font-size: 8.5pt;
}}


/* ----------------------------------------------------------
   BOTONES
---------------------------------------------------------- */

QPushButton {{
    background-color: {PANEL_ALTO};
    color: {TEXTO};

    border: 1px solid {BORDE};
    border-radius: 9px;

    padding: 9px 16px;

    font-size: 10pt;
    font-weight: 500;
}}

QPushButton:hover {{
    background-color: {HOVER};
    border-color: {CIAN};
}}

QPushButton:pressed {{
    background-color: {BORDE};
}}

QPushButton:disabled {{
    color: {TEXTO_3};
    background-color: {SUPERFICIE};
    border-color: {BORDE};
}}

QPushButton#primario {{
    background-color: {ROJO};
    color: white;

    border: none;
    font-weight: 700;
}}

QPushButton#primario:hover {{
    background-color: #FF5965;
}}

QPushButton#primario:pressed {{
    background-color: #C92D3B;
}}

QPushButton#primario:disabled {{
    background-color: #582B36;
    color: {TEXTO_3};
}}

QPushButton#chip {{
    padding: 5px 12px;
    border-radius: 12px;
    font-size: 9pt;
}}

QPushButton#chip:checked {{
    background-color: {CIAN};
    color: {FONDO};

    border-color: {CIAN};
    font-weight: 700;
}}


/* ----------------------------------------------------------
   CAMPOS Y FORMULARIOS
---------------------------------------------------------- */

QLineEdit,
QTextEdit,
QPlainTextEdit,
QSpinBox,
QDoubleSpinBox,
QComboBox {{
    background-color: {SUPERFICIE};
    color: {TEXTO};

    border: 1px solid {BORDE};
    border-radius: 8px;

    padding: 7px 10px;
    selection-background-color: {AZUL};
}}

QLineEdit:focus,
QTextEdit:focus,
QPlainTextEdit:focus,
QSpinBox:focus,
QDoubleSpinBox:focus,
QComboBox:focus {{
    border-color: {CIAN};
}}

QComboBox QAbstractItemView {{
    background-color: {PANEL};
    color: {TEXTO};

    border: 1px solid {BORDE};
    selection-background-color: {AZUL};
}}

QSpinBox::up-button,
QDoubleSpinBox::up-button,
QSpinBox::down-button,
QDoubleSpinBox::down-button {{
    width: 16px;
}}

QCheckBox {{
    spacing: 8px;
}}


/* ----------------------------------------------------------
   SLIDERS
---------------------------------------------------------- */

QSlider::groove:horizontal {{
    height: 5px;
    background-color: {BORDE};
    border-radius: 2px;
}}

QSlider::handle:horizontal {{
    background-color: {CIAN};

    width: 16px;
    margin: -6px 0;

    border-radius: 8px;
}}

QSlider::sub-page:horizontal {{
    background-color: {AZUL};
    border-radius: 2px;
}}


/* ----------------------------------------------------------
   TABLAS
---------------------------------------------------------- */

QTableWidget {{
    background-color: {PANEL};
    color: {TEXTO};

    border: 1px solid {BORDE};
    border-radius: 9px;

    gridline-color: {BORDE};
    alternate-background-color: {PANEL_ALTO};

    selection-background-color: {AZUL};
}}

QHeaderView::section {{
    background-color: {PANEL_ALTO};
    color: {TEXTO_2};

    border: none;
    border-bottom: 1px solid {BORDE};

    padding: 8px;
    font-weight: 700;
}}

QHeaderView {{
    background-color: {PANEL_ALTO};
    border: none;
}}

QTableCornerButton::section {{
    background-color: {PANEL_ALTO};
    border: none;
}}


/* ----------------------------------------------------------
   PESTANAS
---------------------------------------------------------- */

QTabWidget::pane {{
    background-color: {PANEL};

    border: 1px solid {BORDE};
    border-radius: 9px;

    top: -1px;
}}

QTabBar::tab {{
    background: transparent;
    color: {TEXTO_2};

    padding: 10px 16px;
    border: none;
}}

QTabBar::tab:selected {{
    color: {TEXTO};
    font-weight: 700;
    border-bottom: 2px solid {ROJO};
}}

QTabBar::tab:hover {{
    color: {CIAN};
}}


/* ----------------------------------------------------------
   SCROLLBARS
---------------------------------------------------------- */

QScrollBar:vertical {{
    background: transparent;
    width: 10px;
}}

QScrollBar::handle:vertical {{
    background-color: {BORDE};
    border-radius: 5px;
    min-height: 24px;
}}

QScrollBar:horizontal {{
    background: transparent;
    height: 10px;
}}

QScrollBar::handle:horizontal {{
    background-color: {BORDE};
    border-radius: 5px;
    min-width: 24px;
}}

QScrollBar::add-line,
QScrollBar::sub-line {{
    width: 0;
    height: 0;
}}


/* ----------------------------------------------------------
   OTROS COMPONENTES
---------------------------------------------------------- */

QTextBrowser {{
    background-color: {SUPERFICIE};
    color: {TEXTO};

    border: 1px solid {BORDE};
    border-radius: 8px;

    padding: 8px;
}}

QToolTip {{
    background-color: {PANEL_ALTO};
    color: {TEXTO};

    border: 1px solid {BORDE};
    padding: 5px;
}}

QMessageBox,
QDialog {{
    background-color: {PANEL};
}}

"""


# ============================================================
# 3. ESTILO DE GRAFICAS MATPLOTLIB
# ============================================================

def aplicar_estilo_matplotlib() -> None:
    """Aplica la identidad visual a las gráficas científicas."""

    mpl.rcParams.update(
        {
            "figure.facecolor": PANEL,
            "axes.facecolor": PANEL,
            "savefig.facecolor": PANEL,

            "axes.edgecolor": BORDE,
            "axes.labelcolor": TEXTO_2,
            "axes.titlecolor": TEXTO,

            "axes.titlesize": 12,
            "axes.titleweight": "bold",
            "axes.labelsize": 10,

            "axes.grid": True,
            "axes.spines.top": False,
            "axes.spines.right": False,

            "grid.color": BORDE,
            "grid.linewidth": 0.7,
            "grid.alpha": 0.65,

            "xtick.color": TEXTO_2,
            "ytick.color": TEXTO_2,
            "xtick.labelsize": 9,
            "ytick.labelsize": 9,

            "legend.facecolor": PANEL_ALTO,
            "legend.edgecolor": BORDE,
            "legend.labelcolor": TEXTO,
            "legend.fontsize": 9,

            "lines.linewidth": 2.2,
            "lines.markersize": 6,

            "font.family": ["Segoe UI", "DejaVu Sans"],
            "text.color": TEXTO,

            "figure.autolayout": True,
        }
    )


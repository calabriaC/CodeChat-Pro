"""Identidad visual de CodeChat Pro: paleta, hoja de estilos Qt y estilo de gráficas."""

from __future__ import annotations

import matplotlib as mpl

# Paleta de la aplicación ------------------------------------------------------
FONDO = "#0B1120"
PANEL = "#151F32"
PANEL_ALTO = "#1C2940"
BORDE = "#263452"
AZUL = "#2563EB"
CIAN = "#22D3EE"
VERDE = "#22C55E"
NARANJA = "#F59E0B"
ROJO = "#EF4444"
TEXTO = "#F8FAFC"
TEXTO_2 = "#94A3B8"
TEXTO_3 = "#64748B"

# Series categóricas para las gráficas (paleta validada para fondo oscuro;
# se asigna en orden fijo y cada serie lleva además un marcador distinto).
SERIES = ["#3987e5", "#d95926", "#199e70", "#c98500", "#d55181", "#9085e9", "#e66767", "#008300"]
MARCADORES = ["o", "s", "^", "D", "v", "P", "X", "h"]
FUENTE_MONO = "Consolas, 'Cascadia Mono', 'Courier New', monospace"


def color_serie(i: int, total: int) -> str:
    """Color categórico si hay <= 8 series; rampa secuencial (un solo tono) si hay más."""
    if total <= len(SERIES):
        return SERIES[i]
    t = i / max(total - 1, 1)
    return mpl.colors.to_hex(mpl.colormaps["GnBu"](0.35 + 0.6 * t))


def marcador_serie(i: int) -> str:
    return MARCADORES[i % len(MARCADORES)]


HOJA_ESTILOS = f"""
* {{ font-family: 'Segoe UI', 'Inter', sans-serif; font-size: 10pt; color: {TEXTO}; }}
QMainWindow, QWidget#raiz {{ background: {FONDO}; }}
QWidget#pagina {{ background: {FONDO}; }}
QScrollArea {{ background: transparent; border: none; }}
QScrollArea > QWidget > QWidget {{ background: transparent; }}
QLabel {{ background: transparent; }}
QLabel#titulo {{ font-size: 20pt; font-weight: 600; }}
QLabel#subtitulo {{ color: {TEXTO_2}; font-size: 10.5pt; }}
QLabel#seccion {{ font-size: 12pt; font-weight: 600; color: {TEXTO}; }}
QLabel#secundario {{ color: {TEXTO_2}; }}
QLabel#formula {{ font-family: {FUENTE_MONO}; color: {CIAN}; font-size: 10.5pt; }}

QFrame#barraLateral {{ background: {PANEL}; border-right: 1px solid {BORDE}; }}
QLabel#marca {{ font-size: 15pt; font-weight: 700; color: {TEXTO}; }}
QLabel#marcaSub {{ color: {CIAN}; font-size: 8.5pt; letter-spacing: 1px; }}
QPushButton#nav {{
    text-align: left; padding: 10px 14px; border: none; border-radius: 8px;
    background: transparent; color: {TEXTO_2}; font-size: 10.5pt;
}}
QPushButton#nav:hover {{ background: {PANEL_ALTO}; color: {TEXTO}; }}
QPushButton#nav:checked {{ background: {AZUL}; color: white; font-weight: 600; }}

QFrame#panel, QFrame#tarjeta {{
    background: {PANEL}; border: 1px solid {BORDE}; border-radius: 12px;
}}
QLabel#tarjetaValor {{ font-size: 22pt; font-weight: 700; }}
QLabel#tarjetaTitulo {{ color: {TEXTO_2}; font-size: 9pt; }}
QLabel#tarjetaNota {{ color: {TEXTO_3}; font-size: 8.5pt; }}

QPushButton {{
    background: {PANEL_ALTO}; border: 1px solid {BORDE}; border-radius: 8px;
    padding: 7px 14px; color: {TEXTO};
}}
QPushButton:hover {{ border-color: {CIAN}; }}
QPushButton:pressed {{ background: {BORDE}; }}
QPushButton:disabled {{ color: {TEXTO_3}; border-color: {PANEL_ALTO}; }}
QPushButton#primario {{ background: {AZUL}; border: none; font-weight: 600; color: white; }}
QPushButton#primario:hover {{ background: #3B82F6; }}
QPushButton#primario:disabled {{ background: #1E3A8A; color: {TEXTO_2}; }}
QPushButton#chip {{ padding: 4px 10px; border-radius: 12px; font-size: 9pt; }}
QPushButton#chip:checked {{ background: {CIAN}; color: {FONDO}; border-color: {CIAN}; font-weight: 600; }}

QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QDoubleSpinBox, QComboBox {{
    background: {FONDO}; border: 1px solid {BORDE}; border-radius: 8px; padding: 6px 8px;
    selection-background-color: {AZUL};
}}
QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, QSpinBox:focus,
QDoubleSpinBox:focus, QComboBox:focus {{ border-color: {CIAN}; }}
QComboBox QAbstractItemView {{ background: {PANEL}; border: 1px solid {BORDE}; selection-background-color: {AZUL}; }}
QSpinBox::up-button, QDoubleSpinBox::up-button, QSpinBox::down-button, QDoubleSpinBox::down-button {{ width: 16px; }}
QCheckBox {{ spacing: 6px; }}
QSlider::groove:horizontal {{ height: 4px; background: {BORDE}; border-radius: 2px; }}
QSlider::handle:horizontal {{ background: {CIAN}; width: 14px; margin: -6px 0; border-radius: 7px; }}
QSlider::sub-page:horizontal {{ background: {AZUL}; border-radius: 2px; }}

QTextBrowser {{ background: {FONDO}; border: 1px solid {BORDE}; border-radius: 8px; padding: 6px; }}
QTableWidget {{
    background: {PANEL}; border: 1px solid {BORDE}; border-radius: 8px;
    gridline-color: {BORDE}; alternate-background-color: {PANEL_ALTO};
    selection-background-color: {AZUL};
}}
QHeaderView::section {{
    background: {PANEL_ALTO}; color: {TEXTO_2}; border: none; border-bottom: 1px solid {BORDE};
    padding: 6px; font-weight: 600;
}}
QHeaderView {{ background: {PANEL_ALTO}; border: none; }}
QTableCornerButton::section {{ background: {PANEL_ALTO}; border: none; }}
QTabWidget::pane {{ border: 1px solid {BORDE}; border-radius: 8px; top: -1px; background: {PANEL}; }}
QTabBar::tab {{ background: transparent; color: {TEXTO_2}; padding: 8px 14px; border: none; }}
QTabBar::tab:selected {{ color: {TEXTO}; border-bottom: 2px solid {CIAN}; }}
QScrollBar:vertical {{ background: transparent; width: 10px; }}
QScrollBar::handle:vertical {{ background: {BORDE}; border-radius: 5px; min-height: 24px; }}
QScrollBar:horizontal {{ background: transparent; height: 10px; }}
QScrollBar::handle:horizontal {{ background: {BORDE}; border-radius: 5px; min-width: 24px; }}
QScrollBar::add-line, QScrollBar::sub-line {{ width: 0; height: 0; }}
QToolTip {{ background: {PANEL_ALTO}; color: {TEXTO}; border: 1px solid {BORDE}; padding: 4px; }}
QMessageBox, QDialog {{ background: {PANEL}; }}
"""


def aplicar_estilo_matplotlib() -> None:
    """Estilo oscuro coherente con la aplicación para todas las figuras."""
    mpl.rcParams.update(
        {
            "figure.facecolor": PANEL,
            "axes.facecolor": PANEL,
            "savefig.facecolor": PANEL,
            "axes.edgecolor": BORDE,
            "axes.labelcolor": TEXTO_2,
            "axes.titlecolor": TEXTO,
            "axes.titlesize": 11,
            "axes.titleweight": "bold",
            "axes.labelsize": 9.5,
            "axes.grid": True,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "grid.color": BORDE,
            "grid.linewidth": 0.6,
            "grid.alpha": 0.7,
            "xtick.color": TEXTO_2,
            "ytick.color": TEXTO_2,
            "xtick.labelsize": 8.5,
            "ytick.labelsize": 8.5,
            "legend.facecolor": PANEL_ALTO,
            "legend.edgecolor": BORDE,
            "legend.labelcolor": TEXTO,
            "legend.fontsize": 8.5,
            "lines.linewidth": 2.0,
            "lines.markersize": 6,
            "font.family": ["Segoe UI", "DejaVu Sans"],
            "text.color": TEXTO,
        }
    )

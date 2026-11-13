"""Punto de entrada de CodeChat Pro.

Ejecutar desde la raíz del proyecto:

    python main.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib

matplotlib.use("QtAgg")  # backend integrado en PySide6 (antes de importar pyplot)

from PySide6.QtGui import QFont  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from almacenamiento.gestor_json import GestorHistorial  # noqa: E402
from interfaz.estilos import HOJA_ESTILOS, aplicar_estilo_matplotlib  # noqa: E402
from interfaz.ventana_principal import VentanaPrincipal  # noqa: E402


def directorio_base() -> Path:
    """Carpeta del proyecto (o del ejecutable si se empaqueta con PyInstaller)."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


RUTA_HISTORIAL = directorio_base() / "data" / "historial.json"


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("CodeChat Pro")
    app.setFont(QFont("Segoe UI", 10))
    app.setStyleSheet(HOJA_ESTILOS)
    aplicar_estilo_matplotlib()

    ventana = VentanaPrincipal(GestorHistorial(RUTA_HISTORIAL))
    ventana.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())

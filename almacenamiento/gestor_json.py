"""Persistencia del historial de experimentos en un archivo JSON local.

* Si el archivo no existe, el historial se considera vacío (la app arranca igual).
* Las escrituras son atómicas: se escribe un archivo temporal en la misma
  carpeta, se fuerza a disco (fsync) y se reemplaza el original con os.replace.
  Así un cierre inesperado nunca deja un JSON a medio escribir.
* Si el archivo existente está dañado, se conserva una copia de respaldo y se
  continúa con un historial vacío, informando del problema.
"""

from __future__ import annotations

import json
import os
import tempfile
import time
from datetime import datetime
from pathlib import Path


class ErrorHistorial(Exception):
    """Error al leer o escribir el historial."""


def escribir_json_atomico(ruta: Path | str, datos) -> None:
    """Escribe `datos` como JSON (UTF-8) en `ruta` de forma atómica."""
    ruta = Path(ruta)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporal = tempfile.mkstemp(dir=ruta.parent, prefix=f".{ruta.name}.", suffix=".tmp")
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as archivo:
            json.dump(datos, archivo, ensure_ascii=False, indent=2)
            archivo.flush()
            os.fsync(archivo.fileno())
        # En Windows, os.replace puede fallar momentáneamente si otro proceso
        # (antivirus, indexador) tiene abierto el archivo destino.
        for intento in range(5):
            try:
                os.replace(temporal, ruta)
                break
            except PermissionError:
                if intento == 4:
                    raise
                time.sleep(0.1)
    except BaseException:
        if os.path.exists(temporal):
            os.remove(temporal)
        raise


class GestorHistorial:
    """Lee, agrega, filtra y exporta registros de experimentos."""

    def __init__(self, ruta: Path | str):
        self.ruta = Path(ruta)
        self.aviso: str | None = None  # último problema de lectura recuperado

    # --- lectura / escritura ------------------------------------------------
    def cargar(self) -> list[dict]:
        self.aviso = None
        if not self.ruta.exists():
            return []
        try:
            with open(self.ruta, encoding="utf-8") as archivo:
                datos = json.load(archivo)
            if not isinstance(datos, list) or not all(isinstance(r, dict) for r in datos):
                raise ValueError("el contenido no es una lista de registros")
            return datos
        except (json.JSONDecodeError, UnicodeDecodeError, ValueError) as exc:
            respaldo = self.ruta.with_name(
                f"{self.ruta.stem}.corrupto-{datetime.now():%Y%m%d-%H%M%S}{self.ruta.suffix}"
            )
            os.replace(self.ruta, respaldo)
            self.aviso = (
                f"El historial estaba dañado ({exc}). Se guardó una copia en "
                f"'{respaldo.name}' y se inició un historial vacío."
            )
            return []

    def guardar_todo(self, registros: list[dict]) -> None:
        escribir_json_atomico(self.ruta, registros)

    def agregar(self, registro: dict) -> None:
        if not isinstance(registro, dict) or not registro.get("id"):
            raise ErrorHistorial("El registro debe ser un diccionario con un campo 'id'.")
        registros = self.cargar()
        if any(r.get("id") == registro["id"] for r in registros):
            raise ErrorHistorial("Este experimento ya está guardado en el historial.")
        registros.append(registro)
        self.guardar_todo(registros)

    def eliminar(self, id_registro: str) -> bool:
        registros = self.cargar()
        restantes = [r for r in registros if r.get("id") != id_registro]
        if len(restantes) == len(registros):
            return False
        self.guardar_todo(restantes)
        return True

    @staticmethod
    def exportar(registros: list[dict], destino: Path | str) -> None:
        escribir_json_atomico(destino, registros)

    # --- consultas ----------------------------------------------------------
    @staticmethod
    def filtrar(
        registros: list[dict],
        texto: str = "",
        n: int | None = None,
        resultado: str | None = None,
    ) -> list[dict]:
        texto = texto.strip().lower()
        filtrados = []
        for r in registros:
            if n is not None and r.get("longitud_codigo") != n:
                continue
            if resultado and r.get("resultado") != resultado:
                continue
            if texto:
                campos = (r.get("mensaje_original") or "", r.get("mensaje_recuperado") or "", r.get("id", ""))
                if not any(texto in str(c).lower() for c in campos):
                    continue
            filtrados.append(r)
        return filtrados

    @staticmethod
    def indicadores(registros: list[dict]) -> dict:
        """Indicadores agregados para el dashboard, calculados con datos reales."""
        total = len(registros)
        exitosas = sum(1 for r in registros if r.get("resultado") == "exito")
        ambiguas = sum(1 for r in registros if r.get("resultado") == "ambiguo")
        return {
            "total": total,
            "exitosas": exitosas,
            "con_errores": sum(1 for r in registros if r.get("resultado") == "error"),
            "ambiguas": ambiguas,
            "errores_introducidos": sum(int(r.get("errores_introducidos", 0)) for r in registros),
            "errores_residuales": sum(int(r.get("errores_residuales", 0)) for r in registros),
            "ambiguedades": sum(int(r.get("ambiguedades", 0)) for r in registros),
            "porcentaje_recuperados": (100.0 * exitosas / total) if total else None,
        }

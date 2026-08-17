"""Adaptador de demostración: resuelve todo localmente, sin red.

Sustituye al cliente del back-office real. Lee y escribe sobre la misma base
SQLite que usa la aplicación (``MACRO.database``), sembrada con datos sintéticos
por :mod:`demo.seed`. Las operaciones que en un despliegue real implicarían una
llamada remota aquí simulan latencia y reportan progreso, de modo que el sistema
de jobs y el WebSocket de progreso se ejercitan igual que en producción.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

# Latencia simulada por operación remota, en segundos. Suficiente para que la
# barra de progreso sea visible sin volver lenta la suite de tests.
LATENCIA = 0.02


def _dormir(factor: float = 1.0) -> None:
    if LATENCIA:
        time.sleep(LATENCIA * factor)


def _avisar(progreso: Any, actual: int, total: int, mensaje: str) -> None:
    """Invoca el callback de progreso si lo hay, tolerando distintas firmas."""
    if progreso is None:
        return
    try:
        progreso(actual, total, mensaje)
    except TypeError:
        try:
            progreso(mensaje)
        except TypeError:
            pass


class DemoAdapter:
    """Implementación de :class:`~MACRO.adapters.BackofficeAdapter` sin red."""

    nombre = "demo"

    # --- sesión ---------------------------------------------------------
    def verificar_servicios(
        self, *, check_portal: bool = True, check_workflow: bool = True
    ) -> tuple[Any, Any]:
        """En demo ambos servicios están siempre disponibles."""
        _dormir()
        sesion = {"adapter": "demo", "servicio": "portal"} if check_portal else None
        cookie = {"adapter": "demo", "servicio": "workflow"} if check_workflow else None
        return sesion, cookie

    # --- lectura ---------------------------------------------------------
    @staticmethod
    def _registros(df) -> list[dict]:
        """Normaliza a lista de dicts lo que las funciones de BD devuelven.

        ``obtener_tabla_*`` devuelve un DataFrame (o ``None`` si la tabla no
        existe todavía), no una lista.
        """
        if df is None or getattr(df, "empty", True):
            return []
        return df.to_dict(orient="records")

    def listar_casos(self, *, archivados: bool = False) -> list[dict]:
        from MACRO.database import (
            obtener_tabla_asign,
            obtener_tabla_asign_incluye_archivo,
            obtener_tabla_bd,
        )

        if archivados:
            todos = self._registros(obtener_tabla_asign_incluye_archivo())
            vigentes = {str(c.get("num_doc")) for c in self._registros(obtener_tabla_asign())}
            return [c for c in todos if str(c.get("num_doc")) not in vigentes]

        filas = self._registros(obtener_tabla_asign())
        return filas or self._registros(obtener_tabla_bd())

    def cargar_casos(self, num_docs: list[str], progreso: Any = None) -> dict:
        """Alta de casos: en demo se toman del catálogo sintético ya sembrado."""
        from demo.seed import generar_casos

        catalogo = {c["num_doc"]: c for c in generar_casos()}
        total = len(num_docs) or 1
        encontrados, faltantes = [], []
        for i, nd in enumerate(num_docs, start=1):
            _dormir()
            _avisar(progreso, i, total, f"Cargando caso {nd}…")
            (encontrados if nd in catalogo else faltantes).append(nd)
        return {
            "ok": True,
            "cargados": len(encontrados),
            "no_encontrados": faltantes,
            "mensaje": (
                f"{len(encontrados)} caso(s) cargado(s)"
                + (f"; {len(faltantes)} no existen en el catálogo demo" if faltantes else "")
            ),
        }

    # --- documentos ------------------------------------------------------
    def descargar(self, num_doc: str, tipo: str, progreso: Any = None) -> dict:
        """Simula la descarga generando un archivo de texto en la carpeta del caso."""
        from MACRO.funciones.funciones_casos import get_case_folder

        carpeta = Path(get_case_folder({"num_doc": num_doc}))
        carpeta.mkdir(parents=True, exist_ok=True)
        destino = carpeta / f"{tipo}_{num_doc}.txt"

        pasos = 5
        for i in range(1, pasos + 1):
            _dormir()
            _avisar(progreso, i, pasos, f"Descargando {tipo} de {num_doc}…")
        destino.write_text(
            f"Artefacto de demostración\ntipo={tipo}\ncaso={num_doc}\n"
            "Contenido sintético: no corresponde a ningún expediente real.\n",
            encoding="utf8",
        )
        return {"ok": True, "ruta": str(destino), "mensaje": f"{tipo} descargado (demo)"}

    def listar_modelos(self, tipo: str) -> list[str]:
        from MACRO.funciones.funciones_generales import resource_path

        sub = "MODELOS_CARTA" if tipo.lower().startswith("carta") else "MODELOS_RI"
        base = Path(resource_path(str(Path("MACRO") / "RESOURCES" / sub)))
        if not base.is_dir():
            return []
        return sorted(p.name for p in base.glob("*.docx") if not p.name.startswith("~$"))

    def generar_documento(self, num_doc: str, tipo: str, modelo: str) -> dict:
        """Combina la plantilla con los datos del caso y deja el .docx resultante."""
        from MACRO.funciones.funciones_casos import get_case_folder

        carpeta = Path(get_case_folder({"num_doc": num_doc}))
        carpeta.mkdir(parents=True, exist_ok=True)
        destino = carpeta / f"{tipo}_{num_doc}.docx"
        _dormir(3)
        return {
            "ok": True,
            "ruta": str(destino),
            "modelo": modelo,
            "mensaje": f"{tipo.upper()} generada a partir de {modelo} (demo)",
        }

    # --- escritura -------------------------------------------------------
    def autorizar(self, decisiones: list[dict], progreso: Any = None) -> dict:
        total = len(decisiones) or 1
        for i, d in enumerate(decisiones, start=1):
            _dormir()
            _avisar(progreso, i, total, f"Autorizando {d.get('num_doc', '?')}…")
        return {
            "ok": True,
            "aplicadas": len(decisiones),
            "mensaje": f"{len(decisiones)} decisión(es) aplicada(s) (demo)",
        }

    def archivar(self, num_docs: list[str], progreso: Any = None) -> dict:
        from MACRO.database import archivar_casos_db

        total = len(num_docs) or 1
        for i, nd in enumerate(num_docs, start=1):
            _dormir()
            _avisar(progreso, i, total, f"Archivando {nd}…")
        try:
            archivar_casos_db(num_docs)
        except Exception as exc:  # noqa: BLE001 — el demo no debe romper el job
            return {"ok": False, "mensaje": f"No se pudo archivar: {exc}"}
        return {"ok": True, "archivados": len(num_docs), "mensaje": "Casos archivados (demo)"}

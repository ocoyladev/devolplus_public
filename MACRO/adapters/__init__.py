"""Capa de adaptadores hacia el back-office documental.

Este paquete define la frontera entre la aplicación y el sistema externo del que
se leen los casos y al que se envían los documentos generados.

En esta distribución pública solo existe el adaptador de demostración
(:mod:`MACRO.adapters.demo`), que resuelve todo contra una base SQLite sembrada
con datos sintéticos. Un despliegue real implementa :class:`BackofficeAdapter`
contra su propio sistema; ningún otro módulo del proyecto conoce ese detalle.

El adaptador activo se elige con la variable de entorno ``BACKOFFICE_ADAPTER``
(por defecto ``demo``).
"""

from __future__ import annotations

import os
from typing import Any, Protocol, runtime_checkable

# Firma del callback de progreso que JobManager inyecta en las tareas largas.
# ``(actual, total, mensaje)`` -> None
ProgresoCallback = Any


@runtime_checkable
class BackofficeAdapter(Protocol):
    """Contrato mínimo que debe cumplir un back-office para servir a la app.

    Las implementaciones no deben lanzar excepciones de red hacia arriba: los
    fallos se reportan devolviendo ``{"ok": False, "mensaje": ...}`` para que la
    capa de jobs los convierta en un evento de error legible por el frontend.
    """

    # --- sesión ---------------------------------------------------------
    def verificar_servicios(
        self, *, check_portal: bool = True, check_workflow: bool = True
    ) -> tuple[Any, Any]:
        """Devuelve ``(sesion_portal, cookie_workflow)``; ``None`` si no conecta."""
        ...

    # --- lectura de casos ------------------------------------------------
    def listar_casos(self, *, archivados: bool = False) -> list[dict]:
        """Casos vigentes (o archivados) como lista de registros planos."""
        ...

    def cargar_casos(self, num_docs: list[str], progreso: ProgresoCallback = None) -> dict:
        """Da de alta en la BD local los casos indicados por número de documento."""
        ...

    # --- documentos ------------------------------------------------------
    def descargar(
        self, num_doc: str, tipo: str, progreso: ProgresoCallback = None
    ) -> dict:
        """Descarga un artefacto (``expediente``, ``ri``, ``cartas``…) del caso."""
        ...

    def generar_documento(self, num_doc: str, tipo: str, modelo: str) -> dict:
        """Genera carta o resolución a partir de una plantilla de combinación."""
        ...

    def listar_modelos(self, tipo: str) -> list[str]:
        """Nombres de plantilla disponibles para ``tipo`` (``carta`` | ``ri``)."""
        ...

    # --- escritura -------------------------------------------------------
    def autorizar(self, decisiones: list[dict], progreso: ProgresoCallback = None) -> dict:
        """Aplica las decisiones de autorización sobre los casos indicados."""
        ...

    def archivar(self, num_docs: list[str], progreso: ProgresoCallback = None) -> dict:
        """Archiva los casos indicados."""
        ...


def get_adapter() -> BackofficeAdapter:
    """Devuelve el adaptador configurado en ``BACKOFFICE_ADAPTER``.

    Se resuelve en cada llamada (no se cachea) para que los tests puedan cambiar
    la variable de entorno sin reimportar el módulo.
    """
    nombre = os.environ.get("BACKOFFICE_ADAPTER", "demo").strip().lower()
    if nombre == "demo":
        from MACRO.adapters.demo import DemoAdapter

        return DemoAdapter()
    raise RuntimeError(
        f"Adaptador desconocido: {nombre!r}. Esta distribución solo incluye 'demo'. "
        "Para conectar un back-office real, implemente BackofficeAdapter y regístrelo aquí."
    )


__all__ = ["BackofficeAdapter", "get_adapter", "ProgresoCallback"]

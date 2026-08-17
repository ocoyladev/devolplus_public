"""Flujos de negocio de la aplicación.

En esta distribución pública cada módulo de flujo delega en el adaptador
configurado (:func:`MACRO.adapters.get_adapter`), que por defecto es el
adaptador de demostración sin red. Los nombres de módulo y de función se
conservan idénticos a los del despliegue real: los routers, los esquemas y el
frontend no cambian al sustituir el adaptador.
"""

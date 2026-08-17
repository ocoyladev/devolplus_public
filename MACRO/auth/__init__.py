"""Módulo de autenticación y auditoría contra Oracle Autonomous Database.

Reemplaza el mecanismo de licencia por hash local (``MACRO/seguridad.py``) en la
web app: verifica al usuario de Windows contra la tabla ``usuarios`` de Oracle y
audita cada arranque en ``registro_logueos``. Incluye una caché local + cola de
logueos pendientes (en el SQLite existente) para tolerar caídas de conexión.

La lógica de negocio del aplicativo no se toca; este paquete es aditivo.
"""

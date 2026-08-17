# Admin de accesos — DEVOL+

Programa independiente para que el autor (Oscar Coyla) gestione el control de
acceso: aprobar/rechazar/inactivar solicitudes y revisar el historial de
logueos. Reutiliza el módulo compartido `MACRO/auth` (misma conexión Oracle y
mismo `.env` que la web app principal).

## Estructura

```
admin_accesos/
├── backend/    # FastAPI sobre MACRO.auth.admin_service
│   ├── server.py   # GET /api/solicitudes, PATCH /api/solicitudes/{id}, GET /api/logueos
│   └── main.py     # lanzador (uvicorn + ventana WebView2)
└── frontend/   # React + Vite (Solicitudes / Historial de logueos)
```

## Requisitos

- Depende del **mismo venv** del repo (fastapi, uvicorn, oracledb, pywebview):
  `pip install -r requirements-web.txt`.
- `.env` + wallet configurados (ver `.env.example` y `packaging/BUILD_WINDOWS.md`).

## Desarrollo

Backend (desde la raíz del repo, para que `MACRO` sea importable):

```
.venv/bin/python -m admin_accesos.backend.main      # servidor + ventana
```

Frontend (dev con proxy a :8090):

```
cd admin_accesos/frontend
npm install
npm run dev        # http://127.0.0.1:5174
```

## Build (empaquetado)

```
cd admin_accesos/frontend && npm run build      # → frontend/dist
```

El `main.py` sirve `frontend/dist` same-origin. Para el `.exe`, usa el
entrypoint `run_admin.py` y la spec `packaging/admin_accesos.spec`:

```
.venv\Scripts\pyinstaller packaging\admin_accesos.spec   # → dist\DEVOL+ Admin.exe
```

Usa su propio puerto (8090+), distinto del app principal (8080+). Necesita el
mismo `.env` (Oracle) junto al ejecutable. Ver `packaging/BUILD_WINDOWS.md`.

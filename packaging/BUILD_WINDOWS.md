# Construir DEVOL+ (.exe) en Windows

Requisitos en la PC de build: Python 3.14 con el venv del proyecto, Node 20+,
y WebView2 Runtime (incluido en Windows 10/11).

## Forma recomendada: `build.py` (fija la versión en un paso)

`build.py` orquesta todo (compila el frontend y empaqueta el `.exe`) fijando la
misma versión en frontend y backend. Ejecútalo con el Python que quieras usar
para empaquetar (por ejemplo el portátil de la PC de build):

```
D:\Data\Python\Python\python.exe build.py --version 1.0.1     # app + admin
D:\Data\Python\Python\python.exe build.py                     # usa el VERSION actual
D:\Data\Python\Python\python.exe build.py --version 1.0.1 --target app
```

Usa `sys.executable -m PyInstaller`, así el `.exe` se arma con **ese mismo
Python**. `--version` escribe el archivo `VERSION` (fuente única de verdad); la
spec lo embebe en el `.exe` y el backend lo sirve en `GET /api/version`.

**PC de empaquetado con solo Python (sin Node):** la versión NO se hornea en el
frontend (el frontend la consulta en runtime al backend), así que `build.py`
**omite automáticamente** el build del frontend si no encuentra `npm` y empaqueta
el `frontend/dist` ya compilado. Es decir: en la PC corporativa basta el Python
portátil; el `frontend/dist` (y `admin_accesos/frontend/dist`) se genera aparte
en una PC con Node (entorno de desarrollo) y se deja junto al repo.

Requiere PyInstaller instalado para ese intérprete. Con `--skip-frontend` nunca
recompila el frontend aunque haya npm.

> **Antes de distribuir un `.exe` con versión nueva:** corre en Oracle la
> migración `ALTER TABLE registro_logueos ADD (version VARCHAR2(20));` (ver
> `docs/db/oracle_auth_schema.sql`). Si no existe la columna, el INSERT del
> logueo fallará.

## Forma manual (paso a paso)

1. Compilar el frontend:
   ```
   cd frontend
   npm install
   npm run build
   ```
2. Instalar deps web en el venv (si no están):
   ```
   .venv\Scripts\python -m pip install -r requirements-web.txt
   ```
3. Empaquetar:
   ```
   .venv\Scripts\pyinstaller packaging\devolplus.spec
   ```
4. El ejecutable queda en `dist\DEVOL+.exe`. Cópialo a la carpeta de despliegue
   junto a las carpetas de recursos y `devol_plus.db`.

## Control de acceso (Oracle) — `.env`

El arranque verifica al usuario contra Oracle Autonomous Database. El driver
`oracledb` va en modo *thin* (Python puro, no requiere Oracle Instant Client) y
**se instala con `requirements-web.txt`** (paso 2); la spec lo incluye con
`collect_submodules("oracledb")`. La conexión es por **TLS directo** con el DSN
completo (alias `_tp`), **sin wallet**.

**Solo se distribuye el `.exe`** (autocontenido). Al empaquetar, el `.env` de la
**raíz del repo** se **codifica (ofuscado)** y se embebe como `.envx`; la app lo
decodifica al arrancar (`funciones_generales.cargar_env`). Así no hace falta
enviar el `.env` a cada usuario y las credenciales **no quedan en texto plano**
dentro del `.exe` (no aparecen con `strings` ni al desempaquetar).

- En **desarrollo**, el `.env` va en la raíz del repo (texto plano, git-ignored).
- Antes de **empaquetar**, asegúrate de que ese `.env` de la raíz tenga las
  credenciales correctas (`ORACLE_USER/PASSWORD/DSN` y las `DB_*` de SQL Server).
- Para **cambiar credenciales sin reempaquetar**, puedes dejar un `.env` en texto
  plano junto al `.exe`: tiene prioridad sobre el embebido.

> **Importante (seguridad):** la ofuscación evita el texto plano, pero no es
> cifrado fuerte; alguien decidido podría recuperar las credenciales del `.exe`.
> La barrera real es que el usuario Oracle del `.env` sea de **mínimos
> privilegios** (solo INSERT/SELECT/UPDATE sobre `usuarios` y
> `registro_logueos`), **no el ADMIN**. Ver `docs/db/oracle_usuario_app.sql`.

Sin conexión a Oracle, un usuario ya aprobado antes en ese equipo puede entrar
(los logueos quedan en cola local y se suben al reconectar); un usuario nuevo
verá "sin conexión".

## Construir el Admin de accesos (.exe aparte)

Programa independiente para aprobar/rechazar solicitudes y ver el historial.
Usa su **propio puerto (8090+)**, distinto del app principal (8080+), así que
ambos ejecutables pueden convivir.

1. Compilar su frontend:
   ```
   cd admin_accesos\frontend
   npm install
   npm run build
   ```
2. Empaquetar (mismo venv con `requirements-web.txt` ya instalado):
   ```
   .venv\Scripts\pyinstaller packaging\admin_accesos.spec
   ```
3. Queda en `dist\DEVOL+ Admin.exe`. Necesita el mismo `.env` (Oracle) a su lado.

## `console=False` y logs

Ambas specs traen `console=False` (release, sin ventana de terminal). Como en ese
modo `sys.stdout`/`sys.stderr` son `None` y uvicorn fallaría al iniciar
(`DefaultFormatter` llama a `sys.stdout.isatty()`), el arranque redirige esos
streams y **manda los logs de uvicorn a un archivo rotativo** junto al `.exe`:

- `devolplus.log` (app principal) y `devolplus_admin.log` (admin), 1 MB × 3.

Para depurar en desarrollo puedes poner `console=True` temporalmente (verás los
logs también en la terminal), pero no es necesario: el archivo ya los conserva.

## Verificación de humo
Al hacer doble clic en `DEVOL+.exe` debe abrirse una ventana WebView2 con el
título "DEVOL+" mostrando la pantalla de acceso o la vista principal. El
`DEVOL+ Admin.exe` abre la ventana de administración de accesos.

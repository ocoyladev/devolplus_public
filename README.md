# DEVOL+

Aplicación de escritorio para automatizar un back-office de procesamiento
documental: carga de expedientes, descarga de artefactos, generación de
resoluciones y cartas por combinación de plantillas, validación previa al
archivo y registro de tickets en una mesa de ayuda.

Backend en **Python (FastAPI)**, frontend en **React + TypeScript (Vite)**, y un
ejecutable único de Windows empaquetado con **PyInstaller** que embebe el
frontend compilado y abre una ventana nativa (`pywebview`).

> **Esta es una distribución de demostración.** Corre de punta a punta sin
> ninguna infraestructura: sin red, sin base de datos corporativa y con datos
> sintéticos. Ver [Modo demo](#modo-demo).

---

## Arranque rápido

```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements-web.txt
cp .env.example .env

cd frontend && npm install && npm run build && cd ..
python run_web.py
```

Abre <http://127.0.0.1:8000>. No hay que crear usuarios ni pedir accesos: en
modo demo cualquier usuario entra directamente.

Para sembrar la tabla con casos sintéticos:

```bash
python -m demo.seed        # 60 casos deterministas
```

### Tests

```bash
pytest                     # backend + demo
cd frontend && npx tsc -b && npm test
```

---

## Arquitectura

```
┌─────────────────┐   HTTP + WebSocket   ┌──────────────────────────────┐
│  React (Vite)   │ ───────────────────► │  FastAPI (MACRO/app)         │
│  frontend/      │ ◄─────────────────── │  routers → schemas → jobs    │
└─────────────────┘   eventos progress   └──────────────┬───────────────┘
                                                        │
                                         ┌──────────────▼───────────────┐
                                         │  MACRO/flujos  (orquestación)│
                                         └──────────────┬───────────────┘
                                                        │
                                         ┌──────────────▼───────────────┐
                                         │  MACRO/adapters              │
                                         │  BackofficeAdapter (Protocol)│
                                         │  └─ DemoAdapter (sin red)    │
                                         └──────────────────────────────┘
```

| Capa | Ruta | Responsabilidad |
|---|---|---|
| API | `MACRO/app/routers/` | endpoints delgados; sin lógica de negocio |
| Contratos | `MACRO/app/schemas/` | modelos Pydantic de request/response |
| Jobs | `MACRO/app/jobs.py` | tareas en background + progreso por WebSocket |
| Flujos | `MACRO/flujos/` | orquestación por caso de uso |
| Adaptador | `MACRO/adapters/` | frontera con el sistema externo |
| Dominio | `MACRO/funciones/`, `MACRO/itop/` | Excel, PDF, foliado, tickets, cartas |
| Acceso | `MACRO/auth/` | validación de usuarios y caché offline |
| Persistencia | `MACRO/database.py` | SQLite local |

Puntos que vale la pena mirar:

- **Jobs con progreso** (`MACRO/app/jobs.py`): las tareas largas corren en un
  hilo y publican eventos por WebSocket; el frontend los consume en
  `frontend/src/ws/useProgreso.ts`.
- **Caché de acceso offline** (`MACRO/auth/cache_local.py`): si la base de
  accesos no responde, un usuario ya aprobado entra igual y su logueo queda
  encolado para sincronizar después.
- **Versión en runtime** (`MACRO/version.py`): el `.exe` embebe el archivo
  `VERSION` y el frontend la consulta por `GET /api/version`, así el build del
  frontend no depende de la versión.
- **Generación documental** (`MACRO/flujos/flujo_documentos.py`): combina campos
  sobre plantillas `.docx` en `MACRO/RESOURCES/`.

---

## Modo demo

Esta distribución no incluye ningún cliente de sistema externo. En su lugar:

| Pieza | Comportamiento |
|---|---|
| `BACKOFFICE_ADAPTER=demo` | `DemoAdapter` resuelve todo en local, con latencia simulada para que el progreso sea observable |
| `AUTH_MODE=demo` | cualquier usuario queda aprobado; no se abre conexión a ninguna base |
| `demo/seed.py` | 60 casos sintéticos deterministas |
| `MACRO/RESOURCES/` | plantillas de ejemplo, neutralizadas |

### Los datos son sintéticos por construcción

Los RUC generados llevan **dígito verificador inválido a propósito**: conservan
la forma real (11 dígitos, prefijo `10`/`20`) pero fallan la validación módulo
11, así que no pueden corresponder a ningún contribuyente inscrito. Hay un test
que lo verifica como invariante:

```
demo/tests/test_seed.py::test_ningun_ruc_generado_es_valido
```

Los nombres se componen de listas de apellidos y nombres comunes; cualquier
coincidencia con una persona real es casual y no proviene de ningún registro.

### Plantillas

Las plantillas `.docx` de `MACRO/RESOURCES/` son ejemplos con campos de
combinación (`MERGEFIELD`), sin datos de ninguna persona. Fueron procesadas con
`demo/neutralizar_plantillas.py`, que vacía la metadata de autoría, sustituye
las imágenes embebidas y reemplaza las referencias a cualquier organización:

```bash
python -m demo.neutralizar_plantillas MACRO/RESOURCES --verificar
```

### Conectar un back-office real

Implementar el `Protocol` de `MACRO/adapters/__init__.py` y registrarlo en
`get_adapter()`. Ningún otro módulo necesita cambiar: los flujos, los routers,
los esquemas y el frontend son agnósticos del origen de los datos.

---

## Empaquetado (Windows)

El `.exe` embebe `frontend/dist`, así que **hay que compilar el frontend antes**
o el ejecutable queda con una versión vieja:

```bash
cd frontend && npm run build     # → frontend/dist
pyinstaller packaging/devolplus.spec
```

Atajo que hace ambos pasos y fija la versión:

```bash
python build.py --version 1.0.1
```

Detalles en [`packaging/BUILD_WINDOWS.md`](packaging/BUILD_WINDOWS.md).

---

## Limitaciones conocidas

Cosas que en esta base de código están resueltas de forma deliberadamente
simple, y que conviene mirar antes de reutilizarlas:

- **Almacenamiento de credenciales** (`MACRO/database.py`): las contraseñas de
  los sistemas externos se guardan con XOR reversible sobre una clave leída de
  `DEVOL_XOR_KEY`. Es **ofuscación, no cifrado**: protege de una lectura casual
  del archivo, no de un atacante con acceso al disco. Para uso real, sustituir
  por el keyring del sistema operativo (`keyring`, que en Windows usa DPAPI) o,
  mejor, no persistir la contraseña y pedirla una vez por sesión.
- **Licenciamiento local** (`MACRO/seguridad.py`): la clave es un hash del
  usuario con un salt de entorno. Sirve para evitar ejecuciones accidentales,
  no como control de seguridad.
- **RSIRAT**: la automatización de escritorio (`pywinauto`) es solo Windows y no
  forma parte de esta distribución.

---

## Licencia

MIT. Ver [`LICENSE`](LICENSE).

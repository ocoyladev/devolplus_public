# DEVOL+

A desktop application that automates a document-processing back office: loading
case files, fetching supporting artifacts, generating letters and resolutions by
mail-merging templates, running pre-archive validation, and filing service-desk
tickets.

Python **FastAPI** backend, **React + TypeScript (Vite)** frontend, packaged into
a single Windows executable with **PyInstaller** that embeds the compiled
frontend and opens a native window via `pywebview`.

> **This is a demonstration distribution.** It runs end to end with no
> infrastructure at all — no network, no corporate database, and synthetic data
> throughout. See [Demo mode](#demo-mode).

---

## Quick start

```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements-web.txt
cp .env.example .env

cd frontend && npm install && npm run build && cd ..
python run_web.py
```

Open <http://127.0.0.1:8000>. There is no sign-up and no access request: in demo
mode every user is admitted straight away.

Seed the case table with synthetic records:

```bash
python -m demo.seed        # 60 deterministic cases
```

### Tests

```bash
pytest                              # backend + demo helpers
cd frontend && npx tsc -b && npm test
```

---

## Architecture

```
┌─────────────────┐   HTTP + WebSocket   ┌──────────────────────────────┐
│  React (Vite)   │ ───────────────────► │  FastAPI (MACRO/app)         │
│  frontend/      │ ◄─────────────────── │  routers → schemas → jobs    │
└─────────────────┘   progress events    └──────────────┬───────────────┘
                                                        │
                                         ┌──────────────▼───────────────┐
                                         │  MACRO/flujos  (orchestration)│
                                         └──────────────┬───────────────┘
                                                        │
                                         ┌──────────────▼───────────────┐
                                         │  MACRO/adapters              │
                                         │  BackofficeAdapter (Protocol)│
                                         │  └─ DemoAdapter (no network) │
                                         └──────────────────────────────┘
```

| Layer | Path | Responsibility |
|---|---|---|
| API | `MACRO/app/routers/` | thin endpoints, no business logic |
| Contracts | `MACRO/app/schemas/` | Pydantic request/response models |
| Jobs | `MACRO/app/jobs.py` | background tasks with WebSocket progress |
| Flows | `MACRO/flujos/` | one module per use case |
| Adapter | `MACRO/adapters/` | boundary with the external system |
| Domain | `MACRO/funciones/` | spreadsheets, PDFs, pagination, letters, ticket payloads |
| Access | `MACRO/auth/` | user validation and offline cache |
| Storage | `MACRO/database.py` | local SQLite |

Worth a look:

- **Jobs with live progress** (`MACRO/app/jobs.py`) — long tasks run on a worker
  thread and publish events over a WebSocket; the frontend consumes them in
  `frontend/src/ws/useProgreso.ts`.
- **Offline access cache** (`MACRO/auth/cache_local.py`) — when the access
  database is unreachable, an already-approved user still gets in and their
  login is queued for later reconciliation.
- **Runtime versioning** (`MACRO/version.py`) — the executable embeds the
  `VERSION` file and the frontend reads it from `GET /api/version`, so the
  frontend build never has to be rebuilt for a version bump.
- **Document generation** (`MACRO/flujos/flujo_documentos.py`) — merges case
  fields into `.docx` templates under `MACRO/RESOURCES/`.

The codebase is written in Spanish (identifiers, docstrings, and UI strings),
matching the domain it models.

---

## Demo mode

This distribution ships no client for any external system. Instead:

| Piece | Behaviour |
|---|---|
| `BACKOFFICE_ADAPTER=demo` | `DemoAdapter` resolves everything locally, with simulated latency so progress is observable |
| `AUTH_MODE=demo` | every user is approved; no database connection is opened |
| `demo/seed.py` | 60 deterministic synthetic cases |
| `MACRO/RESOURCES/` | sample templates, sanitised |

### The data is synthetic by construction

Generated taxpayer IDs carry a **deliberately invalid check digit**. They keep
the real shape (11 digits, `10`/`20` prefix) but fail the modulo-11 checksum, so
none of them can match a registered taxpayer. This is pinned as an invariant:

```
demo/tests/test_seed.py::test_ningun_ruc_generado_es_valido
```

Names are assembled from lists of common surnames and given names. Any
resemblance to a real person is coincidental and comes from no registry.

### Templates

The `.docx` files under `MACRO/RESOURCES/` are sample mail-merge templates
(`MERGEFIELD` placeholders) containing nobody's data. They were processed with
`demo/neutralizar_plantillas.py`, which clears authorship metadata, replaces
embedded images, and rewrites any organisation references:

```bash
python -m demo.neutralizar_plantillas MACRO/RESOURCES --verificar
```

Run that check after touching any template. A `.docx` is a ZIP, and two of the
three leak paths — `docProps/*.xml` authorship fields and `word/media/*` embedded
images — are invisible when you open the file in a word processor.

### Wiring up a real back office

Implement the `Protocol` in `MACRO/adapters/__init__.py` and register it in
`get_adapter()`. Nothing else changes: the flows, routers, schemas, and frontend
are agnostic about where the data comes from.

---

## Packaging (Windows)

The executable embeds `frontend/dist`, so **the frontend must be built first** or
the `.exe` ships a stale UI:

```bash
cd frontend && npm run build     # → frontend/dist
pyinstaller packaging/devolplus.spec
```

One command that does both and stamps the version:

```bash
python build.py --version 1.0.1
```

Details in [`packaging/BUILD_WINDOWS.md`](packaging/BUILD_WINDOWS.md).

---

## Known limitations

Things this codebase solves deliberately simply — worth understanding before
reusing them:

- **Credential storage** (`MACRO/database.py`): passwords for external systems
  are stored with a reversible XOR over a key read from `DEVOL_XOR_KEY`. That is
  **obfuscation, not encryption**: it defeats a casual look at the file, not an
  attacker with disk access. For production use, switch to the OS keyring
  (`keyring`, which maps to DPAPI on Windows) or, better, don't persist the
  password at all and prompt once per session.
- **Local licensing** (`MACRO/seguridad.py`): the key is a hash of the username
  plus a salt from the environment. It prevents accidental runs; it is not a
  security control.
- **Desktop automation**: one flow drives a legacy desktop application through
  the Windows UI automation API. It is Windows-only and is not part of this
  distribution — the demo adapter stands in for it.

---

## License

MIT. See [`LICENSE`](LICENSE).

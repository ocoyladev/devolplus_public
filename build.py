#!/usr/bin/env python3
"""Genera los ejecutables de DEVOL+ fijando la versión en un solo paso.

Ejecútalo con el mismo Python con el que quieras empaquetar (usa
``sys.executable -m PyInstaller``), típicamente el Python portátil de la PC
Windows donde se arma el ``.exe``:

    D:\\Data\\Python\\Python\\python.exe build.py --version 1.0.1

La versión NO se hornea en el frontend: el backend la sirve en runtime
(``GET /api/version``, desde el archivo ``VERSION`` embebido en el ``.exe``) y el
frontend la consulta. Por eso el ``.exe`` se puede armar en una PC con **solo
Python** (sin Node): si no hay ``npm``, este script omite el build del frontend y
empaqueta el ``frontend/dist`` ya compilado (que se genera en una PC con Node).

Qué hace:
    1. Escribe la versión en ``VERSION`` (si pasas ``--version``).
    2. Compila el frontend con ``npm run build`` SOLO si hay npm (si no, lo omite).
    3. Empaqueta el/los ``.exe`` con PyInstaller (la ``.spec`` embebe la versión).

Ejemplos:
    python build.py --version 1.0.1              # SOLO DEVOL+ (app) — por defecto
    python build.py                              # solo DEVOL+, usa el VERSION actual
    python build.py --target all --version 1.0.1 # DEVOL+ y DEVOL+ Admin
    python build.py --target admin               # solo DEVOL+ Admin
    python build.py --skip-frontend              # nunca recompila el frontend
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

# abspath (no resolve): conserva la unidad mapeada (X:\...) en vez de expandirla
# a una ruta UNC (\\servidor\...), que CMD rechaza como directorio de trabajo.
ROOT = Path(os.path.abspath(__file__)).parent

# (nombre, carpeta_frontend, ruta_spec) por cada ejecutable.
TARGETS = {
    "app": ("DEVOL+", ROOT / "frontend", ROOT / "packaging" / "devolplus.spec"),
    "admin": (
        "DEVOL+ Admin",
        ROOT / "admin_accesos" / "frontend",
        ROOT / "packaging" / "admin_accesos.spec",
    ),
}


def _run(cmd: list[str], cwd: Path, env: dict[str, str], usar_shell: bool) -> None:
    """Ejecuta un comando y aborta el build si falla."""
    print(f"\n>>> {' '.join(cmd)}  (cwd={cwd})", flush=True)
    resultado = subprocess.run(cmd, cwd=str(cwd), env=env, shell=usar_shell)
    if resultado.returncode != 0:
        sys.exit(f"ERROR: '{' '.join(cmd)}' terminó con código {resultado.returncode}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build de los .exe de DEVOL+.")
    parser.add_argument(
        "--version",
        help="Versión a fijar (p. ej. 1.0.1). Si se omite, usa el archivo VERSION.",
    )
    parser.add_argument(
        "--target",
        choices=["all", "app", "admin"],
        default="app",
        help="Qué ejecutable armar: 'app'=solo DEVOL+ (por defecto), "
             "'admin'=solo DEVOL+ Admin, 'all'=ambos.",
    )
    parser.add_argument(
        "--skip-frontend",
        action="store_true",
        help="No recompilar el frontend (usa el dist ya compilado).",
    )
    args = parser.parse_args()

    version_file = ROOT / "VERSION"
    if args.version:
        version = args.version.strip()
        version_file.write_text(version + "\n", encoding="utf-8")
        print(f"VERSION -> {version}")
    else:
        version = version_file.read_text(encoding="utf-8").strip()
        print(f"VERSION (sin cambios) -> {version}")

    # Entorno compartido: la misma versión para el .exe (la lee la spec).
    env = dict(os.environ)
    env["DEVOLPLUS_VERSION"] = version

    # ¿Hay npm? En la PC de empaquetado (solo Python) no lo habrá: se omite el
    # build del frontend y se usa el dist ya compilado.
    npm = shutil.which("npm")
    hacer_frontend = not args.skip_frontend and npm is not None
    if not args.skip_frontend and npm is None:
        print(
            "\n[aviso] npm no está disponible: se OMITE el build del frontend y se "
            "empaqueta el 'dist' ya compilado. Asegúrate de que frontend/dist (y "
            "admin_accesos/frontend/dist) estén actualizados."
        )

    seleccion = ["app", "admin"] if args.target == "all" else [args.target]

    for nombre in seleccion:
        etiqueta, front_dir, spec = TARGETS[nombre]
        print(f"\n=== {etiqueta} ===")
        if hacer_frontend:
            _run(["npm", "run", "build"], cwd=front_dir, env=env, usar_shell=True)
        dist = front_dir / "dist"
        if not (dist / "index.html").exists():
            sys.exit(
                f"ERROR: falta {dist}\\index.html. Compila el frontend en una PC con "
                "Node (npm run build) o copia el dist antes de empaquetar."
            )
        # PyInstaller sin shell: sys.executable es una ruta absoluta y así se evita
        # que CMD intervenga con el directorio de trabajo (UNC).
        _run(
            [sys.executable, "-m", "PyInstaller", "--noconfirm", str(spec)],
            cwd=ROOT,
            env=env,
            usar_shell=False,
        )

    print(f"\nListo. Ejecutables en dist/ con versión {version}.")


if __name__ == "__main__":
    main()

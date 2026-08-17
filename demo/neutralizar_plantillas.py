"""Neutraliza plantillas .docx para su distribución pública.

Un .docx es un ZIP: además del texto visible arrastra metadata de autoría
(``docProps/core.xml``, ``docProps/app.xml``) e imágenes embebidas
(``word/media/``) que no se ven al abrirlo en el procesador de textos. Este
script deja la plantilla utilizable como demostración del motor de combinación
y elimina todo rastro de la organización de origen:

1. reemplaza las imágenes embebidas por un logotipo genérico;
2. vacía la metadata de autoría, empresa e impresión;
3. sustituye las marcas institucionales del cuerpo, encabezados y pies.

Uso::

    python -m demo.neutralizar_plantillas MACRO/RESOURCES --verificar
"""

from __future__ import annotations

import argparse
import re
import shutil
import struct
import sys
import zipfile
from pathlib import Path

# Sustituciones de texto aplicadas a todas las partes XML del documento.
SUSTITUCIONES: tuple[tuple[str, str], ...] = (
    ("INTENDENCIA LIMA", "INTENDENCIA REGIONAL EJEMPLO"),
    ("INTENDENCIA REGIONAL LIMA", "INTENDENCIA REGIONAL EJEMPLO"),
    ("Superintendencia Nacional de Aduanas y de Administración Tributaria",
     "Organismo Recaudador de Ejemplo"),
    ("Superintendencia Nacional de Administración Tributaria",
     "Organismo Recaudador de Ejemplo"),
    ("SUPERINTENDENCIA NACIONAL", "ORGANISMO RECAUDADOR"),
    ("Superintendencia", "Organismo Recaudador"),
    ("SUNAT", "ACME"),
    ("Sunat", "Acme"),
    ("sunat", "acme"),
    ("REPUBLICA DEL PERU", "REPUBLICA DE EJEMPLO"),
    ("REPÚBLICA DEL PERÚ", "REPÚBLICA DE EJEMPLO"),
)

# Metadata que se vacía por completo.
CAMPOS_META = (
    "dc:creator", "cp:lastModifiedBy", "cp:lastPrinted", "dc:title",
    "dc:subject", "dc:description", "cp:keywords", "cp:category",
    "Company", "Manager", "cp:revision",
)

# PNG 1x1 gris claro: sustituto neutro de cualquier imagen embebida.
_PNG_PLACEHOLDER = bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108020000009075"
    "2b0e0000000c4944415408d763c8c8c800000300010021b8a3450000000049"
    "454e44ae426082"
)


def _logo_generico(nombre: str) -> bytes:
    """Imagen de reemplazo. Se usa un PNG mínimo, válido para cualquier lector."""
    del nombre  # el formato original es irrelevante: Word acepta el PNG igual
    return _PNG_PLACEHOLDER


def _limpiar_meta(xml: str) -> str:
    for campo in CAMPOS_META:
        xml = re.sub(
            rf"<{campo}[^>]*>.*?</{campo}>", f"<{campo}></{campo}>", xml, flags=re.S
        )
    return xml


def _sustituir_texto(xml: str) -> str:
    for viejo, nuevo in SUSTITUCIONES:
        xml = xml.replace(viejo, nuevo)
    return xml


def neutralizar(origen: Path, destino: Path | None = None) -> dict:
    """Neutraliza un .docx. Si ``destino`` es ``None``, reescribe en el sitio."""
    destino = destino or origen
    cambios = {"texto": 0, "meta": 0, "imagenes": 0}
    tmp = destino.with_suffix(".docx.tmp")

    with zipfile.ZipFile(origen) as zin, zipfile.ZipFile(
        tmp, "w", zipfile.ZIP_DEFLATED
    ) as zout:
        for item in zin.infolist():
            datos = zin.read(item.filename)

            if item.filename.startswith("word/media/"):
                datos = _logo_generico(item.filename)
                cambios["imagenes"] += 1
            elif item.filename.startswith("docProps/") and item.filename.endswith(".xml"):
                xml = datos.decode("utf8", "ignore")
                nuevo = _sustituir_texto(_limpiar_meta(xml))
                cambios["meta"] += int(nuevo != xml)
                datos = nuevo.encode("utf8")
            elif item.filename.endswith(".xml"):
                xml = datos.decode("utf8", "ignore")
                nuevo = _sustituir_texto(xml)
                cambios["texto"] += int(nuevo != xml)
                datos = nuevo.encode("utf8")

            zout.writestr(item, datos)

    shutil.move(str(tmp), str(destino))
    return cambios


def verificar(ruta: Path) -> list[str]:
    """Devuelve los hallazgos residuales de un .docx ya neutralizado."""
    patron = re.compile(r"sunat|superintendencia|intendencia lima|per[uú]", re.I)
    hallazgos: list[str] = []
    with zipfile.ZipFile(ruta) as z:
        for nombre in z.namelist():
            if nombre.startswith("word/media/"):
                datos = z.read(nombre)
                if datos != _PNG_PLACEHOLDER:
                    hallazgos.append(f"{nombre}: imagen no sustituida ({len(datos)} bytes)")
                continue
            if not nombre.endswith(".xml"):
                continue
            texto = re.sub(r"<[^>]+>", " ", z.read(nombre).decode("utf8", "ignore"))
            for m in set(patron.findall(texto)):
                hallazgos.append(f"{nombre}: '{m}'")
    return hallazgos


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("carpeta", type=Path, help="carpeta con los .docx a neutralizar")
    ap.add_argument("--verificar", action="store_true", help="solo verificar, sin escribir")
    args = ap.parse_args(argv)

    docs = sorted(args.carpeta.rglob("*.docx"))
    if not docs:
        print(f"No se encontraron .docx bajo {args.carpeta}", file=sys.stderr)
        return 1

    fallos = 0
    for doc in docs:
        if args.verificar:
            hallazgos = verificar(doc)
            estado = "OK" if not hallazgos else f"{len(hallazgos)} hallazgo(s)"
            print(f"  [{estado}] {doc.relative_to(args.carpeta)}")
            for h in hallazgos:
                print(f"      - {h}")
            fallos += bool(hallazgos)
        else:
            c = neutralizar(doc)
            print(
                f"  neutralizado {doc.relative_to(args.carpeta)} "
                f"(texto:{c['texto']} meta:{c['meta']} img:{c['imagenes']})"
            )
    return 1 if fallos else 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

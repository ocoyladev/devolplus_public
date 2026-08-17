"""Registro de cartas por solicitud (tabla_cartas).

`tabla_cartas` es la fuente de verdad de las cartas de un caso.
`tabla_asign.carta` queda como espejo denormalizado (ver `sincronizar_espejo`)
para que los consumidores existentes —descarga de cartas, "Agregar numeración",
"Registrar cartas", import de Excel— sigan funcionando sin cambios.
"""
from __future__ import annotations

import sqlite3
from datetime import date, datetime

TIPOS = ("PRIMERA", "REITERATIVA", "AMPLIACION", "OTRA")
ESTADOS = ("ATENDIDA", "SIN_NOTIFICAR", "VENCIDA", "POR_VENCER", "VIGENTE")

_DDL = """
CREATE TABLE IF NOT EXISTS tabla_cartas (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    num_doc             TEXT NOT NULL,
    numero              TEXT DEFAULT '',
    anio                TEXT DEFAULT '',
    tipo                TEXT DEFAULT '',
    fecha_emision       TEXT,
    fecha_notificacion  TEXT,
    plazo               INTEGER,
    fecha_vencimiento   TEXT,
    vencimiento_manual  INTEGER DEFAULT 0,
    atendida            INTEGER DEFAULT 0,
    obs                 TEXT DEFAULT '',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
"""
_DDL_INDICE = (
    "CREATE INDEX IF NOT EXISTS idx_tabla_cartas_num_doc ON tabla_cartas(num_doc)"
)


def crear_tabla_cartas(conn: sqlite3.Connection | None = None) -> None:
    """DDL idempotente de `tabla_cartas`. Si recibe `conn`, no la cierra."""
    propia = conn is None
    if propia:
        from ..database import get_db_connection

        conn = get_db_connection()
    try:
        conn.execute(_DDL)
        conn.execute(_DDL_INDICE)
        if propia:
            conn.commit()
    finally:
        if propia:
            conn.close()


def parse_fecha(txt) -> date | None:
    """'DD/MM/YYYY' -> date. Devuelve None ante vacío o formato inválido."""
    s = str(txt or "").strip()
    if not s:
        return None
    try:
        return datetime.strptime(s, "%d/%m/%Y").date()
    except ValueError:
        return None


def fmt_fecha(d: date) -> str:
    return d.strftime("%d/%m/%Y")


def calcular_vencimiento(fecha_notificacion, plazo, feriados_set: set[str]) -> str:
    """Vencimiento = `plazo` días hábiles después de la notificación.

    Devuelve '' si falta la notificación o el plazo no es un entero positivo.
    """
    desde = parse_fecha(fecha_notificacion)
    if desde is None:
        return ""
    try:
        dias = int(plazo)
    except (TypeError, ValueError):
        return ""
    if dias <= 0:
        return ""

    from .funciones_autorizar import calcular_fecha_final_habiles

    return fmt_fecha(calcular_fecha_final_habiles(dias, feriados_set, desde=desde))


def estado_de(carta: dict, feriados_set: set[str], hoy: date | None = None) -> str:
    """Estado derivado de una carta. Ver la tabla del spec §5."""
    if int(carta.get("atendida") or 0) == 1:
        return "ATENDIDA"
    if parse_fecha(carta.get("fecha_notificacion")) is None:
        return "SIN_NOTIFICAR"
    vence = parse_fecha(carta.get("fecha_vencimiento"))
    if vence is None:
        return "VIGENTE"

    from .funciones_autorizar import calcular_fecha_final_habiles

    hoy = hoy or date.today()
    if vence < hoy:
        return "VENCIDA"
    proximo_habil = calcular_fecha_final_habiles(1, feriados_set, desde=hoy)
    if vence <= proximo_habil:
        return "POR_VENCER"
    return "VIGENTE"


_CAMPOS = (
    "numero", "anio", "tipo", "fecha_emision", "fecha_notificacion",
    "plazo", "fecha_vencimiento", "atendida", "obs",
)
_TABLAS_ESPEJO = ("tabla_asign", "tabla_asign_archivo")


def _feriados() -> set[str]:
    from ..database import obtener_feriados

    return {str(f).strip() for f in (obtener_feriados() or [])}


def _tabla_existe(conn: sqlite3.Connection, tabla: str) -> bool:
    cur = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (tabla,)
    )
    return cur.fetchone() is not None


def _columna_existe(conn: sqlite3.Connection, tabla: str, columna: str) -> bool:
    cols = {row[1] for row in conn.execute(f"PRAGMA table_info({tabla})")}
    return columna in cols


def sincronizar_espejo(num_doc: str, conn: sqlite3.Connection) -> str:
    """Reconstruye `tabla_asign(_archivo).carta` desde `tabla_cartas`.

    Excluye los borradores (numero vacío) y ordena por (anio, numero) de forma
    NUMÉRICA. Usa la conexión recibida: la mutación de `tabla_cartas` y la del
    espejo deben quedar en la misma transacción.
    """
    nd = str(num_doc or "").strip()
    filas = conn.execute(
        "SELECT numero, anio FROM tabla_cartas "
        "WHERE num_doc = ? AND TRIM(COALESCE(numero, '')) <> '' "
        "AND TRIM(COALESCE(anio, '')) <> ''",
        (nd,),
    ).fetchall()
    pares = sorted(
        (
            (str(f[1] or "").strip(), str(f[0] or "").strip())
            for f in filas
        ),
        key=lambda p: (p[0], p[1].zfill(7)),
    )
    espejo = ", ".join(f"{numero}-{anio}" for anio, numero in pares)

    for tabla in _TABLAS_ESPEJO:
        if not _tabla_existe(conn, tabla):
            continue
        if not _columna_existe(conn, tabla, "carta"):
            conn.execute(f"ALTER TABLE {tabla} ADD COLUMN carta TEXT")
        conn.execute(
            f"UPDATE {tabla} SET carta = ? WHERE num_doc = ?", (espejo, nd)
        )
    return espejo


_TEXTOS = (
    "num_doc", "numero", "anio", "tipo", "fecha_emision",
    "fecha_notificacion", "fecha_vencimiento", "obs",
)


def _fila_a_dict(fila: sqlite3.Row) -> dict:
    """Fila -> dict, con los TEXT en NULL normalizados a '' (`plazo` sigue None)."""
    datos = {k: fila[k] for k in fila.keys()}
    for k in _TEXTOS:
        if datos.get(k) is None:
            datos[k] = ""
    for k in ("vencimiento_manual", "atendida"):
        datos[k] = int(datos.get(k) or 0)
    return datos


def caso_existe(num_doc: str) -> bool:
    """True si el num_doc está en tabla_asign o en tabla_asign_archivo."""
    from ..database import get_db_connection

    nd = str(num_doc or "").strip()
    if not nd:
        return False
    conn = get_db_connection()
    try:
        for tabla in _TABLAS_ESPEJO:
            if not _tabla_existe(conn, tabla):
                continue
            fila = conn.execute(
                f"SELECT 1 FROM {tabla} WHERE num_doc = ? LIMIT 1", (nd,)
            ).fetchone()
            if fila:
                return True
        return False
    finally:
        conn.close()


def _leer_carta(conn: sqlite3.Connection, id_carta: int) -> dict | None:
    conn.row_factory = sqlite3.Row
    fila = conn.execute(
        "SELECT * FROM tabla_cartas WHERE id = ?", (int(id_carta),)
    ).fetchone()
    return _fila_a_dict(fila) if fila else None


def _con_estado(carta: dict, feriados_set: set[str]) -> dict:
    carta = dict(carta)
    carta["estado"] = estado_de(carta, feriados_set)
    return carta


def listar_cartas(num_doc: str) -> list[dict]:
    """Cartas del caso, más reciente primero, con `estado` derivado."""
    from ..database import get_db_connection

    feriados_set = _feriados()
    conn = get_db_connection()
    try:
        crear_tabla_cartas(conn)
        conn.row_factory = sqlite3.Row
        filas = conn.execute(
            "SELECT * FROM tabla_cartas WHERE num_doc = ?",
            (str(num_doc or "").strip(),),
        ).fetchall()
    finally:
        conn.close()

    cartas = [_con_estado(_fila_a_dict(f), feriados_set) for f in filas]
    cartas.sort(
        key=lambda c: (
            parse_fecha(c.get("fecha_emision")) or date.min,
            c.get("id") or 0,
        ),
        reverse=True,
    )
    return cartas


def _normalizar(campos: dict) -> dict:
    """Deja solo los campos aceptados, con tipos saneados."""
    datos = {k: v for k, v in campos.items() if k in _CAMPOS}
    for k in ("numero", "anio", "tipo", "fecha_emision", "fecha_notificacion",
              "fecha_vencimiento", "obs"):
        if k in datos:
            datos[k] = str(datos[k] or "").strip()
    if "plazo" in datos:
        try:
            datos["plazo"] = int(datos["plazo"])
        except (TypeError, ValueError):
            datos["plazo"] = None
    if "atendida" in datos:
        datos["atendida"] = 1 if datos["atendida"] else 0
    return datos


def _completar_anio(datos: dict) -> None:
    """Si `anio` queda vacío, lo completa con el año de `fecha_emision`
    (o el año actual si tampoco hay emisión). Muta `datos` in place.

    Evita que una carta sin año llegue a `sincronizar_espejo`, que la
    excluiría igual que a un borrador sin `numero` (ver `_CAMPOS`/espejo).
    """
    if not datos.get("anio"):
        emision = parse_fecha(datos.get("fecha_emision"))
        datos["anio"] = str((emision or date.today()).year)


def crear_carta(num_doc: str, **campos) -> dict:
    """Inserta una carta, calcula su vencimiento y sincroniza el espejo."""
    from ..database import get_db_connection

    nd = str(num_doc or "").strip()
    datos = _normalizar(campos)
    _completar_anio(datos)

    feriados_set = _feriados()
    manual = bool(datos.get("fecha_vencimiento"))
    if not manual:
        datos["fecha_vencimiento"] = calcular_vencimiento(
            datos.get("fecha_notificacion"), datos.get("plazo"), feriados_set
        )
    datos["vencimiento_manual"] = 1 if manual else 0

    columnas = ["num_doc"] + list(datos.keys())
    marcas = ", ".join("?" for _ in columnas)
    valores = [nd] + list(datos.values())

    conn = get_db_connection()
    try:
        crear_tabla_cartas(conn)
        cur = conn.execute(
            f"INSERT INTO tabla_cartas ({', '.join(columnas)}) VALUES ({marcas})",
            valores,
        )
        id_carta = cur.lastrowid
        sincronizar_espejo(nd, conn)
        conn.commit()
        return _con_estado(_leer_carta(conn, id_carta), feriados_set)
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def actualizar_carta(id_carta: int, **campos) -> dict | None:
    """Actualiza una carta; recalcula el vencimiento salvo que sea manual.

    Pasar `fecha_vencimiento` con valor la marca como manual; pasarla vacía
    devuelve la carta al cálculo automático. Devuelve None si el id no existe.
    """
    from ..database import get_db_connection

    datos = _normalizar(campos)
    feriados_set = _feriados()

    conn = get_db_connection()
    try:
        crear_tabla_cartas(conn)
        actual = _leer_carta(conn, id_carta)
        if actual is None:
            return None

        if "fecha_vencimiento" in datos:
            datos["vencimiento_manual"] = 1 if datos["fecha_vencimiento"] else 0

        fusion = {**actual, **datos}
        if not fusion.get("anio"):
            # p.ej. el usuario borró el Año a mano: sin esto, `sincronizar_espejo`
            # dejaría un elemento "numero-" malformado en el espejo.
            _completar_anio(fusion)
            datos["anio"] = fusion["anio"]

        if not int(fusion.get("vencimiento_manual") or 0):
            datos["fecha_vencimiento"] = calcular_vencimiento(
                fusion.get("fecha_notificacion"), fusion.get("plazo"), feriados_set
            )
            datos["vencimiento_manual"] = 0

        if datos:
            asignaciones = ", ".join(f"{k} = ?" for k in datos)
            conn.execute(
                f"UPDATE tabla_cartas SET {asignaciones}, "
                "updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                list(datos.values()) + [int(id_carta)],
            )
        sincronizar_espejo(str(actual["num_doc"]), conn)
        conn.commit()
        return _con_estado(_leer_carta(conn, id_carta), feriados_set)
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def backfill_desde_espejo() -> int:
    """Crea en `tabla_cartas` las cartas presentes en el espejo y ausentes aquí.

    Idempotente: no duplica ni pisa las que ya existen (sus fechas y plazo se
    conservan). Se ignora todo elemento que no tenga exactamente un guion, o
    que tenga vacío alguno de los dos lados. Este criterio es deliberadamente
    MÁS ESTRICTO que `_parsear_cartas` (`MACRO/flujos/flujo_descargas.py:349`),
    que sí acepta un lado vacío (p.ej. "-2026" o "55-"): una entrada con
    `numero` vacío entraría aquí como borrador y aparecería como una fila
    "s/n" en el panel de cartas, por cada dato basura del espejo.
    Devuelve cuántas filas creó.
    """
    from ..database import get_db_connection

    creadas = 0
    conn = get_db_connection()
    try:
        crear_tabla_cartas(conn)
        for tabla in _TABLAS_ESPEJO:
            if not _tabla_existe(conn, tabla) or not _columna_existe(conn, tabla, "carta"):
                continue
            filas = conn.execute(f"SELECT num_doc, carta FROM {tabla}").fetchall()
            for num_doc, texto in filas:
                nd = str(num_doc or "").strip()
                if not nd or not str(texto or "").strip():
                    continue
                existentes = {
                    (str(r[0] or "").strip(), str(r[1] or "").strip())
                    for r in conn.execute(
                        "SELECT numero, anio FROM tabla_cartas WHERE num_doc = ?", (nd,)
                    )
                }
                for item in str(texto).split(","):
                    item = item.strip()
                    if item.count("-") != 1:
                        continue
                    numero, anio = (p.strip() for p in item.split("-"))
                    if not numero or not anio or (numero, anio) in existentes:
                        continue
                    conn.execute(
                        "INSERT INTO tabla_cartas (num_doc, numero, anio) VALUES (?, ?, ?)",
                        (nd, numero, anio),
                    )
                    existentes.add((numero, anio))
                    creadas += 1
        conn.commit()
        return creadas
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def resumen_por_caso() -> dict[str, dict]:
    """Por num_doc: vencimiento y estado de la carta vigente, y cuántas hay.

    La carta "vigente" es la más reciente por `fecha_emision`, con `id` como
    desempate (los borradores no tienen número con el cual ordenar).
    """
    from ..database import get_db_connection

    feriados_set = _feriados()
    conn = get_db_connection()
    try:
        crear_tabla_cartas(conn)
        conn.row_factory = sqlite3.Row
        filas = [_fila_a_dict(f) for f in conn.execute("SELECT * FROM tabla_cartas")]
    finally:
        conn.close()

    por_caso: dict[str, list[dict]] = {}
    for fila in filas:
        por_caso.setdefault(str(fila.get("num_doc") or "").strip(), []).append(fila)

    resumen: dict[str, dict] = {}
    for num_doc, cartas in por_caso.items():
        if not num_doc:
            continue
        vigente = max(
            cartas,
            key=lambda c: (
                parse_fecha(c.get("fecha_emision")) or date.min,
                c.get("id") or 0,
            ),
        )
        numero = str(vigente.get("numero") or "").strip()
        anio = str(vigente.get("anio") or "").strip()
        resumen[num_doc] = {
            "carta_vigente": f"{numero}-{anio}" if numero else "",
            "carta_vencimiento": str(vigente.get("fecha_vencimiento") or ""),
            "carta_estado": estado_de(vigente, feriados_set),
            "carta_n": len(cartas),
        }
    return resumen


def agregar_columnas_cartas(df):
    """Añade `carta_vigente`, `carta_vencimiento`, `carta_estado` y `carta_n`.

    Los casos sin cartas quedan con cadenas vacías y `carta_n = 0`. Nunca lanza:
    ante cualquier fallo devuelve el DataFrame tal como llegó.
    """
    if df is None or getattr(df, "empty", True):
        return df
    try:
        resumen = resumen_por_caso()
        claves = df["num_doc"].astype(str).str.strip()
        for columna, vacio in (
            ("carta_vigente", ""),
            ("carta_vencimiento", ""),
            ("carta_estado", ""),
            ("carta_n", 0),
        ):
            df[columna] = claves.map(
                lambda nd, c=columna, v=vacio: resumen.get(nd, {}).get(c, v)
            )
    except Exception as e:  # noqa: BLE001
        print(f"Error agregando columnas de cartas: {e}")
    return df


def eliminar_carta(id_carta: int) -> bool:
    """Borra una carta y sincroniza el espejo. False si el id no existía."""
    from ..database import get_db_connection

    conn = get_db_connection()
    try:
        crear_tabla_cartas(conn)
        actual = _leer_carta(conn, id_carta)
        if actual is None:
            return False
        conn.execute("DELETE FROM tabla_cartas WHERE id = ?", (int(id_carta),))
        sincronizar_espejo(str(actual["num_doc"]), conn)
        conn.commit()
        return True
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

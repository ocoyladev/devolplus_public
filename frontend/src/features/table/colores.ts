import type { CellClassParams } from "ag-grid-community";

// Relleno de color de la celda RESULTADO según su estado (igual que en Flet).
export const COLOR_RESULTADO: Record<string, string> = {
  "AUTORIZADO TOTAL": "#C8E6C9",
  "AUTORIZADO PARCIAL": "#C8E6C9",
  DENEGADO: "#C8E6C9",
  IMPROCEDENTE: "#C8E6C9",
  DESISTIDO: "#C8E6C9",
  ITOP: "#FFE0B2",
  MIGRACIONES: "#FFE0B2",
  "CARTA ENVIADA": "#FFE0B2",
};

const VERDE = "#C8E6C9";
const NARANJA_RES = "#FFE0B2";
const GRIS = "#B8B8B8";
const ROJO = "#FF6142";
const NARANJA_VCTO = "#FCA797";

export function fechaANumero(v: unknown): number {
  const m = String(v ?? "")
    .trim()
    .match(/^(\d{2})\/(\d{2})\/(\d{4})$/);
  if (!m) return -Infinity; // vacíos / no-fecha al inicio en orden ascendente
  return new Date(Number(m[3]), Number(m[2]) - 1, Number(m[1])).getTime();
}

/** Color de fondo de RESULTADO según su valor, o null si no aplica. */
export function colorResultado(value: unknown): string | null {
  return COLOR_RESULTADO[String(value ?? "").trim().toUpperCase()] ?? null;
}

/** Color de fondo de VCTO. IND. según la fecha vs. hoy (pasada/hoy/mañana). */
export function colorVcto(value: unknown): string | null {
  const t = fechaANumero(value);
  if (!Number.isFinite(t)) return null;
  const hoy = new Date();
  hoy.setHours(0, 0, 0, 0);
  const manana = new Date(hoy);
  manana.setDate(hoy.getDate() + 1);
  if (t < hoy.getTime()) return GRIS;
  if (t === hoy.getTime()) return ROJO;
  if (t === manana.getTime()) return NARANJA_VCTO;
  return null;
}

export function estiloResultado(params: CellClassParams): { backgroundColor: string } | null {
  const c = colorResultado(params.value);
  return c ? { backgroundColor: c } : null;
}

export function estiloVcto(params: CellClassParams): { backgroundColor: string } | null {
  const c = colorVcto(params.value);
  return c ? { backgroundColor: c } : null;
}

// --- Filtro por color -------------------------------------------------------
export interface ColorOpcion {
  clave: string;
  etiqueta: string;
  color: string | null;
}

const OPCIONES_RESULTADO: ColorOpcion[] = [
  { clave: "verde", etiqueta: "Resuelto (verde)", color: VERDE },
  { clave: "naranja", etiqueta: "En trámite (naranja)", color: NARANJA_RES },
  { clave: "sin", etiqueta: "Sin color", color: null },
];

const OPCIONES_VCTO: ColorOpcion[] = [
  { clave: "gris", etiqueta: "Vencido (gris)", color: GRIS },
  { clave: "rojo", etiqueta: "Vence hoy (rojo)", color: ROJO },
  { clave: "naranja", etiqueta: "Vence mañana (naranja)", color: NARANJA_VCTO },
  { clave: "sin", etiqueta: "Sin color", color: null },
];

/** True si la columna usa colores y admite el filtro por color. */
export function esColumnaColor(field: string): boolean {
  return field === "resultado" || field === "CalcVctoInd" || field === "VctoInd";
}

export function opcionesColorDe(field: string): ColorOpcion[] {
  return field === "resultado" ? OPCIONES_RESULTADO : OPCIONES_VCTO;
}

/** Clave de color de una celda, para comparar contra la selección del filtro. */
export function colorClaveDe(field: string, value: unknown): string {
  if (field === "resultado") {
    const c = colorResultado(value);
    if (c === VERDE) return "verde";
    if (c === NARANJA_RES) return "naranja";
    return "sin";
  }
  const c = colorVcto(value);
  if (c === GRIS) return "gris";
  if (c === ROJO) return "rojo";
  if (c === NARANJA_VCTO) return "naranja";
  return "sin";
}

// --- Columna CARTA ----------------------------------------------------------

const COLOR_CARTA: Record<string, string> = {
  VENCIDA: ROJO,
  POR_VENCER: NARANJA_VCTO,
  ATENDIDA: VERDE,
};

/** Color de fondo de la celda CARTA según el estado de su carta vigente. */
export function colorCarta(estado: unknown): string | null {
  return COLOR_CARTA[String(estado ?? "").trim().toUpperCase()] ?? null;
}

export function estiloCarta(params: CellClassParams): { backgroundColor: string } | null {
  const estado = (params.data as Record<string, unknown> | undefined)?.carta_estado;
  const c = colorCarta(estado);
  return c ? { backgroundColor: c } : null;
}

export const OPCIONES_CARTA: ColorOpcion[] = [
  { clave: "VENCIDA", etiqueta: "Vencida", color: ROJO },
  { clave: "POR_VENCER", etiqueta: "Por vencer", color: NARANJA_VCTO },
  { clave: "ATENDIDA", etiqueta: "Atendida", color: VERDE },
  { clave: "VIGENTE", etiqueta: "Vigente", color: null },
  { clave: "SIN_NOTIFICAR", etiqueta: "Sin notificar", color: null },
  { clave: "SIN", etiqueta: "Sin cartas", color: null },
];

/**
 * Texto de la celda CARTA: la carta vigente y, si hay más de una, su cantidad.
 *
 * Recibe `carta_vigente` (no la cadena del espejo `carta`, que va de la más
 * ANTIGUA a la más reciente y por tanto empieza por la equivocada). Un borrador
 * sin numerar se muestra como "s/n".
 */
export function textoCeldaCarta(vigente: unknown, n: unknown): string {
  const texto = String(vigente ?? "").trim();
  const cantidad = Number(n ?? 0) || 0;
  if (cantidad === 0) return "";
  if (cantidad === 1) return texto || "s/n";
  return `${texto || "s/n"} (${cantidad})`;
}

/**
 * Texto de la celda CARTA con reserva: si `carta_vigente` está AUSENTE (falló
 * silenciosamente `agregar_columnas_cartas` en el servidor y no llegó a
 * fusionar las columnas derivadas), usa la cadena cruda del espejo `carta` en
 * vez de dejar la celda en blanco. Una celda vacía se lee como pérdida de
 * datos; el espejo crudo, aunque sin el formato bonito, sigue siendo veraz.
 *
 * `carta_vigente === ""` (caso sin cartas, columnas sí presentes) no cae en
 * la reserva: ahí "vacío" es el dato correcto.
 */
export function textoCeldaCartaConReserva(
  vigente: unknown,
  n: unknown,
  espejoCrudo: unknown,
): string {
  if (vigente === undefined) return String(espejoCrudo ?? "").trim();
  return textoCeldaCarta(vigente, n);
}

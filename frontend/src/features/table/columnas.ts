import type { ColDef } from "ag-grid-community";

import { estiloCarta, estiloResultado, estiloVcto, fechaANumero } from "./colores";
import { CartaFilter } from "./CartaFilter";
import { ColorFilter } from "./ColorFilter";

// Etiquetas en español para los campos conocidos (modo "ver toda la data").
export const LABELS: Record<string, string> = {
  num_doc: "N° DOC",
  num_ruc: "N° RUC",
  ruc: "N° RUC",
  nombre: "Nombre",
  ddp_nombre: "Nombre",
  cod_sol: "COD. SOL.",
  cod_tip_sol: "COD. SOL.",
  cod_for: "COD. FOR.",
  per_doc: "Periodo",
  periodo: "Periodo",
  of_devolucion: "OF",
  forma_dev: "Forma Dev.",
  ind_for_dev: "Forma Dev.",
  resultado: "Resultado",
  num_ri: "RI",
  fec_ri: "Fecha RI",
  carta: "Carta",
  obs_devol: "Observaciones",
  exp_echasqui: "Exp. ECHASQUI",
  num_dev: "N° Dev.",
  DESCARGAS: "Descargas",
};

// Opciones de los dropdowns (idénticas a las de la GUI Flet).
export const RESULTADO_OPCIONES = [
  "AUTORIZADO TOTAL",
  "AUTORIZADO PARCIAL",
  "DENEGADO",
  "IMPROCEDENTE",
  "DESISTIDO",
  "CARTA ENVIADA",
  "ITOP",
  "MIGRACIONES",
];
export const FORMA_DEV_OPCIONES = ["Abono en cuenta", "OPF", "Cheque"];

// Campo de la grilla -> {campo de la API /campos, valores si es dropdown}.
interface EditableConfig {
  campo: string;
  valores?: string[];
}
export const EDITABLES: Record<string, EditableConfig> = {
  resultado: { campo: "resultado", valores: RESULTADO_OPCIONES },
  ind_for_dev: { campo: "forma_dev", valores: FORMA_DEV_OPCIONES },
  forma_dev: { campo: "forma_dev", valores: FORMA_DEV_OPCIONES },
  num_ri: { campo: "ri" },
  ri: { campo: "ri" },
  obs_devol: { campo: "obs" },
};

/** Devuelve el `campo` de la API para un campo de la grilla, o null si no es editable. */
export function campoDeField(field: string): string | null {
  return EDITABLES[field]?.campo ?? null;
}

// Anchos por campo (similares a la tabla Flet; Observaciones al doble).
const ANCHOS: Record<string, number> = {
  DESCARGAS: 90,
  of_devolucion: 80,
  num_doc: 108,
  num_ruc: 104,
  ruc: 104,
  nombre: 150,
  ddp_nombre: 150,
  per_doc: 78,
  periodo: 78,
  cod_tip_sol: 70,
  cod_sol: 70,
  cod_for: 70,
  ind_for_dev: 110,
  ind_dev: 110,
  forma_dev: 110,
  CalcVctoInd: 96,
  VctoInd: 96,
  fec_Fallecido: 80,
  carta: 100,
  num_ri: 120,
  ri: 120,
  fec_ri: 96,
  resultado: 120,
  NIDI: 60,
  num_dev: 110,
  obs_devol: 450, // doble del ancho de Flet (300)
  exp_echasqui: 450, // igual que Resultado
};

// Campos cuyo valor es una fecha DD/MM/YYYY (orden cronológico, no textual).
const CAMPOS_FECHA = new Set(["CalcVctoInd", "VctoInd", "fec_Fallecido", "fec_ri"]);

const comparadorFecha = (a: unknown, b: unknown): number =>
  fechaANumero(a) - fechaANumero(b);

const DEFAULT_SPEC: { header: string; fields: string[] }[] = [
  { header: "DESCARGAS", fields: ["DESCARGAS"] },
  { header: "OF.", fields: ["of_devolucion"] },
  { header: "N° DOC.", fields: ["num_doc"] },
  { header: "N° RUC", fields: ["num_ruc", "ruc"] },
  { header: "Nombre", fields: ["nombre", "ddp_nombre"] },
  { header: "Periodo", fields: ["per_doc", "periodo"] },
  { header: "COD. SOL.", fields: ["cod_tip_sol", "cod_sol"] },
  { header: "COD. FOR.", fields: ["cod_for"] },
  { header: "Forma Dev.", fields: ["ind_for_dev", "ind_dev", "forma_dev"] },
  { header: "VCTO. IND.", fields: ["CalcVctoInd", "VctoInd"] },
  { header: "FALL.", fields: ["fec_Fallecido"] },
  { header: "Carta", fields: ["carta"] },
  { header: "RI", fields: ["num_ri", "ri"] },
  { header: "FECHA RI", fields: ["fec_ri"] },
  { header: "Resultado", fields: ["resultado"] },
  { header: "NIDI", fields: ["NIDI"] },
  { header: "Exp. Electrónico", fields: ["num_dev"] },
  { header: "Observaciones", fields: ["obs_devol"] },
  { header: "Exp. ECHASQUI", fields: ["exp_echasqui"] },
];

export type ModoColumnas = "default" | "todas";

function colDefDe(field: string, headerOverride?: string, editable = true): ColDef {
  const col: ColDef = {
    field,
    headerName: headerOverride ?? LABELS[field] ?? field,
    sortable: true,
    resizable: true,
    filter: "agTextColumnFilter",
  };
  if (ANCHOS[field]) col.width = ANCHOS[field];
  if (CAMPOS_FECHA.has(field)) col.comparator = comparadorFecha;
  if (field === "resultado") {
    col.cellStyle = estiloResultado;
    // Filtrar por color (verde/naranja/sin color) en vez de por texto.
    col.filter = ColorFilter;
  }
  // Orden por defecto + color de fondo por fecha en VCTO. IND.
  if (field === "CalcVctoInd" || field === "VctoInd") {
    col.sort = "asc";
    col.sortIndex = 0;
    col.cellStyle = estiloVcto;
    // Filtrar por color de vencimiento (vencido/hoy/mañana/sin color).
    col.filter = ColorFilter;
  }
  if (field === "carta") {
    col.cellStyle = estiloCarta;
    col.filter = CartaFilter;
    col.width = 130;
  }

  // En la vista de archivo (editable=false) las celdas no son editables.
  const cfg = editable ? EDITABLES[field] : undefined;
  if (cfg) {
    col.editable = true;
    if (cfg.valores) {
      col.cellEditor = "agSelectCellEditor";
      col.cellEditorParams = { values: cfg.valores };
    }
  }
  return col;
}

// Columnas derivadas de las cartas (Task 4): no se muestran como columnas
// sueltas en "ver toda la data" — su información ya está en la celda Carta.
const DERIVADAS_CARTA = new Set([
  "carta_vigente",
  "carta_estado",
  "carta_vencimiento",
  "carta_n",
]);

export function construirColumnas(
  columns: string[],
  modo: ModoColumnas = "todas",
  editable = true,
): ColDef[] {
  const visibles = columns.filter((f) => !DERIVADAS_CARTA.has(f));
  if (modo === "todas") {
    return visibles.map((f) => colDefDe(f, undefined, editable));
  }
  const presentes = new Set(visibles);
  const out: ColDef[] = [];
  for (const spec of DEFAULT_SPEC) {
    const field = spec.fields.find((f) => presentes.has(f));
    if (field) out.push(colDefDe(field, spec.header, editable));
  }
  return out;
}

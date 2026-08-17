type Row = Record<string, unknown>;

export interface ConflictoAutorizar {
  num_doc: string;
  per_doc: string;
  nombre: string;
  c89: number;
}

export interface DecisionAutorizar {
  accion: "confirmar" | "aplicar_c89" | "aplicar_valor";
  valor?: number | null;
}

export interface ConflictoC64 {
  num_doc: string;
  per_doc: string;
  nombre: string;
  g58: number;
}

export interface DecisionC64 {
  accion: "aplicar_g58" | "aplicar_valor";
  valor?: number | null;
}

export interface RepositorioEstado {
  denom: string;
  clasificacion: "OMITIR" | "VIA_ESPECIAL" | "PDF";
  estado: "auto" | "subido" | "pendiente_subir" | "pdf_ok" | "pdf_faltante";
  subible: boolean;
}

export interface CasoRepositorio {
  num_doc: string;
  num_dev: string;
  num_ruc: string;
  nombre: string;
  tipo_exp: "ELECTRONICO" | "FISICO" | "VIRTUAL" | "";
  repositorios: RepositorioEstado[];
  sin_repositorio: boolean;
  error: string;
}

export interface DetalleArchivar {
  num_doc: string;
  exp: string;
  resultado: "archivado" | "concluido" | "pendiente" | "error";
  mensaje: string;
}

export interface ItemRepositorioPendiente {
  num_doc: string;
  num_dev: string;
  num_ruc: string;
  denom: string;
}

export interface AlertaValidacion {
  codigo: string;
  severidad: "error" | "advertencia";
  mensaje: string;
  accion: string;
  /** Insumo de la acción cuando no basta el num_doc (p. ej. el denom del repositorio). */
  item?: string;
}

export interface PatronIndispensable {
  patron: string;
  encontrado: boolean;
}

export interface RepositorioItem {
  denom: string;
  clasificacion: string;
  estado: string;
  subible: boolean;
}

/** Visibilidad de un PDF cargado al expediente electrónico. */
export type EstadoVisibilidad = "si" | "no" | "desconocido";

export interface CasoValidacion {
  num_doc: string;
  num_dev: string;
  num_ruc: string;
  nombre: string;
  of_devolucion: string;
  tipo_exp: "ELECTRONICO" | "FISICO" | "VIRTUAL" | "";
  cod_tip_sol: string;
  /** Rectificatoria: hereda el armado de la solicitud de origen (origen_tipo12). */
  es_tipo12: boolean;
  origen_tipo12: string;
  is_of_multiple: boolean;
  carpeta_existe: boolean;
  paso_papeles_trabajo: boolean;
  insumo_final: { completo: boolean; faltantes: string[]; puede_foliar: boolean };
  exp_repositorio: { registrado: boolean; valor: string; autoregistrado: boolean };
  repositorios: RepositorioItem[];
  carga_1649: {
    aplica: boolean;
    local: { reportes: boolean; cedula: boolean };
    remoto: string;
    remoto_reportes: boolean;
    remoto_cedula: boolean;
    /** Visibilidad al contribuyente; ambos deben ser "no" (Uso Interno). */
    visible_reportes: EstadoVisibilidad;
    visible_cedula: EstadoVisibilidad;
  };
  indispensables: {
    raiz: PatronIndispensable[];
    subcarpetas: Record<string, PatronIndispensable[]>;
  };
  alertas: AlertaValidacion[];
  nivel: "ok" | "advertencia" | "error";
  error: string;
}

export interface AccionSubsanar {
  num_doc: string;
  accion: string;
}

/** Estado de un caso en la verificación previa de las descargas SISTEMA_LEGACY. */
export interface SistemaLegacyPreflightCaso {
  of: string;
  ruc: string;
  carpeta: string;
  estado: "pendiente" | "omitido" | "sin_planeamiento" | "sin_antecedentes" | "error";
  /** Nombres de los PDFs ya presentes en la carpeta del caso. */
  existentes: string[];
  /** Etiquetas de lo que sí se descargaría. */
  faltantes: string[];
  detalle: string;
}

export interface SistemaLegacyPreflight {
  tipo: "ref" | "antec";
  total: number;
  pendientes: number;
  casos: SistemaLegacyPreflightCaso[];
}

interface JobResponse {
  job_id: string;
}

async function postJob(url: string, body: unknown): Promise<string> {
  const resp = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!resp.ok) {
    throw new Error(`Error ${resp.status} en ${url}`);
  }
  const data = (await resp.json()) as JobResponse;
  return data.job_id;
}

async function postJson<T>(url: string, body: unknown): Promise<T> {
  const resp = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!resp.ok) {
    throw new Error(`Error ${resp.status} en ${url}`);
  }
  return (await resp.json()) as T;
}

async function postVoid(url: string, body: unknown): Promise<void> {
  const resp = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!resp.ok) {
    const detalle = await resp.text();
    throw new Error(`Error ${resp.status}: ${detalle || url}`);
  }
}

export const procesos = {
  archivar: (numDocs: string[]) => postJob("/api/procesos/archivar", { num_docs: numDocs }),
  recuperar: (numDocs: string[]) => postJob("/api/procesos/recuperar", { num_docs: numDocs }),
  papeles_trabajo: (numDocs: string[]) => postJob("/api/procesos/papeles-trabajo", { num_docs: numDocs }),
  cargaExpedientes: (numDocs: string[], firmaAuto = false) =>
    postJob("/api/procesos/carga-expedientes", {
      num_docs: numDocs,
      ejecutar_firma_auto: firmaAuto,
    }),
  autorizar: (
    lineas: string[],
    decisiones: Record<string, DecisionAutorizar> = {},
    decisionesC64: Record<string, DecisionC64> = {},
  ) =>
    postJob("/api/procesos/autorizar", {
      lineas,
      decisiones,
      decisiones_c64: decisionesC64,
    }),
  autorizarPreCheck: async (
    lineas: string[],
  ): Promise<{ conflictos: ConflictoAutorizar[]; conflictosC64: ConflictoC64[] }> => {
    const { conflictos, conflictos_c64 } = await postJson<{
      conflictos: ConflictoAutorizar[];
      conflictos_c64: ConflictoC64[];
    }>("/api/procesos/autorizar/pre-check", { lineas });
    return { conflictos, conflictosC64: conflictos_c64 ?? [] };
  },
  verificarRepositorio: async (numDocs: string[]): Promise<CasoRepositorio[]> => {
    const { casos } = await postJson<{ casos: CasoRepositorio[] }>(
      "/api/procesos/verificar-repositorio",
      { num_docs: numDocs },
    );
    return casos;
  },
  subirRepositorioPendientes: (items: ItemRepositorioPendiente[]) =>
    postJob("/api/procesos/verificar-repositorio/subir", { items }),
  archivarRepositorio: (numDocs: string[]) =>
    postJob("/api/procesos/archivar-repositorio", { num_docs: numDocs }),
  validarArchivo: async (numDocs: string[]): Promise<CasoValidacion[]> => {
    const { casos } = await postJson<{ casos: CasoValidacion[] }>(
      "/api/procesos/validar-archivo",
      { num_docs: numDocs },
    );
    return casos;
  },
  validarArchivoSubsanar: (acciones: AccionSubsanar[]) =>
    postJob("/api/procesos/validar-archivo/subsanar", { acciones }),
  validarArchivoExportar: (casos: CasoValidacion[]) =>
    postVoid("/api/procesos/validar-archivo/exportar", { casos }),
  validarArchivoAbrirCarpeta: (numDoc: string) =>
    postVoid("/api/procesos/validar-archivo/abrir-carpeta", { num_doc: numDoc }),
};

export const descargas = {
  ri: (row: Row, archivo = false) => postJob("/api/descargas/ri", { row, archivo }),
  cartas: (row: Row, archivo = false) => postJob("/api/descargas/cartas", { row, archivo }),
  riMasivo: (filas: Row[], archivo = false) =>
    postJob("/api/descargas/ri-masivo", { filas, archivo }),
  cartasMasivo: (filas: Row[], archivo = false) =>
    postJob("/api/descargas/cartas-masivo", { filas, archivo }),
  repositorio: (row: Row, expedientes: string[]) =>
    postJob("/api/descargas/repositorio", { row, expedientes }),
  expElectronico: (row: Row) => postJob("/api/descargas/exp-electronico", { row }),
  tresUit: (row: Row, numFormulario: string | null) =>
    postJob("/api/descargas/3uit", { row, num_formulario: numFormulario }),
  porEjercicios: (row: Row, count: number) =>
    postJob("/api/descargas/ejercicios", { row, count }),
  planeamiento: (row: Row, ruc: string) =>
    postJob("/api/descargas/planeamiento", { row, ruc }),
  numeracion: (filas: Row[]) => postJob("/api/descargas/numeracion", { filas }),
  reintentar: () => postJob("/api/descargas/reintentar", {}),
  sistemaLegacyRef: (filas: Row[]) => postJob("/api/descargas/sistema-legacy-ref", { filas }),
  sistemaLegacyAntecedentes: (filas: Row[]) =>
    postJob("/api/descargas/sistema-legacy-antecedentes", { filas }),
  /** Qué casos ya tienen sus PDFs y cuáles requieren correr la automatización. */
  sistemaLegacyPreflight: (tipo: "ref" | "antec", filas: Row[]) =>
    postJson<SistemaLegacyPreflight>("/api/descargas/sistema-legacy-preflight", { tipo, filas }),
};

export const abrir = {
  carpeta: (row: Row, archivo = false) => postVoid("/api/abrir/carpeta", { row, archivo }),
  macro: (row: Row, archivo = false) => postVoid("/api/abrir/macro", { row, archivo }),
};

export const mesa_ayuda = {
  descarga: (
    tipo: "4ta" | "5ta" | "601" | "601_completo",
    row: Row,
    extra?: {
      ruc_empleador?: string;
      nombre_empleador?: string;
      doc_override?: string;
    },
  ) => postJob("/api/mesa-ayuda/descarga", { tipo, row, ...extra }),
  preview: (
    tipo: "4ta" | "5ta" | "601" | "601_completo",
    row: Row,
    extra?: { ruc_empleador?: string; nombre_empleador?: string; doc_override?: string },
  ) =>
    postJson<{
      tipo: string;
      of: string;
      ruc: string;
      nombre: string;
      periodo_ini: number;
      periodo_fin: number;
      contenido_txt: string;
      titulo: string;
    }>("/api/mesa-ayuda/preview", { tipo, row, ...extra }),
  modificar: (row: Row, modalidad: string, cci: string | null) =>
    postJob("/api/mesa-ayuda/modificar", { row, modalidad, cci }),
  empleadores601: (row: Row) =>
    postJson<{ empleadores: { ruc: string; nombre: string }[] }>(
      "/api/mesa-ayuda/empleadores-601",
      { row },
    ),
};

export const sync = {
  macros: () => postJob("/api/sync/macros", {}),
  remota: () => postJob("/api/sync/remota", {}),
};

export const datos = {
  cargar: (numDocs: string[]) => postJob("/api/datos/cargar", { num_docs: numDocs }),
  cargarArchivo: async (tipo: string, file: File): Promise<string> => {
    const fd = new FormData();
    fd.append("tipo", tipo);
    fd.append("file", file);
    const resp = await fetch("/api/datos/cargar-archivo", { method: "POST", body: fd });
    if (!resp.ok) {
      throw new Error(`Error ${resp.status} al subir el archivo`);
    }
    return ((await resp.json()) as { job_id: string }).job_id;
  },
  planeamientoEstado: async (): Promise<boolean> => {
    const resp = await fetch("/api/datos/planeamiento-estado");
    if (!resp.ok) return true; // ante un fallo, no bloquear la UI
    return ((await resp.json()) as { permitido: boolean }).permitido;
  },
};

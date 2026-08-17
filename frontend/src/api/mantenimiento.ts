export interface DescargaCola {
  id: number;
  num_doc: string | null;
  ruc: string | null;
  tipo_servicio: string | null;
  tipo_descarga: string | null;
  parametro: string | null;
  estado: string | null;
  reintentos: number | null;
  error_log: string | null;
}

async function pedir<T>(url: string, init?: RequestInit): Promise<T> {
  const resp = await fetch(url, init);
  if (!resp.ok) {
    throw new Error(`Error ${resp.status} en ${url}`);
  }
  return (await resp.json()) as T;
}

function postIds(ids: number[]): RequestInit {
  return {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ ids }),
  };
}

export const listarDescargas = () =>
  pedir<{ descargas: DescargaCola[] }>("/api/mantenimiento/descargas");

export const eliminarDescargas = (ids: number[]) =>
  pedir<{ eliminadas: number }>(
    "/api/mantenimiento/descargas/eliminar",
    postIds(ids),
  );

export const ejecutarDescargas = (ids: number[]) =>
  pedir<{ job_id: string }>(
    "/api/mantenimiento/descargas/ejecutar",
    postIds(ids),
  );

export const borrarBd = () =>
  pedir<{ ok: boolean }>("/api/mantenimiento/borrar-bd", { method: "POST" });

export const borrarDescargas = () =>
  pedir<{ ok: boolean }>("/api/mantenimiento/borrar-descargas", { method: "POST" });

export interface BorrarCasoResultado {
  eliminadas: Record<string, number>;
  carpeta_borrada: boolean;
  carpeta: string;
}

export const borrarCaso = (numDoc: string, borrarCarpeta: boolean) =>
  pedir<BorrarCasoResultado>("/api/mantenimiento/borrar-caso", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ num_doc: numDoc, borrar_carpeta: borrarCarpeta }),
  });

export interface PendienteArchivoEchasqui {
  id: number;
  num_doc: string | null;
  ruc: string | null;
  num_ri: string | null;
  aduana: string | null;
  urd: string | null;
  anio: string | null;
  nroexpedi: string | null;
  denom: string | null;
  estado: string | null;
  mensaje: string | null;
  fecha_registro: string | null;
}

export const listarArchivarEchasqui = () =>
  pedir<{ pendientes: PendienteArchivoEchasqui[] }>(
    "/api/mantenimiento/archivar-echasqui",
  );

export const eliminarArchivarEchasqui = (ids: number[]) =>
  pedir<{ eliminadas: number }>(
    "/api/mantenimiento/archivar-echasqui/eliminar",
    postIds(ids),
  );

export const ejecutarArchivarEchasqui = (ids: number[]) =>
  pedir<{ job_id: string }>(
    "/api/mantenimiento/archivar-echasqui/ejecutar",
    postIds(ids),
  );

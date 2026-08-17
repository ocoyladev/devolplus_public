export interface RutasConfig {
  PATH_DESCARGAS: string | null;
  PATH_RI: string | null;
  PATH_AUTORIZAR: string | null;
  PATH_ARCHIVO: string | null;
  PATH_LEGACY_EXE: string | null;
  UNIDAD_ORGANICA_FOLIO: string | null;
}

export interface Credencial {
  sistema: string;
  usuario: string;
}

async function pedir<T>(url: string, init?: RequestInit): Promise<T> {
  const resp = await fetch(url, init);
  if (!resp.ok) {
    throw new Error(`Error ${resp.status} en ${url}`);
  }
  return (await resp.json()) as T;
}

function jsonInit(method: string, body: unknown): RequestInit {
  return {
    method,
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  };
}

export const getRutas = () => pedir<RutasConfig>("/api/config/rutas");
export const putRutas = (rutas: Partial<RutasConfig>) =>
  pedir<RutasConfig>("/api/config/rutas", jsonInit("PUT", rutas));

export const getCredenciales = (sistema: string) =>
  pedir<Credencial>(`/api/config/credenciales/${encodeURIComponent(sistema)}`);
export const putCredenciales = (sistema: string, usuario: string, password: string) =>
  pedir<Credencial>("/api/config/credenciales", jsonInit("PUT", { sistema, usuario, password }));

export async function seleccionarCarpeta(): Promise<string> {
  const resp = await fetch("/api/config/seleccionar-carpeta", { method: "POST" });
  if (!resp.ok) {
    throw new Error(`Error ${resp.status} al abrir el selector de carpeta`);
  }
  return ((await resp.json()) as { ruta: string }).ruta;
}

export const getFeriados = () => pedir<{ feriados: string[] }>("/api/config/feriados");
export const addFeriado = (fecha: string) =>
  pedir<{ feriados: string[] }>("/api/config/feriados", jsonInit("POST", { fecha }));
export const delFeriado = (fecha: string) =>
  pedir<{ feriados: string[] }>(
    "/api/config/feriados/eliminar",
    jsonInit("POST", { fecha }),
  );

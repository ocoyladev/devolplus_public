export interface Carta {
  id: number;
  num_doc: string;
  numero: string;
  anio: string;
  tipo: string;
  fecha_emision: string;
  fecha_notificacion: string;
  plazo: number | null;
  fecha_vencimiento: string;
  vencimiento_manual: number;
  atendida: number;
  obs: string;
  estado: string;
}

// `atendida` sale del Omit y vuelve como boolean: en la UI es un checkbox, y el
// backend lo recibe como bool. Dejarlo como el `number` de Carta rompería el tipo.
export type CartaPatch = Partial<
  Omit<Carta, "id" | "num_doc" | "estado" | "vencimiento_manual" | "atendida"> & {
    atendida: boolean;
  }
>;

export const TIPOS_CARTA = ["PRIMERA", "REITERATIVA", "AMPLIACION", "OTRA"] as const;

async function pedir<T>(url: string, init?: RequestInit): Promise<T> {
  const resp = await fetch(url, init);
  if (!resp.ok) {
    throw new Error(`Error ${resp.status} en ${url}`);
  }
  return (await resp.json()) as T;
}

function cuerpoJson(datos: CartaPatch): RequestInit {
  return {
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(datos),
  };
}

export async function listarCartas(numDoc: string): Promise<Carta[]> {
  const r = await pedir<{ cartas: Carta[] }>(`/api/cartas/${encodeURIComponent(numDoc)}`);
  return r.cartas;
}

export const crearCarta = (numDoc: string, datos: CartaPatch): Promise<Carta> =>
  pedir<Carta>(`/api/cartas/${encodeURIComponent(numDoc)}`, {
    method: "POST",
    ...cuerpoJson(datos),
  });

export const actualizarCarta = (id: number, datos: CartaPatch): Promise<Carta> =>
  pedir<Carta>(`/api/cartas/${id}`, { method: "PATCH", ...cuerpoJson(datos) });

export async function eliminarCarta(id: number): Promise<void> {
  await pedir<{ ok: boolean }>(`/api/cartas/${id}`, { method: "DELETE" });
}

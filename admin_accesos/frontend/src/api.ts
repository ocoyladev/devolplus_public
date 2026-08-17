export type Estado = "pendiente" | "aprobado" | "rechazado" | "inactivo";

export interface Solicitud {
  id: number;
  nombre_completo: string;
  usuario_red: string;
  email: string | null;
  estado: Estado;
  fecha_solicitud: string | null;
  fecha_revision: string | null;
  aprobado_por: string | null;
  observaciones: string | null;
}

export interface Logueo {
  usuario_red: string;
  fecha_hora: string | null;
  resultado: string;
  ip_maquina: string | null;
  version: string | null;
}

async function pedir<T>(url: string, init?: RequestInit): Promise<T> {
  const resp = await fetch(url, init);
  if (!resp.ok) {
    const detalle = await resp.text().catch(() => "");
    throw new Error(`Error ${resp.status} en ${url}${detalle ? `: ${detalle}` : ""}`);
  }
  return (await resp.json()) as T;
}

export const getSolicitudes = (estado?: string) =>
  pedir<Solicitud[]>(
    "/api/solicitudes" + (estado ? `?estado=${encodeURIComponent(estado)}` : ""),
  );

export const decidir = (id: number, estado: Estado, observaciones?: string) =>
  pedir<{ ok: boolean; mensaje: string }>(`/api/solicitudes/${id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ estado, observaciones: observaciones || null }),
  });

export const getLogueos = (usuario_red?: string, limite = 50) => {
  const p = new URLSearchParams();
  if (usuario_red) p.set("usuario_red", usuario_red);
  p.set("limite", String(limite));
  return pedir<Logueo[]>(`/api/logueos?${p.toString()}`);
};

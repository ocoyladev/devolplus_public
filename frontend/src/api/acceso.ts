export type EstadoAcceso =
  | "permitido"
  | "no_registrado"
  | "pendiente"
  | "rechazado"
  | "inactivo"
  | "sin_conexion";

export interface AccesoEstado {
  estado: EstadoAcceso;
  usuario_red: string;
  mensaje: string;
}

export interface AccesoResultado {
  ok: boolean;
  mensaje: string;
}

async function pedir<T>(url: string, init?: RequestInit): Promise<T> {
  const resp = await fetch(url, init);
  if (!resp.ok) {
    throw new Error(`Error ${resp.status} en ${url}`);
  }
  return (await resp.json()) as T;
}

export const getAcceso = () => pedir<AccesoEstado>("/api/acceso");

export const solicitarAcceso = (nombre_completo: string, email: string) =>
  pedir<AccesoResultado>("/api/acceso/solicitud", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ nombre_completo, email }),
  });

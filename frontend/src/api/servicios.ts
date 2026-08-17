export interface ServiciosEstado {
  portal: boolean;
  workflow: boolean;
}

export async function verificarServicios(): Promise<ServiciosEstado> {
  const resp = await fetch("/api/servicios/verificar", { method: "POST" });
  if (!resp.ok) {
    throw new Error(`Error ${resp.status} al verificar servicios`);
  }
  return (await resp.json()) as ServiciosEstado;
}

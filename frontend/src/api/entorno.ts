export interface FirmaAutoEstado {
  disponible: boolean;
  escala: number | null;
  ancho: number | null;
  alto: number | null;
  motivo: string;
  perfil: string | null;
}

/**
 * Consulta si la firma automática por coordenadas puede activarse. Soporta
 * más de un perfil de escala/resolución (ver `perfil`); se puede re-consultar
 * ante cambios de pantalla (conectar/desconectar un monitor).
 */
export async function fetchFirmaAutoEstado(): Promise<FirmaAutoEstado> {
  const resp = await fetch("/api/entorno/firma-auto");
  if (!resp.ok) {
    throw new Error(`Error ${resp.status} al detectar la pantalla`);
  }
  return (await resp.json()) as FirmaAutoEstado;
}

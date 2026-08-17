export interface TablaResponse {
  columns: string[];
  rows: Record<string, unknown>[];
  total: number;
}

export async function fetchTabla(): Promise<TablaResponse> {
  const resp = await fetch("/api/datos/tabla");
  if (!resp.ok) {
    throw new Error(`Error ${resp.status} al cargar la tabla`);
  }
  return (await resp.json()) as TablaResponse;
}

export async function fetchArchivo(): Promise<TablaResponse> {
  const resp = await fetch("/api/datos/archivo");
  if (!resp.ok) {
    throw new Error(`Error ${resp.status} al cargar el archivo`);
  }
  return (await resp.json()) as TablaResponse;
}

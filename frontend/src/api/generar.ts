type Row = Record<string, unknown>;

export async function listarModelos(tipo: "carta" | "ri"): Promise<string[]> {
  const resp = await fetch(`/api/generar/modelos/${tipo}`);
  if (!resp.ok) {
    throw new Error(`Error ${resp.status} al listar modelos`);
  }
  return ((await resp.json()) as { modelos: string[] }).modelos;
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
  return ((await resp.json()) as { job_id: string }).job_id;
}

export const generarCarta = (row: Row, modelos: string[], plazo: number, archivo = false) =>
  postJob("/api/generar/carta", { row, modelos, plazo, archivo });

export const generarRi = (row: Row, modelo: string, numRi: string | null) =>
  postJob("/api/generar/ri", { row, modelo, num_ri: numRi });

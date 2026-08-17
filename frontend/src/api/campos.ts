export async function actualizarCampo(
  numDoc: string,
  campo: string,
  valor: string,
): Promise<void> {
  const resp = await fetch(`/api/campos/${encodeURIComponent(numDoc)}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ campo, valor }),
  });
  if (!resp.ok) {
    throw new Error(`Error ${resp.status} al guardar ${campo}`);
  }
}

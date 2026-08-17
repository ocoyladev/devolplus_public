export async function fetchHealth(): Promise<string> {
  const resp = await fetch("/api/health");
  const data: { status: string } = await resp.json();
  return data.status;
}

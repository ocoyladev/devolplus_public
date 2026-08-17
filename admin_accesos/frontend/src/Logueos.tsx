import { useCallback, useEffect, useState } from "react";

import { getLogueos, type Logueo } from "./api";

const COLOR: Record<string, string> = {
  exitoso: "text-green-700",
  denegado_pendiente: "text-amber-700",
  denegado_rechazado: "text-red-700",
  denegado_inactivo: "text-slate-600",
};

export function Logueos(): JSX.Element {
  const [usuario, setUsuario] = useState("");
  const [filtro, setFiltro] = useState("");
  const [filas, setFilas] = useState<Logueo[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  const cargar = useCallback(() => {
    setFilas(null);
    setError(null);
    getLogueos(filtro || undefined, 100)
      .then(setFilas)
      .catch((e: unknown) => setError(String(e)));
  }, [filtro]);

  useEffect(() => cargar(), [cargar]);

  return (
    <div>
      <div className="mb-3 flex items-center gap-2">
        <input
          value={usuario}
          onChange={(e) => setUsuario(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") setFiltro(usuario.trim());
          }}
          placeholder="Filtrar por usuario de red"
          className="rounded border px-2 py-1 text-sm"
        />
        <button
          onClick={() => setFiltro(usuario.trim())}
          className="rounded border px-3 py-1 text-sm hover:bg-slate-100"
        >
          Buscar
        </button>
        {filtro ? (
          <button
            onClick={() => {
              setUsuario("");
              setFiltro("");
            }}
            className="rounded border px-3 py-1 text-sm hover:bg-slate-100"
          >
            Limpiar
          </button>
        ) : null}
      </div>

      {error ? (
        <p className="p-3 text-sm text-red-600">{error}</p>
      ) : filas === null ? (
        <p className="p-3 text-sm text-slate-500">Cargando…</p>
      ) : filas.length === 0 ? (
        <p className="p-3 text-sm text-slate-500">Sin registros de logueo.</p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="border-b text-xs uppercase text-slate-500">
              <tr>
                <th className="p-2">Fecha/hora (UTC-5)</th>
                <th className="p-2">Usuario</th>
                <th className="p-2">Resultado</th>
                <th className="p-2">Versión</th>
                <th className="p-2">IP</th>
              </tr>
            </thead>
            <tbody>
              {filas.map((l, i) => (
                <tr key={i} className="border-b hover:bg-slate-50">
                  <td className="p-2 text-xs text-slate-500">
                    {l.fecha_hora?.replace("T", " ").slice(0, 19) ?? "—"}
                  </td>
                  <td className="p-2 font-mono">{l.usuario_red}</td>
                  <td className={`p-2 ${COLOR[l.resultado] ?? ""}`}>{l.resultado}</td>
                  <td className="p-2 font-mono text-xs text-slate-600">
                    {l.version ?? "—"}
                  </td>
                  <td className="p-2 text-slate-500">{l.ip_maquina ?? "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

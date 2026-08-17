import { useCallback, useEffect, useState } from "react";

import { decidir, getSolicitudes, type Estado, type Solicitud } from "./api";

const FILTROS: { valor: string; etiqueta: string }[] = [
  { valor: "pendiente", etiqueta: "Pendientes" },
  { valor: "", etiqueta: "Todas" },
  { valor: "aprobado", etiqueta: "Aprobadas" },
  { valor: "rechazado", etiqueta: "Rechazadas" },
  { valor: "inactivo", etiqueta: "Inactivas" },
];

const COLOR: Record<Estado, string> = {
  pendiente: "bg-amber-100 text-amber-800",
  aprobado: "bg-green-100 text-green-800",
  rechazado: "bg-red-100 text-red-800",
  inactivo: "bg-slate-200 text-slate-700",
};

interface Props {
  onAviso: (m: string) => void;
}

export function Solicitudes({ onAviso }: Props): JSX.Element {
  const [filtro, setFiltro] = useState("pendiente");
  const [filas, setFilas] = useState<Solicitud[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  const cargar = useCallback(() => {
    setFilas(null);
    setError(null);
    getSolicitudes(filtro || undefined)
      .then(setFilas)
      .catch((e: unknown) => setError(String(e)));
  }, [filtro]);

  useEffect(() => cargar(), [cargar]);

  async function aplicar(s: Solicitud, estado: Estado): Promise<void> {
    const obs =
      estado === "rechazado" || estado === "inactivo"
        ? window.prompt(`Observaciones para ${s.usuario_red} (opcional):`) ?? undefined
        : undefined;
    try {
      const r = await decidir(s.id, estado, obs);
      onAviso((r.ok ? "✓ " : "✗ ") + r.mensaje);
      cargar();
    } catch (e) {
      onAviso(String(e));
    }
  }

  return (
    <div>
      <div className="mb-3 flex items-center gap-2">
        <select
          value={filtro}
          onChange={(e) => setFiltro(e.target.value)}
          className="rounded border px-2 py-1 text-sm"
        >
          {FILTROS.map((f) => (
            <option key={f.etiqueta} value={f.valor}>
              {f.etiqueta}
            </option>
          ))}
        </select>
        <button
          onClick={cargar}
          className="rounded border px-3 py-1 text-sm hover:bg-slate-100"
        >
          ↻ Refrescar
        </button>
      </div>

      {error ? (
        <p className="p-3 text-sm text-red-600">{error}</p>
      ) : filas === null ? (
        <p className="p-3 text-sm text-slate-500">Cargando…</p>
      ) : filas.length === 0 ? (
        <p className="p-3 text-sm text-slate-500">No hay solicitudes en este filtro.</p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="border-b text-xs uppercase text-slate-500">
              <tr>
                <th className="p-2">Usuario</th>
                <th className="p-2">Nombre</th>
                <th className="p-2">Email</th>
                <th className="p-2">Estado</th>
                <th className="p-2">Solicitud</th>
                <th className="p-2">Observaciones</th>
                <th className="p-2">Acciones</th>
              </tr>
            </thead>
            <tbody>
              {filas.map((s) => (
                <tr key={s.id} className="border-b hover:bg-slate-50">
                  <td className="p-2 font-mono">{s.usuario_red}</td>
                  <td className="p-2">{s.nombre_completo}</td>
                  <td className="p-2 text-slate-500">{s.email ?? "—"}</td>
                  <td className="p-2">
                    <span className={`rounded px-2 py-0.5 text-xs ${COLOR[s.estado]}`}>
                      {s.estado}
                    </span>
                  </td>
                  <td className="p-2 text-xs text-slate-500">
                    {s.fecha_solicitud?.replace("T", " ").slice(0, 19) ?? "—"}
                  </td>
                  <td className="p-2 text-xs text-slate-500">{s.observaciones ?? "—"}</td>
                  <td className="p-2">
                    <div className="flex gap-1">
                      {s.estado !== "aprobado" ? (
                        <button
                          onClick={() => void aplicar(s, "aprobado")}
                          className="rounded bg-green-600 px-2 py-0.5 text-xs text-white"
                        >
                          Aprobar
                        </button>
                      ) : null}
                      {s.estado !== "rechazado" ? (
                        <button
                          onClick={() => void aplicar(s, "rechazado")}
                          className="rounded bg-red-600 px-2 py-0.5 text-xs text-white"
                        >
                          Rechazar
                        </button>
                      ) : null}
                      {s.estado === "aprobado" ? (
                        <button
                          onClick={() => void aplicar(s, "inactivo")}
                          className="rounded bg-slate-500 px-2 py-0.5 text-xs text-white"
                        >
                          Inactivar
                        </button>
                      ) : null}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

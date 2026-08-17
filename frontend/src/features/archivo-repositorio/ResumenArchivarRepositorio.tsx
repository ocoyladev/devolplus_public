import type { DetalleArchivar } from "../../api/acciones";

interface Props {
  detalle: DetalleArchivar[] | null;
  onClose: () => void;
}

const BADGE: Record<DetalleArchivar["resultado"], { txt: string; cls: string }> = {
  archivado: { txt: "Archivado", cls: "bg-green-100 text-green-800" },
  concluido: { txt: "Ya concluido", cls: "bg-sky-100 text-sky-800" },
  pendiente: { txt: "Encolado pendiente", cls: "bg-amber-100 text-amber-800" },
  error: { txt: "Error", cls: "bg-red-100 text-red-800" },
};

/** Ventana emergente con el detalle de "Archivar REPOSITORIO" (uno por repositorio). */
export function ResumenArchivarRepositorio({ detalle, onClose }: Props): JSX.Element | null {
  if (!detalle) return null;
  const cuenta = (r: DetalleArchivar["resultado"]): number =>
    detalle.filter((d) => d.resultado === r).length;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4"
      role="dialog"
      aria-modal="true"
    >
      <div className="w-full max-w-2xl rounded-lg bg-white shadow-xl">
        <div className="rounded-t-lg bg-slate-800 px-5 py-3 text-white">
          <h2 className="text-base font-semibold">Archivar REPOSITORIO — resumen</h2>
        </div>
        <div className="max-h-[60vh] overflow-y-auto px-5 py-4 text-sm text-slate-700">
          <p className="mb-3 text-slate-600">
            Archivados {cuenta("archivado")} · Ya concluidos {cuenta("concluido")} ·
            Pendientes {cuenta("pendiente")} · Errores {cuenta("error")}
          </p>
          {detalle.length === 0 ? (
            <p className="text-slate-500">No había repositorio para archivar.</p>
          ) : (
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-100">
                <tr>
                  <th className="p-1.5">N° Doc</th>
                  <th className="p-1.5">Expediente</th>
                  <th className="p-1.5">Resultado</th>
                  <th className="p-1.5">Detalle</th>
                </tr>
              </thead>
              <tbody>
                {detalle.map((d, i) => (
                  <tr key={`${d.num_doc}-${d.exp}-${i}`} className="border-t">
                    <td className="p-1.5">{d.num_doc}</td>
                    <td className="p-1.5 font-mono">{d.exp}</td>
                    <td className="p-1.5">
                      <span
                        className={`rounded px-1.5 py-0.5 text-[11px] font-semibold ${BADGE[d.resultado].cls}`}
                      >
                        {BADGE[d.resultado].txt}
                      </span>
                    </td>
                    <td className="p-1.5 text-slate-500">{d.mensaje}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
        <div className="flex justify-end border-t px-5 py-3">
          <button
            className="rounded bg-slate-800 px-4 py-1.5 text-sm text-white hover:bg-slate-700"
            onClick={onClose}
            autoFocus
          >
            Aceptar
          </button>
        </div>
      </div>
    </div>
  );
}

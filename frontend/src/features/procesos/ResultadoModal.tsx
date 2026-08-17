export interface ResultadoPptt {
  ok: boolean;
  mensaje: string;
  okCount?: number;
  oks?: string[];
  yaDescargadas?: string[];
  omitidos?: string[];
  errores: { caso: string; motivo: string }[];
  tituloExito?: string;
  tituloError?: string;
}

interface Props {
  resultado: ResultadoPptt | null;
  onClose: () => void;
}

/**
 * Ventana emergente (modal bloqueante) con el resultado de "Generar PPTT".
 * Muestra en verde cuando todo procedió bien o en rojo la lista de casos con error.
 */
export function ResultadoModal({ resultado, onClose }: Props): JSX.Element | null {
  if (!resultado) return null;

  const hayErrores = resultado.errores.length > 0;
  const esError = !resultado.ok || hayErrores;
  const titulo = esError
    ? resultado.tituloError ?? "Generar PPTT — finalizó con errores"
    : resultado.tituloExito ?? "Generar PPTT — completado";

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4"
      role="dialog"
      aria-modal="true"
    >
      <div className="w-full max-w-lg rounded-lg bg-white shadow-xl">
        <div
          className={`rounded-t-lg px-5 py-3 text-white ${
            esError ? "bg-red-600" : "bg-green-600"
          }`}
        >
          <h2 className="text-base font-semibold">{titulo}</h2>
        </div>

        <div className="max-h-[60vh] overflow-y-auto px-5 py-4 text-sm text-slate-700">
          <p className="mb-3">{resultado.mensaje}</p>

          {resultado.oks && resultado.oks.length > 0 ? (
            <div className="mb-4">
              <p className="mb-2 font-medium text-green-700">
                Casos completados correctamente ({resultado.oks.length}):
              </p>
              <ul className="space-y-1">
                {resultado.oks.map((caso, i) => (
                  <li
                    key={`ok-${caso}-${i}`}
                    className="rounded border border-green-200 bg-green-50 px-3 py-1.5 text-green-800"
                  >
                    {caso}
                  </li>
                ))}
              </ul>
            </div>
          ) : null}

          {resultado.yaDescargadas && resultado.yaDescargadas.length > 0 ? (
            <p className="mb-2 text-xs text-slate-500">
              Ya estaban descargadas ({resultado.yaDescargadas.length}):{" "}
              {resultado.yaDescargadas.join(", ")}
            </p>
          ) : null}

          {resultado.omitidos && resultado.omitidos.length > 0 ? (
            <p className="mb-3 text-xs text-slate-500">
              Omitidas ({resultado.omitidos.length}): {resultado.omitidos.join(", ")}
            </p>
          ) : null}

          {resultado.errores.length > 0 ? (
            <>
              <p className="mb-2 font-medium text-red-700">
                Casos con error ({resultado.errores.length}):
              </p>
              <ul className="space-y-2">
                {resultado.errores.map((e, i) => (
                  <li
                    key={`${e.caso}-${i}`}
                    className="rounded border border-red-200 bg-red-50 px-3 py-2"
                  >
                    <span className="font-medium text-red-800">{e.caso}</span>
                    <span className="block text-xs text-red-700">{e.motivo}</span>
                  </li>
                ))}
              </ul>
            </>
          ) : !esError && (!resultado.oks || resultado.oks.length === 0) ? (
            <p className="text-green-700">
              Todos los casos se procesaron correctamente
              {typeof resultado.okCount === "number" ? ` (${resultado.okCount}).` : "."}
            </p>
          ) : null}
        </div>

        <div className="flex justify-end gap-2 border-t px-5 py-3">
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

import { useEffect, useRef } from "react";

export interface EjecucionRun {
  kind: string;
  log: string[];
  done: number;
  total: number;
  etiqueta: string;
}

const KINDS_RSIRAT = new Set(["rsirat_ref", "rsirat_antec"]);

/**
 * Ventana de ejecución (overlay bloqueante) mientras corre una función lenta
 * (Autorizar, Generar PPTT o descargas RSIRAT). Muestra el log en vivo y la
 * barra de progreso. No es descartable: la cierra App al llegar el job_done.
 * La copia del encabezado depende del kind: las descargas RSIRAT advierten que
 * el script controla mouse/teclado; Autorizar/PPTT solo piden esperar.
 */
export function EjecucionOverlay({
  run,
}: {
  run: EjecucionRun | null;
}): JSX.Element | null {
  const finRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    finRef.current?.scrollIntoView({ block: "end" });
  }, [run?.log.length]);

  if (!run) return null;

  const esRsirat = KINDS_RSIRAT.has(run.kind);
  const titulo = esRsirat ? "⚠ Automatización en curso" : "⏳ Procesando…";
  const subtitulo = esRsirat
    ? "NO use el teclado ni el mouse. Para abortar, pulse Ctrl+Shift+Q (o mueva el mouse a una esquina)."
    : "Espere, no cierre la aplicación mientras el proceso termina.";
  const barraColor = esRsirat ? "bg-amber-500" : "bg-blue-600";

  return (
    <div
      className="fixed inset-0 z-[60] flex items-center justify-center bg-black/60 p-4"
      role="dialog"
      aria-modal="true"
      aria-label="Proceso en curso"
    >
      <div className="flex max-h-[80vh] w-full max-w-2xl flex-col rounded-lg bg-white shadow-xl">
        <div className={`rounded-t-lg px-5 py-3 text-white ${barraColor}`}>
          <h2 className="text-base font-semibold">{titulo}</h2>
          <p className="text-sm">{subtitulo}</p>
        </div>

        <div className="flex items-center gap-2 border-b px-5 py-2 text-sm text-slate-600">
          {run.total > 0 ? (
            <>
              <progress className="h-2 w-40" value={run.done} max={run.total} />
              <span>
                {run.etiqueta ? `${run.etiqueta} — ` : ""}
                {run.done}/{run.total}
              </span>
            </>
          ) : (
            <span>⏳ Iniciando…</span>
          )}
        </div>

        <div className="flex-1 overflow-y-auto px-5 py-3">
          <pre className="whitespace-pre-wrap font-mono text-xs text-slate-700">
            {run.log.length ? (
              run.log.map((linea, indice) => <div key={indice}>{linea}</div>)
            ) : (
              <div>Iniciando…</div>
            )}
          </pre>
          <div ref={finRef} />
        </div>
      </div>
    </div>
  );
}

import { useCallback, useEffect, useState } from "react";

import {
  procesos,
  type CasoEchasqui,
  type EchasquiEstado,
  type ItemEchasquiPendiente,
} from "../../api/acciones";
import { useTareaLock } from "../tareas/tareaLock";

type Fila = Record<string, unknown>;

interface Props {
  filas: Fila[];
  abierto: boolean;
  onCerrar: () => void;
  onJobIniciado: (kind: string) => void;
  onError: (mensaje: string) => void;
}

/** Clave estable de un pendiente (caso + denominación). */
function claveP(numDoc: string, denom: string): string {
  return `${numDoc}::${denom}`;
}

function esPendiente(e: EchasquiEstado): boolean {
  return e.estado === "pendiente_subir" || e.estado === "pdf_faltante";
}

/** Etiqueta corta para un echasqui ya resuelto (o automático). */
function etiquetaEstado(e: EchasquiEstado): string {
  switch (e.estado) {
    case "subido":
      return "✓ subido —";
    case "pdf_ok":
      return "✓ PDF generado —";
    case "auto":
      return "• automático —";
    case "pdf_faltante":
      return "⚠ falta PDF —";
    default:
      return "•";
  }
}

export function VerificarEchasquiModal({
  filas,
  abierto,
  onCerrar,
  onJobIniciado,
  onError,
}: Props): JSX.Element | null {
  const [cargando, setCargando] = useState(false);
  const [casos, setCasos] = useState<CasoEchasqui[]>([]);
  const [seleccion, setSeleccion] = useState<Record<string, boolean>>({});
  const { ocupado, iniciar, terminar } = useTareaLock();

  const verificar = useCallback(async (): Promise<void> => {
    const numDocs = filas
      .map((f) => String(f.num_doc ?? "").trim())
      .filter(Boolean);
    if (numDocs.length === 0) {
      onError("No hay casos seleccionados.");
      return;
    }
    setCargando(true);
    try {
      const res = await procesos.verificarEchasqui(numDocs);
      setCasos(res);
      // Por defecto, todos los echasqui subibles marcados.
      const sel: Record<string, boolean> = {};
      for (const c of res)
        for (const e of c.echasquis)
          if (e.subible) sel[claveP(c.num_doc, e.denom)] = true;
      setSeleccion(sel);
    } catch (e) {
      onError(String(e));
    } finally {
      setCargando(false);
    }
  }, [filas, onError]);

  useEffect(() => {
    if (abierto) void verificar();
    else {
      setCasos([]);
      setSeleccion({});
    }
  }, [abierto, verificar]);

  const itemsSeleccionados: ItemEchasquiPendiente[] = casos.flatMap((c) =>
    c.echasquis
      .filter((e) => e.subible && seleccion[claveP(c.num_doc, e.denom)])
      .map((e) => ({
        num_doc: c.num_doc,
        num_dev: c.num_dev,
        num_ruc: c.num_ruc,
        denom: e.denom,
      })),
  );

  async function subir(): Promise<void> {
    if (itemsSeleccionados.length === 0) return;
    if (!iniciar()) return; // ya hay una tarea en curso
    try {
      await procesos.subirEchasquiPendientes(itemsSeleccionados);
      onJobIniciado("subir_echasqui");
      // job en curso: el lock se libera al llegar job_done
    } catch (e) {
      onError(String(e));
      terminar();
    }
  }

  if (!abierto) return null;

  const totalPendientes = casos.reduce(
    (n, c) => n + c.echasquis.filter(esPendiente).length,
    0,
  );

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/30"
      onClick={() => onCerrar()}
    >
      <div
        className="w-[620px] max-w-[92vw] rounded bg-white p-4 shadow-lg"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="mb-2 flex items-center justify-between">
          <h2 className="text-base font-semibold text-slate-800">
            Verificar Exp. Echasqui.
          </h2>
          <button onClick={() => onCerrar()} className="text-slate-500">
            ✕
          </button>
        </div>

        {cargando ? (
          <p className="py-6 text-center text-sm text-slate-500">Verificando…</p>
        ) : (
          <>
            <div className="max-h-[55vh] space-y-3 overflow-y-auto">
              {casos.map((c) => (
                <div key={c.num_doc} className="rounded border p-2 text-sm">
                  <div className="flex items-center gap-2 font-medium text-slate-800">
                    <span>
                      {c.num_doc} · {c.nombre}
                    </span>
                    {c.tipo_exp ? (
                      <span className="rounded bg-slate-200 px-1.5 py-0.5 text-[10px] font-semibold text-slate-600">
                        {c.tipo_exp}
                      </span>
                    ) : null}
                  </div>
                  {c.error ? (
                    <div className="text-xs text-red-600">⚠ {c.error}</div>
                  ) : c.sin_echasqui ? (
                    <div className="text-xs text-slate-500">
                      Sin echasqui identificados.
                    </div>
                  ) : (
                    c.echasquis.map((e) =>
                      e.subible ? (
                        <label
                          key={e.denom}
                          className="flex items-center gap-2 text-xs text-amber-700"
                        >
                          <input
                            type="checkbox"
                            checked={!!seleccion[claveP(c.num_doc, e.denom)]}
                            onChange={(ev) =>
                              setSeleccion((prev) => ({
                                ...prev,
                                [claveP(c.num_doc, e.denom)]: ev.target.checked,
                              }))
                            }
                          />
                          ⚠ {e.denom} — pendiente de subir
                        </label>
                      ) : (
                        <div
                          key={e.denom}
                          className={
                            e.estado === "pdf_faltante"
                              ? "text-xs text-amber-700"
                              : "text-xs text-slate-400"
                          }
                        >
                          {etiquetaEstado(e)} {e.denom}
                        </div>
                      ),
                    )
                  )}
                </div>
              ))}
              {casos.length === 0 ? (
                <p className="text-sm text-slate-500">Sin resultados.</p>
              ) : null}
            </div>

            <div className="mt-3 flex items-center justify-between">
              <span className="text-xs text-slate-500">
                {totalPendientes} pendiente(s) · {itemsSeleccionados.length}{" "}
                seleccionado(s)
              </span>
              <div className="flex gap-2">
                <button
                  onClick={() => void verificar()}
                  className="rounded border px-3 py-1 text-sm hover:bg-slate-100"
                >
                  Re-verificar
                </button>
                <button
                  onClick={() => onCerrar()}
                  className="rounded border px-3 py-1 text-sm hover:bg-slate-100"
                >
                  Cerrar
                </button>
                <button
                  disabled={itemsSeleccionados.length === 0 || ocupado}
                  onClick={() => void subir()}
                  className="rounded bg-blue-600 px-3 py-1 text-sm text-white disabled:opacity-50"
                >
                  Subir pendientes
                </button>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
}

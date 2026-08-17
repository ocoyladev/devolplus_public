import { useCallback, useEffect, useState } from "react";

import {
  procesos,
  type AccionSubsanar,
  type AlertaValidacion,
  type CasoValidacion,
} from "../../api/acciones";
import { useTareaLock } from "../tareas/tareaLock";
import { useProgreso } from "../../ws/useProgreso";

type Fila = Record<string, unknown>;

interface Props {
  filas: Fila[];
  abierto: boolean;
  onCerrar: () => void;
  onJobIniciado: (kind: string) => void;
  onError: (mensaje: string) => void;
}

// 'pptt_of' queda fuera a propósito: rehace la OF entera, y varias rectificatorias
// de una misma OF la lanzarían repetida. Se ofrece solo como botón individual.
const AUTO_SUBSANABLES = new Set(["pptt", "pptt_revertir", "foliar", "registrar_echasqui"]);

const COLOR_NIVEL: Record<string, string> = {
  ok: "border-green-300 bg-green-50",
  advertencia: "border-amber-300 bg-amber-50",
  error: "border-red-300 bg-red-50",
};

const LABEL_ACCION: Record<string, string> = {
  pptt: "Generar PPTT",
  pptt_of: "Regenerar PPTT de la OF",
  pptt_revertir: "Revertir + regenerar PPTT",
  foliar: "Foliar consolidado",
  registrar_echasqui: "Registrar Exp. ECHASQUI",
  cargar_expediente: "Cargar expediente electrónico",
  subir_echasqui: "Subir echasqui al expediente",
  abrir_carpeta: "Abrir carpeta",
};

export function ValidarArchivoModal({
  filas,
  abierto,
  onCerrar,
  onJobIniciado,
  onError,
}: Props): JSX.Element | null {
  const [cargando, setCargando] = useState(false);
  const [casos, setCasos] = useState<CasoValidacion[]>([]);
  const [avance, setAvance] = useState<{ done: number; total: number; etiqueta: string } | null>(
    null,
  );
  const { ocupado, iniciar, terminar } = useTareaLock();

  // La validación es síncrona (el resultado es la respuesta, no un job), pero
  // emite progreso por WS. Solo se escucha mientras el modal está abierto.
  useProgreso((e) => {
    if (e.type !== "progress" || e.kind !== "validar_archivo") return;
    if (typeof e.total !== "number" || e.total <= 0) return;
    setAvance({ done: e.done ?? 0, total: e.total, etiqueta: e.etiqueta ?? "" });
  }, abierto);

  const validar = useCallback(async (): Promise<void> => {
    const numDocs = filas.map((f) => String(f.num_doc ?? "").trim()).filter(Boolean);
    if (numDocs.length === 0) {
      onError("No hay casos seleccionados.");
      return;
    }
    setCargando(true);
    setAvance({ done: 0, total: numDocs.length, etiqueta: "" });
    try {
      setCasos(await procesos.validarArchivo(numDocs));
    } catch (e) {
      onError(String(e));
    } finally {
      setCargando(false);
      setAvance(null);
    }
  }, [filas, onError]);

  useEffect(() => {
    if (abierto) void validar();
    else {
      setCasos([]);
      setAvance(null);
    }
  }, [abierto, validar]);

  async function lanzarSubsanar(acciones: AccionSubsanar[]): Promise<void> {
    if (acciones.length === 0) return;
    if (!iniciar()) return;
    try {
      await procesos.validarArchivoSubsanar(acciones);
      onJobIniciado("validar_subsanar");
    } catch (e) {
      onError(String(e));
      terminar();
    }
  }

  async function lanzarJob(kind: string, fn: () => Promise<unknown>): Promise<void> {
    if (!iniciar()) return;
    try {
      await fn();
      onJobIniciado(kind);
    } catch (e) {
      onError(String(e));
      terminar();
    }
  }

  async function accionItem(caso: CasoValidacion, alerta: AlertaValidacion): Promise<void> {
    // Carga al 1649 de reportes_internos/cedula_verificacion.
    if (alerta.accion === "cargar_expediente") {
      await lanzarJob("carga_expedientes", () => procesos.cargaExpedientes([caso.num_doc]));
      return;
    }
    // Subida de un echasqui por vía especial (la misma que hace Generar PPTT).
    if (alerta.accion === "subir_echasqui") {
      const denom = alerta.item ?? "";
      if (!denom) {
        onError("La alerta no indica qué echasqui subir.");
        return;
      }
      await lanzarJob("subir_echasqui", () =>
        procesos.subirEchasquiPendientes([
          { num_doc: caso.num_doc, num_dev: caso.num_dev, num_ruc: caso.num_ruc, denom },
        ]),
      );
      return;
    }
    await lanzarSubsanar([{ num_doc: caso.num_doc, accion: alerta.accion }]);
  }

  function subsanarTodo(): void {
    const acciones: AccionSubsanar[] = [];
    for (const c of casos)
      for (const a of c.alertas)
        if (AUTO_SUBSANABLES.has(a.accion))
          acciones.push({ num_doc: c.num_doc, accion: a.accion });
    void lanzarSubsanar(acciones);
  }

  async function exportar(): Promise<void> {
    try {
      await procesos.validarArchivoExportar(casos);
    } catch (e) {
      onError(String(e));
    }
  }

  if (!abierto) return null;

  const totalAlertas = casos.reduce((n, c) => n + c.alertas.length, 0);
  const haySubsanables = casos.some((c) => c.alertas.some((a) => AUTO_SUBSANABLES.has(a.accion)));

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30">
      <div
        className="w-[720px] max-w-[94vw] rounded bg-white p-4 shadow-lg"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="mb-2 flex items-center justify-between">
          <h2 className="text-base font-semibold text-slate-800">Validar archivo</h2>
          <button onClick={() => onCerrar()} className="text-slate-500">
            ✕
          </button>
        </div>

        {cargando ? (
          <div className="py-6 text-center text-sm text-slate-500">
            {avance && avance.total > 0 ? (
              <>
                <progress
                  className="h-2 w-64"
                  value={avance.done}
                  max={avance.total}
                  aria-label="Avance de la validación"
                />
                <p className="mt-2">
                  Validando… {avance.done}/{avance.total} (
                  {Math.round((avance.done / avance.total) * 100)}%)
                  {avance.etiqueta ? ` · ${avance.etiqueta}` : ""}
                </p>
              </>
            ) : (
              <p>Validando…</p>
            )}
          </div>
        ) : (
          <>
            <div className="max-h-[60vh] space-y-3 overflow-y-auto">
              {casos.map((c) => (
                <div
                  key={c.num_doc}
                  onDoubleClick={() => void procesos.validarArchivoAbrirCarpeta(c.num_doc)}
                  className={`cursor-default rounded border p-2 text-sm ${COLOR_NIVEL[c.nivel] ?? ""}`}
                >
                  <div className="flex items-center gap-2 font-medium text-slate-800">
                    <span>
                      {c.num_doc} · {c.nombre}
                    </span>
                    {c.tipo_exp ? (
                      <span className="rounded bg-slate-200 px-1.5 py-0.5 text-[10px] font-semibold text-slate-600">
                        {c.tipo_exp}
                        {c.is_of_multiple ? " · MÚLT." : ""}
                      </span>
                    ) : null}
                    {/* Rectificatoria: hereda el armado del origen, por eso no se
                        le exigen PPTT propio ni indispensables. */}
                    {c.es_tipo12 ? (
                      <span
                        title="Rectificatoria: hereda ARCHIVOS_FINALES de su solicitud de origen"
                        className="rounded bg-indigo-100 px-1.5 py-0.5 text-[10px] font-semibold text-indigo-700"
                      >
                        TIPO 12{c.origen_tipo12 ? ` → ${c.origen_tipo12}` : ""}
                      </span>
                    ) : null}
                    <span className="ml-auto text-[10px] uppercase text-slate-500">{c.nivel}</span>
                  </div>
                  {c.error ? <div className="text-xs text-red-600">⚠ {c.error}</div> : null}
                  {c.alertas.length === 0 ? (
                    <div className="text-xs text-green-700">✓ Sin observaciones.</div>
                  ) : (
                    c.alertas.map((a, i) => (
                      <div key={i} className="mt-1 flex items-center gap-2 text-xs">
                        <span className={a.severidad === "error" ? "text-red-700" : "text-amber-700"}>
                          {a.severidad === "error" ? "✗" : "⚠"} {a.mensaje}
                        </span>
                        {a.accion ? (
                          <button
                            disabled={ocupado}
                            onClick={() => void accionItem(c, a)}
                            className="ml-auto rounded border px-2 py-0.5 text-[11px] hover:bg-white disabled:opacity-40"
                          >
                            {LABEL_ACCION[a.accion] ?? a.accion}
                          </button>
                        ) : null}
                      </div>
                    ))
                  )}
                </div>
              ))}
              {casos.length === 0 ? <p className="text-sm text-slate-500">Sin resultados.</p> : null}
            </div>

            <div className="mt-3 flex items-center justify-between">
              <span className="text-xs text-slate-500">
                {casos.length} caso(s) · {totalAlertas} alerta(s)
              </span>
              <div className="flex gap-2">
                <button
                  onClick={() => onCerrar()}
                  className="rounded border px-3 py-1 text-sm hover:bg-slate-100"
                >
                  Cerrar
                </button>
                <button
                  onClick={() => void validar()}
                  className="rounded border px-3 py-1 text-sm hover:bg-slate-100"
                >
                  Re-validar
                </button>
                <button
                  onClick={() => void exportar()}
                  disabled={casos.length === 0}
                  className="rounded border px-3 py-1 text-sm hover:bg-slate-100 disabled:opacity-40"
                >
                  Exportar a Excel
                </button>
                <button
                  onClick={subsanarTodo}
                  disabled={!haySubsanables || ocupado}
                  className="rounded bg-blue-600 px-3 py-1 text-sm text-white disabled:opacity-50"
                >
                  Subsanar todo
                </button>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
}

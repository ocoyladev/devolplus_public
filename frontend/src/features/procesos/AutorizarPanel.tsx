import { useState } from "react";

import {
  procesos,
  type ConflictoAutorizar,
  type ConflictoC64,
  type DecisionAutorizar,
  type DecisionC64,
} from "../../api/acciones";
import { useTareaLock } from "../tareas/tareaLock";

interface Props {
  seleccion: string[];
  filas?: Record<string, unknown>[];
  onJobIniciado: (kind: string) => void;
  onError: (mensaje: string) => void;
}

const BTN =
  "rounded border px-3 py-1 text-sm disabled:opacity-40 disabled:cursor-not-allowed hover:bg-slate-100";

// Formularios asociados que NO llevan fecha inicial autocompletada.
const COD_FOR_ASO_SIN_FECHA = new Set(["0709", "1649", "4949"]);

function normalizarCodForAso(valor: unknown): string {
  let s = String(valor ?? "").trim();
  // El JSON puede entregar un número (1662 → "1662"); quita un ".0" residual.
  if (s.endsWith(".0")) s = s.slice(0, -2);
  return s;
}

function parseFechaDdMmYyyy(valor: unknown): Date | null {
  const m = /^(\d{2})\/(\d{2})\/(\d{4})$/.exec(String(valor ?? "").trim());
  if (!m) return null;
  const dia = Number(m[1]);
  const mes = Number(m[2]);
  const anio = Number(m[3]);
  const d = new Date(anio, mes - 1, dia);
  if (d.getFullYear() !== anio || d.getMonth() !== mes - 1 || d.getDate() !== dia) {
    return null; // fecha calendario inválida (p. ej. 31/02)
  }
  return d;
}

function formatFechaDdMmYyyy(d: Date): string {
  const dd = String(d.getDate()).padStart(2, "0");
  const mm = String(d.getMonth() + 1).padStart(2, "0");
  return `${dd}/${mm}/${d.getFullYear()}`;
}

/**
 * Construye la línea de un caso para el cuadro de Autorizar.
 *
 * Si el caso tiene un formulario asociado (`cod_for_aso`) distinto de vacío y de
 * {0709, 1649, 4949}, agrega como fecha inicial de intereses el día siguiente a
 * `fec_doc_aso` (p. ej. `36486237|14/04/2026`). En cualquier otro caso devuelve
 * solo el `num_doc`.
 */
export function construirLineaAutorizar(fila: Record<string, unknown>): string {
  const numDoc = String(fila.num_doc ?? "").trim();
  const cod = normalizarCodForAso(fila.cod_for_aso);
  if (cod === "" || COD_FOR_ASO_SIN_FECHA.has(cod)) return numDoc;

  const fecha = parseFechaDdMmYyyy(fila.fec_doc_aso);
  if (!fecha) return numDoc; // sin fec_doc_aso utilizable, no se puede autocompletar

  fecha.setDate(fecha.getDate() + 1);
  return `${numDoc}|${formatFechaDdMmYyyy(fecha)}`;
}

type Estado = Record<string, DecisionAutorizar>;
type EstadoC64 = Record<string, DecisionC64>;

export function AutorizarPanel({
  seleccion,
  filas = [],
  onJobIniciado,
  onError,
}: Props): JSX.Element {
  const [abierto, setAbierto] = useState(false);
  const [texto, setTexto] = useState("");
  const [cargando, setCargando] = useState(false);
  const [conflictos, setConflictos] = useState<ConflictoAutorizar[]>([]);
  const [conflictosC64, setConflictosC64] = useState<ConflictoC64[]>([]);
  const [decisiones, setDecisiones] = useState<Estado>({});
  const [decisionesC64, setDecisionesC64] = useState<EstadoC64>({});
  const [lineasPend, setLineasPend] = useState<string[]>([]);
  const { ocupado, iniciar, terminar } = useTareaLock();

  function resetRevision(): void {
    setConflictos([]);
    setConflictosC64([]);
    setDecisiones({});
    setDecisionesC64({});
    setLineasPend([]);
  }

  function abrir(): void {
    // Prellenar cada línea desde las filas seleccionadas: los casos con
    // formulario asociado agregan la fecha inicial (fec_doc_aso + 1 día).
    const lineas =
      filas.length > 0
        ? filas.map(construirLineaAutorizar).filter(Boolean)
        : seleccion;
    setTexto(lineas.join("\n"));
    resetRevision();
    setAbierto(true);
  }

  function cerrar(): void {
    setAbierto(false);
    resetRevision();
  }

  function parseLineas(): string[] {
    return texto
      .split("\n")
      .map((s) => s.trim())
      .filter(Boolean);
  }

  const hayRevision = conflictos.length > 0 || conflictosC64.length > 0;

  async function lanzar(
    lineas: string[],
    decs: Estado,
    decsC64: EstadoC64,
  ): Promise<void> {
    if (!iniciar()) return; // ya hay una tarea en curso
    try {
      await procesos.autorizar(lineas, decs, decsC64);
    } catch (e) {
      terminar();
      throw e;
    }
    onJobIniciado("autorizar");
    setAbierto(false);
    resetRevision();
    // job en curso: el lock se libera al llegar job_done
  }

  async function continuar(): Promise<void> {
    const lineas = parseLineas();
    if (lineas.length === 0) {
      onError("Ingrese al menos un caso.");
      return;
    }
    setCargando(true);
    try {
      const { conflictos: c65, conflictosC64: c64 } =
        await procesos.autorizarPreCheck(lineas);
      if (c65.length === 0 && c64.length === 0) {
        await lanzar(lineas, {}, {});
        return;
      }
      const inicial: Estado = {};
      for (const c of c65) inicial[c.num_doc] = { accion: "confirmar" };
      // C64 no tiene default válido: el usuario debe elegir G58 o valor manual.
      const inicialC64: EstadoC64 = {};
      for (const c of c64)
        inicialC64[c.num_doc] = { accion: "aplicar_g58", valor: null };
      setConflictos(c65);
      setConflictosC64(c64);
      setDecisiones(inicial);
      setDecisionesC64(inicialC64);
      setLineasPend(lineas);
    } catch (e) {
      onError(String(e));
    } finally {
      setCargando(false);
    }
  }

  function setAccion(
    numDoc: string,
    accion: DecisionAutorizar["accion"],
  ): void {
    setDecisiones((prev) => ({
      ...prev,
      [numDoc]: { accion, valor: accion === "aplicar_valor" ? 0 : null },
    }));
  }

  function setValor(numDoc: string, valor: number): void {
    setDecisiones((prev) => ({
      ...prev,
      [numDoc]: { accion: "aplicar_valor", valor },
    }));
  }

  function setAccionC64(
    numDoc: string,
    accion: DecisionC64["accion"],
  ): void {
    setDecisionesC64((prev) => ({
      ...prev,
      [numDoc]: { accion, valor: accion === "aplicar_valor" ? 0 : null },
    }));
  }

  function setValorC64(numDoc: string, valor: number): void {
    setDecisionesC64((prev) => ({
      ...prev,
      [numDoc]: { accion: "aplicar_valor", valor },
    }));
  }

  const decisionesC65Validas = conflictos.every((c) => {
    const d = decisiones[c.num_doc];
    if (!d) return false;
    if (d.accion === "aplicar_valor") return (d.valor ?? 0) > 0;
    return true;
  });

  const decisionesC64Validas = conflictosC64.every((c) => {
    const d = decisionesC64[c.num_doc];
    if (!d) return false;
    if (d.accion === "aplicar_valor") return (d.valor ?? 0) > 0;
    return true; // aplicar_g58 siempre válido
  });

  const decisionesValidas = decisionesC65Validas && decisionesC64Validas;

  async function confirmarRevision(): Promise<void> {
    setCargando(true);
    try {
      await lanzar(lineasPend, decisiones, decisionesC64);
    } catch (e) {
      onError(String(e));
    } finally {
      setCargando(false);
    }
  }

  return (
    <>
      <button
        className={BTN}
        disabled={seleccion.length === 0 || ocupado}
        onClick={abrir}
      >
        Autorizar
      </button>
      {abierto ? (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/30"
          onClick={() => cerrar()}
        >
          <div
            className="w-[560px] rounded bg-white p-4 shadow-lg"
            onClick={(e) => e.stopPropagation()}
          >
            {!hayRevision ? (
              <>
                <h2 className="mb-1 text-base font-semibold text-slate-800">
                  Autorizar casos
                </h2>
                <p className="mb-2 text-xs text-slate-500">
                  Un caso por línea. Formatos admitidos:
                  <br />
                  <code>3154526</code> · <code>3154526|15/03/2026</code> ·{" "}
                  <code>3154526|10/02/2026|15/03/2026</code>
                  <br />
                  Con una sola fecha: anterior a hoy = fecha inicial; hoy o
                  posterior = fecha final.
                </p>
                <textarea
                  value={texto}
                  onChange={(e) => setTexto(e.target.value)}
                  rows={10}
                  className="w-full rounded border p-2 font-mono text-sm"
                  aria-label="Casos a autorizar"
                />
                <div className="mt-3 flex justify-end gap-2">
                  <button
                    onClick={() => cerrar()}
                    className="rounded border px-3 py-1 text-sm"
                  >
                    Cancelar
                  </button>
                  <button
                    disabled={cargando}
                    onClick={() => void continuar()}
                    className="rounded bg-blue-600 px-3 py-1 text-sm text-white disabled:opacity-50"
                  >
                    {cargando ? "Revisando…" : "Autorizar"}
                  </button>
                </div>
              </>
            ) : (
              <>
                <h2 className="mb-1 text-base font-semibold text-slate-800">
                  Revisar montos antes de autorizar
                </h2>
                <div className="max-h-[55vh] space-y-4 overflow-y-auto">
                  {conflictosC64.length > 0 ? (
                    <div>
                      <p className="mb-1 text-xs font-semibold text-slate-600">
                        Importe autorizado (C64) en 0
                      </p>
                      <p className="mb-2 text-xs text-slate-500">
                        Estos casos están autorizados pero el importe autorizado
                        (C64) es 0. Debe corregir cada uno (no se puede dejar 0).
                      </p>
                      <div className="space-y-3">
                        {conflictosC64.map((c) => {
                          const d = decisionesC64[c.num_doc];
                          return (
                            <div
                              key={`c64-${c.num_doc}`}
                              className="rounded border p-2 text-sm"
                            >
                              <div className="font-medium text-slate-800">
                                {c.num_doc} · {c.nombre} · per. {c.per_doc}
                              </div>
                              <label className="mr-3 text-xs">
                                <input
                                  type="radio"
                                  name={`c64-${c.num_doc}`}
                                  checked={d?.accion === "aplicar_g58"}
                                  onChange={() =>
                                    setAccionC64(c.num_doc, "aplicar_g58")
                                  }
                                />{" "}
                                Llenar con G58 (
                                {c.g58.toLocaleString("es-PE", {
                                  minimumFractionDigits: 2,
                                })}
                                )
                              </label>
                              <label className="text-xs">
                                <input
                                  type="radio"
                                  name={`c64-${c.num_doc}`}
                                  checked={d?.accion === "aplicar_valor"}
                                  onChange={() =>
                                    setAccionC64(c.num_doc, "aplicar_valor")
                                  }
                                />{" "}
                                Monto manual:
                              </label>
                              {d?.accion === "aplicar_valor" ? (
                                <input
                                  type="number"
                                  min={0}
                                  step="0.01"
                                  value={d.valor ?? 0}
                                  onChange={(e) =>
                                    setValorC64(c.num_doc, Number(e.target.value))
                                  }
                                  className="ml-2 w-28 rounded border px-1 text-xs"
                                />
                              ) : null}
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  ) : null}

                  {conflictos.length > 0 ? (
                    <div>
                      <p className="mb-1 text-xs font-semibold text-slate-600">
                        Monto a aplicar (C65)
                      </p>
                      <p className="mb-2 text-xs text-slate-500">
                        Estos casos autorizados tienen deuda (C89) pero el monto a
                        aplicar (C65) es 0. Confirme o corrija cada uno.
                      </p>
                      <div className="space-y-3">
                        {conflictos.map((c) => {
                          const d = decisiones[c.num_doc];
                          return (
                            <div
                              key={`c65-${c.num_doc}`}
                              className="rounded border p-2 text-sm"
                            >
                              <div className="font-medium text-slate-800">
                                {c.num_doc} · {c.nombre} · per. {c.per_doc}
                              </div>
                              <div className="mb-1 text-xs text-slate-500">
                                Monto deuda (C89):{" "}
                                {c.c89.toLocaleString("es-PE", {
                                  minimumFractionDigits: 2,
                                })}
                              </div>
                              <label className="mr-3 text-xs">
                                <input
                                  type="radio"
                                  name={`acc-${c.num_doc}`}
                                  checked={d?.accion === "confirmar"}
                                  onChange={() => setAccion(c.num_doc, "confirmar")}
                                />{" "}
                                Es correcto (no aplicar)
                              </label>
                              <label className="mr-3 text-xs">
                                <input
                                  type="radio"
                                  name={`acc-${c.num_doc}`}
                                  checked={d?.accion === "aplicar_c89"}
                                  onChange={() => setAccion(c.num_doc, "aplicar_c89")}
                                />{" "}
                                Aplicar C89 como C65
                              </label>
                              <label className="text-xs">
                                <input
                                  type="radio"
                                  name={`acc-${c.num_doc}`}
                                  checked={d?.accion === "aplicar_valor"}
                                  onChange={() =>
                                    setAccion(c.num_doc, "aplicar_valor")
                                  }
                                />{" "}
                                Aplicar valor:
                              </label>
                              {d?.accion === "aplicar_valor" ? (
                                <input
                                  type="number"
                                  min={0}
                                  step="0.01"
                                  value={d.valor ?? 0}
                                  onChange={(e) =>
                                    setValor(c.num_doc, Number(e.target.value))
                                  }
                                  className="ml-2 w-28 rounded border px-1 text-xs"
                                />
                              ) : null}
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  ) : null}
                </div>
                <div className="mt-3 flex justify-end gap-2">
                  <button
                    onClick={() => cerrar()}
                    className="rounded border px-3 py-1 text-sm"
                  >
                    Cancelar
                  </button>
                  <button
                    disabled={cargando || !decisionesValidas}
                    onClick={() => void confirmarRevision()}
                    className="rounded bg-blue-600 px-3 py-1 text-sm text-white disabled:opacity-50"
                  >
                    {cargando ? "Procesando…" : "Continuar"}
                  </button>
                </div>
              </>
            )}
          </div>
        </div>
      ) : null}
    </>
  );
}

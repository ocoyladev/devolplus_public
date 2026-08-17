import { useCallback, useEffect, useState } from "react";

import { datos } from "../../api/acciones";
import {
  borrarBd,
  borrarCaso,
  borrarDescargas,
  ejecutarDescargas,
  eliminarDescargas,
  listarDescargas,
  type DescargaCola,
} from "../../api/mantenimiento";
import { useTareaLock } from "../tareas/tareaLock";
import { ArchivarEchasquiPanel } from "../archivo-echasqui/ArchivarEchasquiPanel";
import type { EstadoFirmaAuto } from "../entorno/useFirmaAuto";

interface Props {
  onAviso: (mensaje: string) => void;
  onJobIniciado: (kind: string) => void;
  onRecalcularPantalla: () => Promise<EstadoFirmaAuto>;
}

const CONFIRM_BD = "BORRAR BD";
const CONFIRM_DESC = "BORRAR DESCARGAS";

/** True si la descarga es de planeamiento (bloqueable por horario). */
function esPlaneamiento(d: DescargaCola): boolean {
  return (d.tipo_descarga ?? "").toUpperCase() === "PLANEAMIENTO";
}

export function MantenimientoPanel({
  onAviso,
  onJobIniciado,
  onRecalcularPantalla,
}: Props): JSX.Element {
  const [seccion, setSeccion] = useState<"descargas" | "borrado" | null>(null);
  const [menuAbierto, setMenuAbierto] = useState(false);
  const [echasquiAbierto, setEchasquiAbierto] = useState(false);
  const [descargas, setDescargas] = useState<DescargaCola[]>([]);
  const [sel, setSel] = useState<Set<number>>(new Set());
  const [confirmBd, setConfirmBd] = useState("");
  const [confirmDesc, setConfirmDesc] = useState("");
  const [borrarNumDoc, setBorrarNumDoc] = useState("");
  const [borrarCarpetaCaso, setBorrarCarpetaCaso] = useState(false);
  // Si es false, las descargas de planeamiento están bloqueadas por horario.
  const [planeamientoOk, setPlaneamientoOk] = useState(true);
  const { ocupado, iniciar, terminar } = useTareaLock();

  const refrescar = useCallback(() => {
    listarDescargas()
      .then((r) => setDescargas(r.descargas))
      .catch((e: unknown) => onAviso(String(e)));
  }, [onAviso]);

  useEffect(() => {
    if (seccion === "descargas") {
      setSel(new Set());
      refrescar();
      void datos.planeamientoEstado().then(setPlaneamientoOk);
    }
  }, [seccion, refrescar]);

  // Una fila de planeamiento está bloqueada (no seleccionable) en horario laboral.
  const bloqueada = useCallback(
    (d: DescargaCola): boolean => esPlaneamiento(d) && !planeamientoOk,
    [planeamientoOk],
  );

  function toggle(id: number): void {
    setSel((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  function toggleTodos(): void {
    // "Seleccionar todas" ignora las filas bloqueadas por horario (planeamiento).
    const seleccionables = descargas.filter((d) => !bloqueada(d));
    setSel((prev) =>
      prev.size === seleccionables.length
        ? new Set()
        : new Set(seleccionables.map((d) => d.id)),
    );
  }

  async function eliminarSel(): Promise<void> {
    const ids = [...sel];
    if (ids.length === 0) return;
    try {
      const r = await eliminarDescargas(ids);
      onAviso(`✓ ${r.eliminadas} descarga(s) eliminada(s)`);
      setSel(new Set());
      refrescar();
    } catch (e) {
      onAviso(String(e));
    }
  }

  async function ejecutarSel(): Promise<void> {
    // Excluir filas bloqueadas por horario (planeamiento) por si quedaron marcadas.
    const bloqueadas = new Set(descargas.filter(bloqueada).map((d) => d.id));
    const ids = [...sel].filter((id) => !bloqueadas.has(id));
    if (ids.length === 0) return;
    if (!iniciar()) return; // ya hay una tarea en curso
    try {
      await ejecutarDescargas(ids);
      onJobIniciado("descarga_seleccionada");
      setSeccion(null);
      // job en curso: el lock se libera al llegar job_done
    } catch (e) {
      onAviso(String(e));
      terminar();
    }
  }

  async function ejecutarBorrarBd(): Promise<void> {
    try {
      await borrarBd();
      onAviso("✓ Base de datos borrada");
      setConfirmBd("");
    } catch (e) {
      onAviso(String(e));
    }
  }

  async function ejecutarBorrarDescargas(): Promise<void> {
    try {
      await borrarDescargas();
      onAviso("✓ Cola de descargas borrada");
      setConfirmDesc("");
      refrescar();
    } catch (e) {
      onAviso(String(e));
    }
  }

  async function ejecutarBorrarCaso(): Promise<void> {
    const nd = borrarNumDoc.trim();
    if (!nd) return;
    try {
      const r = await borrarCaso(nd, borrarCarpetaCaso);
      const total = Object.values(r.eliminadas).reduce((a, b) => a + b, 0);
      onAviso(
        `✓ Caso ${nd}: ${total} fila(s) eliminada(s)` +
          (r.carpeta_borrada ? " · carpeta borrada" : ""),
      );
      setBorrarNumDoc("");
      setBorrarCarpetaCaso(false);
    } catch (e) {
      onAviso(String(e));
    }
  }

  async function recalcularPantalla(): Promise<void> {
    setMenuAbierto(false);
    const e = await onRecalcularPantalla();
    onAviso(
      e.disponible
        ? `✓ Firma automática disponible${e.perfil ? ` (perfil ${e.perfil})` : ""}`
        : e.motivo || "No se pudo detectar la pantalla.",
    );
  }

  const seleccionables = descargas.filter((d) => !bloqueada(d));
  const todosMarcados =
    seleccionables.length > 0 && sel.size === seleccionables.length;

  return (
    <>
      <div className="relative">
        <button
          onClick={() => setMenuAbierto((o) => !o)}
          disabled={ocupado}
          title="Mantenimiento"
          aria-label="Mantenimiento"
          className="rounded border px-2 py-1 text-sm hover:bg-slate-100 disabled:opacity-50"
        >
          ⚙
        </button>
        {menuAbierto ? (
          <>
            <div className="fixed inset-0 z-40" onClick={() => setMenuAbierto(false)} />
            <div className="absolute right-0 z-50 mt-1 w-44 rounded border bg-white text-sm shadow-lg">
              <button
                className="block w-full px-3 py-1.5 text-left hover:bg-slate-100"
                onClick={() => { setMenuAbierto(false); setSeccion("descargas"); }}
              >
                Descargas
              </button>
              <button
                className="block w-full px-3 py-1.5 text-left hover:bg-slate-100"
                onClick={() => { setMenuAbierto(false); setEchasquiAbierto(true); }}
              >
                ECHASQUI
              </button>
              <button
                className="block w-full px-3 py-1.5 text-left hover:bg-slate-100"
                onClick={() => { setMenuAbierto(false); setSeccion("borrado"); }}
              >
                Borrado
              </button>
              <button
                className="block w-full px-3 py-1.5 text-left hover:bg-slate-100"
                onClick={() => void recalcularPantalla()}
              >
                Recalcular pantalla
              </button>
            </div>
          </>
        ) : null}
      </div>
      {seccion !== null ? (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/30"
          onClick={() => setSeccion(null)}
        >
          <div
            className="max-h-[85vh] w-[680px] max-w-[95vw] overflow-auto rounded bg-white p-4 shadow-lg"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="mb-3 flex items-center justify-between">
              <h2 className="text-base font-semibold text-slate-800">
                {seccion === "descargas" ? "Mantenimiento — Descargas" : "Mantenimiento — Borrado"}
              </h2>
              <button onClick={() => setSeccion(null)} className="text-slate-500">
                ✕
              </button>
            </div>

            {seccion === "descargas" ? (
            <section className="mb-4">
              <div className="mb-2 flex items-center justify-between">
                <h3 className="text-sm font-semibold text-slate-700">
                  Cola de descargas ({descargas.length})
                </h3>
                <button
                  onClick={refrescar}
                  className="rounded border px-2 py-0.5 text-xs hover:bg-slate-100"
                >
                  ↻ Refrescar
                </button>
              </div>
              {descargas.length === 0 ? (
                <p className="text-sm text-slate-400">No hay descargas en cola.</p>
              ) : (
                <div className="max-h-64 overflow-auto rounded border">
                  <table className="w-full text-left text-xs">
                    <thead className="sticky top-0 bg-slate-100">
                      <tr>
                        <th className="p-1.5">
                          <input
                            type="checkbox"
                            checked={todosMarcados}
                            onChange={toggleTodos}
                            aria-label="Seleccionar todas"
                          />
                        </th>
                        <th className="p-1.5">N° Doc</th>
                        <th className="p-1.5">RUC</th>
                        <th className="p-1.5">Tipo</th>
                        <th className="p-1.5">Parámetro</th>
                        <th className="p-1.5">Estado</th>
                      </tr>
                    </thead>
                    <tbody>
                      {descargas.map((d) => {
                        const off = bloqueada(d);
                        return (
                          <tr
                            key={d.id}
                            className={
                              off
                                ? "border-t bg-slate-100 text-slate-400"
                                : "border-t odd:bg-slate-50"
                            }
                            title={
                              off
                                ? "Planeamiento deshabilitado en horario laboral (L–V 08:00–17:00)."
                                : undefined
                            }
                          >
                            <td className="p-1.5">
                              <input
                                type="checkbox"
                                checked={sel.has(d.id)}
                                disabled={off}
                                onChange={() => toggle(d.id)}
                                aria-label={`Seleccionar ${d.id}`}
                              />
                            </td>
                            <td className="p-1.5">{d.num_doc}</td>
                            <td className="p-1.5">{d.ruc}</td>
                            <td className="p-1.5">
                              {d.tipo_servicio}/{d.tipo_descarga}
                              {off ? " ⏸" : ""}
                            </td>
                            <td className="p-1.5 font-mono">{d.parametro}</td>
                            <td className="p-1.5">{d.estado}</td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              )}
              <div className="mt-2 flex gap-2">
                <button
                  onClick={() => void ejecutarSel()}
                  disabled={sel.size === 0}
                  className="rounded bg-blue-600 px-3 py-1 text-sm text-white disabled:opacity-40"
                >
                  Ejecutar seleccionadas ({sel.size})
                </button>
                <button
                  onClick={() => void eliminarSel()}
                  disabled={sel.size === 0}
                  className="rounded border border-red-300 px-3 py-1 text-sm text-red-700 hover:bg-red-50 disabled:opacity-40"
                >
                  Eliminar seleccionadas
                </button>
              </div>
            </section>
            ) : null}

            {seccion === "borrado" ? (
            <section className="rounded border border-red-200 bg-red-50 p-3">
              <h3 className="mb-1 text-sm font-semibold text-red-700">Zona peligrosa</h3>
              <p className="mb-3 text-xs text-red-600">
                Estas acciones son irreversibles. Escriba el texto exacto para habilitar
                cada botón.
              </p>

              <div className="mb-3">
                <p className="mb-1 text-sm text-slate-700">
                  Borrar base de datos (casos, BD y seguimiento)
                </p>
                <div className="flex gap-2">
                  <input
                    value={confirmBd}
                    onChange={(e) => setConfirmBd(e.target.value)}
                    placeholder={`Escriba: ${CONFIRM_BD}`}
                    className="flex-1 rounded border p-1.5 text-sm"
                  />
                  <button
                    onClick={() => void ejecutarBorrarBd()}
                    disabled={confirmBd !== CONFIRM_BD}
                    className="rounded bg-red-600 px-3 py-1 text-sm text-white disabled:opacity-40"
                  >
                    Borrar BD
                  </button>
                </div>
              </div>

              <div>
                <p className="mb-1 text-sm text-slate-700">
                  Borrar toda la cola de descargas
                </p>
                <div className="flex gap-2">
                  <input
                    value={confirmDesc}
                    onChange={(e) => setConfirmDesc(e.target.value)}
                    placeholder={`Escriba: ${CONFIRM_DESC}`}
                    className="flex-1 rounded border p-1.5 text-sm"
                  />
                  <button
                    onClick={() => void ejecutarBorrarDescargas()}
                    disabled={confirmDesc !== CONFIRM_DESC}
                    className="rounded bg-red-600 px-3 py-1 text-sm text-white disabled:opacity-40"
                  >
                    Borrar descargas
                  </button>
                </div>
              </div>

              <div className="mt-3 border-t border-red-200 pt-3">
                <p className="mb-1 text-sm text-slate-700">
                  Borrar un caso específico (BD y, opcionalmente, su carpeta)
                </p>
                <div className="flex gap-2">
                  <input
                    value={borrarNumDoc}
                    onChange={(e) => setBorrarNumDoc(e.target.value)}
                    placeholder="Escriba el num_doc a borrar"
                    className="flex-1 rounded border p-1.5 text-sm"
                  />
                  <button
                    onClick={() => void ejecutarBorrarCaso()}
                    disabled={borrarNumDoc.trim() === ""}
                    className="rounded bg-red-600 px-3 py-1 text-sm text-white disabled:opacity-40"
                  >
                    Borrar caso
                  </button>
                </div>
                <label className="mt-1 flex items-center gap-2 text-xs text-red-600">
                  <input
                    type="checkbox"
                    checked={borrarCarpetaCaso}
                    onChange={(e) => setBorrarCarpetaCaso(e.target.checked)}
                  />
                  Borrar también la carpeta del caso (descargas o archivo)
                </label>
              </div>
            </section>
            ) : null}
          </div>
        </div>
      ) : null}
      <ArchivarEchasquiPanel
        abierto={echasquiAbierto}
        onCerrar={() => setEchasquiAbierto(false)}
        onAviso={onAviso}
        onJobIniciado={onJobIniciado}
      />
    </>
  );
}

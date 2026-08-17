import { useCallback, useEffect, useState } from "react";

import {
  listarArchivarRepositorio,
  eliminarArchivarRepositorio,
  ejecutarArchivarRepositorio,
  type PendienteArchivoRepositorio,
} from "../../api/mantenimiento";
import { useTareaLock } from "../tareas/tareaLock";

interface Props {
  abierto: boolean;
  onCerrar: () => void;
  onAviso: (mensaje: string) => void;
  onJobIniciado: (kind: string) => void;
}

export function ArchivarRepositorioPanel({
  abierto,
  onCerrar,
  onAviso,
  onJobIniciado,
}: Props): JSX.Element | null {
  const [filas, setFilas] = useState<PendienteArchivoRepositorio[]>([]);
  const [sel, setSel] = useState<Set<number>>(new Set());
  const { ocupado, iniciar, terminar } = useTareaLock();

  const refrescar = useCallback(() => {
    listarArchivarRepositorio()
      .then((r) => setFilas(r.pendientes))
      .catch((e: unknown) => onAviso(String(e)));
  }, [onAviso]);

  useEffect(() => {
    if (abierto) {
      setSel(new Set());
      refrescar();
    }
  }, [abierto, refrescar]);

  function toggle(id: number): void {
    setSel((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  function toggleTodos(): void {
    setSel((prev) =>
      prev.size === filas.length ? new Set() : new Set(filas.map((f) => f.id)),
    );
  }

  const todosMarcados = filas.length > 0 && sel.size === filas.length;

  async function eliminarSel(): Promise<void> {
    const ids = [...sel];
    if (ids.length === 0) return;
    try {
      const r = await eliminarArchivarRepositorio(ids);
      onAviso(`✓ ${r.eliminadas} pendiente(s) eliminado(s)`);
      setSel(new Set());
      refrescar();
    } catch (e) {
      onAviso(String(e));
    }
  }

  async function ejecutarSel(): Promise<void> {
    const ids = [...sel];
    if (ids.length === 0) return;
    if (!iniciar()) return; // lock global "una tarea a la vez"
    try {
      await ejecutarArchivarRepositorio(ids);
      onJobIniciado("archivar_repositorio");
      onCerrar();
    } catch (e) {
      onAviso(String(e));
      terminar();
    }
  }

  if (!abierto) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/30"
      onClick={() => onCerrar()}
    >
      <div
        className="max-h-[85vh] w-[720px] max-w-[95vw] overflow-auto rounded bg-white p-4 shadow-lg"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="mb-3 flex items-center justify-between">
          <h2 className="text-base font-semibold text-slate-800">
            Archivar REPOSITORIO — pendientes ({filas.length})
          </h2>
          <button onClick={() => onCerrar()} className="text-slate-500">
            ✕
          </button>
        </div>

        {filas.length === 0 ? (
          <p className="text-sm text-slate-400">
            No hay repositorio pendientes de archivar.
          </p>
        ) : (
          <div className="max-h-[55vh] overflow-auto rounded border">
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
                  <th className="p-1.5">Expediente</th>
                  <th className="p-1.5">N° RI</th>
                  <th className="p-1.5">Estado</th>
                  <th className="p-1.5">Motivo</th>
                </tr>
              </thead>
              <tbody>
                {filas.map((f) => (
                  <tr key={f.id} className="border-t odd:bg-slate-50">
                    <td className="p-1.5">
                      <input
                        type="checkbox"
                        checked={sel.has(f.id)}
                        onChange={() => toggle(f.id)}
                        aria-label={`Seleccionar ${f.id}`}
                      />
                    </td>
                    <td className="p-1.5">{f.num_doc}</td>
                    <td className="p-1.5">{f.ruc}</td>
                    <td className="p-1.5">
                      {f.aduana}-{f.urd}-{f.anio}-{f.nroexpedi}
                    </td>
                    <td className="p-1.5">{f.num_ri}</td>
                    <td className="p-1.5">{f.estado}</td>
                    <td className="p-1.5 text-red-600">{f.mensaje}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        <div className="mt-3 flex gap-2">
          <button
            onClick={() => void ejecutarSel()}
            disabled={sel.size === 0 || ocupado}
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
          <button
            onClick={refrescar}
            className="ml-auto rounded border px-3 py-1 text-sm hover:bg-slate-100"
          >
            ↻ Refrescar
          </button>
        </div>
      </div>
    </div>
  );
}

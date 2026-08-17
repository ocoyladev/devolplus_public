import { useState } from "react";

import { sync } from "../../api/acciones";
import { useLanzarTarea, useTareaLock } from "../tareas/tareaLock";

interface Props {
  onJobIniciado: (kind: string) => void;
  onError: (mensaje: string) => void;
}

export function SyncMenu({ onJobIniciado, onError }: Props): JSX.Element {
  const [open, setOpen] = useState(false);
  const { ocupado } = useTareaLock();
  const lanzar = useLanzarTarea();

  function run(kind: string, fn: () => Promise<unknown>): void {
    setOpen(false);
    void lanzar(kind, fn, onJobIniciado, onError);
  }

  return (
    <div className="relative">
      <button
        onClick={() => setOpen((o) => !o)}
        disabled={ocupado}
        className="rounded border px-3 py-1 text-sm hover:bg-slate-100 disabled:opacity-50"
      >
        Actualizar ▾
      </button>
      {open ? (
        <>
          <div className="fixed inset-0 z-40" onClick={() => setOpen(false)} />
          <div className="absolute right-0 z-50 mt-1 w-52 rounded border bg-white text-sm shadow-lg">
            <button
              onClick={() => run("sync_macros", () => sync.macros())}
              className="block w-full px-3 py-1.5 text-left hover:bg-slate-100"
            >
              Desde MACROs
            </button>
            <button
              onClick={() => run("sync_remota", () => sync.remota())}
              className="block w-full px-3 py-1.5 text-left hover:bg-slate-100"
            >
              Según BD remota
            </button>
          </div>
        </>
      ) : null}
    </div>
  );
}

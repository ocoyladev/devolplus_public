import { type ReactNode, useState } from "react";

import { procesos } from "../../api/acciones";
import { useLanzarTarea, useTareaLock } from "../tareas/tareaLock";
import { AutorizarPanel } from "./AutorizarPanel";
import { MasAccionesMenu } from "./MasAccionesMenu";

interface Props {
  seleccion: string[];
  filas: Record<string, unknown>[];
  firmaAutoDisponible: boolean;
  firmaAutoMotivo: string;
  archivo: boolean;
  onJobIniciado: (kind: string) => void;
  onError: (mensaje: string) => void;
  menuCaso?: ReactNode;
}

const BTN =
  "rounded border px-3 py-1 text-sm disabled:opacity-40 disabled:cursor-not-allowed hover:bg-slate-100";

export function Toolbar({
  seleccion,
  filas,
  firmaAutoDisponible,
  firmaAutoMotivo,
  archivo,
  onJobIniciado,
  onError,
  menuCaso,
}: Props): JSX.Element {
  const { ocupado } = useTareaLock();
  const lanzar = useLanzarTarea();
  const sinSeleccion = seleccion.length === 0;
  const bloqueado = sinSeleccion || ocupado;
  const [firmaAuto, setFirmaAuto] = useState(false);

  function run(kind: string, fn: () => Promise<string>): void {
    void lanzar(kind, fn, onJobIniciado, onError);
  }

  return (
    <div className="flex items-center gap-2 border-b bg-white px-4 py-2">
      <button
        className={BTN}
        disabled={bloqueado}
        onClick={() => run("archivar", () => procesos.archivar(seleccion))}
      >
        Archivar
      </button>
      <button
        className={BTN}
        disabled={bloqueado}
        onClick={() => run("recuperar", () => procesos.recuperar(seleccion))}
      >
        Recuperar
      </button>
      <button
        className={BTN}
        disabled={bloqueado}
        onClick={() => run("papeles_trabajo", () => procesos.papeles_trabajo(seleccion))}
      >
        Generar PAPELES_TRABAJO
      </button>
      <div className="flex items-center gap-1">
        <button
          className={BTN}
          disabled={bloqueado}
          onClick={() =>
            run("carga_expedientes", () =>
              procesos.cargaExpedientes(seleccion, firmaAuto && firmaAutoDisponible),
            )
          }
        >
          Cargar expediente electrónico
        </button>
        <label
          className={`flex items-center ${
            firmaAutoDisponible ? "cursor-pointer" : "cursor-not-allowed opacity-40"
          }`}
          title={firmaAutoMotivo}
        >
          <input
            type="checkbox"
            className="h-4 w-4"
            checked={firmaAuto && firmaAutoDisponible}
            disabled={!firmaAutoDisponible}
            onChange={(e) => setFirmaAuto(e.target.checked)}
            aria-label="Activar firma automática por coordenadas"
          />
        </label>
      </div>
      <button
        className={BTN}
        disabled={bloqueado}
        onClick={() => run("archivar_repositorio", () => procesos.archivarRepositorio(seleccion))}
      >
        Archivar REPOSITORIO
      </button>
      <AutorizarPanel
        seleccion={seleccion}
        filas={filas}
        onJobIniciado={onJobIniciado}
        onError={onError}
      />
      <MasAccionesMenu filas={filas} archivo={archivo} onJobIniciado={onJobIniciado} onError={onError} />
      {menuCaso ? <div className="ml-2">{menuCaso}</div> : null}
      <span className="ml-auto text-sm text-slate-500">
        {seleccion.length} seleccionado(s)
      </span>
    </div>
  );
}

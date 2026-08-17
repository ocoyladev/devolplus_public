import { useEffect, useState } from "react";

import { generarCarta, generarRi, listarModelos } from "../../api/generar";
import { useTareaLock } from "../tareas/tareaLock";

interface Props {
  tipo: "carta" | "ri";
  row: Record<string, unknown>;
  archivo?: boolean;
  onClose: () => void;
  onJobIniciado: (kind: string) => void;
  onError: (mensaje: string) => void;
}

export function GenerarDocPanel({
  tipo,
  row,
  archivo = false,
  onClose,
  onJobIniciado,
  onError,
}: Props): JSX.Element {
  const [modelos, setModelos] = useState<string[]>([]);
  const [seleccion, setSeleccion] = useState<string[]>([]); // carta: varios; ri: uno
  const [plazo, setPlazo] = useState("3");
  const [cargando, setCargando] = useState(true);
  const { iniciar, terminar } = useTareaLock();

  useEffect(() => {
    listarModelos(tipo)
      .then(setModelos)
      .catch((e: unknown) => onError(String(e)))
      .finally(() => setCargando(false));
  }, [tipo, onError]);

  function toggle(nombre: string): void {
    if (tipo === "ri") {
      setSeleccion([nombre]);
      return;
    }
    setSeleccion((prev) =>
      prev.includes(nombre) ? prev.filter((n) => n !== nombre) : [...prev, nombre],
    );
  }

  async function generar(): Promise<void> {
    let kind: string;
    let call: () => Promise<string>;
    if (tipo === "carta") {
      kind = "generar_carta";
      call = () => generarCarta(row, seleccion, parseInt(plazo, 10) || 3, archivo);
    } else {
      if (seleccion.length === 0) {
        onError("Seleccione un modelo de RI.");
        return;
      }
      const numRi = String(row.num_ri ?? row.ri ?? "").trim();
      if (!numRi) {
        const continuar = window.confirm(
          "El caso no tiene N° de RI. ¿Generar de todas formas?\n" +
            "El documento saldrá sin ese dato y el archivo se nombrará como RUC_0.docx.",
        );
        if (!continuar) return;
      }
      kind = "generar_ri";
      call = () => generarRi(row, seleccion[0], numRi || null);
    }
    if (!iniciar()) return; // ya hay una tarea en curso
    try {
      await call();
      onJobIniciado(kind);
      onClose();
      // job en curso: el lock se libera al llegar job_done
    } catch (e) {
      onError(String(e));
      terminar();
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/30"
      onClick={onClose}
    >
      <div
        className="max-h-[85vh] w-[460px] overflow-auto rounded bg-white p-4 shadow-lg"
        onClick={(e) => e.stopPropagation()}
      >
        <h2 className="mb-2 text-base font-semibold text-slate-800">
          Generar {tipo === "carta" ? "Carta" : "RI"}
        </h2>

        {cargando ? (
          <p className="text-sm text-slate-400">Cargando modelos…</p>
        ) : modelos.length === 0 ? (
          <p className="text-sm text-red-600">
            No se encontraron modelos en RESOURCES/
            {tipo === "carta" ? "MODELOS_CARTA" : "MODELOS_RI"}.
          </p>
        ) : (
          <div className="mb-3 max-h-72 overflow-auto rounded border p-2">
            {modelos.map((m) => (
              <label key={m} className="mb-1 flex items-center gap-2 text-sm">
                <input
                  type={tipo === "carta" ? "checkbox" : "radio"}
                  name="modelo"
                  checked={seleccion.includes(m)}
                  onChange={() => toggle(m)}
                />
                {m.replace(/\.docx$/i, "")}
              </label>
            ))}
          </div>
        )}

        {tipo === "carta" ? (
          <label className="mb-3 block text-sm">
            <span className="text-slate-600">Plazo (días)</span>
            <input
              value={plazo}
              onChange={(e) => setPlazo(e.target.value)}
              className="ml-2 w-20 rounded border p-1 text-sm"
            />
          </label>
        ) : null}

        <div className="flex justify-end gap-2">
          <button onClick={onClose} className="rounded border px-3 py-1 text-sm">
            Cancelar
          </button>
          <button
            onClick={() => void generar()}
            className="rounded bg-blue-600 px-3 py-1 text-sm text-white"
          >
            Generar
          </button>
        </div>
      </div>
    </div>
  );
}

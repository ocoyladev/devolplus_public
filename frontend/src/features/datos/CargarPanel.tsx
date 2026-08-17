import { useEffect, useState } from "react";

import { datos } from "../../api/acciones";
import { useTareaLock } from "../tareas/tareaLock";

interface Props {
  onJobIniciado: (kind: string) => void;
  onError: (mensaje: string) => void;
}

// Tipos de carga que dependen de las descargas de planeamiento (deshabilitados
// en horario laboral: L–V 08:00–17:00 hora de Lima).
const TIPOS_PLANEAMIENTO = new Set(["rsirat"]);

export function CargarPanel({ onJobIniciado, onError }: Props): JSX.Element {
  const [abierto, setAbierto] = useState(false);
  const [texto, setTexto] = useState("");
  const [enviando, setEnviando] = useState(false);
  // Si es false, el 'Archivo RSIRAT' está deshabilitado por horario.
  const [planeamientoOk, setPlaneamientoOk] = useState(true);
  const { ocupado, iniciar, terminar } = useTareaLock();

  useEffect(() => {
    if (!abierto) return;
    void datos.planeamientoEstado().then(setPlaneamientoOk);
  }, [abierto]);

  async function subir(tipo: string, file: File | null): Promise<void> {
    if (!file) return;
    if (!iniciar()) return; // ya hay una tarea en curso
    try {
      await datos.cargarArchivo(tipo, file);
      onJobIniciado(`cargar_${tipo}`);
      setAbierto(false);
      // job en curso: el lock se libera al llegar job_done
    } catch (e) {
      onError(String(e));
      terminar();
    }
  }

  async function cargar(): Promise<void> {
    const numDocs = texto
      .split("\n")
      .map((s) => s.trim())
      .filter(Boolean);
    if (numDocs.length === 0) {
      onError("Ingrese al menos un número de documento.");
      return;
    }
    if (!iniciar()) return; // ya hay una tarea en curso
    setEnviando(true);
    try {
      await datos.cargar(numDocs);
      onJobIniciado("cargar_datos");
      setAbierto(false);
      setTexto("");
      // job en curso: el lock se libera al llegar job_done
    } catch (e) {
      onError(String(e));
      terminar();
    } finally {
      setEnviando(false);
    }
  }

  return (
    <>
      <button
        onClick={() => setAbierto(true)}
        disabled={ocupado}
        className="rounded border px-3 py-1 text-sm hover:bg-slate-100 disabled:opacity-50"
      >
        Cargar datos
      </button>
      {abierto ? (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/30"
          onClick={() => setAbierto(false)}
        >
          <div
            className="w-[480px] rounded bg-white p-4 shadow-lg"
            onClick={(e) => e.stopPropagation()}
          >
            <h2 className="mb-1 text-base font-semibold text-slate-800">
              Cargar casos por lista
            </h2>
            <p className="mb-2 text-sm text-slate-500">
              Ingrese los números de documento (uno por línea).
            </p>
            <textarea
              value={texto}
              onChange={(e) => setTexto(e.target.value)}
              rows={10}
              className="w-full rounded border p-2 font-mono text-sm"
              placeholder={"3154526\n3154527"}
              aria-label="Números de documento"
            />
            <div className="mt-3 flex justify-end gap-2">
              <button
                onClick={() => setAbierto(false)}
                className="rounded border px-3 py-1 text-sm"
              >
                Cancelar
              </button>
              <button
                onClick={() => void cargar()}
                disabled={enviando}
                className="rounded bg-blue-600 px-3 py-1 text-sm text-white disabled:opacity-50"
              >
                {enviando ? "Cargando…" : "Cargar"}
              </button>
            </div>

            <div className="mt-4 border-t pt-3">
              <p className="mb-2 text-sm font-medium text-slate-700">
                O cargar desde archivo (.xlsx / .xls)
              </p>
              <div className="flex flex-wrap gap-2">
                {[
                  { tipo: "asignacion", label: "Archivo de asignación" },
                  { tipo: "rsirat", label: "Archivo RSIRAT" },
                  { tipo: "autorizacion", label: "Archivo de autorización (RI)" },
                ].map(({ tipo, label }) => {
                  const bloqueado = TIPOS_PLANEAMIENTO.has(tipo) && !planeamientoOk;
                  return (
                    <label
                      key={tipo}
                      title={
                        bloqueado
                          ? "Deshabilitado en horario laboral (L–V 08:00–17:00). Disponible fuera de ese horario o el fin de semana."
                          : undefined
                      }
                      className={
                        bloqueado
                          ? "cursor-not-allowed rounded border px-3 py-1 text-sm text-slate-400 opacity-60"
                          : "cursor-pointer rounded border px-3 py-1 text-sm hover:bg-slate-100"
                      }
                    >
                      {label}
                      <input
                        type="file"
                        accept=".xlsx,.xls"
                        className="hidden"
                        disabled={bloqueado}
                        onChange={(e) => {
                          void subir(tipo, e.target.files?.[0] ?? null);
                          e.target.value = "";
                        }}
                      />
                    </label>
                  );
                })}
              </div>
            </div>
          </div>
        </div>
      ) : null}
    </>
  );
}

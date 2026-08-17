import { useEffect, useMemo, useState } from "react";

import { itop } from "../../api/acciones";

type Row = Record<string, unknown>;
type Tipo = "4ta" | "5ta" | "601" | "601_completo";

export interface ItopDescargaExtra {
  ruc_empleador?: string;
  nombre_empleador?: string;
  doc_override?: string;
}

interface Preview {
  tipo: string;
  of: string;
  ruc: string;
  nombre: string;
  periodo_ini: number;
  periodo_fin: number;
  contenido_txt: string;
  titulo: string;
}

interface Empleador {
  ruc: string;
  nombre: string;
}

interface Props {
  tipo: Tipo;
  row: Row;
  onConfirmado: (extra: ItopDescargaExtra) => void;
  onCancelar: () => void;
}

const es601 = (t: Tipo): boolean => t === "601" || t === "601_completo";

// 601 y 5ta piden N° de identificación cuando el RUC del contribuyente no es
// persona natural (no inicia en "10" con 11 dígitos). 601_completo nunca lo pide.
function requiereDoc(tipo: Tipo, ruc: string): boolean {
  if (tipo !== "5ta" && tipo !== "601") return false;
  const r = ruc.trim();
  return !(r.startsWith("10") && r.length === 11);
}

export function ConfirmarTicketModal({
  tipo,
  row,
  onConfirmado,
  onCancelar,
}: Props): JSX.Element {
  const rucContrib = String(row.ruc ?? row.num_ruc ?? "").trim();

  const [empleadores, setEmpleadores] = useState<Empleador[]>([]);
  const [seleccion, setSeleccion] = useState<number>(-1); // -1 = manual
  const [rucEmp, setRucEmp] = useState("");
  const [nombreEmp, setNombreEmp] = useState("");
  const [doc, setDoc] = useState("");
  const [preview, setPreview] = useState<Preview | null>(null);
  const [error, setError] = useState<string | null>(null);

  const necesitaDoc = requiereDoc(tipo, rucContrib);

  // Cargar empleadores del archivo (solo 601/601_completo).
  useEffect(() => {
    if (!es601(tipo)) return;
    let vivo = true;
    itop
      .empleadores601(row)
      .then((r) => {
        if (!vivo) return;
        setEmpleadores(r.empleadores);
        if (r.empleadores.length > 0) {
          setSeleccion(0);
          setRucEmp(r.empleadores[0].ruc);
          setNombreEmp(r.empleadores[0].nombre);
        } else {
          setSeleccion(-1);
        }
      })
      .catch(() => {
        if (vivo) setSeleccion(-1);
      });
    return () => {
      vivo = false;
    };
  }, [tipo, row]);

  const extra: ItopDescargaExtra = useMemo(() => {
    const e: ItopDescargaExtra = {};
    if (es601(tipo)) {
      e.ruc_empleador = rucEmp.trim();
      e.nombre_empleador = nombreEmp.trim();
    }
    if (necesitaDoc && doc.trim()) e.doc_override = doc.trim();
    return e;
  }, [tipo, rucEmp, nombreEmp, necesitaDoc, doc]);

  // Recalcular el preview cuando cambian empleador/doc (601) o al montar.
  useEffect(() => {
    // Para 601 necesitamos empleador antes de poder previsualizar el .txt.
    if (es601(tipo) && !extra.ruc_empleador) {
      setPreview(null);
      setError(null);
      return;
    }
    let vivo = true;
    setError(null);
    itop
      .preview(tipo, row, extra)
      .then((p) => {
        if (vivo) {
          setPreview(p);
          setError(null);
        }
      })
      .catch((err) => {
        if (vivo) {
          setError(String(err));
          setPreview(null);
        }
      });
    return () => {
      vivo = false;
    };
  }, [tipo, row, extra]);

  function elegirEmpleador(idx: number): void {
    setSeleccion(idx);
    if (idx >= 0) {
      setRucEmp(empleadores[idx].ruc);
      setNombreEmp(empleadores[idx].nombre);
    } else {
      setRucEmp("");
      setNombreEmp("");
    }
  }

  const puedeConfirmar =
    (!es601(tipo) || (rucEmp.trim() !== "" && nombreEmp.trim() !== "")) &&
    (!necesitaDoc || doc.trim() !== "");

  const titulos: Record<Tipo, string> = {
    "4ta": "Confirmar ticket — Rentas 4ta",
    "5ta": "Confirmar ticket — Rentas 5ta",
    "601": "Confirmar ticket — PDT 601",
    "601_completo": "Confirmar ticket — PDT 601 (empleador completo)",
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/30"
      onClick={onCancelar}
    >
      <div
        className="w-[560px] max-w-[92vw] rounded bg-white p-4 shadow-lg"
        onClick={(e) => e.stopPropagation()}
      >
        <h2 className="mb-3 text-base font-semibold text-slate-800">{titulos[tipo]}</h2>

        {es601(tipo) ? (
          <div className="mb-3 space-y-2">
            {empleadores.length > 0 ? (
              <label className="block text-sm">
                <span className="text-slate-600">Empleador (del archivo)</span>
                <select
                  className="mt-1 w-full rounded border p-1"
                  value={seleccion}
                  onChange={(e) => elegirEmpleador(Number(e.target.value))}
                >
                  {empleadores.map((emp, i) => (
                    <option key={`${emp.ruc}-${i}`} value={i}>
                      {emp.ruc} — {emp.nombre}
                    </option>
                  ))}
                  <option value={-1}>Ingresar manualmente…</option>
                </select>
              </label>
            ) : (
              <p className="text-sm text-slate-500">
                No se encontró empleador en el archivo del caso. Ingréselo manualmente.
              </p>
            )}
            <label className="block text-sm">
              <span className="text-slate-600">RUC del empleador</span>
              <input
                className="mt-1 w-full rounded border p-1 disabled:bg-slate-100"
                value={rucEmp}
                disabled={seleccion >= 0}
                onChange={(e) => setRucEmp(e.target.value)}
              />
            </label>
            <label className="block text-sm">
              <span className="text-slate-600">Nombre del empleador</span>
              <input
                className="mt-1 w-full rounded border p-1 disabled:bg-slate-100"
                value={nombreEmp}
                disabled={seleccion >= 0}
                onChange={(e) => setNombreEmp(e.target.value)}
              />
            </label>
          </div>
        ) : null}

        {necesitaDoc ? (
          <label className="mb-3 block text-sm">
            <span className="text-slate-600">
              N° de identificación (el RUC no inicia en 10)
            </span>
            <input
              className="mt-1 w-full rounded border p-1"
              value={doc}
              onChange={(e) => setDoc(e.target.value)}
            />
          </label>
        ) : null}

        <div className="mb-3 rounded bg-slate-50 p-2 text-sm text-slate-700">
          {error ? (
            <p className="text-red-600">{error}</p>
          ) : preview ? (
            <>
              <p>
                <b>OF:</b> {preview.of} · <b>Periodos:</b> {preview.periodo_ini} –{" "}
                {preview.periodo_fin}
              </p>
              <p className="mt-1 text-xs text-slate-500">Contenido del .txt a adjuntar:</p>
              <pre className="mt-0.5 overflow-x-auto rounded bg-white p-1 font-mono text-xs">
                {preview.contenido_txt}
              </pre>
            </>
          ) : (
            <p className="text-slate-400">Calculando resumen…</p>
          )}
        </div>

        <div className="flex justify-end gap-2">
          <button
            onClick={onCancelar}
            className="rounded border px-3 py-1 text-sm hover:bg-slate-100"
          >
            Cancelar
          </button>
          <button
            onClick={() => onConfirmado(extra)}
            disabled={!puedeConfirmar}
            className="rounded bg-blue-600 px-3 py-1 text-sm text-white disabled:opacity-40"
          >
            Confirmar y enviar
          </button>
        </div>
      </div>
    </div>
  );
}

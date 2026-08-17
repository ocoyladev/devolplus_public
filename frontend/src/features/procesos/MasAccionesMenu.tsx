import { useState } from "react";

import { descargas, type RsiratPreflight } from "../../api/acciones";
import { useLanzarTarea, useTareaLock } from "../tareas/tareaLock";
import { ValidarArchivoModal } from "./ValidarArchivoModal";
import { VerificarEchasquiModal } from "./VerificarEchasquiModal";

type Fila = Record<string, unknown>;

interface Props {
  filas: Fila[];
  archivo?: boolean;
  onJobIniciado: (kind: string) => void;
  onError: (mensaje: string) => void;
}

/** Genera una línea "OF,RUC,Expediente" por cada fila seleccionada. */
function generarRegistroCartas(filas: Fila[]): string {
  return filas
    .map((r) => {
      const of = String(r.of_devolucion ?? "").trim();
      const ruc = String(r.num_ruc ?? r.ruc ?? "").trim();
      const exp = String(r.num_dev ?? "").trim();
      return `${of},${ruc},${exp}`;
    })
    .join("\n");
}

export function MasAccionesMenu({ filas, archivo = false, onJobIniciado, onError }: Props): JSX.Element {
  const [open, setOpen] = useState(false);
  const [verificarAbierto, setVerificarAbierto] = useState(false);
  const [validarAbierto, setValidarAbierto] = useState(false);
  const [texto, setTexto] = useState<string | null>(null);
  const [copiado, setCopiado] = useState(false);
  const [confirmarRsirat, setConfirmarRsirat] = useState<null | "ref" | "antec">(null);
  // Verificación previa: null mientras carga; `preflightError` si no se pudo consultar.
  const [preflight, setPreflight] = useState<RsiratPreflight | null>(null);
  const [preflightError, setPreflightError] = useState<string | null>(null);
  const { ocupado } = useTareaLock();
  const lanzar = useLanzarTarea();
  const sinSeleccion = filas.length === 0;

  function registrarCartas(): void {
    setOpen(false);
    setCopiado(false);
    setTexto(generarRegistroCartas(filas));
  }

  function agregarNumeracion(): void {
    setOpen(false);
    void lanzar(
      "numeracion_cartas",
      () => descargas.numeracion(filas),
      onJobIniciado,
      onError,
    );
  }

  function descargarRiSel(): void {
    setOpen(false);
    void lanzar(
      "descarga_ri",
      () => descargas.riMasivo(filas, archivo),
      onJobIniciado,
      onError,
    );
  }

  function descargarCartasSel(): void {
    setOpen(false);
    void lanzar(
      "descarga_cartas_masivo",
      () => descargas.cartasMasivo(filas, archivo),
      onJobIniciado,
      onError,
    );
  }

  function pedirRsirat(tipo: "ref" | "antec"): void {
    setOpen(false);
    setPreflight(null);
    setPreflightError(null);
    setConfirmarRsirat(tipo);
    // Verifica en el backend qué PDFs ya existen antes de ofrecer "Iniciar".
    descargas
      .rsiratPreflight(tipo, filas)
      .then(setPreflight)
      .catch((e: unknown) => setPreflightError(e instanceof Error ? e.message : String(e)));
  }

  function ejecutarRsirat(): void {
    const tipo = confirmarRsirat;
    setConfirmarRsirat(null);
    if (tipo === "ref") {
      void lanzar("rsirat_ref", () => descargas.rsiratRef(filas), onJobIniciado, onError);
    } else if (tipo === "antec") {
      void lanzar(
        "rsirat_antec",
        () => descargas.rsiratAntecedentes(filas),
        onJobIniciado,
        onError,
      );
    }
  }

  async function copiar(): Promise<void> {
    if (texto === null) return;
    try {
      await navigator.clipboard.writeText(texto);
    } catch {
      // Fallback para entornos sin clipboard API (WebView antiguo).
      const ta = document.getElementById("registro-cartas-ta") as HTMLTextAreaElement | null;
      if (ta) {
        ta.select();
        document.execCommand("copy");
      }
    }
    setCopiado(true);
    window.setTimeout(() => setCopiado(false), 2000);
  }

  return (
    <div className="relative">
      <button
        onClick={() => setOpen((o) => !o)}
        disabled={sinSeleccion || ocupado}
        className="rounded border px-3 py-1 text-sm hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-40"
      >
        Más acciones ▾
      </button>
      {open ? (
        <>
          <div className="fixed inset-0 z-40" onClick={() => setOpen(false)} />
          <div className="absolute left-0 z-50 mt-1 w-56 rounded border bg-white text-sm shadow-lg">
            <button
              onClick={descargarRiSel}
              disabled={sinSeleccion || ocupado}
              className="block w-full px-3 py-1.5 text-left hover:bg-slate-100 disabled:opacity-40"
            >
              Descargar RI (selección)
            </button>
            <button
              onClick={descargarCartasSel}
              disabled={sinSeleccion || ocupado}
              className="block w-full px-3 py-1.5 text-left hover:bg-slate-100 disabled:opacity-40"
            >
              Descargar cartas (selección)
            </button>
            <button
              onClick={registrarCartas}
              className="block w-full px-3 py-1.5 text-left hover:bg-slate-100"
            >
              Registrar cartas
            </button>
            <button
              onClick={agregarNumeracion}
              className="block w-full px-3 py-1.5 text-left hover:bg-slate-100"
            >
              Agregar numeración
            </button>
            <button
              onClick={() => {
                setOpen(false);
                setVerificarAbierto(true);
              }}
              className="block w-full px-3 py-1.5 text-left hover:bg-slate-100"
            >
              Verificar Exp. Echasqui.
            </button>
            <button
              onClick={() => {
                setOpen(false);
                setValidarAbierto(true);
              }}
              className="block w-full px-3 py-1.5 text-left hover:bg-slate-100"
            >
              Validar archivo
            </button>
            <div className="my-1 border-t" />
            <button
              onClick={() => pedirRsirat("ref")}
              disabled={sinSeleccion || ocupado}
              className="block w-full px-3 py-1.5 text-left hover:bg-slate-100 disabled:opacity-40"
            >
              Descargar REF/Tiempos (RSIRAT)
            </button>
            <button
              onClick={() => pedirRsirat("antec")}
              disabled={sinSeleccion || ocupado}
              className="block w-full px-3 py-1.5 text-left hover:bg-slate-100 disabled:opacity-40"
            >
              Descargar antecedentes (RSIRAT)
            </button>
          </div>
        </>
      ) : null}

      {confirmarRsirat !== null ? (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/30"
          onClick={() => setConfirmarRsirat(null)}
        >
          <div
            className="w-[480px] max-w-[90vw] rounded bg-white p-4 shadow-lg"
            onClick={(e) => e.stopPropagation()}
          >
            <h2 className="mb-2 text-base font-semibold text-slate-800">
              {confirmarRsirat === "ref"
                ? "Descargar REF/Tiempos (RSIRAT)"
                : "Descargar antecedentes (RSIRAT)"}
            </h2>
            <p className="mb-2 text-sm text-slate-600">
              Se automatizará la aplicación de escritorio SIRAT sobre{" "}
              {preflight ? preflight.pendientes : filas.length} caso(s). Durante el
              proceso el mouse y el teclado los controla el script.
            </p>

            {preflight === null && preflightError === null ? (
              <p className="mb-3 text-sm text-slate-500">
                Verificando archivos ya descargados…
              </p>
            ) : null}

            {preflightError !== null ? (
              <p className="mb-3 rounded bg-rose-50 p-2 text-sm text-rose-800">
                No se pudo verificar los archivos existentes ({preflightError}). Se
                puede iniciar igual: el proceso vuelve a verificar antes de descargar.
              </p>
            ) : null}

            {preflight !== null ? (
              <div className="mb-3">
                <p className="mb-1 text-sm font-medium text-slate-700">
                  {preflight.pendientes} de {preflight.total} caso(s) con descargas
                  pendientes.
                </p>
                <ul className="max-h-48 overflow-y-auto rounded border text-sm">
                  {preflight.casos.map((c) => (
                    <li
                      key={c.of}
                      className="flex gap-2 border-b px-2 py-1 last:border-b-0"
                    >
                      <span className="font-mono text-xs text-slate-500">OF {c.of}</span>
                      <span className="flex-1">
                        {c.estado === "pendiente"
                          ? `⬇ pendiente — ${c.detalle}`
                          : c.estado === "omitido"
                            ? `✅ ya descargado — ${c.existentes.join(", ")}`
                            : `⚠ ${c.detalle} — se omitirá`}
                      </span>
                    </li>
                  ))}
                </ul>
              </div>
            ) : null}

            {preflight !== null && preflight.pendientes === 0 ? (
              <p className="mb-3 rounded bg-slate-100 p-2 text-sm text-slate-700">
                No hay descargas pendientes. Todos los casos seleccionados ya tienen
                sus archivos.
              </p>
            ) : (
              <p className="mb-3 rounded bg-amber-50 p-2 text-sm text-amber-800">
                ⚠ No use el equipo mientras se ejecuta. Para <b>abortar</b>, pulse{" "}
                <b>Ctrl+Shift+Q</b> (o mueva el mouse a una{" "}
                <b>esquina de la pantalla</b>).
              </p>
            )}

            <div className="flex justify-end gap-2">
              <button
                onClick={() => setConfirmarRsirat(null)}
                className="rounded border px-3 py-1 text-sm hover:bg-slate-100"
              >
                Cancelar
              </button>
              <button
                onClick={ejecutarRsirat}
                disabled={preflight !== null && preflight.pendientes === 0}
                className="rounded bg-blue-600 px-3 py-1 text-sm text-white disabled:opacity-40"
              >
                Iniciar
              </button>
            </div>
          </div>
        </div>
      ) : null}

      {texto !== null ? (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/30"
          onClick={() => setTexto(null)}
        >
          <div
            className="w-[560px] max-w-[90vw] rounded bg-white p-4 shadow-lg"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="mb-2 flex items-center justify-between">
              <h2 className="text-base font-semibold text-slate-800">
                Registrar cartas ({filas.length})
              </h2>
              <button onClick={() => setTexto(null)} className="text-slate-500">
                ✕
              </button>
            </div>
            <p className="mb-2 text-xs text-slate-500">
              Formato: OF,RUC,Expediente — una línea por caso. Edite y copie.
            </p>
            <textarea
              id="registro-cartas-ta"
              value={texto}
              onChange={(e) => setTexto(e.target.value)}
              spellCheck={false}
              className="h-56 w-full resize-y rounded border p-2 font-mono text-sm"
            />
            <div className="mt-3 flex justify-end gap-2">
              <button
                onClick={() => void copiar()}
                className="rounded bg-blue-600 px-3 py-1 text-sm text-white"
              >
                {copiado ? "✓ Copiado" : "Copiar"}
              </button>
              <button
                onClick={() => setTexto(null)}
                className="rounded border px-3 py-1 text-sm hover:bg-slate-100"
              >
                Cerrar
              </button>
            </div>
          </div>
        </div>
      ) : null}

      <VerificarEchasquiModal
        filas={filas}
        abierto={verificarAbierto}
        onCerrar={() => setVerificarAbierto(false)}
        onJobIniciado={(kind) => {
          setVerificarAbierto(false);
          onJobIniciado(kind);
        }}
        onError={onError}
      />

      <ValidarArchivoModal
        filas={filas}
        abierto={validarAbierto}
        onCerrar={() => setValidarAbierto(false)}
        onJobIniciado={(kind) => {
          onJobIniciado(kind);
        }}
        onError={onError}
      />
    </div>
  );
}

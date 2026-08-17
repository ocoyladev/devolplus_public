import { useEffect, useState } from "react";

import {
  addFeriado,
  delFeriado,
  getCredenciales,
  getFeriados,
  getRutas,
  putCredenciales,
  putRutas,
  seleccionarCarpeta,
  type RutasConfig,
} from "../../api/config";

interface Props {
  onAviso: (mensaje: string) => void;
  abrirInicial?: boolean;
}

const RUTA_LABELS: Record<keyof RutasConfig, string> = {
  PATH_DESCARGAS: "Descargas",
  PATH_RI: "RI",
  PATH_AUTORIZAR: "Autorizar",
  PATH_ARCHIVO: "Archivo",
  PATH_SIRAT_EXE: "Ejecutable SIRAT (.exe)",
  UNIDAD_ORGANICA_FOLIO: "Unidad orgánica (folio)",
};

// Sistemas de credenciales reales del aplicativo.
const SISTEMAS: { id: string; label: string }[] = [
  { id: "Portal", label: "Portal" },
  { id: "Workflow", label: "Workflow / iTop" },
];

const INPUT = "mt-0.5 w-full rounded border p-1.5 text-sm";

interface Cred {
  usuario: string;
  password: string;
}

export function ConfigPanel({ onAviso, abrirInicial }: Props): JSX.Element {
  const [abierto, setAbierto] = useState(false);

  useEffect(() => {
    if (abrirInicial) setAbierto(true);
  }, [abrirInicial]);
  const [rutas, setRutas] = useState<RutasConfig | null>(null);
  const [creds, setCreds] = useState<Record<string, Cred>>({});
  const [feriados, setFeriados] = useState<string[]>([]);
  const [nuevoFeriado, setNuevoFeriado] = useState("");

  useEffect(() => {
    if (!abierto) return;
    getRutas()
      .then(setRutas)
      .catch((e: unknown) => onAviso(String(e)));
    getFeriados()
      .then((r) => setFeriados(r.feriados))
      .catch(() => setFeriados([]));
    for (const s of SISTEMAS) {
      getCredenciales(s.id)
        .then((c) =>
          setCreds((prev) => ({ ...prev, [s.id]: { usuario: c.usuario, password: "" } })),
        )
        .catch(() => {});
    }
  }, [abierto, onAviso]);

  function setCred(id: string, campo: keyof Cred, valor: string): void {
    setCreds((prev) => {
      const actual = prev[id] ?? { usuario: "", password: "" };
      return { ...prev, [id]: { ...actual, [campo]: valor } };
    });
  }

  async function elegirCarpeta(k: keyof RutasConfig): Promise<void> {
    if (!rutas) return;
    try {
      const ruta = await seleccionarCarpeta();
      if (ruta) setRutas({ ...rutas, [k]: ruta });
    } catch (e) {
      onAviso(String(e));
    }
  }

  async function guardarRutas(): Promise<void> {
    if (!rutas) return;
    try {
      await putRutas(rutas);
      onAviso("✓ Rutas guardadas");
    } catch (e) {
      onAviso(String(e));
    }
  }

  async function guardarCred(id: string, label: string): Promise<void> {
    const c = creds[id] ?? { usuario: "", password: "" };
    try {
      await putCredenciales(id, c.usuario, c.password);
      setCred(id, "password", "");
      onAviso(`✓ Credenciales de ${label} guardadas`);
    } catch (e) {
      onAviso(String(e));
    }
  }

  async function agregarFeriado(): Promise<void> {
    const f = nuevoFeriado.trim();
    if (!f) return;
    try {
      const r = await addFeriado(f);
      setFeriados(r.feriados);
      setNuevoFeriado("");
    } catch (e) {
      onAviso(String(e));
    }
  }

  async function quitarFeriado(fecha: string): Promise<void> {
    try {
      const r = await delFeriado(fecha);
      setFeriados(r.feriados);
    } catch (e) {
      onAviso(String(e));
    }
  }

  return (
    <>
      <button
        onClick={() => setAbierto(true)}
        className="rounded border px-3 py-1 text-sm hover:bg-slate-100"
      >
        Configuración
      </button>
      {abierto ? (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/30"
          onClick={() => setAbierto(false)}
        >
          <div
            className="max-h-[85vh] w-[520px] overflow-auto rounded bg-white p-4 shadow-lg"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="mb-3 flex items-center justify-between">
              <h2 className="text-base font-semibold text-slate-800">Configuración</h2>
              <button onClick={() => setAbierto(false)} className="text-slate-500">
                ✕
              </button>
            </div>

            <section className="mb-4">
              <h3 className="mb-2 text-sm font-semibold text-slate-700">Rutas</h3>
              {rutas ? (
                (Object.keys(RUTA_LABELS) as (keyof RutasConfig)[]).map((k) => (
                  <label key={k} className="mb-2 block text-sm">
                    <span className="text-slate-600">{RUTA_LABELS[k]}</span>
                    <div className="mt-0.5 flex gap-1">
                      <input
                        value={rutas[k] ?? ""}
                        onChange={(e) => setRutas({ ...rutas, [k]: e.target.value })}
                        className="w-full rounded border p-1.5 font-mono text-sm"
                      />
                      {k.startsWith("PATH_") && k !== "PATH_SIRAT_EXE" ? (
                        <button
                          type="button"
                          onClick={() => void elegirCarpeta(k)}
                          title="Seleccionar carpeta…"
                          className="rounded border px-2 hover:bg-slate-100"
                        >
                          📁
                        </button>
                      ) : null}
                    </div>
                  </label>
                ))
              ) : (
                <p className="text-sm text-slate-400">Cargando…</p>
              )}
              <button
                onClick={() => void guardarRutas()}
                className="rounded bg-blue-600 px-3 py-1 text-sm text-white"
              >
                Guardar rutas
              </button>
            </section>

            <section className="mb-4 border-t pt-3">
              <h3 className="mb-2 text-sm font-semibold text-slate-700">Credenciales</h3>
              {SISTEMAS.map((s) => (
                <div key={s.id} className="mb-3 rounded bg-slate-50 p-2">
                  <p className="mb-1 text-sm font-medium text-slate-700">{s.label}</p>
                  <label className="mb-1 block text-sm">
                    <span className="text-slate-600">Usuario</span>
                    <input
                      value={creds[s.id]?.usuario ?? ""}
                      onChange={(e) =>
                        setCred(
                          s.id,
                          "usuario",
                          s.id === "Portal"
                            ? e.target.value.toUpperCase()
                            : e.target.value,
                        )
                      }
                      className={`${INPUT}${s.id === "Portal" ? " uppercase" : ""}`}
                    />
                  </label>
                  <label className="mb-1 block text-sm">
                    <span className="text-slate-600">Contraseña</span>
                    <input
                      type="password"
                      value={creds[s.id]?.password ?? ""}
                      onChange={(e) => setCred(s.id, "password", e.target.value)}
                      placeholder="(sin cambios)"
                      className={INPUT}
                    />
                  </label>
                  <button
                    onClick={() => void guardarCred(s.id, s.label)}
                    className="mt-1 rounded bg-blue-600 px-3 py-1 text-sm text-white"
                  >
                    Guardar {s.label}
                  </button>
                </div>
              ))}
            </section>

            <section className="mb-4 border-t pt-3">
              <h3 className="mb-1 text-sm font-semibold text-slate-700">
                Días no laborables
              </h3>
              <p className="mb-2 text-xs text-slate-500">
                Afectan el cálculo de intereses (días hábiles).
              </p>
              <div className="mb-2 flex gap-2">
                <input
                  value={nuevoFeriado}
                  onChange={(e) => setNuevoFeriado(e.target.value)}
                  placeholder="DD/MM/AAAA"
                  className="flex-1 rounded border p-1.5 text-sm"
                />
                <button
                  onClick={() => void agregarFeriado()}
                  className="rounded bg-blue-600 px-3 py-1 text-sm text-white"
                >
                  Agregar
                </button>
              </div>
              {feriados.length === 0 ? (
                <p className="text-xs text-slate-400">No hay días registrados.</p>
              ) : (
                <ul className="max-h-32 overflow-auto rounded border">
                  {feriados.map((f) => (
                    <li
                      key={f}
                      className="flex items-center justify-between px-2 py-1 text-sm odd:bg-slate-50"
                    >
                      <span>{f}</span>
                      <button
                        onClick={() => void quitarFeriado(f)}
                        className="text-red-500 hover:text-red-700"
                        title="Quitar"
                      >
                        ✕
                      </button>
                    </li>
                  ))}
                </ul>
              )}
            </section>
          </div>
        </div>
      ) : null}
    </>
  );
}

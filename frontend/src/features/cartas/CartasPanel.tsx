import { useEffect, useRef, useState } from "react";

import {
  actualizarCarta,
  type Carta,
  type CartaPatch,
  crearCarta,
  eliminarCarta,
  listarCartas,
  TIPOS_CARTA,
} from "../../api/cartas";

interface Props {
  numDoc: string;
  onClose: () => void;
  /** Se invoca tras cada cambio persistido, para que la grilla se recargue. */
  onCambio?: () => void;
  /**
   * Si es true y el caso todavía no tiene cartas, crea el borrador de alta
   * automáticamente al cargar (spec §9: "Con `+`, el panel abre directo en el
   * formulario de alta"). No hace nada si el caso ya tiene cartas.
   */
  altaInmediata?: boolean;
}

const ETIQUETA_ESTADO: Record<string, string> = {
  ATENDIDA: "Atendida",
  SIN_NOTIFICAR: "Sin notificar",
  VENCIDA: "Vencida",
  POR_VENCER: "Por vencer",
  VIGENTE: "Vigente",
};

const CLASE_ESTADO: Record<string, string> = {
  VENCIDA: "bg-red-100 text-red-800",
  POR_VENCER: "bg-orange-100 text-orange-800",
  ATENDIDA: "bg-green-100 text-green-800",
};

export function CartasPanel({
  numDoc,
  onClose,
  onCambio,
  altaInmediata = false,
}: Props): JSX.Element {
  const [cartas, setCartas] = useState<Carta[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [guardando, setGuardando] = useState(false);
  const [porBorrar, setPorBorrar] = useState<Carta | null>(null);
  // Evita que el alta automática se dispare más de una vez por montaje
  // (p. ej. si `cartas` se recalcula por cualquier otro motivo).
  const altaDisparada = useRef(false);

  // Evita tocar el estado de React tras un desmontaje (p. ej. el usuario
  // cierra el modal mientras una carga o un guardado siguen en vuelo). Los
  // pedidos igual se completan en el servidor; solo dejamos de reaccionar.
  const montado = useRef(true);
  useEffect(() => {
    montado.current = true;
    return () => {
      montado.current = false;
    };
  }, []);

  function recargar(): void {
    listarCartas(numDoc)
      .then((datos) => {
        if (montado.current) setCartas(datos);
      })
      .catch((e: unknown) => {
        if (!montado.current) return;
        setError(e instanceof Error ? e.message : String(e));
        // Sin esto, una carga inicial fallida deja "Cargando…" para siempre
        // (cartas sigue en null). Con [] el mensaje de error queda visible
        // y el usuario puede reintentar.
        setCartas([]);
      });
  }

  useEffect(recargar, [numDoc]);

  function mutar(accion: () => Promise<unknown>): void {
    setGuardando(true);
    setError(null);
    accion()
      .then(() => {
        if (!montado.current) return;
        recargar();
        onCambio?.();
      })
      .catch((e: unknown) => {
        if (montado.current) setError(e instanceof Error ? e.message : String(e));
      })
      .finally(() => {
        if (montado.current) setGuardando(false);
      });
  }

  const guardar = (id: number, datos: CartaPatch): void =>
    mutar(() => actualizarCarta(id, datos));

  const agregar = (): void =>
    mutar(() =>
      crearCarta(numDoc, {
        tipo: (cartas?.length ?? 0) === 0 ? "PRIMERA" : "REITERATIVA",
        fecha_emision: hoyDdMmYyyy(),
      }),
    );

  useEffect(() => {
    if (!altaInmediata || altaDisparada.current) return;
    if (cartas === null || cartas.length !== 0) return; // cargando o ya tiene cartas
    altaDisparada.current = true;
    agregar();
  }, [altaInmediata, cartas]);

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/30"
      onClick={onClose}
    >
      <div
        className="max-h-[85vh] w-[720px] overflow-auto rounded bg-white p-4 shadow-lg"
        onClick={(e) => e.stopPropagation()}
      >
        <h2 className="mb-1 text-base font-semibold text-slate-800">
          Cartas del caso {numDoc}
        </h2>
        <p className="mb-3 text-xs text-slate-500">
          El vencimiento se calcula con la fecha de notificación y el plazo en días
          hábiles. Si lo escribe a mano, deja de recalcularse.
        </p>

        {error ? (
          <p className="mb-2 text-sm text-red-600">
            {error}{" "}
            <button onClick={recargar} className="text-blue-600 underline">
              Reintentar
            </button>
          </p>
        ) : null}

        {cartas === null ? (
          <p className="text-sm text-slate-400">Cargando…</p>
        ) : cartas.length === 0 ? (
          <p className="mb-3 text-sm text-slate-400">
            Este caso todavía no tiene cartas registradas.
          </p>
        ) : (
          <table className="mb-3 w-full text-sm">
            <thead>
              <tr className="border-b text-left text-xs uppercase text-slate-500">
                <th className="py-1">N°</th>
                <th>Año</th>
                <th>Tipo</th>
                <th>Emisión</th>
                <th>Notificación</th>
                <th>Plazo</th>
                <th>Vencimiento</th>
                <th>Estado</th>
                <th>Atendida</th>
                <th>Obs.</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {cartas.map((c) => (
                <tr key={c.id} className="border-b last:border-b-0">
                  <td className="py-1">
                    <CampoTexto
                      valor={c.numero}
                      ancho="w-20"
                      placeholder="s/n"
                      onGuardar={(v) => guardar(c.id, { numero: v })}
                    />
                  </td>
                  <td>
                    <CampoTexto
                      valor={c.anio}
                      ancho="w-16"
                      onGuardar={(v) => guardar(c.id, { anio: v })}
                    />
                  </td>
                  <td>
                    <select
                      value={c.tipo}
                      onChange={(e) => guardar(c.id, { tipo: e.target.value })}
                      className="rounded border px-1 py-0.5 text-sm"
                    >
                      <option value="" />
                      {TIPOS_CARTA.map((t) => (
                        <option key={t} value={t}>
                          {t}
                        </option>
                      ))}
                    </select>
                  </td>
                  <td>
                    <CampoTexto
                      valor={c.fecha_emision}
                      ancho="w-24"
                      placeholder="DD/MM/AAAA"
                      onGuardar={(v) => guardar(c.id, { fecha_emision: v })}
                    />
                  </td>
                  <td>
                    <CampoTexto
                      valor={c.fecha_notificacion}
                      ancho="w-24"
                      placeholder="DD/MM/AAAA"
                      onGuardar={(v) => guardar(c.id, { fecha_notificacion: v })}
                    />
                  </td>
                  <td>
                    <CampoTexto
                      valor={c.plazo === null ? "" : String(c.plazo)}
                      ancho="w-14"
                      onGuardar={(v) =>
                        guardar(c.id, { plazo: v.trim() === "" ? null : Number(v) })
                      }
                    />
                  </td>
                  <td>
                    <CampoTexto
                      valor={c.fecha_vencimiento}
                      ancho="w-24"
                      placeholder="DD/MM/AAAA"
                      onGuardar={(v) => guardar(c.id, { fecha_vencimiento: v })}
                    />
                    {c.vencimiento_manual === 1 ? (
                      <button
                        onClick={() => guardar(c.id, { fecha_vencimiento: "" })}
                        title="Volver al cálculo automático"
                        className="ml-1 text-xs text-blue-600 underline"
                      >
                        manual
                      </button>
                    ) : null}
                  </td>
                  <td>
                    <span
                      className={`rounded px-1.5 py-0.5 text-xs ${
                        CLASE_ESTADO[c.estado] ?? "text-slate-500"
                      }`}
                    >
                      {ETIQUETA_ESTADO[c.estado] ?? c.estado}
                    </span>
                  </td>
                  <td className="text-center">
                    <input
                      type="checkbox"
                      checked={c.atendida === 1}
                      onChange={(e) => guardar(c.id, { atendida: e.target.checked })}
                    />
                  </td>
                  <td>
                    <CampoTexto
                      valor={c.obs}
                      ancho="w-40"
                      onGuardar={(v) => guardar(c.id, { obs: v })}
                    />
                  </td>
                  <td className="text-right">
                    <button
                      onClick={() => setPorBorrar(c)}
                      className="text-xs text-red-600 hover:underline"
                    >
                      Borrar
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}

        <div className="flex items-center justify-between">
          <button
            onClick={agregar}
            disabled={guardando}
            className="rounded border px-3 py-1 text-sm hover:bg-slate-100 disabled:opacity-40"
          >
            Agregar carta
          </button>
          <button onClick={onClose} className="rounded border px-3 py-1 text-sm hover:bg-slate-100">
            Cerrar
          </button>
        </div>

        {porBorrar ? (
          <div className="mt-3 rounded border border-red-300 bg-red-50 p-3 text-sm">
            <p className="mb-2">
              ¿Borrar la carta{" "}
              <strong>
                {porBorrar.numero ? `${porBorrar.numero}-${porBorrar.anio}` : "sin numerar"}
              </strong>
              ? No se puede deshacer.
            </p>
            <button
              onClick={() => {
                const id = porBorrar.id;
                setPorBorrar(null);
                mutar(() => eliminarCarta(id));
              }}
              className="mr-2 rounded bg-red-600 px-3 py-1 text-white"
            >
              Borrar
            </button>
            <button onClick={() => setPorBorrar(null)} className="rounded border px-3 py-1">
              Cancelar
            </button>
          </div>
        ) : null}
      </div>
    </div>
  );
}

function hoyDdMmYyyy(): string {
  const d = new Date();
  const dd = String(d.getDate()).padStart(2, "0");
  const mm = String(d.getMonth() + 1).padStart(2, "0");
  return `${dd}/${mm}/${d.getFullYear()}`;
}

/** Input que solo persiste al perder el foco o con Enter (evita un PATCH por tecla). */
function CampoTexto({
  valor,
  ancho,
  placeholder,
  onGuardar,
}: {
  valor: string;
  ancho: string;
  placeholder?: string;
  onGuardar: (v: string) => void;
}): JSX.Element {
  const [borrador, setBorrador] = useState(valor);
  useEffect(() => setBorrador(valor), [valor]);

  const confirmar = (): void => {
    if (borrador !== valor) onGuardar(borrador);
  };

  return (
    <input
      type="text"
      value={borrador}
      placeholder={placeholder}
      onChange={(e) => setBorrador(e.target.value)}
      onBlur={confirmar}
      onKeyDown={(e) => {
        if (e.key === "Enter") e.currentTarget.blur();
      }}
      className={`${ancho} rounded border px-1 py-0.5 text-sm`}
    />
  );
}

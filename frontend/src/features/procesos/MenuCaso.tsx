import type { ReactNode } from "react";
import { useState } from "react";

import { abrir, descargas, mesa_ayuda } from "../../api/acciones";
import { useLanzarTarea, useTareaLock } from "../tareas/tareaLock";
import { CartasPanel } from "../cartas/CartasPanel";
import { ConfirmarTicketModal, type MesaAyudaDescargaExtra } from "./ConfirmarTicketModal";
import { GenerarDocPanel } from "./GenerarDocPanel";

// Modalidades EXACTAS del backend (una tiene un espacio inicial intencional).
const MODALIDADES = [
  "De Abono en Cuenta a Cheque",
  " De Cheque a Abono en Cuenta",
  "De Cheque a OPF",
  "De OPF a Cheque",
];

interface Props {
  row: Record<string, unknown>;
  tablaArchivo?: boolean;
  onJobIniciado: (kind: string) => void;
  onError: (mensaje: string) => void;
  /** Se invoca tras un cambio persistido en el panel de cartas, para recargar la tabla. */
  onDatosCambiados?: () => void;
}

function Grupo({ title, children }: { title: string; children: ReactNode }): JSX.Element {
  return (
    <div className="border-t first:border-t-0">
      <p className="px-3 pt-1.5 text-xs font-semibold uppercase text-slate-400">
        {title}
      </p>
      {children}
    </div>
  );
}

function Item({
  children,
  onClick,
  disabled,
}: {
  children: ReactNode;
  onClick?: () => void;
  disabled?: boolean;
}): JSX.Element {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className="block w-full px-3 py-1.5 text-left hover:bg-slate-100 disabled:cursor-not-allowed disabled:text-slate-300 disabled:hover:bg-transparent"
    >
      {children}
    </button>
  );
}

export function MenuCaso({
  row,
  tablaArchivo = false,
  onJobIniciado,
  onError,
  onDatosCambiados,
}: Props): JSX.Element {
  const [open, setOpen] = useState(false);
  const [gen, setGen] = useState<"carta" | "ri" | null>(null);
  const [ticket, setTicket] = useState<"4ta" | "5ta" | "601" | "601_completo" | null>(null);
  const [cartasAbierto, setCartasAbierto] = useState(false);
  const { ocupado } = useTareaLock();
  const lanzar = useLanzarTarea();

  function run(kind: string, fn: () => Promise<unknown>): void {
    setOpen(false);
    void lanzar(kind, fn, onJobIniciado, onError);
  }

  function repositorio(): void {
    setOpen(false);
    const exp = window.prompt("N° de expediente(s) E-Doc (separe con /):");
    if (!exp) return;
    const lista = exp
      .split("/")
      .map((s) => s.trim())
      .filter(Boolean);
    if (lista.length > 0) {
      run("descarga_repositorio", () => descargas.repositorio(row, lista));
    }
  }

  function porEjercicios(): void {
    setOpen(false);
    const val = window.prompt("¿Cuántos ejercicio(s) previo(s) descargar?", "1");
    if (val === null) return;
    const count = parseInt(val, 10);
    if (Number.isNaN(count) || count < 1) {
      onError("Ingrese un número de ejercicios válido (≥ 1).");
      return;
    }
    run("descarga_ejercicios", () => descargas.porEjercicios(row, count));
  }

  function planeamiento(): void {
    setOpen(false);
    const sugerido = String(row.ruc ?? row.num_ruc ?? "");
    const ruc = window.prompt("RUC para la descarga de Planeamiento:", sugerido);
    if (ruc === null) return;
    const val = ruc.trim();
    if (!val) {
      onError("Debe indicar el RUC.");
      return;
    }
    run("descarga_planeamiento", () => descargas.planeamiento(row, val));
  }

  function tresUit(): void {
    setOpen(false);
    const sugerido = String(row.num_doc_aso ?? "");
    const num = window.prompt("N° de orden del formulario (3UIT - Casilla 514):", sugerido);
    if (num === null) return;
    run("descarga_3uit", () => descargas.tresUit(row, num.trim() || null));
  }

  function abrirTicket(tipo: "4ta" | "5ta" | "601" | "601_completo"): void {
    setOpen(false);
    setTicket(tipo);
  }

  function mesaAyudaModificar(): void {
    setOpen(false);
    const lista = MODALIDADES.map((m, i) => `${i + 1}) ${m.trim()}`).join("\n");
    const sel = window.prompt(`Modalidad de devolución:\n${lista}\n\nNúmero:`, "1");
    if (sel === null) return;
    const idx = parseInt(sel, 10) - 1;
    if (Number.isNaN(idx) || idx < 0 || idx >= MODALIDADES.length) {
      onError("Selección de modalidad inválida.");
      return;
    }
    const modalidad = MODALIDADES[idx];
    let cci: string | null = null;
    if (modalidad.trim() === "De Cheque a Abono en Cuenta") {
      const c = window.prompt("CCI (requerido para 'De Cheque a Abono en Cuenta'):");
      if (!c) return;
      cci = c.trim();
    }
    run("mesa_ayuda_modificar", () => mesa_ayuda.modificar(row, modalidad, cci));
  }

  return (
    <div className="relative">
      <button
        onClick={() => setOpen((o) => !o)}
        disabled={ocupado}
        className="rounded border border-blue-300 bg-blue-50 px-3 py-1 text-sm text-blue-800 hover:bg-blue-100 disabled:cursor-not-allowed disabled:opacity-50"
      >
        Acciones del caso ▾
      </button>
      {open ? (
        <>
          <div className="fixed inset-0 z-40" onClick={() => setOpen(false)} />
          <div className="absolute left-0 z-50 mt-1 w-60 rounded border bg-white text-sm shadow-lg">
            <Grupo title="Caso">
              <Item onClick={() => run("descarga_ri", () => descargas.ri(row, tablaArchivo))}>
                Descargar RI
              </Item>
              <Item
                onClick={() => {
                  setOpen(false);
                  setCartasAbierto(true);
                }}
              >
                Cartas…
              </Item>
              <Item onClick={() => run("descarga_cartas", () => descargas.cartas(row, tablaArchivo))}>
                Descargar Cartas
              </Item>
              <Item onClick={() => run("abrir_carpeta", () => abrir.carpeta(row, tablaArchivo))}>
                Abrir carpeta
              </Item>
              <Item onClick={() => run("abrir_macro", () => abrir.macro(row, tablaArchivo))}>
                Abrir MACRO
              </Item>
            </Grupo>
            <Grupo title="Generar Docs">
              <Item
                onClick={() => {
                  setOpen(false);
                  setGen("carta");
                }}
              >
                Carta
              </Item>
              {!tablaArchivo ? (
                <Item
                  onClick={() => {
                    setOpen(false);
                    setGen("ri");
                  }}
                >
                  RI
                </Item>
              ) : null}
            </Grupo>
            {!tablaArchivo ? (
              <Grupo title="Descargas adicionales">
                <Item onClick={porEjercicios}>Por ejercicio(s)</Item>
                <Item onClick={tresUit}>3UIT - Casilla 514</Item>
                <Item onClick={() => run("descarga_exp", () => descargas.expElectronico(row))}>
                  Exp. Electrónico
                </Item>
                <Item onClick={repositorio}>E-Doc</Item>
                <Item onClick={planeamiento}>Planeamiento</Item>
              </Grupo>
            ) : null}
            {!tablaArchivo ? (
              <Grupo title="Mesa de Ayuda">
                <Item onClick={() => abrirTicket("4ta")}>Rentas 4ta</Item>
                <Item onClick={() => abrirTicket("5ta")}>Rentas 5ta</Item>
                <Item onClick={() => abrirTicket("601")}>PDT 601</Item>
                <Item onClick={() => abrirTicket("601_completo")}>
                  PDT 601 - empleador completo
                </Item>
                <Item onClick={mesaAyudaModificar}>Modificar modalidad</Item>
              </Grupo>
            ) : null}
          </div>
        </>
      ) : null}
      {cartasAbierto ? (
        <CartasPanel
          numDoc={String(row.num_doc ?? "")}
          onClose={() => setCartasAbierto(false)}
          onCambio={onDatosCambiados}
        />
      ) : null}
      {gen ? (
        <GenerarDocPanel
          tipo={gen}
          row={row}
          archivo={tablaArchivo}
          onClose={() => setGen(null)}
          onJobIniciado={onJobIniciado}
          onError={onError}
        />
      ) : null}
      {ticket ? (
        <ConfirmarTicketModal
          tipo={ticket}
          row={row}
          onCancelar={() => setTicket(null)}
          onConfirmado={(extra: MesaAyudaDescargaExtra) => {
            const tipo = ticket;
            setTicket(null);
            run(`mesa_ayuda_${tipo}`, () => mesa_ayuda.descarga(tipo, row, extra));
          }}
        />
      ) : null}
    </div>
  );
}

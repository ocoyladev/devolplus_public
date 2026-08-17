import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, expect, test, vi } from "vitest";

import { procesos, type AlertaValidacion, type CasoValidacion } from "../../api/acciones";
import { ValidarArchivoModal } from "./ValidarArchivoModal";

vi.mock("../tareas/tareaLock", () => ({
  useTareaLock: () => ({ ocupado: false, iniciar: () => true, terminar: () => {} }),
}));

/** WebSocket falso: el modal se suscribe al abrirse para recibir el avance. */
let sockets: { onmessage?: (e: { data: string }) => void }[] = [];

beforeEach(() => {
  sockets = [];
  vi.stubGlobal(
    "WebSocket",
    class {
      onopen?: () => void;
      onclose?: () => void;
      onmessage?: (e: { data: string }) => void;
      constructor() {
        sockets.push(this);
        queueMicrotask(() => this.onopen?.());
      }
      close() {}
    },
  );
});

/** Empuja un evento por el WS falso, como haría el backend. */
function emitirWs(evento: Record<string, unknown>): void {
  act(() => {
    for (const s of sockets) s.onmessage?.({ data: JSON.stringify(evento) });
  });
}

function caso(alertas: AlertaValidacion[], extra: Partial<CasoValidacion> = {}): CasoValidacion {
  return {
    num_doc: "D1", num_dev: "", num_ruc: "", nombre: "ACME", of_devolucion: "OF1",
    tipo_exp: "ELECTRONICO", cod_tip_sol: "02", es_tipo12: false, origen_tipo12: "",
    is_of_multiple: false, carpeta_existe: true, paso_papeles_trabajo: false,
    insumo_final: { completo: false, faltantes: [], puede_foliar: false },
    exp_repositorio: { registrado: true, valor: "", autoregistrado: false },
    repositorios: [],
    carga_1649: {
      aplica: true,
      local: { reportes: false, cedula: false },
      remoto: "no_verificado",
      remoto_reportes: false,
      remoto_cedula: false,
      visible_reportes: "desconocido",
      visible_cedula: "desconocido",
    },
    indispensables: { raiz: [], subcarpetas: {} },
    alertas,
    nivel: "error", error: "",
    ...extra,
  };
}

test("muestra los casos validados y el nivel", async () => {
  vi.spyOn(procesos, "validarArchivo").mockResolvedValue([
    caso([{ codigo: "sin_papeles_trabajo", severidad: "error", mensaje: "No pasó por PAPELES_TRABAJO.", accion: "papeles_trabajo" }]),
  ]);

  render(
    <ValidarArchivoModal
      filas={[{ num_doc: "D1" }]}
      abierto={true}
      onCerrar={() => {}}
      onJobIniciado={() => {}}
      onError={() => {}}
    />,
  );

  await waitFor(() => expect(screen.getByText(/ACME/)).toBeInTheDocument());
  expect(screen.getByText(/No pasó por PAPELES_TRABAJO/)).toBeInTheDocument();
});

test("el repositorio pendiente se sube por vía especial, no carga el expediente", async () => {
  vi.spyOn(procesos, "validarArchivo").mockResolvedValue([
    caso(
      [{
        codigo: "repositorio_item", severidad: "advertencia",
        mensaje: "Repositorio '000-URD999-2026-611260-1' no figura en el expediente electrónico.",
        accion: "subir_repositorio", item: "000-URD999-2026-611260-1",
      }],
      { num_dev: "50020261757051", num_ruc: "10402973846", nivel: "advertencia" },
    ),
  ]);
  const subir = vi.spyOn(procesos, "subirRepositorioPendientes").mockResolvedValue("job1");
  const cargar = vi.spyOn(procesos, "cargaExpedientes").mockResolvedValue("job2");

  render(
    <ValidarArchivoModal
      filas={[{ num_doc: "D1" }]}
      abierto={true}
      onCerrar={() => {}}
      onJobIniciado={() => {}}
      onError={() => {}}
    />,
  );

  const boton = await screen.findByRole("button", { name: /Subir repositorio al expediente/ });
  fireEvent.click(boton);

  await waitFor(() =>
    expect(subir).toHaveBeenCalledWith([
      {
        num_doc: "D1",
        num_dev: "50020261757051",
        num_ruc: "10402973846",
        denom: "000-URD999-2026-611260-1",
      },
    ]),
  );
  expect(cargar).not.toHaveBeenCalled();
});

test("marca la rectificatoria tipo 12 y su solicitud de origen", async () => {
  vi.spyOn(procesos, "validarArchivo").mockResolvedValue([
    caso([], { es_tipo12: true, cod_tip_sol: "12", origen_tipo12: "36039451", nivel: "ok" }),
  ]);

  render(
    <ValidarArchivoModal
      filas={[{ num_doc: "D1" }]}
      abierto={true}
      onCerrar={() => {}}
      onJobIniciado={() => {}}
      onError={() => {}}
    />,
  );

  expect(await screen.findByText(/TIPO 12 → 36039451/)).toBeInTheDocument();
});


test("muestra el avance por caso mientras valida", async () => {
  // La respuesta queda pendiente para poder observar el estado "cargando".
  let resolver: (c: CasoValidacion[]) => void = () => {};
  vi.spyOn(procesos, "validarArchivo").mockReturnValue(
    new Promise<CasoValidacion[]>((r) => {
      resolver = r;
    }),
  );

  render(
    <ValidarArchivoModal
      filas={[{ num_doc: "D1" }, { num_doc: "D2" }, { num_doc: "D3" }, { num_doc: "D4" }]}
      abierto={true}
      onCerrar={() => {}}
      onJobIniciado={() => {}}
      onError={() => {}}
    />,
  );

  // Antes de recibir eventos ya se conoce el total (los casos seleccionados).
  expect(await screen.findByText(/Validando… 0\/4 \(0%\)/)).toBeInTheDocument();

  // Evento de avance emitido por el backend durante la validación.
  emitirWs({
    type: "progress",
    kind: "validar_archivo",
    job_id: "",
    done: 3,
    total: 4,
    etiqueta: "D3",
  });
  expect(await screen.findByText(/Validando… 3\/4 \(75%\) · D3/)).toBeInTheDocument();

  resolver([]);
  await waitFor(() => expect(screen.queryByText(/Validando…/)).not.toBeInTheDocument());
});

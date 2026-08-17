import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";

import { ConfirmarTicketModal } from "./ConfirmarTicketModal";
import { mesa_ayuda } from "../../api/acciones";

vi.mock("../../api/acciones", () => ({
  mesa_ayuda: {
    preview: vi.fn(async () => ({
      tipo: "4ta", of: "OF1", ruc: "10111111112", nombre: "PEPE",
      periodo_ini: 202401, periodo_fin: 202412,
      contenido_txt: "10111111112|202401|202412|", titulo: "DESCARGA RENTAS DE 4TA_OF OF1",
    })),
    empleadores601: vi.fn(async () => ({ empleadores: [] })),
  },
}));

afterEach(() => vi.clearAllMocks());

test("4ta muestra el resumen y no pide empleador", async () => {
  render(
    <ConfirmarTicketModal
      tipo="4ta"
      row={{ of_devolucion: "OF1", ruc: "10111111112", per_doc: "202412" }}
      onConfirmado={() => {}}
      onCancelar={() => {}}
    />,
  );
  await waitFor(() =>
    expect(screen.getByText(/10111111112\|202401\|202412\|/)).toBeInTheDocument());
  expect(screen.queryByText(/empleador/i)).not.toBeInTheDocument();
});

test("601 sin empleadores en archivo pide RUC y nombre manual", async () => {
  render(
    <ConfirmarTicketModal
      tipo="601"
      row={{ of_devolucion: "OF9", ruc: "10103903980", per_doc: "202512" }}
      onConfirmado={() => {}}
      onCancelar={() => {}}
    />,
  );
  await waitFor(() => expect(mesa_ayuda.empleadores601).toHaveBeenCalled());
  expect(screen.getByLabelText(/RUC del empleador/i)).toBeInTheDocument();
  expect(screen.getByLabelText(/Nombre del empleador/i)).toBeInTheDocument();
});

test("601 limpia el error stale cuando un preview posterior tiene exito", async () => {
  const previewMock = vi.mocked(mesa_ayuda.preview);
  previewMock
    .mockRejectedValueOnce(new Error("fallo de red"))
    .mockResolvedValueOnce({
      tipo: "601", of: "OF9", ruc: "20100039368", nombre: "EMPRESA SA",
      periodo_ini: 202401, periodo_fin: 202412,
      contenido_txt: "20100039368|202401|202412|", titulo: "DESCARGA PDT 601_OF OF9",
    });

  render(
    <ConfirmarTicketModal
      tipo="601"
      row={{ of_devolucion: "OF9", ruc: "10103903980", per_doc: "202512" }}
      onConfirmado={() => {}}
      onCancelar={() => {}}
    />,
  );

  await vi.waitFor(() => expect(mesa_ayuda.empleadores601).toHaveBeenCalled());

  // Primer intento: falla y muestra el error.
  fireEvent.change(screen.getByLabelText(/RUC del empleador/i), {
    target: { value: "20100039368" },
  });
  await vi.waitFor(() => expect(screen.getByText(/fallo de red/)).toBeInTheDocument());

  // Segundo intento (recompute de `extra`): tiene exito y el error stale debe desaparecer.
  fireEvent.change(screen.getByLabelText(/Nombre del empleador/i), {
    target: { value: "EMPRESA SA" },
  });
  await vi.waitFor(() =>
    expect(screen.getByText(/20100039368\|202401\|202412\|/)).toBeInTheDocument());
  expect(screen.queryByText(/fallo de red/)).not.toBeInTheDocument();
  expect(previewMock).toHaveBeenCalledTimes(2);
});

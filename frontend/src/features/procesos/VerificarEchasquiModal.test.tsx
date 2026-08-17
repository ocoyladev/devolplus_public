import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";

import { VerificarEchasquiModal } from "./VerificarEchasquiModal";
import { procesos } from "../../api/acciones";

vi.mock("../../api/acciones", () => ({
  procesos: {
    verificarEchasqui: vi.fn(async () => [
      {
        num_doc: "111", num_dev: "D", num_ruc: "R", nombre: "Ana",
        tipo_exp: "ELECTRONICO",
        echasquis: [
          { denom: "000-URD999-2026-1-1", clasificacion: "VIA_ESPECIAL",
            estado: "subido", subible: false },
          { denom: "000-URD999-2026-2-1", clasificacion: "VIA_ESPECIAL",
            estado: "pendiente_subir", subible: true },
        ],
        sin_echasqui: false, error: "",
      },
    ]),
    subirEchasquiPendientes: vi.fn(async () => "job-1"),
  },
}));

afterEach(() => vi.clearAllMocks());

test("verifica al abrir y sube el pendiente seleccionado", async () => {
  const onJobIniciado = vi.fn();
  render(
    <VerificarEchasquiModal
      filas={[{ num_doc: "111" }]}
      abierto={true}
      onCerrar={() => {}}
      onJobIniciado={onJobIniciado}
      onError={() => {}}
    />,
  );

  await screen.findByText(/000-URD999-2026-2-1/);
  expect(procesos.verificarEchasqui).toHaveBeenCalledWith(["111"]);

  // El pendiente viene marcado por defecto; subir.
  fireEvent.click(screen.getByRole("button", { name: /Subir pendientes/ }));

  await waitFor(() =>
    expect(procesos.subirEchasquiPendientes).toHaveBeenCalledWith([
      { num_doc: "111", num_dev: "D", num_ruc: "R", denom: "000-URD999-2026-2-1" },
    ]),
  );
  await waitFor(() => expect(onJobIniciado).toHaveBeenCalledWith("subir_echasqui"));
});

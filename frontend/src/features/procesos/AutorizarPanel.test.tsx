import { fireEvent, render, screen } from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";

import { AutorizarPanel, construirLineaAutorizar } from "./AutorizarPanel";
import { procesos } from "../../api/acciones";

vi.mock("../../api/acciones", () => ({
  procesos: {
    autorizar: vi.fn(async () => undefined),
    autorizarPreCheck: vi.fn(async () => ({
      conflictos: [{ num_doc: "1", per_doc: "202501", nombre: "Juan", c89: 100 }],
      conflictosC64: [],
    })),
  },
}));

afterEach(() => vi.clearAllMocks());

test("construirLineaAutorizar agrega fec_doc_aso+1 cuando el formulario asociado aplica", () => {
  expect(
    construirLineaAutorizar({
      num_doc: "36486237",
      cod_for_aso: "1662",
      fec_doc_aso: "13/04/2026",
    }),
  ).toBe("36486237|14/04/2026");
});

test("construirLineaAutorizar suma 1 día cruzando fin de mes", () => {
  expect(
    construirLineaAutorizar({
      num_doc: "1",
      cod_for_aso: "1662",
      fec_doc_aso: "30/04/2026",
    }),
  ).toBe("1|01/05/2026");
});

test("construirLineaAutorizar no agrega fecha para cod_for_aso excluidos o vacío", () => {
  for (const cod of ["0709", "1649", "4949", "", undefined]) {
    expect(
      construirLineaAutorizar({
        num_doc: "9",
        cod_for_aso: cod,
        fec_doc_aso: "13/04/2026",
      }),
    ).toBe("9");
  }
});

test("construirLineaAutorizar sin fec_doc_aso utilizable devuelve solo num_doc", () => {
  expect(
    construirLineaAutorizar({ num_doc: "7", cod_for_aso: "1662", fec_doc_aso: "" }),
  ).toBe("7");
});

test("el cuadro se prellena con las fechas calculadas desde las filas", () => {
  render(
    <AutorizarPanel
      seleccion={["36486237", "9"]}
      filas={[
        { num_doc: "36486237", cod_for_aso: "1662", fec_doc_aso: "13/04/2026" },
        { num_doc: "9", cod_for_aso: "0709", fec_doc_aso: "13/04/2026" },
      ]}
      onJobIniciado={() => {}}
      onError={() => {}}
    />,
  );

  fireEvent.click(screen.getByRole("button", { name: "Autorizar" }));
  const textarea = screen.getByLabelText("Casos a autorizar") as HTMLTextAreaElement;
  expect(textarea.value).toBe("36486237|14/04/2026\n9");
});

test("cancelar desde la revisión de conflictos y reabrir no deja estado obsoleto", async () => {
  render(
    <AutorizarPanel seleccion={["1"]} onJobIniciado={() => {}} onError={() => {}} />,
  );

  fireEvent.click(screen.getByRole("button", { name: "Autorizar" }));
  const botonesAutorizar = screen.getAllByRole("button", { name: "Autorizar" });
  fireEvent.click(botonesAutorizar[botonesAutorizar.length - 1]);

  await screen.findByText("Revisar montos antes de autorizar");
  fireEvent.click(screen.getByText("Cancelar"));

  fireEvent.click(screen.getByRole("button", { name: "Autorizar" }));
  expect(screen.getByText("Autorizar casos")).toBeInTheDocument();
  expect(screen.queryByText("Revisar montos antes de autorizar")).not.toBeInTheDocument();
  expect(procesos.autorizarPreCheck).toHaveBeenCalledTimes(1);
});

test("con conflicto C64, Continuar exige elegir corrección (G58 o manual)", async () => {
  (procesos.autorizarPreCheck as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
    conflictos: [],
    conflictosC64: [{ num_doc: "5", per_doc: "202501", nombre: "Ana", g58: 1475 }],
  });

  render(
    <AutorizarPanel seleccion={["5"]} onJobIniciado={() => {}} onError={() => {}} />,
  );

  fireEvent.click(screen.getByRole("button", { name: "Autorizar" }));
  const botones = screen.getAllByRole("button", { name: "Autorizar" });
  fireEvent.click(botones[botones.length - 1]);

  await screen.findByText("Revisar montos antes de autorizar");

  // Elegir "Llenar con G58" habilita Continuar y lo manda como decisión C64.
  fireEvent.click(screen.getByLabelText(/Llenar con G58/));
  const continuar = screen.getByRole("button", { name: "Continuar" });
  expect(continuar).not.toBeDisabled();

  fireEvent.click(continuar);
  expect(procesos.autorizar).toHaveBeenCalledWith(
    ["5"],
    {},
    { "5": { accion: "aplicar_g58", valor: null } },
  );
});

test("con conflicto C64, Monto manual en 0 mantiene Continuar deshabilitado", async () => {
  (procesos.autorizarPreCheck as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
    conflictos: [],
    conflictosC64: [{ num_doc: "9", per_doc: "202501", nombre: "Test", g58: 100 }],
  });

  render(
    <AutorizarPanel seleccion={["9"]} onJobIniciado={() => {}} onError={() => {}} />,
  );

  fireEvent.click(screen.getByRole("button", { name: "Autorizar" }));
  const botones = screen.getAllByRole("button", { name: "Autorizar" });
  fireEvent.click(botones[botones.length - 1]);

  await screen.findByText("Revisar montos antes de autorizar");

  fireEvent.click(screen.getByLabelText(/Monto manual/));
  expect(screen.getByRole("button", { name: "Continuar" })).toBeDisabled();
});

import type { IDoesFilterPassParams, IRowNode } from "ag-grid-community";
import type { CustomFilterProps } from "ag-grid-react";
import { fireEvent, render, screen } from "@testing-library/react";
import { expect, test, vi } from "vitest";

import { ColorFilter } from "./ColorFilter";

type Model = { texto?: string; claves?: string[] };
type Props = CustomFilterProps<Record<string, unknown>, unknown, Model>;

// useGridFilter guarda la callback doesFilterPass; la capturamos para probar la
// lógica de "texto Y color" sin montar toda la grilla.
let doesFilterPass: ((p: IDoesFilterPassParams) => boolean) | null = null;
vi.mock("ag-grid-react", () => ({
  useGridFilter: (h: { doesFilterPass: (p: IDoesFilterPassParams) => boolean }) => {
    doesFilterPass = h.doesFilterPass;
  },
}));

function nodoCon(valor: unknown): IRowNode {
  return { data: { resultado: valor } } as unknown as IRowNode;
}

function renderFiltro(model: Model | null) {
  const onModelChange = vi.fn();
  const props = {
    model,
    onModelChange,
    colDef: { field: "resultado" },
    getValue: (node: IRowNode) => (node.data as { resultado: unknown }).resultado,
  } as unknown as Props;
  render(<ColorFilter {...props} />);
  return onModelChange;
}

test("sin modelo, todas las filas pasan", () => {
  renderFiltro(null);
  expect(doesFilterPass?.({ node: nodoCon("DENEGADO") } as IDoesFilterPassParams)).toBe(true);
});

test("filtra por texto (contiene, sin distinguir mayúsculas)", () => {
  renderFiltro({ texto: "deneg" });
  expect(doesFilterPass?.({ node: nodoCon("DENEGADO") } as IDoesFilterPassParams)).toBe(true);
  expect(doesFilterPass?.({ node: nodoCon("MESA_AYUDA") } as IDoesFilterPassParams)).toBe(false);
});

test("combina texto Y color: debe cumplir ambos", () => {
  // "verde" agrupa DENEGADO/AUTORIZADO…; texto 'auto' + color verde.
  renderFiltro({ texto: "auto", claves: ["verde"] });
  expect(
    doesFilterPass?.({ node: nodoCon("AUTORIZADO TOTAL") } as IDoesFilterPassParams),
  ).toBe(true);
  // color verde pero no contiene 'auto'
  expect(doesFilterPass?.({ node: nodoCon("DENEGADO") } as IDoesFilterPassParams)).toBe(false);
  // contiene 'auto' pero color naranja
  expect(doesFilterPass?.({ node: nodoCon("MESA_AYUDA") } as IDoesFilterPassParams)).toBe(false);
});

test("escribir texto compone el modelo", () => {
  const onModelChange = renderFiltro(null);
  fireEvent.change(screen.getByLabelText("Filtrar por texto"), {
    target: { value: "abc" },
  });
  expect(onModelChange).toHaveBeenCalledWith({ texto: "abc" });
});

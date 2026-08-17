import type { IDoesFilterPassParams, IRowNode } from "ag-grid-community";
import type { CustomFilterProps } from "ag-grid-react";
import { fireEvent, render, screen } from "@testing-library/react";
import { expect, test, vi } from "vitest";

import { CartaFilter } from "./CartaFilter";

type Model = { texto?: string; estados?: string[] };
type Props = CustomFilterProps<Record<string, unknown>, unknown, Model>;

let doesFilterPass: ((p: IDoesFilterPassParams) => boolean) | null = null;
vi.mock("ag-grid-react", () => ({
  useGridFilter: (h: { doesFilterPass: (p: IDoesFilterPassParams) => boolean }) => {
    doesFilterPass = h.doesFilterPass;
  },
}));

function nodo(carta: string, estado: string): IRowNode {
  return { data: { carta, carta_estado: estado } } as unknown as IRowNode;
}

function renderFiltro(model: Model | null) {
  const onModelChange = vi.fn();
  const props = {
    model,
    onModelChange,
    colDef: { field: "carta" },
    getValue: (n: IRowNode) => (n.data as Record<string, unknown>).carta,
  } as unknown as Props;
  render(<CartaFilter {...props} />);
  return onModelChange;
}

test("sin filtro activo pasan todas las filas", () => {
  renderFiltro(null);
  expect(doesFilterPass?.({ node: nodo("78954-2026", "VIGENTE") } as IDoesFilterPassParams)).toBe(true);
});

test("filtra por texto contenido", () => {
  renderFiltro({ texto: "789" });
  expect(doesFilterPass?.({ node: nodo("78954-2026", "VIGENTE") } as IDoesFilterPassParams)).toBe(true);
  expect(doesFilterPass?.({ node: nodo("12-2025", "VIGENTE") } as IDoesFilterPassParams)).toBe(false);
});

test("filtra por estado", () => {
  renderFiltro({ estados: ["VENCIDA"] });
  expect(doesFilterPass?.({ node: nodo("1-2026", "VENCIDA") } as IDoesFilterPassParams)).toBe(true);
  expect(doesFilterPass?.({ node: nodo("1-2026", "VIGENTE") } as IDoesFilterPassParams)).toBe(false);
});

test("texto y estado se combinan con AND", () => {
  renderFiltro({ texto: "789", estados: ["VENCIDA"] });
  expect(doesFilterPass?.({ node: nodo("78954-2026", "VENCIDA") } as IDoesFilterPassParams)).toBe(true);
  expect(doesFilterPass?.({ node: nodo("78954-2026", "VIGENTE") } as IDoesFilterPassParams)).toBe(false);
  expect(doesFilterPass?.({ node: nodo("12-2025", "VENCIDA") } as IDoesFilterPassParams)).toBe(false);
});

test("el caso sin cartas cae en la opción SIN", () => {
  renderFiltro({ estados: ["SIN"] });
  expect(doesFilterPass?.({ node: nodo("", "") } as IDoesFilterPassParams)).toBe(true);
  expect(doesFilterPass?.({ node: nodo("1-2026", "VIGENTE") } as IDoesFilterPassParams)).toBe(false);
});

test("marcar un estado emite el modelo", () => {
  const onModelChange = renderFiltro(null);
  fireEvent.click(screen.getByLabelText("Vencida"));
  expect(onModelChange).toHaveBeenCalledWith({ estados: ["VENCIDA"] });
});

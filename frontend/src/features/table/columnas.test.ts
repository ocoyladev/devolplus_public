import { expect, test } from "vitest";

import { campoDeField, construirColumnas } from "./columnas";
import { CartaFilter } from "./CartaFilter";
import { ColorFilter } from "./ColorFilter";

test("aplica etiquetas conocidas y deja crudas las desconocidas", () => {
  const cols = construirColumnas(["num_doc", "xyz"]);
  expect(cols[0].headerName).toBe("N° DOC");
  expect(cols[1].headerName).toBe("xyz");
});

test("todas las columnas son filtrables y ordenables", () => {
  const cols = construirColumnas(["nombre", "num_doc"]);
  for (const c of cols) {
    expect(c.sortable).toBe(true);
    expect(c.filter).toBe("agTextColumnFilter");
  }
});

test("las columnas con color usan el filtro por color", () => {
  const [resultado] = construirColumnas(["resultado"]);
  expect(resultado.filter).toBe(ColorFilter);
  const [vcto] = construirColumnas(["VctoInd"]);
  expect(vcto.filter).toBe(ColorFilter);
});

test("resultado es editable con dropdown de opciones", () => {
  const [col] = construirColumnas(["resultado"]);
  expect(col.editable).toBe(true);
  expect(col.cellEditor).toBe("agSelectCellEditor");
  expect((col.cellEditorParams as { values: string[] }).values).toContain("DENEGADO");
});

test("carta ya no es editable en la grilla (se edita en el panel)", () => {
  const [col] = construirColumnas(["carta"]);
  expect(col.editable).toBeUndefined();
  expect(col.filter).toBe(CartaFilter);
});

test("campos no editables no son editables", () => {
  const [col] = construirColumnas(["nombre"]);
  expect(col.editable).toBeFalsy();
});

test("modo 'default' usa solo las columnas del Table original, en orden", () => {
  const disponibles = [
    "secreto",
    "num_doc",
    "DESCARGAS",
    "of_devolucion",
    "obs_devol",
    "otro",
  ];
  const cols = construirColumnas(disponibles, "default");
  const headers = cols.map((c) => c.headerName);
  // Respeta el orden del spec (DESCARGAS, OF., N° DOC. …) y excluye 'secreto'/'otro'.
  expect(headers).toEqual(["DESCARGAS", "OF.", "N° DOC.", "Observaciones"]);
});

test("modo 'default' conserva editabilidad de las columnas conocidas", () => {
  const cols = construirColumnas(["resultado", "obs_devol"], "default");
  const resultado = cols.find((c) => c.headerName === "Resultado");
  expect(resultado?.editable).toBe(true);
  expect(resultado?.cellEditor).toBe("agSelectCellEditor");
});

test("columnas de fecha ordenan cronológicamente (no como texto)", () => {
  const [vcto] = construirColumnas(["CalcVctoInd"], "default");
  const cmp = vcto.comparator as (a: unknown, b: unknown) => number;
  expect(typeof cmp).toBe("function");
  expect(cmp("01/01/2026", "02/01/2026")).toBeLessThan(0);
  // textualmente "10/.." < "02/.." pero como fecha 10 ene > 02 ene:
  expect(cmp("10/01/2026", "02/01/2026")).toBeGreaterThan(0);
});

test("RESULTADO tiene relleno de color por estado", () => {
  const [r] = construirColumnas(["resultado"], "default");
  const style = r.cellStyle as (p: { value: unknown }) => unknown;
  expect(style({ value: "DENEGADO" })).toEqual({ backgroundColor: "#C8E6C9" });
  expect(style({ value: "MESA_AYUDA" })).toEqual({ backgroundColor: "#FFE0B2" });
  expect(style({ value: "OTRO" })).toBeNull();
});

test("Observaciones al doble de ancho y aparece FECHA RI", () => {
  const cols = construirColumnas(["obs_devol", "fec_ri"], "default");
  expect(cols.find((c) => c.headerName === "Observaciones")?.width).toBe(450);
  expect(cols.find((c) => c.headerName === "FECHA RI")).toBeDefined();
});

test("campoDeField mapea campos de grilla a campos de la API", () => {
  expect(campoDeField("resultado")).toBe("resultado");
  expect(campoDeField("ind_for_dev")).toBe("forma_dev");
  expect(campoDeField("num_ri")).toBe("ri");
  expect(campoDeField("obs_devol")).toBe("obs");
  expect(campoDeField("nombre")).toBeNull();
});

test("incluye columna Exp. REPOSITORIO no editable al final en modo default", () => {
  const cols = construirColumnas(
    ["num_doc", "resultado", "obs_devol", "exp_repositorio"],
    "default",
    true,
  );
  const exp = cols.find((c) => c.field === "exp_repositorio");
  expect(exp).toBeDefined();
  expect(exp?.headerName).toBe("Exp. REPOSITORIO");
  expect(exp?.width).toBe(450);
  expect(exp?.editable).toBeFalsy();
  // Debe ir después de Observaciones.
  const idxObs = cols.findIndex((c) => c.field === "obs_devol");
  const idxExp = cols.findIndex((c) => c.field === "exp_repositorio");
  expect(idxExp).toBeGreaterThan(idxObs);
});

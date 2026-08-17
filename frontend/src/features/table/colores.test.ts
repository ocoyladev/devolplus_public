import { expect, test } from "vitest";

import {
  colorClaveDe,
  colorCarta,
  opcionesColorDe,
  textoCeldaCarta,
  textoCeldaCartaConReserva,
} from "./colores";

test("clave de color de RESULTADO por grupo", () => {
  expect(colorClaveDe("resultado", "AUTORIZADO TOTAL")).toBe("verde");
  expect(colorClaveDe("resultado", "DENEGADO")).toBe("verde");
  expect(colorClaveDe("resultado", "MESA_AYUDA")).toBe("naranja");
  expect(colorClaveDe("resultado", "")).toBe("sin");
});

test("clave de color de VCTO. IND. según la fecha", () => {
  const hoy = new Date();
  const dd = String(hoy.getDate()).padStart(2, "0");
  const mm = String(hoy.getMonth() + 1).padStart(2, "0");
  const yyyy = hoy.getFullYear();
  expect(colorClaveDe("VctoInd", `${dd}/${mm}/${yyyy}`)).toBe("rojo");
  expect(colorClaveDe("VctoInd", "01/01/2000")).toBe("gris");
  expect(colorClaveDe("VctoInd", "")).toBe("sin");
});

test("opciones de color según la columna", () => {
  expect(opcionesColorDe("resultado").map((o) => o.clave)).toEqual([
    "verde",
    "naranja",
    "sin",
  ]);
  expect(opcionesColorDe("VctoInd").map((o) => o.clave)).toEqual([
    "gris",
    "rojo",
    "naranja",
    "sin",
  ]);
});

test("colorCarta mapea cada estado", () => {
  expect(colorCarta("VENCIDA")).toBe("#FF6142");
  expect(colorCarta("POR_VENCER")).toBe("#FCA797");
  expect(colorCarta("ATENDIDA")).toBe("#C8E6C9");
  expect(colorCarta("VIGENTE")).toBeNull();
  expect(colorCarta("SIN_NOTIFICAR")).toBeNull();
  expect(colorCarta("")).toBeNull();
});

test("textoCeldaCarta agrega el conteo solo cuando hay más de una", () => {
  expect(textoCeldaCarta("78954-2026", 1)).toBe("78954-2026");
  expect(textoCeldaCarta("78954-2026", 2)).toBe("78954-2026 (2)");
  expect(textoCeldaCarta("", 0)).toBe("");
  expect(textoCeldaCarta("", 1)).toBe("s/n");
  expect(textoCeldaCarta("", 3)).toBe("s/n (3)");
});

test("textoCeldaCartaConReserva usa el espejo crudo si carta_vigente está ausente", () => {
  // Falla silenciosa de agregar_columnas_cartas: ni carta_vigente ni carta_n llegaron.
  expect(textoCeldaCartaConReserva(undefined, undefined, "78954-2026, 12-2025")).toBe(
    "78954-2026, 12-2025",
  );
  expect(textoCeldaCartaConReserva(undefined, undefined, "")).toBe("");
});

test("textoCeldaCartaConReserva no usa la reserva cuando las columnas sí llegaron", () => {
  // Caso sin cartas: carta_vigente = "" es el dato correcto, no una falla.
  expect(textoCeldaCartaConReserva("", 0, "")).toBe("");
  expect(textoCeldaCartaConReserva("78954-2026", 1, "78954-2026")).toBe("78954-2026");
});

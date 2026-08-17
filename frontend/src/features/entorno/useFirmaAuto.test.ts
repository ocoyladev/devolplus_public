import { renderHook, waitFor, act } from "@testing-library/react";
import { afterEach, beforeEach, expect, test, vi } from "vitest";

import { useFirmaAuto } from "./useFirmaAuto";
import * as entorno from "../../api/entorno";

beforeEach(() => {
  vi.spyOn(entorno, "fetchFirmaAutoEstado").mockResolvedValue({
    disponible: true,
    escala: 125,
    ancho: 1920,
    alto: 1200,
    motivo: "",
    perfil: "125@1920x1200",
  });
});

afterEach(() => vi.restoreAllMocks());

test("consulta una sola vez al montar", async () => {
  const { result } = renderHook(() => useFirmaAuto());
  await waitFor(() => expect(result.current.disponible).toBe(true));
  expect(entorno.fetchFirmaAutoEstado).toHaveBeenCalledTimes(1);
});

test("no re-consulta ante resize/focus", async () => {
  renderHook(() => useFirmaAuto());
  await waitFor(() => expect(entorno.fetchFirmaAutoEstado).toHaveBeenCalledTimes(1));
  act(() => {
    window.dispatchEvent(new Event("resize"));
    window.dispatchEvent(new Event("focus"));
  });
  expect(entorno.fetchFirmaAutoEstado).toHaveBeenCalledTimes(1);
});

test("recargar re-consulta y resuelve con el estado", async () => {
  const { result } = renderHook(() => useFirmaAuto());
  await waitFor(() => expect(result.current.disponible).toBe(true));
  let devuelto;
  await act(async () => {
    devuelto = await result.current.recargar();
  });
  expect(entorno.fetchFirmaAutoEstado).toHaveBeenCalledTimes(2);
  expect(devuelto).toMatchObject({ disponible: true, perfil: "125@1920x1200" });
});

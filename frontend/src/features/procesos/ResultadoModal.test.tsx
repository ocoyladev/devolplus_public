import { render, screen } from "@testing-library/react";
import { expect, test, vi } from "vitest";

import { ResultadoModal } from "./ResultadoModal";

test("no renderiza nada sin resultado", () => {
  const { container } = render(<ResultadoModal resultado={null} onClose={() => {}} />);
  expect(container).toBeEmptyDOMElement();
});

test("lista los casos OK en verde", () => {
  render(
    <ResultadoModal
      resultado={{ ok: true, mensaje: "listo", okCount: 2, oks: ["D1", "D2"], errores: [] }}
      onClose={vi.fn()}
    />,
  );
  expect(screen.getByText(/completados correctamente/i)).toBeInTheDocument();
  expect(screen.getByText("D1")).toBeInTheDocument();
  expect(screen.getByText("D2")).toBeInTheDocument();
});

test("muestra oks y errores a la vez", () => {
  render(
    <ResultadoModal
      resultado={{
        ok: true, mensaje: "parcial", okCount: 1, oks: ["D1"],
        errores: [{ caso: "D2", motivo: "falló" }],
      }}
      onClose={vi.fn()}
    />,
  );
  expect(screen.getByText("D1")).toBeInTheDocument();
  expect(screen.getByText("D2")).toBeInTheDocument();
  expect(screen.getByText(/falló/)).toBeInTheDocument();
});

test("ok:false sin errores estructurados se muestra en rojo, no en verde", () => {
  render(
    <ResultadoModal
      resultado={{
        ok: false,
        mensaje: "Error en Autorizar: boom",
        errores: [],
        oks: [],
        tituloExito: "Autorizar — completado",
        tituloError: "Autorizar — finalizó con errores",
      }}
      onClose={vi.fn()}
    />,
  );
  expect(screen.getByText("Autorizar — finalizó con errores")).toBeInTheDocument();
  expect(screen.queryByText("Autorizar — completado")).not.toBeInTheDocument();
  expect(screen.queryByText(/Todos los casos se procesaron correctamente/)).not.toBeInTheDocument();
});

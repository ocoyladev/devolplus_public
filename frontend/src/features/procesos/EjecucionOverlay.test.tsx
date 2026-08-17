import { render, screen } from "@testing-library/react";
import { expect, test } from "vitest";

import { EjecucionOverlay } from "./EjecucionOverlay";

test("no renderiza nada sin corrida", () => {
  const { container } = render(<EjecucionOverlay run={null} />);
  expect(container).toBeEmptyDOMElement();
});

test("RSIRAT muestra advertencia de teclado/mouse", () => {
  render(
    <EjecucionOverlay
      run={{ kind: "rsirat_ref", log: ["-> REF.pdf"], done: 1, total: 3, etiqueta: "OF 26001" }}
    />,
  );
  expect(screen.getByText(/NO use el teclado ni el mouse/i)).toBeInTheDocument();
  // El hotkey es el camino fiable con pantalla extendida; la esquina se conserva.
  expect(screen.getByText(/Ctrl\+Shift\+Q/)).toBeInTheDocument();
  expect(screen.getByText(/esquina/i)).toBeInTheDocument();
  expect(screen.getByText("-> REF.pdf")).toBeInTheDocument();
  expect(screen.getByText(/1\/3/)).toBeInTheDocument();
});

test("Autorizar muestra copia neutra (sin advertencia de teclado)", () => {
  render(
    <EjecucionOverlay
      run={{ kind: "autorizar", log: ["Procesando D1"], done: 0, total: 0, etiqueta: "" }}
    />,
  );
  expect(screen.getByText(/no cierre la aplicación/i)).toBeInTheDocument();
  expect(screen.queryByText(/NO use el teclado ni el mouse/i)).not.toBeInTheDocument();
});

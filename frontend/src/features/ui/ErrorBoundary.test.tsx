import { render, screen } from "@testing-library/react";
import { expect, test, vi } from "vitest";

import { ErrorBoundary } from "./ErrorBoundary";

function Explota(): JSX.Element {
  throw new Error("boom");
}

test("muestra fallback cuando un hijo lanza", () => {
  vi.spyOn(console, "error").mockImplementation(() => {});
  render(
    <ErrorBoundary>
      <Explota />
    </ErrorBoundary>,
  );
  expect(screen.getByText(/algo salió mal/i)).toBeInTheDocument();
  expect(screen.getByText(/boom/)).toBeInTheDocument();
  vi.restoreAllMocks();
});

test("renderiza los hijos cuando no hay error", () => {
  render(
    <ErrorBoundary>
      <p>contenido ok</p>
    </ErrorBoundary>,
  );
  expect(screen.getByText("contenido ok")).toBeInTheDocument();
});

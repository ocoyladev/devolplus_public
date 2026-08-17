import { Component, type ErrorInfo, type ReactNode } from "react";

interface Props {
  children: ReactNode;
}

interface State {
  error: Error | null;
}

/**
 * Captura errores de render de todo el árbol y muestra un mensaje legible en
 * lugar de una página en blanco. Facilita diagnosticar fallos en producción.
 */
export class ErrorBoundary extends Component<Props, State> {
  state: State = { error: null };

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  componentDidCatch(error: Error, info: ErrorInfo): void {
    console.error("ErrorBoundary capturó un error:", error, info);
  }

  render(): ReactNode {
    if (this.state.error) {
      return (
        <div className="flex h-screen flex-col items-center justify-center gap-3 bg-slate-50 p-6 text-center">
          <h1 className="text-lg font-semibold text-red-700">Algo salió mal</h1>
          <p className="max-w-lg text-sm text-slate-600">
            La interfaz encontró un error y no pudo continuar. Recargue la aplicación;
            si persiste, comparta el detalle:
          </p>
          <pre className="max-w-lg overflow-auto rounded border border-red-200 bg-red-50 p-3 text-left font-mono text-xs text-red-800">
            {this.state.error.message}
          </pre>
          <button
            onClick={() => window.location.reload()}
            className="rounded bg-slate-800 px-4 py-1.5 text-sm text-white hover:bg-slate-700"
          >
            Recargar
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}

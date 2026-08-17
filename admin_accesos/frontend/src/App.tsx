import { useState } from "react";

import { Logueos } from "./Logueos";
import { Solicitudes } from "./Solicitudes";
import { useAppVersion } from "./version";

type Tab = "solicitudes" | "logueos";

export default function App(): JSX.Element {
  const version = useAppVersion();
  const [tab, setTab] = useState<Tab>("solicitudes");
  const [aviso, setAviso] = useState<string | null>(null);

  function mostrarAviso(m: string): void {
    setAviso(m);
    window.setTimeout(() => setAviso(null), 4000);
  }

  return (
    <div className="flex h-screen flex-col bg-slate-50">
      <header className="flex items-center gap-4 border-b bg-white px-4 py-2 shadow-sm">
        <h1 className="text-lg font-semibold text-slate-800">
          DEVOL+ · Administración de accesos
        </h1>
        <nav className="ml-4 flex gap-1">
          <TabBtn activo={tab === "solicitudes"} onClick={() => setTab("solicitudes")}>
            Solicitudes
          </TabBtn>
          <TabBtn activo={tab === "logueos"} onClick={() => setTab("logueos")}>
            Historial de logueos
          </TabBtn>
        </nav>
      </header>

      {aviso ? (
        <div className="bg-amber-50 px-4 py-1 text-sm text-amber-800">{aviso}</div>
      ) : null}

      <main className="flex-1 overflow-auto p-4">
        {tab === "solicitudes" ? <Solicitudes onAviso={mostrarAviso} /> : <Logueos />}
      </main>

      <footer className="border-t bg-white px-4 py-1 text-center text-xs text-slate-400">
        Diseñado por{" "}
        <a
          href="https://www.linkedin.com/in/ocoyladev"
          target="_blank"
          rel="noreferrer noopener"
          className="font-medium text-blue-600 hover:underline"
          title="Ver perfil de LinkedIn de Oscar Coyla"
        >
          Oscar Arnold Coyla Urquizo
        </a>{" "}

        {version ? (
          <span className="ml-2 font-mono text-slate-300">v{version}</span>
        ) : null}
      </footer>
    </div>
  );
}

function TabBtn({
  activo,
  onClick,
  children,
}: {
  activo: boolean;
  onClick: () => void;
  children: React.ReactNode;
}): JSX.Element {
  return (
    <button
      onClick={onClick}
      className={
        "rounded px-3 py-1 text-sm " +
        (activo ? "bg-blue-600 text-white" : "text-slate-600 hover:bg-slate-100")
      }
    >
      {children}
    </button>
  );
}

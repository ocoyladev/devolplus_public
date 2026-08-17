import { useState } from "react";

import { solicitarAcceso, type AccesoEstado } from "../../api/acceso";
import { AutorLink, TextoAutor } from "../../autor";
import { ManualButton } from "../../ManualButton";
import { useAppVersion } from "../../version";

// Correo institucional obligatorio: usuario@example.org.
const EMAIL_ORG_RE = /^[a-z0-9._%+-]+@acme\.gob\.pe$/i;

interface Props {
  acceso: AccesoEstado;
  onReintentar: () => void;
}

function Marco({ children }: { children: React.ReactNode }): JSX.Element {
  const version = useAppVersion();
  return (
    <div className="flex h-screen items-center justify-center bg-slate-100">
      <div className="w-[440px] rounded-lg border bg-white p-6 shadow">
        <div className="mb-1 flex items-center justify-between">
          <h1 className="text-xl font-semibold text-slate-800">DEVOL+</h1>
          <ManualButton />
        </div>
        {children}
        <p className="mt-4 border-t pt-3 text-center text-xs text-slate-400">
          Diseñado por <AutorLink>Oscar Arnold Coyla Urquizo</AutorLink>
          {version ? (
            <span className="ml-2 font-mono text-slate-300">v{version}</span>
          ) : null}
        </p>
      </div>
    </div>
  );
}

/** Compuerta de acceso: formulario de solicitud, estados y sin conexión. */
export function AccesoScreen({ acceso, onReintentar }: Props): JSX.Element {
  const { estado, usuario_red, mensaje } = acceso;

  if (estado === "no_registrado") {
    return (
      <Marco>
        <FormularioSolicitud usuarioRed={usuario_red} mensaje={mensaje} />
      </Marco>
    );
  }

  if (estado === "sin_conexion") {
    return (
      <Marco>
        <p className="mb-4 text-sm text-slate-600">
        <TextoAutor texto={mensaje} />
      </p>
        <button
          onClick={onReintentar}
          className="w-full rounded bg-blue-600 px-3 py-2 text-sm text-white"
        >
          Reintentar
        </button>
      </Marco>
    );
  }

  // pendiente / rechazado / inactivo
  return (
    <Marco>
      {usuario_red ? (
        <p className="mb-1 text-sm text-slate-700">
          Usuario: <span className="font-mono font-semibold">{usuario_red}</span>
        </p>
      ) : null}
      <p className="mb-4 text-sm text-slate-600">
        <TextoAutor texto={mensaje} />
      </p>
      <button
        onClick={onReintentar}
        className="w-full rounded border px-3 py-2 text-sm hover:bg-slate-100"
      >
        Verificar de nuevo
      </button>
    </Marco>
  );
}

function FormularioSolicitud({
  usuarioRed,
  mensaje,
}: {
  usuarioRed: string;
  mensaje: string;
}): JSX.Element {
  const [nombre, setNombre] = useState("");
  const [email, setEmail] = useState("");
  const [enviando, setEnviando] = useState(false);
  const [resultado, setResultado] = useState<string | null>(null);
  const [enviado, setEnviado] = useState(false);

  const emailValido = EMAIL_ORG_RE.test(email.trim());
  const puedeEnviar = nombre.trim().length > 0 && emailValido;

  async function enviar(): Promise<void> {
    if (!puedeEnviar) return;
    setEnviando(true);
    setResultado(null);
    try {
      const r = await solicitarAcceso(nombre.trim(), email.trim());
      setResultado(r.mensaje);
      setEnviado(r.ok);
    } catch (e) {
      setResultado(String(e));
    } finally {
      setEnviando(false);
    }
  }

  if (enviado) {
    return (
      <>
        <p className="mb-2 text-sm text-green-700">{resultado}</p>
        <p className="text-xs text-slate-500">
          <TextoAutor texto="Oscar Coyla revisará su solicitud. Vuelva a abrir DEVOL+ una vez autorizado." />
        </p>
      </>
    );
  }

  return (
    <>
      <p className="mb-1 text-sm text-slate-700">
        Usuario: <span className="font-mono font-semibold">{usuarioRed}</span>
      </p>
      <p className="mb-4 text-sm text-slate-500">
        <TextoAutor texto={mensaje} />
      </p>
      <label className="mb-1 block text-xs font-medium text-slate-600">
        Nombre completo
      </label>
      <input
        value={nombre}
        onChange={(e) => setNombre(e.target.value)}
        placeholder="Nombres y apellidos"
        className="mb-3 w-full rounded border p-2 text-sm"
        autoFocus
      />
      <label className="mb-1 block text-xs font-medium text-slate-600">
        Correo institucional
      </label>
      <input
        value={email}
        onChange={(e) => setEmail(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter" && puedeEnviar) void enviar();
        }}
        placeholder="correo@example.org"
        className="mb-1 w-full rounded border p-2 text-sm"
        type="email"
      />
      {email.trim() && !emailValido ? (
        <p className="mb-2 text-xs text-red-600">
          El correo debe ser institucional (…@example.org).
        </p>
      ) : (
        <div className="mb-2" />
      )}
      {resultado ? (
        <p className="mb-2 text-sm text-red-600">{resultado}</p>
      ) : null}
      <button
        onClick={() => void enviar()}
        disabled={enviando || !puedeEnviar}
        className="w-full rounded bg-blue-600 px-3 py-2 text-sm text-white disabled:opacity-50"
      >
        {enviando ? "Enviando…" : "Solicitar acceso"}
      </button>
    </>
  );
}
